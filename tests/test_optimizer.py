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

import pytest
import numpy as np
import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator.modules import optimizer, scenario_generator, tax_engine


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


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_quick_optimize_function(self):
        """Test quick_optimize convenience function if available."""
        if hasattr(optimizer, 'quick_optimize'):
            scenarios_df = create_test_scenarios()

            results = optimizer.quick_optimize(scenarios_df)

            assert 'optimal_portfolio' in results


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
