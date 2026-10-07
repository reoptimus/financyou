"""
Comprehensive Unit Tests for Module 4: Portfolio Optimization (MOCA)

Tests cover:
- PortfolioOptimizer initialization
- Configuration validation
- Asset return extraction
- Portfolio optimization (max Sharpe, min volatility, etc.)
- Efficient frontier generation
- Monte Carlo simulations
- Sensitivity analysis
- Goal analysis
- Edge cases and data quality
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator.modules import optimizer, scenario_generator


# Helper functions
def create_test_scenarios(num_scenarios=20):
    """Create test scenarios for optimizer testing."""
    gen = scenario_generator.ScenarioGenerator(random_seed=42)
    config = {
        'num_scenarios': num_scenarios,
        'time_horizon': 10,
        'timestep': 1.0,
        'use_stochastic': False
    }
    return gen.generate(config)['scenarios']


def create_test_optimizer_config():
    """Create test configuration for optimizer."""
    scenarios_df = create_test_scenarios()

    # Simple time series
    time_series = pd.DataFrame({
        'period': range(10),
        'age': range(35, 45),
        'contribution': [1000] * 10
    })

    constraints = {
        'max_equity_allocation': 0.80,
        'min_bond_allocation': 0.15,
        'exclude_sectors': [],
        'rebalancing_frequency': 'annual'
    }

    return {
        'scenarios': scenarios_df,
        'user_constraints': constraints,
        'investment_time_series': time_series,
        'optimization_objective': 'max_sharpe'
    }


class TestPortfolioOptimizerInitialization:
    """Test PortfolioOptimizer initialization."""

    def test_init(self):
        """Test basic initialization."""
        opt = optimizer.PortfolioOptimizer()
        assert opt is not None

    def test_multiple_instances(self):
        """Test creating multiple instances."""
        opt1 = optimizer.PortfolioOptimizer()
        opt2 = optimizer.PortfolioOptimizer()
        assert opt1 is not opt2


class TestConfigurationValidation:
    """Test configuration validation."""

    def test_valid_config(self):
        """Test validation with valid configuration."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)

        # Should return expected keys
        assert 'optimal_portfolio' in results
        assert 'efficient_frontier' in results
        assert 'simulation_results' in results

    def test_missing_scenarios(self):
        """Test that missing scenarios raises error or uses defaults."""
        opt = optimizer.PortfolioOptimizer()

        # Try with minimal config (may have defaults)
        try:
            config = {
                'user_constraints': {},
                'optimization_objective': 'max_sharpe'
            }
            results = opt.optimize(config)
            # If it works, check it has results
            assert 'optimal_portfolio' in results
        except (ValueError, KeyError):
            # Expected if scenarios are required
            pass

    def test_default_optimization_params(self):
        """Test that default optimization params are applied."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()
        # Don't provide optimization_params
        if 'optimization_params' in config:
            del config['optimization_params']

        results = opt.optimize(config)

        # Should complete with defaults
        assert 'optimal_portfolio' in results


class TestOptimalPortfolio:
    """Test optimal portfolio generation."""

    def test_optimal_portfolio_structure(self):
        """Test optimal portfolio output structure."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        portfolio = results['optimal_portfolio']

        # Check expected fields
        assert 'weights' in portfolio
        assert isinstance(portfolio['weights'], dict)

    def test_weights_sum_to_one(self):
        """Test that portfolio weights sum to approximately 1."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        weights = results['optimal_portfolio']['weights']

        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01  # Allow small numerical error

    def test_weights_non_negative(self):
        """Test that portfolio weights are non-negative (long-only)."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        weights = results['optimal_portfolio']['weights']

        # All weights should be non-negative
        for weight in weights.values():
            assert weight >= -0.001  # Allow tiny numerical errors

    def test_portfolio_metrics(self):
        """Test that portfolio has expected metrics."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        portfolio = results['optimal_portfolio']

        # Should have performance metrics
        expected_metrics = ['expected_return', 'volatility', 'sharpe_ratio']
        for metric in expected_metrics:
            if metric in portfolio:
                assert isinstance(portfolio[metric], (int, float))


class TestOptimizationObjectives:
    """Test different optimization objectives."""

    def test_max_sharpe_objective(self):
        """Test maximum Sharpe ratio objective."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()
        config['optimization_objective'] = 'max_sharpe'

        results = opt.optimize(config)

        assert 'optimal_portfolio' in results
        if 'sharpe_ratio' in results['optimal_portfolio']:
            assert results['optimal_portfolio']['sharpe_ratio'] is not None

    def test_min_volatility_objective(self):
        """Test minimum volatility objective."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()
        config['optimization_objective'] = 'min_volatility'

        results = opt.optimize(config)

        assert 'optimal_portfolio' in results
        if 'volatility' in results['optimal_portfolio']:
            assert results['optimal_portfolio']['volatility'] > 0

    def test_equal_weight_objective(self):
        """Test equal weight portfolio."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()
        config['optimization_objective'] = 'equal_weight'

        results = opt.optimize(config)
        weights = results['optimal_portfolio']['weights']

        # All non-zero weights should be approximately equal
        non_zero_weights = [w for w in weights.values() if w > 0.01]
        if len(non_zero_weights) > 1:
            avg_weight = sum(non_zero_weights) / len(non_zero_weights)
            for w in non_zero_weights:
                assert abs(w - avg_weight) < 0.1  # Allow some variation


class TestEfficientFrontier:
    """Test efficient frontier generation."""

    def test_efficient_frontier_structure(self):
        """Test efficient frontier DataFrame structure."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        frontier = results['efficient_frontier']

        # Should be a DataFrame
        assert isinstance(frontier, pd.DataFrame)

    def test_efficient_frontier_columns(self):
        """Test efficient frontier has expected columns."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        frontier = results['efficient_frontier']

        # Should have return and risk columns
        if len(frontier) > 0:
            expected_cols = ['expected_return', 'volatility']
            for col in expected_cols:
                if col in frontier.columns:
                    assert not frontier[col].isnull().all()

    def test_efficient_frontier_points(self):
        """Test that frontier has multiple points."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        frontier = results['efficient_frontier']

        # Should have at least a few points
        assert len(frontier) >= 2


class TestSimulationResults:
    """Test Monte Carlo simulation results."""

    def test_simulation_results_structure(self):
        """Test simulation results structure."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        simulations = results['simulation_results']

        # Should be a dictionary
        assert isinstance(simulations, dict)

    def test_simulation_has_scenarios(self):
        """Test that simulations use multiple scenarios."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        simulations = results['simulation_results']

        # Should have scenario-based results
        if 'portfolio_values' in simulations:
            values = simulations['portfolio_values']
            assert len(values) > 0


class TestUserConstraints:
    """Test user constraint handling."""

    def test_equity_allocation_constraint(self):
        """Test maximum equity allocation constraint."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()
        config['user_constraints']['max_equity_allocation'] = 0.50

        results = opt.optimize(config)
        weights = results['optimal_portfolio']['weights']

        # Stock weight should respect constraint
        if 'stocks' in weights:
            assert weights['stocks'] <= 0.51  # Allow small numerical error

    def test_bond_allocation_constraint(self):
        """Test minimum bond allocation constraint."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()
        config['user_constraints']['min_bond_allocation'] = 0.20

        results = opt.optimize(config)
        weights = results['optimal_portfolio']['weights']

        # Bond weight should respect constraint
        if 'bonds' in weights:
            assert weights['bonds'] >= 0.19  # Allow small numerical error


class TestGoalAnalysis:
    """Test goal achievement analysis."""

    def test_goal_analysis_structure(self):
        """Test goal analysis structure."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        goal_analysis = results['goal_analysis']

        # Should be a dictionary
        assert isinstance(goal_analysis, dict)

    def test_goal_probability(self):
        """Test goal achievement probability."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        # Add goal target
        config['goal_target'] = 500000

        results = opt.optimize(config)
        goal_analysis = results['goal_analysis']

        # Should have probability metric if implemented
        if 'success_probability' in goal_analysis:
            prob = goal_analysis['success_probability']
            assert 0 <= prob <= 1


class TestSensitivityAnalysis:
    """Test sensitivity analysis."""

    def test_sensitivity_analysis_structure(self):
        """Test sensitivity analysis structure."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        sensitivity = results['sensitivity_analysis']

        # Should be a dictionary
        assert isinstance(sensitivity, dict)


class TestEdgeCases:
    """Test edge cases."""

    def test_single_scenario(self):
        """Test optimization with single scenario."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        # Replace with single scenario
        single_scenario = create_test_scenarios(num_scenarios=1)
        config['scenarios'] = single_scenario

        results = opt.optimize(config)

        # Should complete
        assert 'optimal_portfolio' in results

    def test_very_short_time_horizon(self):
        """Test optimization with very short horizon."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        # Short time series
        config['investment_time_series'] = pd.DataFrame({
            'period': [0],
            'age': [35],
            'contribution': [1000]
        })

        results = opt.optimize(config)

        # Should complete
        assert 'optimal_portfolio' in results

    def test_extreme_constraints(self):
        """Test optimization with extreme constraints."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        # Very tight but feasible constraints
        config['user_constraints']['max_equity_allocation'] = 0.20
        config['user_constraints']['min_bond_allocation'] = 0.60

        try:
            results = opt.optimize(config)
            # Should still find a solution
            assert 'optimal_portfolio' in results
        except ValueError:
            # Some constraint combinations may be infeasible - that's acceptable
            pass


class TestDataQuality:
    """Test data quality and consistency."""

    def test_no_null_values_in_weights(self):
        """Test that weights have no null values."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        weights = results['optimal_portfolio']['weights']

        # No null weights
        for weight in weights.values():
            assert weight is not None
            assert not np.isnan(weight)

    def test_no_infinite_values(self):
        """Test that results have no infinite values."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results = opt.optimize(config)
        weights = results['optimal_portfolio']['weights']

        # No infinite weights
        for weight in weights.values():
            assert not np.isinf(weight)

    def test_consistent_optimization(self):
        """Test that same inputs produce same outputs."""
        opt1 = optimizer.PortfolioOptimizer()
        opt2 = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()

        results1 = opt1.optimize(config.copy())
        results2 = opt2.optimize(config.copy())

        # Weights should be similar (may not be exactly equal due to numerical optimization)
        weights1 = results1['optimal_portfolio']['weights']
        weights2 = results2['optimal_portfolio']['weights']

        # Check that key weights exist in both
        for asset in weights1.keys():
            if asset in weights2:
                # Should be reasonably close
                assert abs(weights1[asset] - weights2[asset]) < 0.1


class TestPeriodicCovariance:
    """
    Étape 1.C.1 : les moments sont estimés sur les rendements périodiques.

    L'ancienne version moyennait les pas de temps de chaque scénario avant
    d'estimer la covariance, ce qui divisait la volatilité par ~√T.
    """

    @staticmethod
    def _periodic_returns(scenarios_df):
        cols = [c for c in scenarios_df.columns if c.endswith('_return_after_tax')]
        if not cols:
            cols = [c for c in scenarios_df.columns if c.endswith('_return')]
        return scenarios_df[cols]

    def test_single_asset_volatility_is_periodic_volatility(self):
        """Un portefeuille 100 % actions a la volatilité annuelle des actions, pas σ/√T."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()
        config['scenarios'] = create_test_scenarios(num_scenarios=200)
        config['optimization_objective'] = 'max_return'
        config['user_constraints'] = {}

        portfolio = opt.optimize(config)['optimal_portfolio']
        best_asset = max(portfolio['weights'], key=portfolio['weights'].get)
        periodic = self._periodic_returns(config['scenarios'])
        asset_vol = periodic[f'{best_asset}_return'].std()
        horizon = config['scenarios']['time_period'].nunique()

        assert portfolio['expected_volatility'] == pytest.approx(asset_vol, rel=1e-9)
        # L'ancienne estimation était de l'ordre de asset_vol / √T.
        assert portfolio['expected_volatility'] > 2 * asset_vol / np.sqrt(horizon)

    def test_portfolio_volatility_same_order_as_assets(self):
        """La volatilité du portefeuille optimal est du même ordre que celle des actifs."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()
        config['scenarios'] = create_test_scenarios(num_scenarios=200)

        portfolio = opt.optimize(config)['optimal_portfolio']
        asset_vols = self._periodic_returns(config['scenarios']).std()

        # Un portefeuille long-only ne peut pas dépasser la plus volatile de ses
        # composantes, et la diversification seule ne divise pas σ par √T.
        assert portfolio['expected_volatility'] <= asset_vols.max() + 1e-12
        assert portfolio['expected_volatility'] > asset_vols.min() / 3

    def test_non_annual_timestep_is_refused(self):
        """Un pas infra-annuel est refusé plutôt qu'annualisé au hasard."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        scenarios = gen.generate({
            'num_scenarios': 5, 'time_horizon': 2, 'timestep': 0.25, 'use_stochastic': False
        })['scenarios']
        config = create_test_optimizer_config()
        config['scenarios'] = scenarios

        with pytest.raises(ValueError, match='pas annuel'):
            optimizer.PortfolioOptimizer().optimize(config)

    def test_max_drawdown_is_computed_per_scenario(self):
        """La perte maximale est une vraie mesure, comprise dans [0, 1]."""
        opt = optimizer.PortfolioOptimizer()
        config = create_test_optimizer_config()
        config['scenarios'] = create_test_scenarios(num_scenarios=100)

        drawdown = opt.optimize(config)['optimal_portfolio']['max_drawdown']

        assert 0.0 < drawdown < 1.0


@pytest.fixture(scope='module')
def frontier_results():
    """
    Scénarios du chemin stochastique : le chemin simple construit trois actifs
    à partir de deux chocs seulement, sa covariance est donc singulière (voir
    test_minimum_variance_portfolio_is_unique).
    """
    gen = scenario_generator.ScenarioGenerator(random_seed=42)
    scenarios = gen.generate({
        'num_scenarios': 200,
        'time_horizon': 10,
        'timestep': 1.0,
        'use_stochastic': True,
        'currency': 'EUR',
        'yield_curve_id': 'eiopa-fr-2018-04',
    })['scenarios']
    config = create_test_optimizer_config()
    config['scenarios'] = scenarios
    config['optimization_objective'] = 'min_volatility'
    config['user_constraints'] = {}
    return config, optimizer.PortfolioOptimizer().optimize(config)


class TestEfficientFrontierProperties:
    """Étape 1.C.1 : propriétés de la frontière efficiente."""

    @pytest.fixture
    def results(self, frontier_results):
        return frontier_results

    def test_frontier_weights_sum_to_one(self, results):
        _, res = results
        frontier = res['efficient_frontier']
        weight_cols = [c for c in frontier.columns if c.endswith('_weight')]
        np.testing.assert_allclose(frontier[weight_cols].sum(axis=1), 1.0, atol=1e-6)

    def test_return_increases_with_risk_on_efficient_branch(self, results):
        """Au-dessus du portefeuille de variance minimale, plus de risque ⇒ plus de rendement."""
        _, res = results
        frontier = res['efficient_frontier'].sort_values('return')
        min_var_idx = frontier['volatility'].idxmin()
        efficient = frontier.loc[frontier['return'] >= frontier.loc[min_var_idx, 'return']]

        assert len(efficient) > 2
        assert (np.diff(efficient['volatility'].to_numpy()) >= -1e-6).all()

    def test_minimum_variance_portfolio_is_unique(self, results):
        """
        La covariance est définie positive : la variance est strictement
        convexe, le portefeuille de variance minimale est donc unique et
        coïncide avec le point le moins risqué de la frontière.
        """
        config, res = results
        opt = optimizer.PortfolioOptimizer()
        asset_returns = opt._extract_asset_returns(config['scenarios'])

        assert np.linalg.eigvalsh(asset_returns.cov().to_numpy()).min() > 0

        min_vol = res['optimal_portfolio']['expected_volatility']
        assert min_vol == pytest.approx(res['efficient_frontier']['volatility'].min(), rel=1e-3)


class TestRebalancingAndTransactionCosts:
    """Étape 1.C.4 : rééquilibrage à seuil et coûts de transaction appliqués."""

    @staticmethod
    def _run(threshold, cost_scale=1.0, num_scenarios=100):
        config = create_test_optimizer_config()
        config['scenarios'] = create_test_scenarios(num_scenarios=num_scenarios)
        config['optimization_objective'] = 'equal_weight'
        config['user_constraints'] = {}
        config['optimization_params'] = {
            'rebalancing_threshold': threshold,
            'transaction_costs': {
                'stocks': 0.001 * cost_scale,
                'bonds': 0.0005 * cost_scale,
                'real_estate': 0.002 * cost_scale,
            },
        }
        return optimizer.PortfolioOptimizer().optimize(config)['simulation_results']

    def test_constant_mix_without_costs_matches_closed_form(self):
        """
        Sans coût et rééquilibré chaque année, le patrimoine suit
        W(t+1) = W(t)·(1 + w·r(t+1)) + versement(t+1), sans double compte de la
        mise initiale.
        """
        sim = self._run(threshold=0.0, cost_scale=0.0, num_scenarios=3)
        config = create_test_optimizer_config()
        scenario = create_test_scenarios(num_scenarios=3)
        first = scenario[scenario['scenario_id'] == scenario['scenario_id'].iloc[0]]
        asset_columns = ['stock_return', 'bond_return', 'real_estate_return']
        portfolio_returns = first[asset_columns].mean(axis=1)
        flows = config['investment_time_series']['contribution'].to_numpy()

        expected = [flows[0]]
        for t, r in enumerate(portfolio_returns, start=1):
            flow = flows[t] if t < len(flows) else 0.0
            expected.append(expected[-1] * (1 + r) + flow)

        path = sim['wealth_paths'].iloc[0, 1:].to_numpy(dtype=float)
        np.testing.assert_allclose(path, expected, rtol=1e-12)

    def test_costs_reduce_net_wealth_monotonically(self):
        medians = [
            self._run(threshold=0.0, cost_scale=scale)['statistics']['median_terminal_wealth']
            for scale in (0.0, 1.0, 5.0, 20.0)
        ]
        assert all(a > b for a, b in zip(medians, medians[1:], strict=False))

    def test_cost_drag_increases_with_turnover(self):
        """À turnover croissant, la performance nette (après coûts) décroît."""
        thresholds = (1.0, 0.10, 0.02, 0.0)  # du moins au plus de rééquilibrages
        turnovers, drags = [], []
        for threshold in thresholds:
            gross = self._run(threshold, cost_scale=0.0)['terminal_wealth']['wealth']
            net = self._run(threshold, cost_scale=1.0)
            turnovers.append(net['rebalancing_schedule']['mean_turnover'].sum())
            drags.append(float((gross - net['terminal_wealth']['wealth']).mean()))

        assert turnovers == sorted(turnovers)
        assert drags[0] == pytest.approx(0.0, abs=1e-9)
        assert all(a < b for a, b in zip(drags, drags[1:], strict=False))

    def test_rebalancing_schedule_reports_real_activity(self):
        schedule = self._run(threshold=0.05)['rebalancing_schedule']
        assert len(schedule) == 10
        assert schedule['share_of_scenarios_rebalanced'].between(0, 1).all()
        assert schedule['mean_cost'].sum() > 0

    def test_missing_transaction_cost_is_an_error(self):
        config = create_test_optimizer_config()
        config['optimization_params'] = {'transaction_costs': {'stocks': 0.001}}
        with pytest.raises(ValueError, match='coût de transaction'):
            optimizer.PortfolioOptimizer().optimize(config)

    def test_missing_investment_flows_is_an_error(self):
        config = create_test_optimizer_config()
        config['investment_time_series'] = pd.DataFrame()
        with pytest.raises(ValueError, match='investment_time_series'):
            optimizer.PortfolioOptimizer().optimize(config)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_quick_optimize_function(self):
        """Test quick_optimize convenience function if available."""
        if hasattr(optimizer, 'quick_optimize'):
            scenarios_df = create_test_scenarios()

            results = optimizer.quick_optimize(scenarios_df, initial_wealth=10_000)

            assert 'optimal_portfolio' in results


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
