"""
Projection du patrimoine sur GSE+ : versements, frais, impôt annuel et impôt de sortie.

L'optimiseur (:mod:`investment_calculator.modules.placement_optimizer`) choisit
des poids entre placements. Ce module projette, scénario par scénario, ce que
deviennent les versements de l'utilisateur répartis selon ces poids :

1. chaque versement, diminué des frais d'entrée de chaque placement, suit les
   rendements de GSE+ (déjà nets des frais annuels) ;
2. dans une enveloppe imposée au fil de l'eau (le CTO), les revenus distribués
   sont imposés chaque année et leur part nette s'ajoute au prix de revient ;
3. à l'horizon, chaque enveloppe est liquidée une fois, sur la somme de ses
   placements, avec l'ancienneté de l'enveloppe : abattement de
   l'assurance-vie et seuil de primes s'appliquent au contrat, pas à chaque
   versement.

Chaque euro versé suit l'allocation cible et n'est pas rééquilibré ensuite,
comme dans GSE++ : la valeur projetée est la somme exacte des trajectoires de
chaque versement (assemblage linéaire). Seul l'impôt de sortie, calculé par
enveloppe, n'est pas linéaire.

L'épargne existante (:class:`Holding`) reste dans ses placements : elle n'est
ni réallouée ni soumise à des frais d'entrée, garde son prix de revient et
l'ancienneté de son enveloppe, et rejoint l'enveloppe à la liquidation.

Les retraits avant l'horizon ne sont pas modélisés : ils sont refusés.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from investment_calculator.modules.net_returns import TaxProfile, _distributed_yield
from investment_calculator.modules.placements import entry_fee_rates
from investment_calculator.placement_catalog import PlacementCatalog
from investment_calculator.wrapper_allocation import TOLERANCE
from investment_calculator.wrapper_tax import liquidation_tax

logger = logging.getLogger(__name__)

__all__ = ["Holding", "WealthSimulation", "contribution_flows", "simulate_wealth"]


@dataclass(frozen=True)
class Holding:
    """
    Épargne existante, laissée dans un placement du catalogue.

    Attributes:
        placement_id: placement du catalogue qui la porte.
        value: valeur actuelle, en euros.
        contributions: versements cumulés, en euros : prix de revient d'un
            compte-titres ou d'un PEA, primes versées d'une assurance-vie.
        years_held: ancienneté de l'enveloppe, en années.
    """

    placement_id: str
    value: float
    contributions: float
    years_held: float

    def __post_init__(self) -> None:
        if self.value < 0 or self.contributions < 0 or self.years_held < 0:
            raise ValueError(
                f"Épargne existante sur {self.placement_id!r} : valeur, versements et "
                f"ancienneté doivent être positifs (reçu {self.value}, "
                f"{self.contributions}, {self.years_held})."
            )


@dataclass
class _WrapperBook:
    """Cumul, par enveloppe, des placements qu'elle contient."""

    value: np.ndarray
    basis: np.ndarray
    taxed: np.ndarray
    paid: float = 0.0
    annual_income: bool = False


@dataclass(frozen=True)
class WealthSimulation:
    """Patrimoine projeté par scénario, avant et après l'impôt de sortie."""

    scenario_ids: list[str]
    value_paths: np.ndarray = field(repr=False)  # [scénarios, années + 1], avant impôt de sortie
    net_terminal: np.ndarray = field(repr=False)  # [scénarios], après impôt de sortie
    contributions: dict[str, float]  # enveloppe -> versements cumulés, en euros
    income_tax: dict[str, np.ndarray] = field(repr=False)  # enveloppe -> impôt annuel cumulé
    exit_tax: dict[str, np.ndarray] = field(repr=False)  # enveloppe -> impôt de sortie

    def statistics(self) -> dict[str, object]:
        """Statistiques du patrimoine net à l'horizon, sur les scénarios."""
        net = self.net_terminal
        tail = net[net <= np.percentile(net, 5)]
        return {
            "mean_terminal_wealth": float(net.mean()),
            "median_terminal_wealth": float(np.median(net)),
            "std_terminal_wealth": float(net.std()),
            "percentiles": {str(q): float(np.percentile(net, q)) for q in (5, 25, 50, 75, 95)},
            "var_95": float(np.percentile(net, 5)),
            "cvar_95": float(tail.mean()),
            "total_contributions": float(sum(self.contributions.values())),
            "mean_tax_by_wrapper": {
                w: float((self.income_tax[w] + self.exit_tax[w]).mean()) for w in self.exit_tax
            },
        }


def contribution_flows(time_series: pd.DataFrame, n_periods: int) -> np.ndarray:
    """
    Versements par année : ``flows[0]`` est la mise initiale, ``flows[t]`` le
    versement de fin d'année ``t``.

    Raises:
        ValueError: série vide ou sans colonne de versements.
        NotImplementedError: la série contient un retrait avant l'horizon. Un
            retrait à l'horizon même est ignoré : le patrimoine y est liquidé.
    """
    if time_series.empty:
        raise ValueError(
            "investment_time_series est vide : la projection a besoin des versements "
            "de l'utilisateur (module 3, user_profile)."
        )
    if "net_flow" in time_series.columns:
        series = time_series["net_flow"]
    elif "contribution" in time_series.columns:
        series = time_series["contribution"] - time_series.get("withdrawal", 0.0)
    else:
        raise ValueError("investment_time_series doit contenir 'net_flow' ou 'contribution'.")
    flows = np.zeros(n_periods + 1)
    values = series.to_numpy(dtype=float)[: n_periods + 1]
    flows[: len(values)] = values
    if flows[n_periods] < 0:
        # Un retrait à l'horizon même coïncide avec la liquidation : tout le
        # patrimoine est alors restitué, le retrait n'a rien à retrancher.
        logger.info(
            "Retrait de %.0f à l'horizon %d ignoré : le patrimoine y est liquidé.",
            -flows[n_periods], n_periods,
        )
        flows[n_periods] = 0.0
    if (flows < 0).any():
        years = np.flatnonzero(flows < 0).tolist()
        raise NotImplementedError(
            f"Retraits aux années {years} : la projection par placement ne modélise pas "
            "encore les retraits avant l'horizon. Retirez-les du profil ou ramenez "
            "l'horizon avant le premier retrait."
        )
    return flows


def simulate_wealth(
    gross: pd.DataFrame,
    catalog: PlacementCatalog,
    profile: TaxProfile,
    weights: pd.Series,
    flows: np.ndarray,
    horizon: int,
    holdings: tuple[Holding, ...] = (),
) -> WealthSimulation:
    """
    Projeter le patrimoine net d'une allocation entre placements.

    Args:
        gross: GSE+, indexé par (``scenario_id``, ``time_period``), une colonne par
            placement.
        catalog: catalogue des placements et, par lui, le régime fiscal.
        profile: situation fiscale ; seuls ``couple`` et ``wrapper_seniority``
            servent ici, les montants venant de ``flows``.
        weights: poids par placement (somme 1), par exemple
            ``optimize_horizon(...).weights``.
        flows: versements par année (:func:`contribution_flows`).
        horizon: année de liquidation, de 1 à la durée des scénarios.
        holdings: épargne existante, laissée dans ses placements. L'ancienneté
            d'une enveloppe est la plus grande entre ``profile.wrapper_seniority``
            et celle de ses avoirs.

    Raises:
        ValueError: poids qui ne somment pas à 1, placement absent de GSE+,
            horizon hors des scénarios, ou aucun versement.
    """
    if not np.isclose(float(weights.sum()), 1.0) or (weights < -TOLERANCE).any():
        raise ValueError(f"Les poids doivent être positifs et sommer à 1 (somme {weights.sum()}).")
    missing = [p for p in [*weights.index, *(h.placement_id for h in holdings)]
               if p not in gross.columns]
    if missing:
        raise ValueError(
            f"Placements absents de GSE+ : {missing}. Disponibles : {list(gross.columns)}."
        )
    ordered = gross.sort_index()
    scenario_ids = list(dict.fromkeys(ordered.index.get_level_values(0)))
    n_scenarios = len(scenario_ids)
    n_periods = len(ordered) // n_scenarios
    if not 1 <= horizon <= n_periods:
        raise ValueError(
            f"Horizon {horizon} hors des scénarios : il doit être entre 1 et {n_periods}."
        )
    flows = np.asarray(flows, dtype=float)[: horizon + 1]
    if flows.sum() <= 0:
        raise ValueError("Aucun versement avant l'horizon : il n'y a rien à projeter.")

    regime = catalog.regime
    entry_fees = entry_fee_rates(catalog, list(weights.index))
    paths = np.zeros((n_scenarios, horizon + 1))
    books: dict[str, _WrapperBook] = {}
    seniority = {w: float(y) for w, y in profile.wrapper_seniority.items()}

    def project(pid: str, paid: np.ndarray, fee: float, value0: float, basis0: float) -> None:
        """Projeter une position : mise de départ, puis versements de fin d'année."""
        placement = catalog.placement(pid)
        wrapper = str(placement["wrapper"])
        spec = regime.wrapper(wrapper)
        returns = ordered[pid].to_numpy(dtype=float).reshape(n_scenarios, n_periods)[:, :horizon]
        income_yield, income_rate = None, 0.0
        if spec.get("tax_treatment") == "taxable" and not spec.get("growth_taxed_annually"):
            rule = regime.select_withdrawal_rule(wrapper, holding_years=0.0)
            income_rate = regime.resolve_income_tax_rate(
                rule, taxable_amount=1.0
            ) + regime.resolve_social_rate(rule)
            support = placement["support"]
            income_yield = _distributed_yield(
                str(support.get("series") or support.get("reference_series")), returns
            )
        value = np.full(n_scenarios, value0 + paid[0] * (1.0 - fee))
        basis = np.full(n_scenarios, basis0 + paid[0])
        taxed = np.zeros(n_scenarios)
        paths[:, 0] += value
        for t in range(horizon):
            grown = value * (1.0 + returns[:, t])
            if income_yield is not None:
                tax = value * income_yield[:, t] * income_rate
                grown -= tax
                taxed += tax
                basis += value * income_yield[:, t] - tax
            value = np.clip(grown, 0.0, None) + paid[t + 1] * (1.0 - fee)
            basis += paid[t + 1]
            paths[:, t + 1] += value
        book = books.setdefault(wrapper, _WrapperBook(
            np.zeros(n_scenarios), np.zeros(n_scenarios), np.zeros(n_scenarios)
        ))
        book.value += value
        book.basis += basis
        book.taxed += taxed
        book.paid += basis0 + float(paid.sum())
        book.annual_income = book.annual_income or income_yield is not None

    for pid, weight in weights.items():
        if weight > 0:
            project(str(pid), flows * float(weight), entry_fees[str(pid)], 0.0, 0.0)
    no_flow = np.zeros(horizon + 1)
    for holding in holdings:
        # Ni frais d'entrée ni réallocation : l'avoir garde sa valeur et son prix de revient.
        project(holding.placement_id, no_flow, 0.0, holding.value, holding.contributions)
        wrapper = str(catalog.placement(holding.placement_id)["wrapper"])
        seniority[wrapper] = max(seniority.get(wrapper, 0.0), holding.years_held)

    net_terminal = np.zeros(n_scenarios)
    contributions: dict[str, float] = {}
    income_tax: dict[str, np.ndarray] = {}
    exit_tax: dict[str, np.ndarray] = {}
    for wrapper, book in books.items():
        result = liquidation_tax(
            regime,
            wrapper,
            contributions=book.paid,
            final_value=book.value,
            holding_years=seniority.get(wrapper, 0.0) + horizon,
            couple=profile.couple,
            cost_basis=book.basis if book.annual_income else None,
        )
        net_terminal += result.net_value
        contributions[wrapper] = book.paid
        income_tax[wrapper] = book.taxed
        exit_tax[wrapper] = book.value - result.net_value

    logger.info(
        "Patrimoine projeté à %d ans sur %d scénarios : médiane nette %.0f €",
        horizon, n_scenarios, float(np.median(net_terminal)),
    )
    return WealthSimulation(scenario_ids, paths, net_terminal, contributions, income_tax, exit_tax)
