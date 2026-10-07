"""
Étape 1.C.3 : éligibilité et plafonds de versement par enveloppe dans l'optimiseur.

Le régime fr-2026 donne le PEA (actions européennes, 150 000 € de versements à
vie), le Livret A (22 950 €), et des enveloppes sans plafond (CTO, assurance-vie).
"""

import numpy as np
import pandas as pd
import pytest

from investment_calculator.modules import optimizer, scenario_generator
from investment_calculator.tax_regime import load_regime
from investment_calculator.wrapper_allocation import (
    InfeasibleConstraintsError,
    build_wrapper_rules,
    place_in_wrappers,
)

ASSETS = ['stock', 'bond', 'real_estate']


@pytest.fixture(scope='module')
def scenarios():
    return scenario_generator.ScenarioGenerator(random_seed=42).generate({
        'num_scenarios': 200,
        'time_horizon': 10,
        'timestep': 1.0,
        'use_stochastic': True,
        'currency': 'EUR',
        'yield_curve_id': 'eiopa-fr-2018-04',
    })['scenarios']


def _config(scenarios, contribution=10_000.0, **extra):
    return {
        'scenarios': scenarios,
        'investment_time_series': pd.DataFrame({
            'period': range(10), 'net_flow': [contribution] * 10,
        }),
        'optimization_objective': 'max_return',
        **extra,
    }


def _rules(total, available=None):
    return build_wrapper_rules(
        load_regime('FR', 2026), ASSETS, total_contributions=total, n_periods=10,
        available_wrappers=available,
    )


def test_placement_never_exceeds_pea_cap():
    rules = _rules(1_000_000.0)
    placement = place_in_wrappers({'stock': 0.8, 'bond': 0.1, 'real_estate': 0.1}, rules)
    pea = placement[placement['wrapper'] == 'pea']['amount'].sum()
    assert pea <= 150_000.0 + 1e-6
    assert placement['amount'].sum() == pytest.approx(1_000_000.0)


def test_only_pea_cannot_hold_a_large_portfolio():
    rules = _rules(1_000_000.0, available=['pea'])
    with pytest.raises(InfeasibleConstraintsError, match='pea'):
        place_in_wrappers({'stock': 1.0, 'bond': 0.0, 'real_estate': 0.0}, rules)


def test_only_pea_is_infeasible_for_the_optimizer(scenarios):
    config = _config(
        scenarios, contribution=100_000.0,
        wrapper_constraints={'country': 'FR', 'fiscal_year': 2026,
                             'available_wrappers': ['pea']},
    )
    with pytest.raises(InfeasibleConstraintsError):
        optimizer.PortfolioOptimizer().optimize(config)


def test_pea_alone_forces_everything_into_eligible_equity(scenarios):
    """Budget tenant dans le PEA : seules les actions éligibles peuvent être détenues."""
    config = _config(
        scenarios, contribution=5_000.0,
        wrapper_constraints={'country': 'FR', 'fiscal_year': 2026,
                             'available_wrappers': ['pea']},
    )
    config['optimization_objective'] = 'min_volatility'
    results = optimizer.PortfolioOptimizer().optimize(config)
    weights = results['optimal_portfolio']['weights']
    assert weights['stock'] == pytest.approx(1.0, abs=1e-6)
    assert set(results['wrapper_allocation']['wrapper']) == {'pea'}


def test_optimizer_returns_feasible_placement(scenarios):
    config = _config(
        scenarios,
        wrapper_constraints={'country': 'FR', 'fiscal_year': 2026},
    )
    for objective in ('max_sharpe', 'min_volatility', 'max_return', 'risk_parity'):
        config['optimization_objective'] = objective
        results = optimizer.PortfolioOptimizer().optimize(config)
        placement = results['wrapper_allocation']
        assert placement['amount'].sum() == pytest.approx(100_000.0, rel=1e-6)
        assert placement.loc[placement['wrapper'] == 'pea', 'amount'].sum() <= 150_000.0 + 1e-6
        assert sum(results['optimal_portfolio']['weights'].values()) == pytest.approx(1.0)


def test_without_wrapper_constraints_nothing_changes(scenarios):
    results = optimizer.PortfolioOptimizer().optimize(_config(scenarios))
    assert 'wrapper_allocation' not in results


def test_bond_floor_does_not_bind_other_assets(scenarios):
    """min_bond_allocation ne borne que les obligations (point 4 du journal)."""
    config = _config(scenarios)
    config['optimization_objective'] = 'max_return'
    config['user_constraints'] = {'min_bond_allocation': 0.15, 'max_equity_allocation': 0.6}
    weights = optimizer.PortfolioOptimizer().optimize(config)['optimal_portfolio']['weights']
    assert weights['bond'] >= 0.15 - 1e-6
    assert weights['stock'] <= 0.6 + 1e-6
    assert weights['real_estate'] >= 0.0


def test_random_profiles_are_always_feasible_or_explicitly_refused(scenarios):
    rng = np.random.default_rng(7)
    wrappers = ['cto', 'pea', 'assurance_vie', 'per', 'livret_a', 'immobilier_direct']
    n_ok = 0
    for _ in range(200):
        chosen = list(rng.choice(wrappers, size=rng.integers(1, 5), replace=False))
        total = float(rng.uniform(1_000, 2_000_000))
        rules = _rules(total, available=chosen)
        constraints = optimizer.PortfolioOptimizer()._build_weight_constraints(
            ASSETS, {'min_weight': 0.0, 'max_weight': 1.0}, {}, rules
        )
        try:
            w = constraints.feasible_start()
        except InfeasibleConstraintsError:
            continue
        n_ok += 1
        assert constraints.is_feasible(w)
        placement = place_in_wrappers(dict(zip(ASSETS, w, strict=True)), rules)
        assert placement['amount'].sum() == pytest.approx(total, rel=1e-6)
        for _, row in placement.iterrows():
            assert row['amount'] >= -1e-6
    assert n_ok > 0


# --- Étape 1.D.2 : impôt par enveloppe dans la simulation --------------------------------------

from investment_calculator.modules import tax_engine  # noqa: E402
from investment_calculator.tax_regime import load_regime as _load_regime  # noqa: E402


def _tax_config(**wrapper):
    return {'country': 'FR', 'fiscal_year': 2026, **wrapper}


def _no_cost(config):
    config['optimization_params'] = {
        'transaction_costs': {'stock': 0.0, 'bond': 0.0, 'real_estate': 0.0},
    }
    return config


def test_pea_only_matches_closed_form(scenarios):
    """PEA seul, actions seules, sans coût : patrimoine net = brut moins prélèvements sociaux."""
    regime = _load_regime('FR', 2026)
    config = _no_cost(_config(
        scenarios, contribution=5_000.0,
        wrapper_constraints=_tax_config(available_wrappers=['pea']),
    ))
    config['optimization_objective'] = 'min_volatility'
    results = optimizer.PortfolioOptimizer().optimize(config)
    terminal = results['simulation_results']['terminal_wealth']

    # Versements : mise initiale puis 5 000 en fin de chaque année, soit 10 versements.
    contributions = 10 * 5_000.0
    pre = terminal['pre_liquidation_wealth'].to_numpy()
    gain = np.clip(pre - contributions, 0.0, None)
    assert terminal['exit_tax_pea'].to_numpy() == pytest.approx(gain * regime.social_rate)
    assert terminal['wealth'].to_numpy() == pytest.approx(pre - gain * regime.social_rate)
    assert (terminal['annual_income_tax_pea'] == 0).all()


def test_net_wealth_is_below_gross_and_taxes_are_reported(scenarios):
    config = _config(scenarios, wrapper_constraints=_tax_config())
    results = optimizer.PortfolioOptimizer().optimize(config)
    terminal = results['simulation_results']['terminal_wealth']
    assert (terminal['wealth'] <= terminal['pre_liquidation_wealth'] + 1e-9).all()
    stats = results['simulation_results']['statistics']
    assert set(stats['mean_tax_by_wrapper']) == set(results['wrapper_allocation']['wrapper'])
    assert stats['mean_pre_liquidation_wealth'] > stats['mean_terminal_wealth']


def test_after_tax_scenario_columns_are_not_taxed_twice(scenarios):
    taxed = tax_engine.apply_taxes_simple(scenarios, jurisdiction='FR')['after_tax_scenarios']
    base = optimizer.PortfolioOptimizer().optimize(
        _config(scenarios, wrapper_constraints=_tax_config())
    )
    again = optimizer.PortfolioOptimizer().optimize(
        _config(taxed, wrapper_constraints=_tax_config())
    )
    assert again['optimal_portfolio']['weights'] == base['optimal_portfolio']['weights']
    assert again['simulation_results']['statistics']['median_terminal_wealth'] == pytest.approx(
        base['simulation_results']['statistics']['median_terminal_wealth']
    )


def test_unmodelled_wrappers_are_declared_not_silently_used(scenarios):
    results = optimizer.PortfolioOptimizer().optimize(
        _config(scenarios, wrapper_constraints=_tax_config())
    )
    assert set(results['wrapper_gaps']) == {'per', 'immobilier_direct'}
    assert not {'per', 'immobilier_direct'} & set(results['wrapper_allocation']['wrapper'])


def test_explicit_unmodelled_wrapper_is_refused(scenarios):
    config = _config(
        scenarios, wrapper_constraints=_tax_config(available_wrappers=['cto', 'per']),
    )
    with pytest.raises(NotImplementedError, match='per'):
        optimizer.PortfolioOptimizer().optimize(config)


def test_withdrawals_are_refused_with_wrapper_tax(scenarios):
    config = _config(scenarios, wrapper_constraints=_tax_config())
    config['investment_time_series'] = pd.DataFrame({
        'period': range(10), 'net_flow': [10_000.0] * 9 + [-5_000.0],
    })
    with pytest.raises(NotImplementedError, match='retraits'):
        optimizer.PortfolioOptimizer().optimize(config)


def test_disabling_wrapper_tax_keeps_gross_wealth(scenarios):
    on = optimizer.PortfolioOptimizer().optimize(
        _config(scenarios, wrapper_constraints=_tax_config())
    )
    off = optimizer.PortfolioOptimizer().optimize(
        _config(scenarios, wrapper_constraints=_tax_config(apply_wrapper_tax=False))
    )
    assert 'exit_tax_pea' not in off['simulation_results']['terminal_wealth'].columns
    assert (
        off['simulation_results']['statistics']['median_terminal_wealth']
        > on['simulation_results']['statistics']['median_terminal_wealth']
    )


def test_cto_reinvested_income_is_not_taxed_again_at_exit(scenarios):
    """CTO seul : l'impôt de sortie porte sur le prix de revient relevé, pas sur les versements."""
    regime = _load_regime('FR', 2026)
    config = _no_cost(_config(
        scenarios, contribution=5_000.0,
        wrapper_constraints=_tax_config(available_wrappers=['cto']),
    ))
    config['optimization_objective'] = 'min_volatility'
    config['user_constraints'] = {'min_bond_allocation': 0.0}
    results = optimizer.PortfolioOptimizer().optimize(config)
    terminal = results['simulation_results']['terminal_wealth']
    pre = terminal['pre_liquidation_wealth'].to_numpy()
    naive = np.clip(pre - 50_000.0, 0.0, None) * (
        regime.flat_tax_income_rate + regime.social_rate
    )
    assert (terminal['annual_income_tax_cto'] > 0).all()
    assert (terminal['exit_tax_cto'].to_numpy() <= naive + 1e-9).all()
    assert (terminal['exit_tax_cto'].to_numpy() < naive - 1.0).any()
