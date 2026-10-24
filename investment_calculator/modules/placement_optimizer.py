"""
Optimisation de Markowitz sur GSE++ : une allocation entre placements par horizon.

L'entrée est GSE++ (:mod:`investment_calculator.modules.net_returns`) : pour
chaque scénario, le rendement annualisé net de frais et d'impôts de chaque
placement à la durée de détention H. Moyenne et covariance sont lues telles
quelles sur ces rendements, sans correction après coup (ADR 0002, décision 5).

La seule contrainte fiscale qui reste à l'optimiseur est le plafond de
versement des enveloppes : les placements logés dans une même enveloppe
partagent sa capacité. Chaque euro versé suivant l'allocation cible, cette
capacité est une part des versements totaux, ``plafond / versements``.

Équivalent R : ``legacy/R_scripts/gen_alpha_optim.R``, qui produit ``soltot``,
les poids par placement et par horizon, en maximisant l'utilité
moyenne-variance pour une aversion au risque donnée.

Le rééchantillonnage de Michaud (:func:`optimize_horizon_resampled`) porte
``legacy/R_Financyou/MOCA/FCT/Script_Bootstrap_V5_quick.R``. Les scénarios sont
découpés en paquets, l'optimum est calculé sur chaque paquet, puis on fait la
moyenne des poids. Les allocations obtenues varient moins d'un jeu de
scénarios à l'autre et sont plus diversifiées. La traduction fidèle est dans
``tests/reference_r/bootstrap_michaud.py``. Sur un même découpage, le portage
donne les poids du R. Il s'en écarte sur trois points :

1. **Solveur exact.** Le R résout le lagrangien en forme fermée, puis force à
   zéro un poids négatif sans jamais le relâcher : c'est une heuristique. Ici,
   chaque paquet est résolu sous toutes les contraintes du profil (plafonds
   d'enveloppe, actions, obligations), que le R ignorait.
2. **Horizon.** Le R ne lit que la première date du GSE (« pour accélérer »).
   Ici, chaque paquet utilise GSE++ à l'horizon demandé.
3. **Tous les scénarios.** Le R écarte le reste de la division des scénarios
   par le nombre de paquets. Ici, les paquets se partagent tous les scénarios,
   à une unité près.

La moyenne de poids qui respectent chacun les contraintes linéaires respecte
encore ces contraintes : le résultat reste admissible.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from investment_calculator.modules.net_returns import NetReturns, net_return_moments
from investment_calculator.modules.placements import asset_exposures
from investment_calculator.placement_catalog import PlacementCatalog
from investment_calculator.wrapper_allocation import (
    TOLERANCE,
    WeightConstraints,
    contribution_capacity,
)

logger = logging.getLogger(__name__)

__all__ = [
    "OBJECTIVES",
    "HorizonAllocation",
    "OptimizationError",
    "efficient_frontier",
    "optimize_by_horizon",
    "optimize_horizon",
    "optimize_horizon_resampled",
    "placement_constraints",
]

OBJECTIVES = ("mean_variance", "min_volatility", "target_return", "max_sharpe")


class OptimizationError(RuntimeError):
    """Le solveur n'a pas trouvé d'allocation qui respecte les contraintes."""


@dataclass(frozen=True)
class HorizonAllocation:
    """Allocation optimale entre placements pour une durée de détention."""

    horizon: int
    objective: str
    weights: pd.Series
    expected_return: float
    volatility: float


def placement_constraints(
    catalog: PlacementCatalog,
    placement_ids: Sequence[str],
    *,
    total_contributions: float,
    n_periods: int,
    lower: float = 0.0,
    upper: float = 1.0,
    max_equity: float | None = None,
    min_bond: float | None = None,
    existing_contributions: Mapping[str, float] | None = None,
) -> WeightConstraints:
    """
    Bornes de poids, plafonds de versement des enveloppes et contraintes du
    profil (actions au plus, obligations au moins), pour des placements.

    Args:
        catalog: catalogue qui rattache chaque placement à son enveloppe.
        placement_ids: placements, dans l'ordre des colonnes de GSE++.
        total_contributions: versements totaux de l'utilisateur, en euros.
        n_periods: nombre d'années de versement, pour les plafonds annuels.
        lower, upper: bornes communes du poids de chaque placement.
        max_equity: part du portefeuille exposée aux actions, au plus ; ``None``
            pour ne pas contraindre. L'exposition de chaque placement vient de
            :func:`~investment_calculator.modules.placements.asset_exposures`.
        min_bond: part du portefeuille exposée aux obligations, au moins.
        existing_contributions: versements déjà faits, par enveloppe, sur
            l'épargne existante ; ils s'imputent sur les plafonds à vie.

    Raises:
        ValueError: versements nuls ou négatifs, ou contrainte du profil hors de
            [0, 1].
    """
    for name, value in (("max_equity", max_equity), ("min_bond", min_bond)):
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError(
                f"{name} = {value} : une part du portefeuille est comprise entre 0 et 1."
            )
    if total_contributions <= 0:
        raise ValueError(
            f"Les versements totaux doivent être strictement positifs (reçu "
            f"{total_contributions}) : un plafond de versement se rapporte à eux."
        )
    wrappers = [str(catalog.placement(p)["wrapper"]) for p in placement_ids]
    rows: list[np.ndarray] = []
    bounds: list[float] = []
    notes: list[str] = []
    for wrapper_id in dict.fromkeys(wrappers):
        already_paid = (existing_contributions or {}).get(wrapper_id, 0.0)
        capacity = contribution_capacity(catalog.regime, wrapper_id, n_periods, already_paid)
        share = capacity / total_contributions
        if share >= 1.0 - TOLERANCE:
            continue
        rows.append(np.array([1.0 if w == wrapper_id else 0.0 for w in wrappers]))
        # Marge d'un epsilon : un solveur respecte ses contraintes à ~1e-7 près.
        bounds.append(max(share - TOLERANCE, 0.0))
        notes.append(
            f"L'enveloppe {wrapper_id} accepte {_euros(capacity)} sur "
            f"{_euros(total_contributions)} versés, soit {share:.1%} au plus. "
        )
    exposures = asset_exposures(catalog, list(placement_ids))
    if max_equity is not None:
        rows.append(exposures["equity"].to_numpy())
        bounds.append(max(max_equity - TOLERANCE, 0.0))
        notes.append(f"Le profil limite les actions à {max_equity:.0%} du portefeuille. ")
    if min_bond is not None:
        # Au moins min_bond : s'écrit -exposition·w <= -min_bond.
        rows.append(-exposures["bond"].to_numpy())
        bounds.append(-min(min_bond + TOLERANCE, 1.0))
        notes.append(
            f"Le profil demande au moins {min_bond:.0%} d'obligations "
            f"(fonds en euros compté au prorata de son actif). "
        )
    n = len(placement_ids)
    return WeightConstraints(
        asset_names=tuple(placement_ids),
        lower=np.full(n, float(lower)),
        upper=np.full(n, float(upper)),
        a_ub=np.vstack(rows) if rows else np.zeros((0, n)),
        b_ub=np.array(bounds),
        explanation="".join(notes),
    )


def _euros(amount: float) -> str:
    return f"{amount:,.0f} €".replace(",", " ")


def _solve(
    objective_fn: Callable[[np.ndarray], float],
    constraints: WeightConstraints,
    label: str,
    extra: list[dict[str, object]] | None = None,
) -> np.ndarray:
    result = minimize(
        objective_fn,
        constraints.feasible_start(),
        method="SLSQP",
        bounds=constraints.bounds,
        constraints=constraints.slsqp_constraints() + (extra or []),
        options={"ftol": 1e-12, "maxiter": 500},
    )
    weights = np.asarray(result.x)
    if not result.success or not constraints.is_feasible(weights, tol=1e-6):
        raise OptimizationError(
            f"L'optimisation {label} n'a pas abouti ({result.message}). "
            f"{constraints.explanation}"
            "Changez d'objectif, assouplissez les bornes de poids, ou ajoutez un "
            "placement dans une enveloppe sans plafond."
        )
    return weights


def optimize_horizon(
    net: NetReturns,
    horizon: int,
    constraints: WeightConstraints,
    *,
    objective: str = "mean_variance",
    risk_aversion: float | None = None,
    target_return: float | None = None,
    risk_free_rate: float | None = None,
) -> HorizonAllocation:
    """
    Allocation optimale à l'horizon H, sur les moments de GSE++.

    Objectifs :

    - ``mean_variance`` : maximise ``w·μ − (λ/2) w'Σw`` (``risk_aversion`` = λ),
      comme ``gen_alpha_optim.R`` ;
    - ``min_volatility`` : variance minimale ;
    - ``target_return`` : variance minimale à rendement net ``target_return`` ;
    - ``max_sharpe`` : ratio de Sharpe maximal au-dessus de ``risk_free_rate``.

    Le paramètre propre à l'objectif n'a pas de valeur par défaut : c'est un
    choix de l'utilisateur, pas du code.

    Raises:
        ValueError: objectif inconnu, paramètre manquant, ou placements de
            ``constraints`` différents de ceux de GSE++.
        OptimizationError: le solveur n'aboutit pas.
    """
    if list(constraints.asset_names) != net.placement_ids:
        raise ValueError(
            f"Les contraintes portent sur {list(constraints.asset_names)}, GSE++ sur "
            f"{net.placement_ids}. Construisez-les avec placement_constraints("
            "catalog, net.placement_ids, ...)."
        )
    mean_s, cov_df = net_return_moments(net, horizon)
    mu, cov = mean_s.to_numpy(), cov_df.to_numpy()

    def variance(w: np.ndarray) -> float:
        return float(w @ cov @ w)

    label = f"{objective} (H={horizon})"
    if objective == "mean_variance":
        lam = _required_param(risk_aversion, "risk_aversion", objective)
        weights = _solve(lambda w: -(float(w @ mu) - 0.5 * lam * variance(w)), constraints, label)
    elif objective == "min_volatility":
        weights = _solve(variance, constraints, label)
    elif objective == "target_return":
        target = _required_param(target_return, "target_return", objective)
        extra: list[dict[str, object]] = [
            {"type": "eq", "fun": lambda w: float(w @ mu) - target}
        ]
        weights = _solve(variance, constraints, label, extra)
    elif objective == "max_sharpe":
        rf = _required_param(risk_free_rate, "risk_free_rate", objective)

        def neg_sharpe(w: np.ndarray) -> float:
            sd = np.sqrt(max(variance(w), 1e-18))
            return float(-(float(w @ mu) - rf) / sd)

        weights = _solve(neg_sharpe, constraints, label)
    else:
        raise ValueError(f"Objectif {objective!r} inconnu. Objectifs disponibles : {OBJECTIVES}.")

    allocation = HorizonAllocation(
        horizon=horizon,
        objective=objective,
        weights=pd.Series(weights, index=net.placement_ids),
        expected_return=float(weights @ mu),
        volatility=float(np.sqrt(max(variance(weights), 0.0))),
    )
    logger.info(
        "Allocation %s : rendement net %.4f, volatilité %.4f", label,
        allocation.expected_return, allocation.volatility,
    )
    return allocation


def _required_param(value: float | None, name: str, objective: str) -> float:
    if value is None:
        raise ValueError(f"L'objectif {objective!r} demande le paramètre {name}.")
    return float(value)


def optimize_horizon_resampled(
    net: NetReturns,
    horizon: int,
    constraints: WeightConstraints,
    *,
    n_batches: int,
    objective: str = "mean_variance",
    risk_aversion: float | None = None,
    target_return: float | None = None,
    risk_free_rate: float | None = None,
) -> HorizonAllocation:
    """
    Allocation à l'horizon H rééchantillonnée à la Michaud : moyenne des optima
    calculés sur ``n_batches`` paquets de scénarios consécutifs.

    Le rendement et la volatilité rendus sont ceux des poids moyens, sur tous
    les scénarios. Les paramètres de l'objectif sont ceux de :func:`optimize_horizon`.

    Raises:
        ValueError: moins d'un paquet, ou paquets de moins de deux scénarios
            (la covariance d'un paquet n'est alors pas définie).
        OptimizationError: le solveur n'aboutit pas sur un paquet ; le message
            nomme le paquet.
    """
    n_scenarios = len(net.scenario_ids)
    if n_batches < 1:
        raise ValueError(f"n_batches = {n_batches} : il faut au moins un paquet.")
    if n_scenarios // n_batches < 2:
        raise ValueError(
            f"{n_scenarios} scénarios pour {n_batches} paquets : chaque paquet doit en "
            f"compter au moins deux. Réduisez n_batches à {max(n_scenarios // 2, 1)} au plus."
        )
    if horizon not in net.horizons:
        raise ValueError(f"Horizon {horizon} non calculé. Horizons disponibles : {net.horizons}.")
    h = net.horizons.index(horizon)
    batches = np.array_split(np.arange(n_scenarios), n_batches)
    weights = []
    for number, rows in enumerate(batches, start=1):
        batch = NetReturns(
            multiples=net.multiples[rows][:, [h], :],
            scenario_ids=[net.scenario_ids[i] for i in rows],
            horizons=[horizon],
            placement_ids=net.placement_ids,
        )
        try:
            allocation = optimize_horizon(
                batch, horizon, constraints, objective=objective,
                risk_aversion=risk_aversion, target_return=target_return,
                risk_free_rate=risk_free_rate,
            )
        except OptimizationError as error:
            raise OptimizationError(
                f"Paquet {number} sur {n_batches} ({len(rows)} scénarios) : {error}"
            ) from error
        weights.append(allocation.weights.to_numpy())
    mean_weights = np.mean(weights, axis=0)
    mean_s, cov_df = net_return_moments(net, horizon)
    mu, cov = mean_s.to_numpy(), cov_df.to_numpy()
    resampled = HorizonAllocation(
        horizon=horizon,
        objective=objective,
        weights=pd.Series(mean_weights, index=net.placement_ids),
        expected_return=float(mean_weights @ mu),
        volatility=float(np.sqrt(max(float(mean_weights @ cov @ mean_weights), 0.0))),
    )
    logger.info(
        "Allocation %s (H=%d) rééchantillonnée sur %d paquets : rendement net %.4f, "
        "volatilité %.4f", objective, horizon, n_batches, resampled.expected_return,
        resampled.volatility,
    )
    return resampled


def optimize_by_horizon(
    net: NetReturns,
    constraints: WeightConstraints,
    horizons: Sequence[int] | None = None,
    *,
    objective: str = "mean_variance",
    risk_aversion: float | None = None,
    target_return: float | None = None,
    risk_free_rate: float | None = None,
    n_batches: int | None = None,
) -> pd.DataFrame:
    """
    Poids optimaux par placement (lignes) et par horizon (colonnes).

    C'est l'équivalent de ``soltot`` dans ``gen_alpha_optim.R``. Les paramètres
    de l'objectif sont ceux de :func:`optimize_horizon`. Avec ``n_batches``,
    chaque horizon est rééchantillonné à la Michaud
    (:func:`optimize_horizon_resampled`).
    """
    selected = list(horizons) if horizons is not None else net.horizons
    params: dict[str, float | None] = {
        "risk_aversion": risk_aversion,
        "target_return": target_return,
        "risk_free_rate": risk_free_rate,
    }
    columns = {
        h: (
            optimize_horizon(net, h, constraints, objective=objective, **params)
            if n_batches is None
            else optimize_horizon_resampled(
                net, h, constraints, n_batches=n_batches, objective=objective, **params
            )
        ).weights
        for h in selected
    }
    return pd.DataFrame(columns)


def efficient_frontier(
    net: NetReturns,
    horizon: int,
    constraints: WeightConstraints,
    *,
    n_points: int = 20,
) -> pd.DataFrame:
    """
    Frontière efficiente à l'horizon H : volatilité minimale pour des rendements
    nets cibles, du portefeuille de variance minimale au rendement maximal
    atteignable sous les contraintes.

    Un point que le solveur n'atteint pas est omis et journalisé, jamais
    remplacé par une valeur approchée.

    Returns:
        Un tableau aux colonnes ``return`` et ``volatility``, trié par rendement.
    """
    if n_points < 2:
        raise ValueError(f"La frontière demande au moins 2 points (reçu {n_points}).")
    mean_s, _ = net_return_moments(net, horizon)
    low = optimize_horizon(net, horizon, constraints, objective="min_volatility")
    _, high = constraints.return_range(mean_s.to_numpy())
    points = [(low.expected_return, low.volatility)]
    for target in np.linspace(low.expected_return, high, n_points)[1:]:
        try:
            allocation = optimize_horizon(
                net, horizon, constraints, objective="target_return", target_return=target
            )
        except OptimizationError as error:
            logger.warning("Point de frontière %.4f omis : %s", target, error)
            continue
        points.append((allocation.expected_return, allocation.volatility))
    return pd.DataFrame(points, columns=["return", "volatility"])
