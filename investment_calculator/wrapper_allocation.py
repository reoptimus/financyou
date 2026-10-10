"""
Contraintes d'enveloppe de l'optimiseur : éligibilité et plafonds de versement.

Un actif n'est pas imposé en soi : il l'est au sein d'une enveloppe (PEA,
assurance-vie, PER, CTO...). Chaque enveloppe n'accepte que certaines classes
d'actifs (``eligible_assets`` du régime fiscal) et certaines ont un plafond de
versement cumulé (``contribution_limit``, 150 000 € pour le PEA). Une allocation
qui l'ignore est irréalisable.

Ce module traduit ces règles en contraintes linéaires sur les poids du
portefeuille et place ensuite l'allocation optimale dans les enveloppes.

Ce que les contraintes expriment
--------------------------------
Chaque euro versé suit l'allocation cible. Le plafond d'une enveloppe borne donc
sa part des versements totaux : ``plafond / versements_totaux``. Les actifs
placés dans des enveloppes plafonnées partagent cette capacité. L'allocation
est réalisable si et seulement si, pour tout sous-ensemble S d'actifs, le poids
total de S ne dépasse pas la capacité cumulée des enveloppes qui peuvent
accueillir au moins un actif de S (théorème de Gale pour un problème de
transport). C'est cette famille de conditions, finie, qui est imposée à
l'optimiseur.

Ce que ce module ne fait pas
----------------------------
Le placement dans les enveloppes n'est **pas optimisé fiscalement** : le moteur
fiscal calcule encore les rendements après impôt par type de compte, pas par
enveloppe du régime. Le placement suit un ordre de priorité (enveloppes
plafonnées d'abord) qui garantit seulement la réalisabilité.
"""

from __future__ import annotations

import itertools
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from investment_calculator.tax_regime import TaxRegime, load_regime

logger = logging.getLogger(__name__)

# Tolérance numérique sur les poids (les solveurs respectent leurs contraintes
# à ~1e-7 près).
TOLERANCE = 1e-7

# Au-delà, l'énumération des sous-ensembles d'actifs (2^n) devient coûteuse.
MAX_ASSETS = 12

# Classes d'actifs du régime fiscal que chaque actif simulé peut prendre. Un
# actif peut être détenu dans une enveloppe dès que l'une de ses classes figure
# dans les ``eligible_assets`` de l'enveloppe.
#   stock       : indice actions diversifié, détenu via des ETF éligibles au PEA
#                 (décision de l'utilisateur du 2026-10-07) ;
#   bond        : obligations ;
#   real_estate : immobilier détenu en direct, pas de parts de fonds immobilier.
DEFAULT_ASSET_CLASSES: dict[str, tuple[str, ...]] = {
    "stock": ("etf", "etf_eu"),
    "bond": ("bond",),
    "real_estate": ("real_estate",),
}


class InfeasibleConstraintsError(ValueError):
    """Aucune allocation ne respecte toutes les contraintes."""


@dataclass(frozen=True)
class WeightConstraints:
    """
    Contraintes sur le vecteur de poids ``w`` : ``lower <= w <= upper``,
    ``sum(w) == 1`` et ``a_ub @ w <= b_ub``.
    """

    asset_names: tuple[str, ...]
    lower: np.ndarray
    upper: np.ndarray
    a_ub: np.ndarray
    b_ub: np.ndarray
    explanation: str = ""

    @property
    def n_assets(self) -> int:
        return len(self.asset_names)

    @property
    def bounds(self) -> list[tuple[float, float]]:
        return list(zip(self.lower.tolist(), self.upper.tolist(), strict=True))

    def slsqp_constraints(self) -> list[dict[str, Any]]:
        """Contraintes au format de ``scipy.optimize.minimize`` (SLSQP)."""
        constraints: list[dict[str, Any]] = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0, "jac": lambda w: np.ones_like(w)}
        ]
        if len(self.b_ub):
            a_ub, b_ub = self.a_ub, self.b_ub
            constraints.append({
                "type": "ineq",
                "fun": lambda w: b_ub - a_ub @ w,
                "jac": lambda w: -a_ub,
            })
        return constraints

    def is_feasible(self, weights: np.ndarray, tol: float = TOLERANCE) -> bool:
        """Les poids respectent-ils toutes les contraintes, à ``tol`` près ?"""
        w = np.asarray(weights, dtype=float)
        return bool(
            abs(w.sum() - 1.0) <= tol
            and (w >= self.lower - tol).all()
            and (w <= self.upper + tol).all()
            and (not len(self.b_ub) or (self.a_ub @ w <= self.b_ub + tol).all())
        )

    def _linprog(self, cost: np.ndarray) -> np.ndarray | None:
        """Minimise ``cost @ w`` sous les contraintes ; ``None`` si infaisable."""
        result = linprog(
            cost,
            A_ub=self.a_ub if len(self.b_ub) else None,
            b_ub=self.b_ub if len(self.b_ub) else None,
            A_eq=np.ones((1, self.n_assets)),
            b_eq=np.array([1.0]),
            bounds=self.bounds,
            method="highs",
        )
        return np.asarray(result.x) if result.success else None

    def feasible_start(self) -> np.ndarray:
        """
        Point de départ réalisable : l'équipondération si elle respecte les
        contraintes, sinon un sommet du polytope.

        Raises:
            InfeasibleConstraintsError: aucune allocation n'est réalisable.
        """
        equal = np.full(self.n_assets, 1.0 / self.n_assets)
        if self.is_feasible(equal):
            return equal
        point = self._linprog(np.zeros(self.n_assets))
        if point is None:
            raise InfeasibleConstraintsError(
                "Aucune allocation ne respecte à la fois les bornes de poids, "
                "l'éligibilité des enveloppes et leurs plafonds de versement. "
                f"{self.explanation}"
                "Ajoutez une enveloppe sans plafond qui accepte ces actifs, "
                "ou assouplissez les bornes de poids."
            )
        return point

    def maximize(self, values: np.ndarray) -> np.ndarray:
        """Poids maximisant ``values @ w`` sous les contraintes (programme linéaire)."""
        self.feasible_start()  # lève une erreur claire si infaisable
        point = self._linprog(-np.asarray(values, dtype=float))
        if point is None:  # pragma: no cover - feasible_start a déjà validé
            raise InfeasibleConstraintsError("Programme linéaire infaisable.")
        return point

    def return_range(self, mean_returns: np.ndarray) -> tuple[float, float]:
        """Rendements minimal et maximal atteignables sous les contraintes."""
        high = float(mean_returns @ self.maximize(mean_returns))
        low = float(mean_returns @ self.maximize(-mean_returns))
        return low, high


@dataclass(frozen=True)
class WrapperRules:
    """Règles d'enveloppe résolues pour un jeu d'actifs et un volume de versements."""

    regime_id: str
    asset_names: tuple[str, ...]
    available: tuple[str, ...]
    eligible: dict[str, tuple[str, ...]]  # actif -> enveloppes pouvant le détenir
    capacity_share: dict[str, float]  # enveloppe -> part max des versements (inf = sans plafond)
    capacity_amount: dict[str, float]  # enveloppe -> plafond de versement en euros (inf = aucun)
    priority: tuple[str, ...]
    total_contributions: float

    def hall_constraints(self) -> tuple[np.ndarray, np.ndarray]:
        """Une inégalité par sous-ensemble d'actifs dont la capacité est inférieure à 1."""
        n = len(self.asset_names)
        rows, bounds = [], []
        for size in range(1, n + 1):
            for subset in itertools.combinations(range(n), size):
                wrappers = {w for i in subset for w in self.eligible[self.asset_names[i]]}
                capacity = sum(self.capacity_share[w] for w in wrappers)
                if capacity < 1.0 - TOLERANCE:
                    row = np.zeros(n)
                    row[list(subset)] = 1.0
                    rows.append(row)
                    # Marge d'un epsilon : les solveurs respectent leurs
                    # contraintes à ~1e-7 près, et le placement ne doit pas
                    # dépasser un plafond.
                    bounds.append(max(capacity - TOLERANCE, 0.0))
        if not rows:
            return np.zeros((0, n)), np.zeros(0)
        return np.vstack(rows), np.array(bounds)

    def explain(self) -> str:
        """Diagnostic lisible des causes d'infaisabilité."""
        lines = []
        for asset in self.asset_names:
            if not self.eligible[asset]:
                lines.append(
                    f"L'actif {asset!r} ne peut être détenu dans aucune des enveloppes "
                    f"disponibles ({', '.join(self.available)}). "
                )
        capacity = sum(
            self.capacity_share[w] for w in self.available
        )
        if capacity < 1.0:
            capped = ", ".join(
                f"{w} {self.capacity_amount[w]:,.0f} €".replace(",", " ")
                for w in self.available if np.isfinite(self.capacity_amount[w])
            )
            lines.append(
                f"Les plafonds de versement ({capped}) ne couvrent que "
                f"{capacity:.1%} des versements totaux de "
                f"{self.total_contributions:,.0f} €. ".replace(",", " ")
            )
        return "".join(lines)


def _finite_or_inf(value: float | None) -> float:
    return float("inf") if value is None else float(value)


def contribution_capacity(regime: TaxRegime, wrapper_id: str, n_periods: int) -> float:
    """
    Versements cumulés qu'une enveloppe accepte sur ``n_periods`` années, en euros.

    ``inf`` pour une enveloppe sans plafond ; un plafond annuel est multiplié
    par le nombre d'années.

    Raises:
        ValueError: période de plafond inconnue du code.
    """
    wrapper = regime.wrapper(wrapper_id)
    limit = wrapper.get("contribution_limit")
    if limit is None:
        return float("inf")
    period = wrapper.get("contribution_limit_period", "lifetime")
    if period == "lifetime":
        return float(limit)
    if period == "annual":
        return float(limit) * n_periods
    raise ValueError(
        f"Période de plafond {period!r} non gérée pour l'enveloppe "
        f"{wrapper_id!r} (attendu : 'lifetime' ou 'annual')."
    )


def build_wrapper_rules(
    regime: TaxRegime,
    asset_names: Sequence[str],
    *,
    total_contributions: float,
    n_periods: int,
    available_wrappers: Sequence[str] | None = None,
    asset_classes: Mapping[str, Sequence[str]] | None = None,
    wrapper_priority: Sequence[str] | None = None,
) -> WrapperRules:
    """
    Résoudre l'éligibilité et les capacités des enveloppes d'un régime.

    Args:
        regime: régime fiscal fournissant les enveloppes.
        asset_names: actifs du portefeuille (colonnes des rendements).
        total_contributions: somme des versements sur l'horizon, en euros.
        n_periods: nombre de périodes (années) de l'horizon.
        available_wrappers: enveloppes que l'utilisateur peut ouvrir ; par défaut
            toutes celles du régime.
        asset_classes: classes d'actifs du régime que chaque actif peut prendre ;
            par défaut ``DEFAULT_ASSET_CLASSES``.
        wrapper_priority: ordre de remplissage des enveloppes ; par défaut les
            enveloppes plafonnées d'abord, puis l'ordre du régime.

    Raises:
        ValueError: enveloppe inconnue, actif sans classe, plafond d'une période
            non gérée, ou trop d'actifs.
    """
    if len(asset_names) > MAX_ASSETS:
        raise ValueError(
            f"{len(asset_names)} actifs : les contraintes d'enveloppe énumèrent les "
            f"sous-ensembles d'actifs et sont limitées à {MAX_ASSETS} actifs."
        )
    if total_contributions <= 0:
        raise ValueError(
            "Les versements totaux sont nuls : impossible de rapporter un plafond "
            "de versement à une part du portefeuille. Renseignez investment_time_series."
        )

    available = tuple(available_wrappers) if available_wrappers else tuple(regime.wrapper_ids)
    for wrapper_id in available:
        regime.wrapper(wrapper_id)  # lève KeyError avec la liste des enveloppes connues

    classes = {**DEFAULT_ASSET_CLASSES, **{k: tuple(v) for k, v in (asset_classes or {}).items()}}
    missing = [a for a in asset_names if a not in classes]
    if missing:
        raise ValueError(
            f"Aucune classe d'actifs du régime pour {missing}. Fournissez "
            "wrapper_constraints['asset_classes'] = {actif: [classes du régime]}."
        )

    eligible: dict[str, tuple[str, ...]] = {}
    for asset in asset_names:
        holders = {w for c in classes[asset] for w in regime.eligible_wrappers(c)}
        eligible[asset] = tuple(w for w in available if w in holders)

    capacity_amount: dict[str, float] = {}
    capacity_share: dict[str, float] = {}
    for wrapper_id in available:
        amount = contribution_capacity(regime, wrapper_id, n_periods)
        capacity_amount[wrapper_id] = amount
        capacity_share[wrapper_id] = amount / total_contributions

    if wrapper_priority is not None:
        unknown = [w for w in wrapper_priority if w not in available]
        if unknown:
            raise ValueError(
                f"wrapper_priority cite des enveloppes indisponibles : {unknown}. "
                f"Disponibles : {list(available)}."
            )
        rest = tuple(w for w in available if w not in wrapper_priority)
        priority = tuple(wrapper_priority) + rest
    else:
        # sorted est stable : à plafonnement égal, l'ordre du régime est conservé.
        priority = tuple(sorted(available, key=lambda w: np.isinf(capacity_amount[w])))

    return WrapperRules(
        regime_id=regime.id,
        asset_names=tuple(asset_names),
        available=available,
        eligible=eligible,
        capacity_share=capacity_share,
        capacity_amount=capacity_amount,
        priority=priority,
        total_contributions=float(total_contributions),
    )


def place_in_wrappers(
    weights: Mapping[str, float],
    rules: WrapperRules,
    *,
    net_multiples: Mapping[tuple[str, str], float] | None = None,
) -> pd.DataFrame:
    """
    Placer une allocation dans les enveloppes, en respectant éligibilité et plafonds.

    Programme linéaire à poids fixés. Sans ``net_multiples``, on remplit en
    priorité les enveloppes d'ordre de priorité le plus bas : le résultat est
    réalisable, pas optimal fiscalement. Avec ``net_multiples`` (patrimoine net
    final par euro versé de chaque couple ``(actif, enveloppe)``), on maximise le
    patrimoine net attendu, sous les mêmes contraintes.

    Returns:
        DataFrame ``asset, wrapper, share_of_contributions, amount`` : part des
        versements et montant en euros de chaque couple (actif, enveloppe).

    Raises:
        InfeasibleConstraintsError: l'allocation ne tient pas dans les enveloppes.
    """
    assets = list(rules.asset_names)
    w = np.clip(np.array([weights[a] for a in assets], dtype=float), 0.0, None)
    pairs = [(i, wrapper) for i, a in enumerate(assets) for wrapper in rules.eligible[a]]
    if net_multiples is None:
        rank = {wrapper: r for r, wrapper in enumerate(rules.priority)}
        cost = np.array([rank[wrapper] for _, wrapper in pairs], dtype=float)
    else:
        # Un actif de poids nul n'est placé nulle part : son multiple est sans effet.
        missing = [
            (assets[i], wr) for i, wr in pairs
            if w[i] > 0 and (assets[i], wr) not in net_multiples
        ]
        if missing:
            raise ValueError(
                f"net_multiples ne couvre pas les couples (actif, enveloppe) {missing}. "
                "Calculez un multiple pour chaque couple éligible."
            )
        cost = -np.array(
            [net_multiples.get((assets[i], wr), 0.0) for i, wr in pairs], dtype=float
        )

    a_eq = np.zeros((len(assets), len(pairs)))
    for k, (i, _) in enumerate(pairs):
        a_eq[i, k] = 1.0

    capped = [x for x in rules.available if np.isfinite(rules.capacity_share[x])]
    a_ub = np.zeros((len(capped), len(pairs)))
    for r, wrapper in enumerate(capped):
        for k, (_, wk) in enumerate(pairs):
            if wk == wrapper:
                a_ub[r, k] = 1.0
    b_ub = np.array([rules.capacity_share[x] for x in capped])

    result = linprog(
        cost,
        A_ub=a_ub if capped else None,
        b_ub=b_ub if capped else None,
        A_eq=a_eq,
        b_eq=w,
        bounds=(0, None),
        method="highs",
    )
    if not result.success:
        raise InfeasibleConstraintsError(
            "L'allocation optimale ne tient pas dans les enveloppes disponibles. "
            f"{rules.explain()}"
        )

    shares = np.asarray(result.x)
    # Les solveurs respectent leurs contraintes à ~1e-7 près : on ramène chaque
    # enveloppe plafonnée à son plafond, ce qui ne retire que cet écart.
    for wrapper in capped:
        idx = [k for k, (_, wk) in enumerate(pairs) if wk == wrapper]
        total = shares[idx].sum()
        if total > rules.capacity_share[wrapper] > 0:
            shares[idx] *= rules.capacity_share[wrapper] / total

    rows = [
        {
            "asset": assets[i],
            "wrapper": wrapper,
            "share_of_contributions": float(share),
            "amount": float(share * rules.total_contributions),
        }
        for (i, wrapper), share in zip(pairs, shares, strict=True)
        if share > 1e-12
    ]
    return pd.DataFrame(rows, columns=["asset", "wrapper", "share_of_contributions", "amount"])


def total_contributions_of(flows: np.ndarray) -> float:
    """Versements totaux : mise initiale et versements positifs, sans les retraits."""
    return float(np.clip(flows, 0.0, None).sum())


def regime_from_config(config: Mapping[str, Any]) -> TaxRegime:
    """Régime d'une configuration ``wrapper_constraints`` (objet, ou pays et millésime)."""
    regime = config.get("regime")
    if isinstance(regime, TaxRegime):
        return regime
    return load_regime(str(config.get("country", "FR")), config.get("fiscal_year"))
