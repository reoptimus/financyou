"""
Module GSE++ : les placements nets de frais et d'impôts, pour un utilisateur.

Pour chaque placement de GSE+ (:mod:`investment_calculator.modules.placements`),
chaque scénario et chaque durée de détention H, on suit un versement unique
fait en début de projection, puis liquidé au bout de H ans :

1. le versement, diminué des frais d'entrée, suit les rendements de GSE+ ;
2. dans une enveloppe imposée au fil de l'eau (le CTO), les revenus distribués
   sont imposés chaque année, et leur part nette s'ajoute au prix de revient ;
3. à l'horizon, l'impôt de sortie de l'enveloppe est calculé par
   :func:`investment_calculator.wrapper_tax.liquidation_tax`, qui lit le régime
   fiscal : durée de détention, seuil de primes, abattement selon le foyer.

Le résultat est le **multiple net** (valeur nette par euro versé) et le
**rendement net annualisé** ``multiple ** (1 / H) - 1``. Moyenne et covariance
de ce rendement sur les scénarios, à l'horizon H, sont ce que lit
l'optimisation de Markowitz (:func:`net_return_moments`).

Équivalent R : ``legacy/R_scripts/Earn_Aft_Int_TaxesV3.R`` (``Ra``). Différence
assumée : les frais d'entrée sont prélevés sur le versement (A × (1 − f)), là
où le R divise par (1 + f). Voir ``docs/adr/0002-le-placement-est-l-unite-d-optimisation.md``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from investment_calculator.market_assumptions import load_market_assumptions
from investment_calculator.modules.placements import entry_fee_rates
from investment_calculator.placement_catalog import PlacementCatalog
from investment_calculator.wrapper_tax import liquidation_tax

logger = logging.getLogger(__name__)

__all__ = ["NetReturns", "TaxProfile", "build_net_returns", "net_return_moments"]


@dataclass(frozen=True)
class TaxProfile:
    """
    Ce dont l'impôt des placements dépend chez l'utilisateur.

    Attributes:
        invested_amount: montant versé dans chaque placement, en euros. Il fixe
            la part de la plus-value couverte par l'abattement de l'assurance-vie
            et le seuil de primes (« Investmoy » dans le R).
        couple: foyer soumis à imposition commune (abattement doublé).
        wrapper_seniority: ancienneté, en années, des enveloppes déjà ouvertes
            (``{"pea": 6}``) ; une enveloppe absente est ouverte au versement.
    """

    invested_amount: float
    couple: bool = False
    wrapper_seniority: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.invested_amount <= 0:
            raise ValueError(
                f"Le montant versé doit être strictement positif (reçu "
                f"{self.invested_amount}). Indiquez le montant que l'utilisateur place."
            )


@dataclass(frozen=True)
class NetReturns:
    """GSE++ : multiples nets par (scénario, horizon, placement)."""

    multiples: np.ndarray = field(repr=False)
    scenario_ids: list[str]
    horizons: list[int]
    placement_ids: list[str]

    def annualized(self, horizon: int) -> pd.DataFrame:
        """Rendement net annualisé à l'horizon donné : une ligne par scénario."""
        h = self._horizon_index(horizon)
        values = np.power(self.multiples[:, h, :], 1.0 / horizon) - 1.0
        return pd.DataFrame(values, index=self.scenario_ids, columns=self.placement_ids)

    def _horizon_index(self, horizon: int) -> int:
        if horizon not in self.horizons:
            raise ValueError(
                f"Horizon {horizon} non calculé. Horizons disponibles : {self.horizons}."
            )
        return self.horizons.index(horizon)


def _distributed_yield(series: str, returns: np.ndarray) -> np.ndarray:
    """Part du rendement annuel distribuée (dividendes, coupons), imposable dans un CTO."""
    if series == "stock_return":
        return np.full_like(returns, load_market_assumptions().dividend_yield)
    if series == "bond_return":
        clipped: np.ndarray = np.clip(returns, 0.0, None)
        return clipped
    raise NotImplementedError(
        f"Revenu distribué de la série {series!r} inconnu : seuls stock_return et "
        f"bond_return sont modélisés dans une enveloppe imposée au fil de l'eau."
    )


def _paths(
    returns: np.ndarray, entry_fee: float, income_yield: np.ndarray | None, income_rate: float
) -> tuple[np.ndarray, np.ndarray]:
    """Valeur et prix de revient, par euro versé, à chaque fin d'année (scénarios × T+1)."""
    n_scenarios, n_periods = returns.shape
    value = np.empty((n_scenarios, n_periods + 1))
    basis = np.ones((n_scenarios, n_periods + 1))
    value[:, 0] = 1.0 - entry_fee
    for t in range(n_periods):
        grown = value[:, t] * (1.0 + returns[:, t])
        basis[:, t + 1] = basis[:, t]
        if income_yield is not None:
            tax = value[:, t] * income_yield[:, t] * income_rate
            grown = grown - tax
            basis[:, t + 1] += value[:, t] * income_yield[:, t] - tax
        value[:, t + 1] = np.clip(grown, 0.0, None)
    return value, basis


def build_net_returns(
    gross: pd.DataFrame,
    catalog: PlacementCatalog,
    profile: TaxProfile,
    horizons: list[int],
) -> NetReturns:
    """
    Construire GSE++ à partir de GSE+, pour un utilisateur.

    Args:
        gross: sortie de :func:`~investment_calculator.modules.placements.build_gross_placements`,
            indexée par (``scenario_id``, ``time_period``), une colonne par placement.
        catalog: catalogue des placements (et, par lui, le régime fiscal).
        profile: situation fiscale de l'utilisateur.
        horizons: durées de détention, en années entières, de 1 au nombre d'années
            des scénarios.

    Raises:
        ValueError: horizons hors des scénarios, ou scénarios de longueurs inégales.
        UnsourcedValueError: un frais d'entrée n'est pas sourcé dans le catalogue.
        NotImplementedError: impôt d'une enveloppe non modélisé (PER, immobilier).
    """
    ordered = gross.sort_index()
    scenario_ids = list(dict.fromkeys(ordered.index.get_level_values(0)))
    n_scenarios = len(scenario_ids)
    n_periods = len(ordered) // n_scenarios
    if n_scenarios * n_periods != len(ordered):
        raise ValueError("Les scénarios de GSE+ n'ont pas tous le même nombre d'années.")
    bad = [h for h in horizons if not 1 <= h <= n_periods]
    if bad or not horizons:
        raise ValueError(
            f"Horizons {bad or horizons} invalides : ils doivent être des entiers entre 1 "
            f"et {n_periods}, la durée des scénarios."
        )

    placement_ids = list(ordered.columns)
    tensor = ordered.to_numpy(dtype=float).reshape(n_scenarios, n_periods, len(placement_ids))
    entry_fees = entry_fee_rates(catalog, placement_ids)
    regime = catalog.regime
    amount = profile.invested_amount
    multiples = np.empty((n_scenarios, len(horizons), len(placement_ids)))

    for p, pid in enumerate(placement_ids):
        placement = catalog.placement(pid)
        wrapper = placement["wrapper"]
        spec = regime.wrapper(wrapper)
        returns = tensor[:, :, p]
        income_yield = None
        income_rate = 0.0
        if spec.get("tax_treatment") == "taxable" and not spec.get("growth_taxed_annually"):
            rule = regime.select_withdrawal_rule(wrapper, holding_years=0.0)
            income_rate = regime.resolve_income_tax_rate(
                rule, taxable_amount=1.0
            ) + regime.resolve_social_rate(rule)
            series = placement["support"].get("series") or placement["support"].get(
                "reference_series"
            )
            income_yield = _distributed_yield(str(series), returns)
        value, basis = _paths(returns, entry_fees[pid], income_yield, income_rate)

        seniority = float(profile.wrapper_seniority.get(wrapper, 0.0))
        for h_index, horizon in enumerate(horizons):
            result = liquidation_tax(
                regime,
                wrapper,
                contributions=amount,
                final_value=value[:, horizon] * amount,
                holding_years=seniority + horizon,
                couple=profile.couple,
                cost_basis=basis[:, horizon] * amount if income_yield is not None else None,
            )
            multiples[:, h_index, p] = result.net_value / amount

    logger.info(
        "GSE++ construit : %d placement(s), %d scénario(s), horizons %s, versement %.0f",
        len(placement_ids), n_scenarios, horizons, amount,
    )
    return NetReturns(multiples, scenario_ids, list(horizons), placement_ids)


def net_return_moments(net: NetReturns, horizon: int) -> tuple[pd.Series, pd.DataFrame]:
    """
    Espérance et covariance du rendement net annualisé à l'horizon H, sur les scénarios.

    C'est l'entrée de Markowitz : aucune correction fiscale n'est faite ensuite.
    """
    annualized = net.annualized(horizon)
    return annualized.mean(), annualized.cov()
