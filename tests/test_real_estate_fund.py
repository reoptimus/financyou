"""
Parts de SCPI détenues en direct : revenus fonciers imposés chaque année au
barème, revenus nets réinvestis en lots, cession lot par lot.

Le catalogue de production ne propose pas encore ce placement : ces tests en
ajoutent un, ``scpi_direct``, à une copie du catalogue.
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from investment_calculator.market_assumptions import load_market_assumptions
from investment_calculator.modules.net_returns import TaxProfile, build_net_returns
from investment_calculator.modules.real_estate_fund import project_distributing
from investment_calculator.modules.wealth_simulation import (
    Holding,
    simulate_wealth,
    wealth_waterfall,
)
from investment_calculator.placement_catalog import PlacementCatalog, load_placement_catalog
from investment_calculator.wrapper_tax import real_estate_liquidation_tax

FR_2026 = load_placement_catalog("fr-2026")
ENTRY_FEE = 0.075
MARGINAL_RATE = 0.30
DISTRIBUTION = load_market_assumptions().real_estate_fund_distribution_rate


def _catalog() -> PlacementCatalog:
    document = copy.deepcopy(FR_2026.document)
    document["placements"].append({
        "id": "scpi_direct",
        "label": "SCPI détenue en direct (test)",
        "wrapper": "immobilier_direct",
        "asset_class": "real_estate_fund",
        "support": {"model": "gse_series", "series": "real_estate_return"},
        "fees": {"entry_rate": ENTRY_FEE, "annual_rate": 0.0},
    })
    return PlacementCatalog(document=document, source=FR_2026.source, regime=FR_2026.regime)


CATALOG = _catalog()


def _gross(returns: np.ndarray) -> pd.DataFrame:
    n_scenarios, n_periods = returns.shape
    index = pd.MultiIndex.from_product(
        [[f"s{i:02d}" for i in range(n_scenarios)], [float(t + 1) for t in range(n_periods)]],
        names=["scenario_id", "time_period"],
    )
    return pd.DataFrame({"scpi_direct": returns.ravel()}, index=index)


def _random_returns(n_scenarios: int = 40, n_periods: int = 12) -> np.ndarray:
    return 0.04 + 0.08 * np.random.default_rng(7).standard_normal((n_scenarios, n_periods))


def _profile(**kwargs: object) -> TaxProfile:
    return TaxProfile(**{"invested_amount": 1.0, "marginal_income_tax_rate": MARGINAL_RATE,
                         **kwargs})  # type: ignore[arg-type]


def test_les_lots_reconstituent_la_valeur() -> None:
    returns = _random_returns()
    paid = np.r_[10_000.0, np.full(12, 1_000.0)]
    position = project_distributing(
        returns, paid, entry_fee=ENTRY_FEE, distribution_yield=DISTRIBUTION,
        income_tax_rate=0.472, initial_value=5_000.0, initial_cost=4_000.0, initial_years=3,
    )
    for horizon in (1, 6, 12):
        total = sum(np.broadcast_to(lot.value, (40,)) for lot in position.lots(horizon))
        np.testing.assert_allclose(total, position.value[:, horizon])


def test_les_revenus_sont_imposes_puis_reinvestis_avec_frais() -> None:
    returns = _random_returns()
    paid = np.r_[10_000.0, np.zeros(12)]
    rate = 0.472
    position = project_distributing(
        returns, paid, entry_fee=ENTRY_FEE, distribution_yield=DISTRIBUTION, income_tax_rate=rate,
    )
    distributed = position.value[:, 0] * DISTRIBUTION
    np.testing.assert_allclose(position.income_tax[:, 1], distributed * rate)
    np.testing.assert_allclose(position.purchases[:, 1], distributed * (1 - rate))
    expected = (
        position.value[:, 0] * (1 + returns[:, 0] - DISTRIBUTION)
        + distributed * (1 - rate) * (1 - ENTRY_FEE)
    )
    np.testing.assert_allclose(position.value[:, 1], expected)


def test_gse_plus_plus_et_projection_concordent() -> None:
    gross = _gross(_random_returns())
    amount, horizon = 80_000.0, 10
    flows = np.zeros(13)
    flows[0] = amount
    weights = pd.Series({"scpi_direct": 1.0})
    sim = simulate_wealth(gross, CATALOG, _profile(), weights, flows, horizon)
    net = build_net_returns(gross, CATALOG, _profile(invested_amount=amount), [horizon])
    np.testing.assert_allclose(sim.net_terminal, amount * net.multiples[:, 0, 0], rtol=1e-12)
    assert (sim.income_tax["immobilier_direct"] > 0).all()


def test_sans_tranche_marginale_la_scpi_en_direct_est_refusee() -> None:
    gross = _gross(_random_returns())
    with pytest.raises(NotImplementedError, match="marginal_income_tax_rate"):
        build_net_returns(gross, CATALOG, TaxProfile(invested_amount=1.0), [5])


def test_un_lot_ancien_est_exonere_a_la_cession() -> None:
    # Prix des parts constant : les lots réinvestis, payés frais compris, sont
    # en moins-value ; les parts détenues depuis 30 ans sont exonérées.
    returns = np.full((3, 5), DISTRIBUTION)
    gross = _gross(returns)
    holding = Holding("scpi_direct", value=100_000.0, contributions=20_000.0, years_held=30)
    sim = simulate_wealth(
        gross, CATALOG, _profile(), pd.Series({"scpi_direct": 1.0}),
        np.r_[1.0, np.zeros(5)], 5, holdings=(holding,),
    )
    np.testing.assert_allclose(sim.exit_tax["immobilier_direct"], 0.0, atol=1e-9)
    rate = MARGINAL_RATE + FR_2026.regime.social_rate
    assert sim.income_tax["immobilier_direct"][0] > 100_000.0 * DISTRIBUTION * rate


def test_un_lot_recent_paie_l_impot_sans_abattement() -> None:
    returns = np.full((2, 4), DISTRIBUTION + 0.10)
    gross = _gross(returns)
    sim = simulate_wealth(
        gross, CATALOG, _profile(), pd.Series({"scpi_direct": 1.0}),
        np.r_[50_000.0, np.zeros(4)], 4,
    )
    position = project_distributing(
        returns, np.r_[50_000.0, np.zeros(4)], entry_fee=ENTRY_FEE,
        distribution_yield=DISTRIBUTION, income_tax_rate=MARGINAL_RATE + FR_2026.regime.social_rate,
    )
    expected = real_estate_liquidation_tax(FR_2026.regime, "immobilier_direct", position.lots(4))
    np.testing.assert_allclose(sim.net_terminal, expected.net_value)
    assert (expected.income_tax > 0).all()


def test_la_cascade_reste_exacte_avec_la_scpi_en_direct() -> None:
    gross = _gross(_random_returns())
    flows = np.r_[30_000.0, np.full(12, 2_000.0)]
    waterfall = wealth_waterfall(
        gross, gross, CATALOG, _profile(), pd.Series({"scpi_direct": 1.0}), flows, 8,
    )
    total = (waterfall.starting_capital + waterfall.market_gains - waterfall.fees
             - waterfall.income_tax - waterfall.exit_tax)
    assert total == pytest.approx(waterfall.net_wealth)
    assert waterfall.income_tax > 0
