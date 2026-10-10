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
moyenne-variance pour une aversion au risque donnée. Le rééchantillonnage de
Michaud n'est pas encore porté (``Script_Bootstrap_V5_quick.R`` manque au dépôt).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from investment_calculator.modules.net_returns import NetReturns, net_return_moments
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
) -> WeightConstraints:
    """
    Bornes de poids et plafonds de versement des enveloppes, pour des placements.

    Args:
        catalog: catalogue qui rattache chaque placement à son enveloppe.
        placement_ids: placements, dans l'ordre des colonnes de GSE++.
        total_contributions: versements totaux de l'utilisateur, en euros.
        n_periods: nombre d'années de versement, pour les plafonds annuels.
        lower, upper: bornes communes du poids de chaque placement.

    Raises:
        ValueError: versements nuls ou négatifs.
    """
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
        capacity = contribution_capacity(catalog.regime, wrapper_id, n_periods)
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


def optimize_by_horizon(
    net: NetReturns,
    constraints: WeightConstraints,
    horizons: Sequence[int] | None = None,
    *,
    objective: str = "mean_variance",
    risk_aversion: float | None = None,
    target_return: float | None = None,
    risk_free_rate: float | None = None,
) -> pd.DataFrame:
    """
    Poids optimaux par placement (lignes) et par horizon (colonnes).

    C'est l'équivalent de ``soltot`` dans ``gen_alpha_optim.R``. Les paramètres
    de l'objectif sont ceux de :func:`optimize_horizon`.
    """
    selected = list(horizons) if horizons is not None else net.horizons
    columns = {
        h: optimize_horizon(
            net, h, constraints, objective=objective, risk_aversion=risk_aversion,
            target_return=target_return, risk_free_rate=risk_free_rate,
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
