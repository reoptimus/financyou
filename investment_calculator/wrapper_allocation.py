"""
Contraintes de poids de l'optimiseur : bornes et plafonds de versement des enveloppes.

Chaque euro versé suit l'allocation cible. Le plafond d'une enveloppe borne donc
sa part des versements totaux : ``plafond / versements_totaux``. Les placements
logés dans une même enveloppe partagent cette capacité (voir
:func:`investment_calculator.modules.placement_optimizer.placement_constraints`).

:class:`WeightConstraints` porte ces contraintes linéaires ;
:func:`contribution_capacity` lit le plafond d'une enveloppe dans le régime.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.optimize import linprog

from investment_calculator.tax_regime import TaxRegime

logger = logging.getLogger(__name__)

# Tolérance numérique sur les poids (les solveurs respectent leurs contraintes
# à ~1e-7 près).
TOLERANCE = 1e-7


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
