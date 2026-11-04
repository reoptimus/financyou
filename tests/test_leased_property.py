"""
Bien loué à loyer fixe (évolution E1) : test de martingale.

En risque neutre, la richesse déflatée du propriétaire,
D(t)·V(t) + Σ_{s <= t} D(s)·loyer(s), doit avoir pour espérance V(0) à toute
date. La décomposition jambe de loyers + valeur libre le vérifie ; l'approche
« indice » (valeur du bien = indice de prix du GSE, loyer en euros du bail)
l'échoue.
"""

from __future__ import annotations

import numpy as np
import pytest

from investment_calculator.market_assumptions import load_market_assumptions
from investment_calculator.modules import scenario_generator
from investment_calculator.stochastic_models import (
    CorrelatedRandomGenerator,
    FixedRentLease,
    HullWhiteModel,
    RealEstateModel,
    leased_property_paths,
)

N_SCENARIOS, HORIZON, DT = 20_000, 30, 0.25
N_DATES = int(HORIZON / DT) + 1
INITIAL_VALUE = 300_000.0
# Rendement locatif de marché du test : un paramètre d'essai, pas une hypothèse
# de marché retenue (aucune ne l'est encore, voir KNOWN_GAPS).
MARKET_YIELD = 0.04


@pytest.fixture(scope="module")
def risk_neutral_world():
    """Taux Hull-White et indice immobilier risque neutre, câblés comme le GSE."""
    np.random.seed(11)
    generator = scenario_generator.ScenarioGenerator(random_seed=11)
    _, _, f0t, P0t = generator._load_yield_curve(None, 'EUR', DT, N_DATES + 1)
    params = generator.default_params
    assumptions = load_market_assumptions()

    rates = HullWhiteModel(
        a=params['mean_reversion_speed'], sigma=params['hw_volatility'],
        f0t=f0t, P0t=P0t, dt=DT, n_scenarios=N_SCENARIOS, T=(N_DATES + 0.5) * DT,
    )
    rate_results = rates.generate_scenarios(filter_explosive=False)
    correlation = CorrelatedRandomGenerator(
        n_scenarios=N_SCENARIOS, n_steps=N_DATES, random_seed=11
    )
    shocks = correlation.generate(rate_residuals=rate_results['residuals'])['shocks']
    real_estate = RealEstateModel(
        a=assumptions.real_estate_mean_reversion,
        sigma=assumptions.real_estate_instantaneous_volatility,
        # Seule l'approche indice lit ce rendement : part du loyer dans le
        # rendement total, log(1 + rental_yield)·dt = y·dt.
        rental_yield=np.expm1(MARKET_YIELD),
        dt=DT, n_scenarios=N_SCENARIOS, T=(N_DATES + 0.5) * DT,
    )
    drift = real_estate.risk_neutral_drift(
        f0t, P0t, N_DATES, rates.log_deflator_loadings(),
        correlation.shock_covariances(['short_rate', 'real_estate', 'inflation']),
    )
    returns = real_estate.generate_returns(
        rate_results['Rt'], f0t,
        re_price_shocks=correlation.get_asset_shocks(shocks, 'real_estate'),
        re_rental_shocks=correlation.get_asset_shocks(shocks, 'inflation'),
        risk_premium=0.0,
        drift=drift,
    )
    return rates, rate_results, returns


def _deflated_wealth(deflators, value, rent):
    """D(t)·V(t) + Σ_{s <= t} D(s)·loyer(s), par scénario et par date."""
    return deflators * value + np.cumsum(deflators * rent, axis=1)


def _market_lease(n_periods: int) -> FixedRentLease:
    """Bail signé au loyer de marché : loyer de période V(0)·(exp(y·dt) - 1)."""
    rent = INITIAL_VALUE * np.expm1(MARKET_YIELD * DT)
    return FixedRentLease(rents=np.full(n_periods, rent), market_yield=MARKET_YIELD)


@pytest.mark.parametrize("lease_years", [9, 30])
def test_richesse_deflatee_martingale(risk_neutral_world, lease_years):
    """E[D·(V + loyers capitalisés)] = V(0) à toute date, bail fini ou couvrant l'horizon."""
    rates, rate_results, returns = risk_neutral_world
    lease = _market_lease(int(lease_years / DT))
    paths = leased_property_paths(
        rates, rate_results['rt'], returns['total_returns'], lease, INITIAL_VALUE
    )
    np.testing.assert_allclose(paths.value[:, 0], INITIAL_VALUE, rtol=1e-12)

    wealth = _deflated_wealth(rate_results['deflators'], paths.value, paths.rent)
    mean = wealth.mean(axis=0)
    standard_error = wealth.std(axis=0, ddof=1) / np.sqrt(N_SCENARIOS)
    gap = np.abs(mean - INITIAL_VALUE)
    # Tolérance Monte-Carlo : 4 erreurs-types à chaque date.
    assert np.all(gap <= 4 * standard_error + 1e-9 * INITIAL_VALUE), (
        f"écart maximal {gap.max():.0f} € pour une erreur-type de "
        f"{standard_error[gap.argmax()]:.0f} € en t = {gap.argmax() * DT} ans"
    )
    assert gap.max() / INITIAL_VALUE < 5e-3


def test_valeur_libre_derive_r_moins_y(risk_neutral_world):
    """E[D(t)·H(t)·exp(y·t)] = H(0) : la valeur libre a la dérive r - y."""
    rates, rate_results, returns = risk_neutral_world
    paths = leased_property_paths(
        rates, rate_results['rt'], returns['total_returns'], _market_lease(36),
        INITIAL_VALUE,
    )
    times = DT * np.arange(N_DATES)
    scaled = rate_results['deflators'] * paths.free_value * np.exp(MARKET_YIELD * times)
    np.testing.assert_allclose(
        scaled.mean(axis=0) / paths.initial_free_value, 1.0, atol=5e-3
    )


def test_approche_indice_echoue(risk_neutral_world):
    """
    Valeur = indice de prix du GSE, loyer = loyers en euros du bail : la richesse
    déflatée n'est pas martingale. C'est le défaut que corrige E1.
    """
    rates, rate_results, returns = risk_neutral_world
    lease = _market_lease(N_DATES - 1)
    index_value = INITIAL_VALUE * np.exp(np.cumsum(returns['price_returns'], axis=1))
    index_rent = np.zeros_like(index_value)
    index_rent[:, 1:] = lease.rents
    wealth = _deflated_wealth(rate_results['deflators'], index_value, index_rent)
    mean = wealth[:, -1].mean()
    standard_error = wealth[:, -1].std(ddof=1) / np.sqrt(N_SCENARIOS)
    gap = abs(mean - INITIAL_VALUE)
    assert gap > 10 * standard_error
    assert gap / INITIAL_VALUE > 0.01


def test_bail_plus_cher_que_le_bien_refuse(risk_neutral_world):
    rates, rate_results, returns = risk_neutral_world
    lease = FixedRentLease(rents=np.full(40, 20_000.0), market_yield=MARKET_YIELD)
    with pytest.raises(ValueError, match="valeur libre serait négative"):
        leased_property_paths(
            rates, rate_results['rt'], returns['total_returns'], lease, INITIAL_VALUE
        )


@pytest.mark.parametrize(
    ("rents", "market_yield", "message"),
    [
        (np.array([]), 0.04, "au moins un loyer"),
        (np.array([1_000.0, -1.0]), 0.04, "positifs ou nuls"),
        (np.array([1_000.0]), float('nan'), "Rendement locatif"),
    ],
)
def test_bail_invalide_refuse(rents, market_yield, message):
    with pytest.raises(ValueError, match=message):
        FixedRentLease(rents=rents, market_yield=market_yield)
