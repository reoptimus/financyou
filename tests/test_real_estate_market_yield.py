"""
Contrainte de martingale de la valeur libre H d'un immeuble loué (évolution E3).

Papier EAJ (registre A15) : en risque neutre, la valeur libre H d'un bien loué,
sans flux, a pour dérive r - y, où y est le rendement locatif de marché. La
contrainte E[D(t) * H(t) * e^(y t)] = 1 retire y * dt au niveau k_A de chaque
pas. Ces tests vérifient la formule par Monte-Carlo, comme le demande le doc.

Le calibrage immobilier est celui du papier EAJ (a = 0,51 ; σ = 5,7 % ;
corrélation -0,039 avec les taux), retenu par seb le 4 novembre 2026 ; il sera
porté dans les hypothèses de marché par E4. Ici, ce n'est qu'une configuration
de test. Le rendement y = 3 % est une valeur de test, pas une hypothèse.
"""

import numpy as np
import pytest

from investment_calculator.modules import scenario_generator
from investment_calculator.stochastic_models import (
    BlackScholesEquity,
    CorrelatedRandomGenerator,
    HullWhiteModel,
    RealEstateModel,
)

EAJ_MEAN_REVERSION = 0.51
EAJ_VOLATILITY = 0.057
EAJ_RATE_CORRELATION = -0.039
TEST_MARKET_YIELD = 0.03


def _simulate(n_scenarios: int, horizon: int, dt: float, seed: int):
    """Taux Hull-White, chocs corrélés et modèle immobilier au calibrage EAJ."""
    np.random.seed(seed)
    n_steps = int(horizon / dt)
    generator = scenario_generator.ScenarioGenerator(random_seed=seed)
    _, _, f0t, P0t = generator._load_yield_curve(None, 'EUR', dt, n_steps)
    params = generator.default_params

    rates = HullWhiteModel(
        a=params['mean_reversion_speed'], sigma=params['hw_volatility'],
        f0t=f0t, P0t=P0t, dt=dt, n_scenarios=n_scenarios, T=horizon,
    )
    rate_results = rates.generate_scenarios()
    names = ['short_rate', 'real_estate', 'inflation']
    correlation = CorrelatedRandomGenerator(
        correlation_matrix=np.array([
            [1.0, EAJ_RATE_CORRELATION, 0.0],
            [EAJ_RATE_CORRELATION, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]),
        asset_names=names, n_scenarios=n_scenarios, n_steps=n_steps,
    )
    shocks = correlation.generate(rate_residuals=rate_results['residuals'])['shocks']
    model = RealEstateModel(
        a=EAJ_MEAN_REVERSION, sigma=EAJ_VOLATILITY, dt=dt,
        n_scenarios=n_scenarios, T=horizon,
    )
    return {
        'model': model, 'rates': rates, 'rate_results': rate_results,
        'f0t': f0t, 'P0t': P0t, 'n_steps': n_steps,
        'covariances': correlation.shock_covariances(names),
        'price_shocks': correlation.get_asset_shocks(shocks, 'real_estate'),
        'aux_shocks': correlation.get_asset_shocks(shocks, 'inflation'),
    }


def _drift(sim, market_yield):
    return sim['model'].risk_neutral_drift(
        sim['f0t'], sim['P0t'], sim['n_steps'],
        sim['rates'].log_deflator_loadings(), sim['covariances'],
        market_yield=market_yield,
    )


def _free_value(sim, drift):
    """Valeur libre H(t), H(0) = 1, une ligne par scénario."""
    returns = sim['model'].generate_returns(
        sim['rate_results']['Rt'], sim['f0t'],
        re_price_shocks=sim['price_shocks'], re_rental_shocks=sim['aux_shocks'],
        drift=drift,
    )['total_returns']
    return np.exp(np.cumsum(returns, axis=1))


def test_valeur_libre_martingale_avec_rendement_locatif():
    """E[D(t) * H(t) * e^(y t)] = 1 à toutes les dates, à la tolérance Monte-Carlo."""
    dt, horizon = 0.25, 30
    sim = _simulate(n_scenarios=20_000, horizon=horizon, dt=dt, seed=11)
    free_value = _free_value(sim, _drift(sim, TEST_MARKET_YIELD))
    times = dt * np.arange(sim['n_steps'])
    deflated = sim['rate_results']['deflators'] * free_value * np.exp(TEST_MARKET_YIELD * times)

    mean = deflated.mean(axis=0)
    standard_error = deflated.std(axis=0) / np.sqrt(deflated.shape[0])
    # Quatre écarts-types sur 120 dates : un échec par hasard est improbable.
    assert np.all(np.abs(mean - 1.0) <= 4 * standard_error + 1e-12), (
        f"écart maximal {np.max(np.abs(mean - 1.0)):.2e}"
    )
    assert abs(mean[-1] - 1.0) < 0.01

    # Sans y dans la contrainte, l'indice capitalise le loyer : D·H·e^(yt)
    # dérive de e^(yt), soit +146 % à 30 ans. La contrainte n'est pas triviale.
    total_index = _free_value(sim, _drift(sim, 0.0))
    biased = (sim['rate_results']['deflators'] * total_index
              * np.exp(TEST_MARKET_YIELD * times)).mean(axis=0)
    assert biased[-1] == pytest.approx(np.exp(TEST_MARKET_YIELD * times[-1]), rel=0.01)


def test_rendement_locatif_ne_deplace_que_le_niveau():
    """y retire exactement y·dt au drift de chaque pas ; y = 0 garde le drift d'avant."""
    dt = 0.5
    sim = _simulate(n_scenarios=200, horizon=20, dt=dt, seed=3)
    without = _drift(sim, 0.0)
    with_yield = _drift(sim, TEST_MARKET_YIELD)
    np.testing.assert_allclose(without - with_yield, TEST_MARKET_YIELD * dt, rtol=0, atol=1e-14)

    legacy = sim['model'].risk_neutral_drift(
        sim['f0t'], sim['P0t'], sim['n_steps'],
        sim['rates'].log_deflator_loadings(), sim['covariances'],
    )
    np.testing.assert_array_equal(without, legacy)


@pytest.mark.parametrize('bad_yield', [-0.01, float('nan'), float('inf')])
def test_rendement_locatif_invalide_refuse(bad_yield):
    sim = _simulate(n_scenarios=20, horizon=5, dt=0.5, seed=1)
    with pytest.raises(ValueError, match='rendement locatif'):
        _drift(sim, bad_yield)


def test_indice_de_prix_black_scholes_martingale_avec_rendement():
    """
    Côté Black-Scholes, la dérive diminuée de y·δ existe déjà.

    L'indice de prix (``price_returns``) retire log(1 + d)·dt à chaque pas de
    l'indice de rendement total : E[D(t) * S(t) * (1 + d)^t] = 1. Ce test le
    fixe pour qu'une modification future ne le casse pas en silence.
    """
    np.random.seed(5)
    dt, horizon, n_scenarios = 0.25, 30, 20_000
    n_steps = int(horizon / dt)
    generator = scenario_generator.ScenarioGenerator(random_seed=5)
    _, _, f0t, P0t = generator._load_yield_curve(None, 'EUR', dt, n_steps)
    params = generator.default_params
    rates = HullWhiteModel(
        a=params['mean_reversion_speed'], sigma=params['hw_volatility'],
        f0t=f0t, P0t=P0t, dt=dt, n_scenarios=n_scenarios, T=horizon,
    )
    rate_results = rates.generate_scenarios()
    equity = BlackScholesEquity(
        sigma=0.18, dividend_yield=TEST_MARKET_YIELD, dt=dt,
        n_scenarios=n_scenarios, T=horizon,
    )
    shocks = np.random.normal(0, 1, (n_scenarios, n_steps))
    price = np.exp(np.cumsum(
        equity.generate_returns(rate_results['Rt'], equity_shocks=shocks)['price_returns'],
        axis=1,
    ))
    times = dt * np.arange(n_steps)
    deflated = rate_results['deflators'] * price * (1 + TEST_MARKET_YIELD) ** times
    mean = deflated.mean(axis=0)
    standard_error = deflated.std(axis=0) / np.sqrt(n_scenarios)
    assert np.all(np.abs(mean - 1.0) <= 4 * standard_error + 1e-12)
