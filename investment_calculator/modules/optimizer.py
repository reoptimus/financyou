"""
Module 4: Portfolio Optimization (MOCA)

This module optimizes portfolio allocation and simulates investment outcomes across scenarios.

INPUT STRUCTURE:
{
    'scenarios': pd.DataFrame,          # After-tax scenarios from Module 2
    'user_constraints': dict,           # From Module 3 validated profile
    'investment_time_series': pd.DataFrame,  # From Module 3
    'optimization_objective': str,      # 'max_return', 'max_sharpe', 'min_volatility',
                                       # 'min_cvar', 'risk_parity', 'target_return'
    'optimization_params': {
        'target_return': float,
        'risk_aversion': float,
        'confidence_level': float,
        'min_weight': float,
        'max_weight': float,
        'transaction_costs': dict,
        'rebalancing_threshold': float
    },
    'asset_universe': dict
}

OUTPUT STRUCTURE:
{
    'optimal_portfolio': dict,
    'efficient_frontier': pd.DataFrame,
    'simulation_results': dict,
    'rebalancing_schedule': pd.DataFrame,
    'sensitivity_analysis': dict,
    'goal_analysis': dict
}
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from scipy.optimize import minimize
from enum import Enum


class OptimizationObjective(Enum):
    """Portfolio optimization objectives"""
    MAX_RETURN = "max_return"
    MAX_SHARPE = "max_sharpe"
    MIN_VOLATILITY = "min_volatility"
    MIN_CVAR = "min_cvar"
    RISK_PARITY = "risk_parity"
    TARGET_RETURN = "target_return"
    EQUAL_WEIGHT = "equal_weight"


class PortfolioOptimizer:
    """
    Portfolio Optimization Engine (MOCA) - Module 4

    Optimizes portfolio allocation and simulates outcomes across scenarios.

    Example:
        >>> from investment_calculator.modules import optimizer
        >>> config = {
        ...     'scenarios': after_tax_scenarios_df,
        ...     'user_constraints': profile['constraints'],
        ...     'investment_time_series': time_series_df,
        ...     'optimization_objective': 'max_sharpe'
        ... }
        >>> opt = optimizer.PortfolioOptimizer()
        >>> results = opt.optimize(config)
        >>> print(results['optimal_portfolio'])
    """

    def __init__(self):
        """Initialize the Portfolio Optimizer."""
        pass

    def optimize(self, config: Dict) -> Dict:
        """
        Optimize portfolio and run simulations.

        Args:
            config: Configuration dictionary (see module docstring)

        Returns:
            Dictionary with optimal portfolio, simulations, and analysis
        """
        # Validate configuration
        validated_config = self._validate_config(config)

        scenarios_df = validated_config['scenarios']
        objective = validated_config['optimization_objective']
        params = validated_config['optimization_params']
        constraints = validated_config['user_constraints']

        # Extract returns for optimization
        asset_returns = self._extract_asset_returns(scenarios_df)

        # Run optimization
        optimal_portfolio = self._run_optimization(
            asset_returns,
            objective,
            params,
            constraints
        )

        # Generate efficient frontier
        efficient_frontier = self._generate_efficient_frontier(
            asset_returns,
            constraints,
            params
        )

        # Run simulations
        simulation_results = self._run_simulations(
            scenarios_df,
            optimal_portfolio,
            validated_config['investment_time_series'],
            params
        )

        # Create rebalancing schedule
        rebalancing_schedule = self._create_rebalancing_schedule(
            optimal_portfolio,
            params,
            validated_config['investment_time_series']
        )

        # Sensitivity analysis
        sensitivity_analysis = self._sensitivity_analysis(
            asset_returns,
            optimal_portfolio,
            params
        )

        # Goal analysis
        goal_analysis = self._analyze_goals(
            simulation_results,
            validated_config.get('goal_amount', None)
        )

        return {
            'optimal_portfolio': optimal_portfolio,
            'efficient_frontier': efficient_frontier,
            'simulation_results': simulation_results,
            'rebalancing_schedule': rebalancing_schedule,
            'sensitivity_analysis': sensitivity_analysis,
            'goal_analysis': goal_analysis
        }

    def _validate_config(self, config: Dict) -> Dict:
        """
        Validate and complete configuration.

        Args:
            config: User configuration

        Returns:
            Validated configuration
        """
        if 'scenarios' not in config:
            raise ValueError("Missing required field: scenarios")

        validated = {
            'scenarios': config['scenarios'],
            'user_constraints': config.get('user_constraints', {}),
            'investment_time_series': config.get('investment_time_series', pd.DataFrame()),
            'optimization_objective': config.get('optimization_objective', 'max_sharpe'),
            'asset_universe': config.get('asset_universe', {}),
            'goal_amount': config.get('goal_amount', None)
        }

        # Default optimization parameters
        default_params = {
            'target_return': 0.08,
            'risk_aversion': 5.0,
            'confidence_level': 0.95,
            'min_weight': 0.0,
            'max_weight': 1.0,
            'transaction_costs': {
                'stocks': 0.001,
                'bonds': 0.0005,
                'real_estate': 0.002
            },
            'rebalancing_threshold': 0.05
        }

        user_params = config.get('optimization_params', {})
        validated['optimization_params'] = {**default_params, **user_params}

        return validated

    def _extract_asset_returns(self, scenarios_df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract asset returns from scenarios DataFrame.

        Args:
            scenarios_df: Scenarios with after-tax returns

        Returns:
            DataFrame of asset returns (scenarios × assets)
        """
        # Identify return columns (after_tax versions if available)
        return_columns = []
        asset_names = []

        for col in scenarios_df.columns:
            if 'return' in col.lower() and 'after_tax' in col.lower():
                return_columns.append(col)
                # Extract asset name
                asset_name = col.replace('_after_tax', '').replace('_return', '')
                asset_names.append(asset_name)

        if not return_columns:
            # Fallback to pre-tax returns
            for col in scenarios_df.columns:
                if 'return' in col.lower() and col not in ['interest_rate', 'inflation', 'gdp_growth']:
                    return_columns.append(col)
                    asset_name = col.replace('_return', '')
                    asset_names.append(asset_name)

        # Create pivot table: scenarios × assets
        # Group by scenario_id and calculate mean returns
        returns_by_scenario = scenarios_df.groupby('scenario_id')[return_columns].mean()
        returns_by_scenario.columns = asset_names

        return returns_by_scenario

    def _run_optimization(
        self,
        asset_returns: pd.DataFrame,
        objective: str,
        params: Dict,
        constraints: Dict
    ) -> Dict:
        """
        Run portfolio optimization.

        Args:
            asset_returns: Asset return DataFrame
            objective: Optimization objective
            params: Optimization parameters
            constraints: User constraints

        Returns:
            Dictionary with optimal weights and statistics
        """
        n_assets = len(asset_returns.columns)
        asset_names = list(asset_returns.columns)

        # Calculate mean returns and covariance
        mean_returns = asset_returns.mean().values
        cov_matrix = asset_returns.cov().values

        # Handle constraints
        min_weight = max(params['min_weight'], constraints.get('min_bond_allocation', 0.0))
        max_weight = min(params['max_weight'], constraints.get('max_equity_allocation', 1.0))

        if objective == 'max_sharpe':
            optimal_weights = self._optimize_max_sharpe(
                mean_returns, cov_matrix, n_assets, min_weight, max_weight
            )
        elif objective == 'min_volatility':
            optimal_weights = self._optimize_min_volatility(
                cov_matrix, n_assets, min_weight, max_weight
            )
        elif objective == 'max_return':
            # Max return = 100% in highest return asset (within constraints)
            max_return_idx = np.argmax(mean_returns)
            optimal_weights = np.zeros(n_assets)
            optimal_weights[max_return_idx] = 1.0
        elif objective == 'target_return':
            target_return = params['target_return']
            optimal_weights = self._optimize_target_return(
                mean_returns, cov_matrix, n_assets, target_return, min_weight, max_weight
            )
        elif objective == 'risk_parity':
            optimal_weights = self._optimize_risk_parity(
                cov_matrix, n_assets, min_weight, max_weight
            )
        elif objective == 'equal_weight':
            optimal_weights = np.ones(n_assets) / n_assets
        else:
            # Default to max Sharpe
            optimal_weights = self._optimize_max_sharpe(
                mean_returns, cov_matrix, n_assets, min_weight, max_weight
            )

        # Calculate portfolio statistics
        portfolio_return = np.dot(optimal_weights, mean_returns)
        portfolio_variance = np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0.0

        # Calculate max drawdown (estimated from simulations)
        max_drawdown = self._estimate_max_drawdown(asset_returns, optimal_weights)

        return {
            'weights': dict(zip(asset_names, optimal_weights)),
            'expected_return': float(portfolio_return),
            'expected_volatility': float(portfolio_volatility),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown)
        }

    def _optimize_max_sharpe(
        self,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        n_assets: int,
        min_weight: float,
        max_weight: float
    ) -> np.ndarray:
        """Optimize for maximum Sharpe ratio."""
        def neg_sharpe(weights):
            portfolio_return = np.dot(weights, mean_returns)
            portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return -portfolio_return / portfolio_std if portfolio_std > 0 else 1e10

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        x0 = np.ones(n_assets) / n_assets

        result = minimize(neg_sharpe, x0, method='SLSQP', bounds=bounds, constraints=constraints)

        return result.x if result.success else x0

    def _optimize_min_volatility(
        self,
        cov_matrix: np.ndarray,
        n_assets: int,
        min_weight: float,
        max_weight: float
    ) -> np.ndarray:
        """Optimize for minimum volatility."""
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        x0 = np.ones(n_assets) / n_assets

        result = minimize(portfolio_volatility, x0, method='SLSQP', bounds=bounds, constraints=constraints)

        return result.x if result.success else x0

    def _optimize_target_return(
        self,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        n_assets: int,
        target_return: float,
        min_weight: float,
        max_weight: float
    ) -> np.ndarray:
        """Optimize for target return with minimum volatility."""
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
            {'type': 'eq', 'fun': lambda w: np.dot(w, mean_returns) - target_return}
        ]
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        x0 = np.ones(n_assets) / n_assets

        result = minimize(portfolio_volatility, x0, method='SLSQP', bounds=bounds, constraints=constraints)

        if result.success:
            return result.x
        else:
            # If target return not achievable, return max Sharpe
            return self._optimize_max_sharpe(mean_returns, cov_matrix, n_assets, min_weight, max_weight)

    def _optimize_risk_parity(
        self,
        cov_matrix: np.ndarray,
        n_assets: int,
        min_weight: float,
        max_weight: float
    ) -> np.ndarray:
        """Optimize for risk parity (equal risk contribution)."""
        def risk_parity_objective(weights):
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            marginal_contrib = np.dot(cov_matrix, weights)
            risk_contrib = weights * marginal_contrib / np.sqrt(portfolio_variance)
            return np.sum((risk_contrib - risk_contrib.mean()) ** 2)

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        x0 = np.ones(n_assets) / n_assets

        result = minimize(risk_parity_objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)

        return result.x if result.success else x0

    def _estimate_max_drawdown(self, asset_returns: pd.DataFrame, weights: np.ndarray) -> float:
        """
        Estimate maximum drawdown from scenarios.

        Args:
            asset_returns: Asset returns DataFrame
            weights: Portfolio weights

        Returns:
            Estimated maximum drawdown
        """
        # Calculate portfolio returns for each scenario
        portfolio_returns = (asset_returns * weights).sum(axis=1)

        # Calculate cumulative returns
        cumulative_returns = (1 + portfolio_returns).cumprod()

        # Calculate drawdown
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max

        return abs(drawdown.min())

    def _generate_efficient_frontier(
        self,
        asset_returns: pd.DataFrame,
        constraints: Dict,
        params: Dict,
        n_points: int = 50
    ) -> pd.DataFrame:
        """
        Generate efficient frontier.

        Args:
            asset_returns: Asset returns
            constraints: User constraints
            params: Optimization parameters
            n_points: Number of points on frontier

        Returns:
            DataFrame with efficient frontier points
        """
        mean_returns = asset_returns.mean().values
        cov_matrix = asset_returns.cov().values
        n_assets = len(asset_returns.columns)

        min_return = mean_returns.min()
        max_return = mean_returns.max()

        target_returns = np.linspace(min_return, max_return, n_points)

        frontier_results = []

        for target_ret in target_returns:
            try:
                weights = self._optimize_target_return(
                    mean_returns,
                    cov_matrix,
                    n_assets,
                    target_ret,
                    params['min_weight'],
                    params['max_weight']
                )

                portfolio_return = np.dot(weights, mean_returns)
                portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                sharpe = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0

                result_dict = {
                    'return': portfolio_return,
                    'volatility': portfolio_volatility,
                    'sharpe': sharpe
                }

                # Add weights
                for i, asset in enumerate(asset_returns.columns):
                    result_dict[f'{asset}_weight'] = weights[i]

                frontier_results.append(result_dict)

            except:
                continue

        return pd.DataFrame(frontier_results)

    def _run_simulations(
        self,
        scenarios_df: pd.DataFrame,
        optimal_portfolio: Dict,
        time_series: pd.DataFrame,
        params: Dict
    ) -> Dict:
        """
        Run Monte Carlo simulations with optimal portfolio.

        Args:
            scenarios_df: After-tax scenarios
            optimal_portfolio: Optimal portfolio weights
            time_series: Investment time series
            params: Parameters

        Returns:
            Dictionary with simulation results
        """
        weights = optimal_portfolio['weights']

        # Simulate terminal wealth for each scenario
        terminal_wealth_list = []
        wealth_paths = []

        scenario_ids = scenarios_df['scenario_id'].unique()

        for scenario_id in scenario_ids:
            scenario_data = scenarios_df[scenarios_df['scenario_id'] == scenario_id]

            # Simulate wealth path for this scenario
            wealth_path, terminal_wealth = self._simulate_wealth_path(
                scenario_data,
                weights,
                time_series,
                params
            )

            terminal_wealth_list.append({
                'scenario_id': scenario_id,
                'wealth': terminal_wealth,
                'real_wealth': terminal_wealth  # Could adjust for inflation
            })

            wealth_paths.append(wealth_path)

        terminal_wealth_df = pd.DataFrame(terminal_wealth_list)

        # Calculate percentiles
        wealth_values = terminal_wealth_df['wealth'].values
        terminal_wealth_df['percentile'] = terminal_wealth_df['wealth'].rank(pct=True) * 100

        # Calculate statistics
        statistics = {
            'mean_terminal_wealth': float(wealth_values.mean()),
            'median_terminal_wealth': float(np.median(wealth_values)),
            'std_terminal_wealth': float(wealth_values.std()),
            'percentiles': {
                '5': float(np.percentile(wealth_values, 5)),
                '25': float(np.percentile(wealth_values, 25)),
                '50': float(np.percentile(wealth_values, 50)),
                '75': float(np.percentile(wealth_values, 75)),
                '95': float(np.percentile(wealth_values, 95))
            },
            'probability_of_success': 0.0,  # Will be calculated in goal_analysis
            'shortfall_risk': 0.0,
            'var_95': float(np.percentile(wealth_values, 5)),
            'cvar_95': float(wealth_values[wealth_values <= np.percentile(wealth_values, 5)].mean())
        }

        # Create wealth paths DataFrame
        max_len = max(len(path) for path in wealth_paths)
        wealth_paths_array = np.zeros((len(scenario_ids), max_len))

        for i, path in enumerate(wealth_paths):
            wealth_paths_array[i, :len(path)] = path

        wealth_paths_df = pd.DataFrame(
            wealth_paths_array,
            columns=[f"year_{i}" for i in range(max_len)]
        )
        wealth_paths_df.insert(0, 'scenario_id', scenario_ids)

        return {
            'terminal_wealth': terminal_wealth_df,
            'wealth_paths': wealth_paths_df,
            'statistics': statistics
        }

    def _simulate_wealth_path(
        self,
        scenario_data: pd.DataFrame,
        weights: Dict,
        time_series: pd.DataFrame,
        params: Dict
    ) -> Tuple[np.ndarray, float]:
        """
        Simulate wealth path for a single scenario.

        Args:
            scenario_data: Scenario data
            weights: Portfolio weights
            time_series: Investment time series
            params: Parameters

        Returns:
            Tuple of (wealth_path, terminal_wealth)
        """
        # Simplified simulation
        # In reality, this would incorporate contributions, withdrawals, rebalancing

        n_periods = len(scenario_data)
        wealth_path = np.zeros(n_periods + 1)

        # Initial wealth (from time_series if available)
        initial_wealth = 10000  # Default
        if not time_series.empty and 'contribution' in time_series.columns:
            initial_wealth = time_series['contribution'].iloc[0] if len(time_series) > 0 else 10000

        wealth_path[0] = initial_wealth

        # Iterate through periods
        for t in range(n_periods):
            period_data = scenario_data.iloc[t]

            # Calculate portfolio return
            portfolio_return = 0.0
            for asset, weight in weights.items():
                return_col = f"{asset}_return_after_tax"
                if return_col not in period_data:
                    return_col = f"{asset}_after_tax"
                if return_col not in period_data:
                    return_col = f"{asset}_return"

                if return_col in period_data:
                    portfolio_return += weight * period_data[return_col]

            # Add contribution/withdrawal if available
            contribution = 0.0
            if not time_series.empty and t < len(time_series):
                if 'net_flow' in time_series.columns:
                    contribution = time_series.iloc[t]['net_flow']

            # Update wealth
            wealth_path[t + 1] = wealth_path[t] * (1 + portfolio_return) + contribution

        terminal_wealth = wealth_path[-1]

        return wealth_path, terminal_wealth

    def _create_rebalancing_schedule(
        self,
        optimal_portfolio: Dict,
        params: Dict,
        time_series: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create rebalancing schedule.

        Args:
            optimal_portfolio: Optimal portfolio
            params: Parameters
            time_series: Time series

        Returns:
            Rebalancing schedule DataFrame
        """
        # Placeholder for rebalancing schedule
        # In full implementation, this would calculate when to rebalance based on drift

        return pd.DataFrame({
            'period': [],
            'action': [],
            'from_asset': [],
            'to_asset': [],
            'amount': [],
            'cost': []
        })

    def _sensitivity_analysis(
        self,
        asset_returns: pd.DataFrame,
        optimal_portfolio: Dict,
        params: Dict
    ) -> Dict:
        """
        Perform sensitivity analysis.

        Args:
            asset_returns: Asset returns
            optimal_portfolio: Optimal portfolio
            params: Parameters

        Returns:
            Sensitivity analysis results
        """
        # Analyze sensitivity to return assumptions
        mean_returns = asset_returns.mean()
        weights = np.array(list(optimal_portfolio['weights'].values()))

        # Test +/-10% change in expected returns
        return_sensitivity = {}
        for asset in asset_returns.columns:
            modified_returns = mean_returns.copy()
            modified_returns[asset] *= 1.1  # +10%

            new_portfolio_return = np.dot(weights, modified_returns.values)
            impact = new_portfolio_return - optimal_portfolio['expected_return']

            return_sensitivity[asset] = float(impact)

        return {
            'return_sensitivity': return_sensitivity,
            'volatility_sensitivity': {},
            'correlation_sensitivity': {}
        }

    def _analyze_goals(
        self,
        simulation_results: Dict,
        goal_amount: Optional[float]
    ) -> Dict:
        """
        Analyze goal achievement probability.

        Args:
            simulation_results: Simulation results
            goal_amount: Target goal amount

        Returns:
            Goal analysis dictionary
        """
        terminal_wealth = simulation_results['terminal_wealth']['wealth'].values

        if goal_amount is None:
            goal_amount = np.median(terminal_wealth)

        # Calculate probability of achieving goal
        probability_of_achieving = (terminal_wealth >= goal_amount).mean()

        # Expected surplus/deficit
        surplus_deficit = terminal_wealth - goal_amount
        expected_surplus_deficit = surplus_deficit.mean()

        # Years to goal distribution (simplified - would need time-series analysis)
        years_to_goal = {}

        return {
            'goal_amount': float(goal_amount),
            'probability_of_achieving': float(probability_of_achieving),
            'expected_surplus_deficit': float(expected_surplus_deficit),
            'years_to_goal': years_to_goal
        }


# Convenience functions
def quick_optimize(
    scenarios_df: pd.DataFrame,
    objective: str = 'max_sharpe'
) -> Dict:
    """
    Quick optimization with default parameters.

    Args:
        scenarios_df: Scenarios DataFrame
        objective: Optimization objective

    Returns:
        Optimization results

    Example:
        >>> results = quick_optimize(scenarios_df, 'max_sharpe')
    """
    config = {
        'scenarios': scenarios_df,
        'optimization_objective': objective
    }

    optimizer = PortfolioOptimizer()
    return optimizer.optimize(config)
