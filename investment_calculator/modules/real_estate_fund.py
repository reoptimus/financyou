"""
Parts de fonds immobilier détenues en direct (SCPI) : revenus distribués et lots.

Une part de SCPI détenue en direct verse chaque année des revenus fonciers,
imposés au barème du foyer et aux prélèvements sociaux. Les revenus nets
d'impôt sont réinvestis en nouvelles parts, qui paient à leur tour les frais
d'entrée : chaque réinvestissement est un nouveau lot, avec sa date
d'acquisition. À la cession, chaque lot reçoit l'abattement de son ancienneté
(:func:`~investment_calculator.wrapper_tax.real_estate_liquidation_tax`).

Le rendement total de la série (``real_estate_return``, déjà net des frais
annuels) contient les revenus distribués : une part existante ne s'apprécie que
du rendement total diminué de sa distribution.

Aucune valeur fiscale ni hypothèse de marché n'est écrite ici : le taux
d'imposition des revenus est passé par l'appelant (tranche marginale du foyer
et taux social du régime), le taux de distribution vient des hypothèses de
marché.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from investment_calculator.wrapper_tax import RealEstateLot

__all__ = ["DistributingPosition", "project_distributing"]


@dataclass(frozen=True)
class DistributingPosition:
    """
    Une position en parts de SCPI, année par année, scénario par scénario.

    Attributes:
        value: valeur des parts en fin d'année, [scénarios, années + 1].
        purchases: prix payé pour le lot acquis à chaque date, frais compris,
            [scénarios, années + 1] : versements et revenus nets réinvestis.
        price_index: indice cumulé du prix d'une part, 1 à la date 0.
        income_tax: impôt sur les revenus distribués payé chaque année.
        entry_fee: frais d'entrée de chaque achat de parts.
        initial_cost: prix d'acquisition de parts déjà détenues à la date 0.
        initial_years: ancienneté de ces parts à la date 0.
    """

    value: np.ndarray = field(repr=False)
    purchases: np.ndarray = field(repr=False)
    price_index: np.ndarray = field(repr=False)
    income_tax: np.ndarray = field(repr=False)
    entry_fee: float
    initial_value: float
    initial_cost: float
    initial_years: float

    def lots(self, horizon: int, scale: float = 1.0) -> list[RealEstateLot]:
        """Lots détenus à la cession en ``horizon``, montants multipliés par ``scale``."""
        growth_to_horizon = self.price_index[:, [horizon]] / self.price_index[:, : horizon + 1]
        lots = []
        if self.initial_value > 0 or self.initial_cost > 0:
            lots.append(RealEstateLot(
                cost=self.initial_cost * scale,
                value=self.initial_value * growth_to_horizon[:, 0] * scale,
                holding_years=self.initial_years + horizon,
            ))
        for k in range(horizon + 1):
            paid = self.purchases[:, k]
            if not paid.any():
                continue
            lots.append(RealEstateLot(
                cost=paid * scale,
                value=paid * (1.0 - self.entry_fee) * growth_to_horizon[:, k] * scale,
                holding_years=float(horizon - k),
            ))
        return lots


def project_distributing(
    returns: np.ndarray,
    paid: np.ndarray,
    *,
    entry_fee: float,
    distribution_yield: float,
    income_tax_rate: float,
    initial_value: float = 0.0,
    initial_cost: float = 0.0,
    initial_years: float = 0.0,
) -> DistributingPosition:
    """
    Projeter des parts de SCPI détenues en direct.

    Args:
        returns: rendement total annuel des parts, net des frais annuels,
            [scénarios, années].
        paid: versements, ``paid[0]`` à la date 0 et ``paid[t]`` en fin d'année ``t``.
        entry_fee: frais d'entrée de chaque achat, versements comme réinvestissements.
        distribution_yield: revenus distribués chaque année, en fraction de la valeur.
        income_tax_rate: impôt sur ces revenus (tranche marginale et prélèvements
            sociaux), en fraction des revenus. Zéro pour une projection sans impôt.
        initial_value, initial_cost, initial_years: parts déjà détenues, sans frais
            d'entrée.

    Raises:
        ValueError: taux hors de [0, 1], ou versements plus courts que les rendements.
    """
    n_scenarios, n_periods = returns.shape
    for name, rate in (("entry_fee", entry_fee), ("distribution_yield", distribution_yield),
                       ("income_tax_rate", income_tax_rate)):
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"{name} doit être entre 0 et 1 (reçu {rate}).")
    if len(paid) < n_periods + 1:
        raise ValueError(
            f"{len(paid)} versements pour {n_periods} années : il en faut un par date, "
            "de la date 0 à l'horizon."
        )
    value = np.zeros((n_scenarios, n_periods + 1))
    purchases = np.zeros((n_scenarios, n_periods + 1))
    price_index = np.ones((n_scenarios, n_periods + 1))
    income_tax = np.zeros((n_scenarios, n_periods + 1))

    purchases[:, 0] = paid[0]
    value[:, 0] = initial_value + paid[0] * (1.0 - entry_fee)
    for t in range(n_periods):
        price_growth = 1.0 + returns[:, t] - distribution_yield
        distributed = value[:, t] * distribution_yield
        tax = distributed * income_tax_rate
        reinvested = distributed - tax
        purchases[:, t + 1] = paid[t + 1] + reinvested
        price_index[:, t + 1] = price_index[:, t] * np.clip(price_growth, 0.0, None)
        income_tax[:, t + 1] = tax
        value[:, t + 1] = (
            np.clip(value[:, t] * price_growth, 0.0, None)
            + purchases[:, t + 1] * (1.0 - entry_fee)
        )
    return DistributingPosition(
        value=value,
        purchases=purchases,
        price_index=price_index,
        income_tax=income_tax,
        entry_fee=entry_fee,
        initial_value=initial_value,
        initial_cost=initial_cost,
        initial_years=initial_years,
    )
