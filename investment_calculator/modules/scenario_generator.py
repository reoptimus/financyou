"""
Module 1: Economic Scenario Generator (GSE)

This module generates Monte Carlo economic scenarios for all asset classes.

INPUT STRUCTURE:
{
    'num_scenarios': int,           # Number of Monte Carlo scenarios (e.g., 1000)
    'time_horizon': int,            # Years to simulate (e.g., 30)
    'timestep': float,              # Time step in years (e.g., 1/12 for monthly, 1 for annual)
    'use_stochastic': bool,         # Use advanced ESG models vs simple
    'calibration_date': str,        # Date for EIOPA curve calibration (YYYY-MM-DD)
    'currency': str,                # Currency for calibration (e.g., 'EUR', 'USD')
    'correlation_matrix': dict,     # Cross-asset correlations (optional)
    'economic_params': {
        'mean_reversion_speed': float,    # Hull-White parameter
        'volatility': float,              # Interest rate volatility
        'equity_drift': float,            # Equity expected return
        'equity_volatility': float,       # Equity volatility
        'real_estate_drift': float,       # Real estate expected return
        'real_estate_volatility': float,  # Real estate volatility
        'inflation_mean': float,          # Long-term inflation target
        'inflation_volatility': float,    # Inflation volatility
        'bond_return_mean': float,        # Bond expected return
        'bond_return_std': float          # Bond volatility
    }
}

OUTPUT STRUCTURE:
{
    'scenarios': pd.DataFrame,      # Shape: (num_scenarios * time_steps, n_columns)
                                   # Columns: ['scenario_id', 'time_period',
                                   #          'interest_rate', 'stock_return',
                                   #          'bond_return', 'real_estate_return',
                                   #          'inflation', 'gdp_growth']

    'deflators': pd.DataFrame,     # Risk-neutral deflators for pricing
                                   # Shape: (num_scenarios, time_steps)

    'metadata': {
        'generation_timestamp': datetime,
        'calibration_info': dict,
        'model_versions': dict,
        'random_seed': int
    },

    'diagnostics': {
        'mean_returns': dict,       # Average returns per asset class
        'volatilities': dict,       # Volatilities per asset class
        'correlations': pd.DataFrame, # Realized correlations
        'martingale_test': dict     # Martingale property tests (if stochastic)
    }
}
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, Tuple
import warnings

# Import from existing modules
from investment_calculator.stochastic_models import (
    HullWhiteModel,
    CorrelatedRandomGenerator,
    BlackScholesEquity,
    RealEstateModel,
    EIOPACalibrator
)


class ScenarioGenerator:
    """
    Economic Scenario Generator (GSE) - Module 1

    Generates comprehensive multi-asset economic scenarios using either:
    - Simple method: Correlated normal distributions
    - Advanced method: Stochastic models (Hull-White, Black-Scholes, etc.)

    Example:
        >>> config = {
        ...     'num_scenarios': 1000,
        ...     'time_horizon': 30,
        ...     'timestep': 1.0,
        ...     'use_stochastic': True,
        ...     'currency': 'EUR'
        ... }
        >>> generator = ScenarioGenerator()
        >>> results = generator.generate(config)
        >>> scenarios_df = results['scenarios']
    """

    def __init__(self, random_seed: Optional[int] = None):
        """
        Initialize the Scenario Generator.

        Args:
            random_seed: Random seed for reproducibility
        """
        self.random_seed = random_seed
        if random_seed is not None:
            np.random.seed(random_seed)

        # Default economic parameters (US historical averages)
        self.default_params = {
            'inflation_mean': 0.025,
            'inflation_volatility': 0.015,
            'interest_mean': 0.03,
            'interest_volatility': 0.02,
            'equity_drift': 0.10,
            'equity_volatility': 0.18,
            'bond_return_mean': 0.05,
            'bond_return_std': 0.07,
            'real_estate_drift': 0.08,
            'real_estate_volatility': 0.12,
            'gdp_growth_mean': 0.025,
            'gdp_growth_std': 0.02,
            # Advanced model parameters
            'mean_reversion_speed': 0.1,  # Hull-White a parameter
            'hw_volatility': 0.01,        # Hull-White sigma
            'equity_dividend_yield': 0.02,
            're_mean_reversion': 0.15,
            're_rental_yield': 0.03,
            're_inflation_adj': 0.02
        }

        # Default correlation matrix
        self.default_correlations = {
            ('interest_rate', 'inflation'): 0.5,
            ('stock_return', 'gdp_growth'): 0.6,
            ('stock_return', 'bond_return'): -0.3,
            ('real_estate_return', 'stock_return'): 0.5,
            ('real_estate_return', 'interest_rate'): 0.3
        }

    def generate(self, config: Dict) -> Dict:
        """
        Generate economic scenarios based on configuration.

        Args:
            config: Configuration dictionary (see module docstring for structure)

        Returns:
            Dictionary with scenarios, deflators, metadata, and diagnostics
        """
        # Validate and merge config with defaults
        validated_config = self._validate_config(config)

        # Choose generation method
        if validated_config['use_stochastic']:
            return self._generate_stochastic(validated_config)
        else:
            return self._generate_simple(validated_config)

    def _validate_config(self, config: Dict) -> Dict:
        """
        Validate and complete configuration with defaults.

        Args:
            config: User-provided configuration

        Returns:
            Complete validated configuration
        """
        # Required fields
        required = ['num_scenarios', 'time_horizon', 'timestep']
        for field in required:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")

        # Set defaults for optional fields
        validated = {
            'num_scenarios': int(config['num_scenarios']),
            'time_horizon': int(config['time_horizon']),
            'timestep': float(config['timestep']),
            'use_stochastic': config.get('use_stochastic', False),
            'calibration_date': config.get('calibration_date', '2025-01-01'),
            'currency': config.get('currency', 'USD'),
            'correlation_matrix': config.get('correlation_matrix', {}),
            'economic_params': {}
        }

        # Merge economic parameters with defaults
        user_params = config.get('economic_params', {})
        validated['economic_params'] = {**self.default_params, **user_params}

        # Merge correlations with defaults
        validated['correlation_matrix'] = {**self.default_correlations, **validated['correlation_matrix']}

        return validated

    def _generate_simple(self, config: Dict) -> Dict:
        """
        Generate scenarios using simple correlated normal distributions.

        This is faster and simpler but less realistic than stochastic models.

        Args:
            config: Validated configuration

        Returns:
            Results dictionary
        """
        n_scenarios = config['num_scenarios']
        time_horizon = config['time_horizon']
        timestep = config['timestep']
        params = config['economic_params']

        n_steps = int(time_horizon / timestep)

        # Total number of data points
        total_points = n_scenarios * n_steps

        # Initialize arrays for all scenarios and time periods
        scenario_ids = []
        time_periods = []
        interest_rates = []
        stock_returns = []
        bond_returns = []
        real_estate_returns = []
        inflation_rates = []
        gdp_growth = []

        for scenario_idx in range(n_scenarios):
            scenario_id = f"scenario_{scenario_idx + 1:04d}"

            # Generate correlated shocks
            base_shock = np.random.randn(n_steps)
            inflation_shock = np.random.randn(n_steps)
            market_shock = np.random.randn(n_steps)

            # Generate time series for this scenario
            inflation = (
                params['inflation_mean'] +
                params['inflation_volatility'] * (0.7 * base_shock + 0.3 * inflation_shock)
            )

            interest = (
                params['interest_mean'] +
                params['interest_volatility'] * (0.5 * base_shock + 0.5 * inflation_shock)
            )

            stocks = (
                params['equity_drift'] +
                params['equity_volatility'] * (0.8 * market_shock + 0.2 * base_shock)
            )

            bonds = (
                params['bond_return_mean'] +
                params['bond_return_std'] * (-0.3 * market_shock + 0.7 * base_shock)
            )

            real_estate = (
                params['real_estate_drift'] +
                params['real_estate_volatility'] * (0.5 * market_shock + 0.5 * base_shock)
            )

            gdp = (
                params['gdp_growth_mean'] +
                params['gdp_growth_std'] * (0.6 * market_shock + 0.4 * base_shock)
            )

            # Append to lists
            for step in range(n_steps):
                scenario_ids.append(scenario_id)
                time_periods.append((step + 1) * timestep)
                interest_rates.append(interest[step])
                stock_returns.append(stocks[step])
                bond_returns.append(bonds[step])
                real_estate_returns.append(real_estate[step])
                inflation_rates.append(inflation[step])
                gdp_growth.append(gdp[step])

        # Create scenarios DataFrame
        scenarios_df = pd.DataFrame({
            'scenario_id': scenario_ids,
            'time_period': time_periods,
            'interest_rate': interest_rates,
            'stock_return': stock_returns,
            'bond_return': bond_returns,
            'real_estate_return': real_estate_returns,
            'inflation': inflation_rates,
            'gdp_growth': gdp_growth
        })

        # Create deflators (simple discount factors)
        deflators_array = np.zeros((n_scenarios, n_steps))
        for i in range(n_scenarios):
            scenario_data = scenarios_df[scenarios_df['scenario_id'] == f"scenario_{i+1:04d}"]
            rates = scenario_data['interest_rate'].values
            deflators_array[i, :] = np.exp(-np.cumsum(rates * timestep))

        deflators_df = pd.DataFrame(
            deflators_array,
            columns=[f"t_{i+1}" for i in range(n_steps)]
        )
        deflators_df.insert(0, 'scenario_id', [f"scenario_{i+1:04d}" for i in range(n_scenarios)])

        # Calculate diagnostics
        diagnostics = self._calculate_diagnostics(scenarios_df, method='simple')

        # Metadata
        metadata = {
            'generation_timestamp': datetime.now(),
            'calibration_info': {
                'method': 'simple',
                'currency': config['currency'],
                'calibration_date': config['calibration_date']
            },
            'model_versions': {
                'gse': '2.0.0',
                'method': 'correlated_normal'
            },
            'random_seed': self.random_seed
        }

        return {
            'scenarios': scenarios_df,
            'deflators': deflators_df,
            'metadata': metadata,
            'diagnostics': diagnostics
        }

    def _generate_stochastic(self, config: Dict) -> Dict:
        """
        Generate scenarios using advanced stochastic models.

        This uses Hull-White for rates, Black-Scholes for equities, etc.
        More realistic but computationally intensive.

        Args:
            config: Validated configuration

        Returns:
            Results dictionary
        """
        n_scenarios = config['num_scenarios']
        T = config['time_horizon']
        dt = config['timestep']
        params = config['economic_params']

        n_steps = int(T / dt)

        # Step 1: Create or load EIOPA calibration curve
        spot_rates = self._create_yield_curve(config['currency'])

        calibrator = EIOPACalibrator(spot_rates=spot_rates, dt=dt)
        calibrator.calibrate()

        f0t = calibrator.get_forward_curve(n_steps=n_steps)
        P0t = calibrator.get_bond_prices(n_steps=n_steps)

        # Step 2: Generate Hull-White interest rate scenarios
        hw_model = HullWhiteModel(
            a=params['mean_reversion_speed'],
            sigma=params['hw_volatility'],
            f0t=f0t,
            P0t=P0t,
            dt=dt,
            n_scenarios=n_scenarios,
            T=T
        )

        hw_results = hw_model.generate_scenarios()

        # Step 3: Generate correlated shocks
        corr_gen = CorrelatedRandomGenerator(
            n_scenarios=n_scenarios,
            n_steps=n_steps,
            random_seed=self.random_seed
        )

        corr_results = corr_gen.generate(rate_residuals=hw_results['residuals'])

        # Step 4: Generate equity scenarios
        equity_model = BlackScholesEquity(
            sigma=params['equity_volatility'],
            dividend_yield=params['equity_dividend_yield'],
            dt=dt,
            n_scenarios=n_scenarios,
            T=T
        )

        equity_shocks = corr_gen.get_asset_shocks(corr_results['shocks'], 'equity')
        equity_results = equity_model.generate_returns(
            hw_results['Rt'],
            equity_shocks=equity_shocks
        )

        # Step 5: Generate real estate scenarios
        re_model = RealEstateModel(
            a=params['re_mean_reversion'],
            sigma=params['real_estate_volatility'],
            rental_yield=params['re_rental_yield'],
            inflation_adjustment=params['re_inflation_adj'],
            dt=dt,
            n_scenarios=n_scenarios,
            T=T
        )

        re_price_shocks = corr_gen.get_asset_shocks(corr_results['shocks'], 'real_estate')
        re_rental_shocks = corr_gen.get_asset_shocks(corr_results['shocks'], 'inflation')

        re_results = re_model.generate_returns(
            hw_results['Rt'],
            f0t,
            re_price_shocks=re_price_shocks,
            re_rental_shocks=re_rental_shocks
        )

        # Step 6: Generate bond returns (simplified - use interest rates)
        # Bond returns approximately = forward rate - duration * rate change
        bond_returns = hw_results['Rt'].copy()  # Simplified: use forward rates

        # Step 7: Generate inflation (from correlated shocks)
        inflation_shocks = corr_gen.get_asset_shocks(corr_results['shocks'], 'inflation')
        inflation_rates = params['inflation_mean'] + params['inflation_volatility'] * inflation_shocks

        # Step 8: Generate GDP growth (correlated with equity returns)
        gdp_growth = params['gdp_growth_mean'] + params['gdp_growth_std'] * (
            0.6 * equity_shocks + 0.4 * (hw_results['residuals'] / params['hw_volatility'])
        )

        # Step 9: Assemble into DataFrame
        scenario_ids = []
        time_periods = []
        interest_rates_list = []
        stock_returns_list = []
        bond_returns_list = []
        real_estate_returns_list = []
        inflation_rates_list = []
        gdp_growth_list = []

        for scenario_idx in range(n_scenarios):
            scenario_id = f"scenario_{scenario_idx + 1:04d}"

            for step in range(n_steps):
                scenario_ids.append(scenario_id)
                time_periods.append((step + 1) * dt)
                interest_rates_list.append(hw_results['Rt'][scenario_idx, step])
                stock_returns_list.append(equity_results['total_returns'][scenario_idx, step])
                bond_returns_list.append(bond_returns[scenario_idx, step])
                real_estate_returns_list.append(re_results['total_returns'][scenario_idx, step])
                inflation_rates_list.append(inflation_rates[scenario_idx, step])
                gdp_growth_list.append(gdp_growth[scenario_idx, step])

        scenarios_df = pd.DataFrame({
            'scenario_id': scenario_ids,
            'time_period': time_periods,
            'interest_rate': interest_rates_list,
            'stock_return': stock_returns_list,
            'bond_return': bond_returns_list,
            'real_estate_return': real_estate_returns_list,
            'inflation': inflation_rates_list,
            'gdp_growth': gdp_growth_list
        })

        # Create deflators DataFrame
        deflators_df = pd.DataFrame(
            hw_results['deflators'],
            columns=[f"t_{i+1}" for i in range(n_steps)]
        )
        deflators_df.insert(0, 'scenario_id', [f"scenario_{i+1:04d}" for i in range(n_scenarios)])

        # Calculate diagnostics
        diagnostics = self._calculate_diagnostics(scenarios_df, method='stochastic')
        diagnostics['martingale_test'] = self._test_martingale(hw_results['deflators'], hw_results['Rt'], dt)

        # Metadata
        metadata = {
            'generation_timestamp': datetime.now(),
            'calibration_info': {
                'method': 'stochastic',
                'currency': config['currency'],
                'calibration_date': config['calibration_date'],
                'forward_curve_range': (float(f0t.min()), float(f0t.max()))
            },
            'model_versions': {
                'gse': '2.0.0',
                'hull_white': '1.0.0',
                'black_scholes': '1.0.0',
                'real_estate': '1.0.0'
            },
            'random_seed': self.random_seed
        }

        return {
            'scenarios': scenarios_df,
            'deflators': deflators_df,
            'metadata': metadata,
            'diagnostics': diagnostics
        }

    def _create_yield_curve(self, currency: str) -> np.ndarray:
        """
        Create synthetic yield curve for calibration.

        In production, this would load actual EIOPA curves from CSV files.

        Args:
            currency: Currency code

        Returns:
            Array of spot rates
        """
        # Synthetic yield curve (Nelson-Siegel parametric form)
        maturities = np.arange(1, 61)

        # Different curves per currency
        if currency == 'EUR':
            spot_rates = 0.015 + 0.020 * (1 - np.exp(-maturities / 10))
        elif currency == 'USD':
            spot_rates = 0.025 + 0.020 * (1 - np.exp(-maturities / 10))
        elif currency == 'GBP':
            spot_rates = 0.020 + 0.025 * (1 - np.exp(-maturities / 10))
        else:
            warnings.warn(f"Unknown currency {currency}, using EUR curve")
            spot_rates = 0.015 + 0.020 * (1 - np.exp(-maturities / 10))

        return spot_rates

    def _calculate_diagnostics(self, scenarios_df: pd.DataFrame, method: str) -> Dict:
        """
        Calculate diagnostic statistics for generated scenarios.

        Args:
            scenarios_df: Scenarios DataFrame
            method: Generation method ('simple' or 'stochastic')

        Returns:
            Dictionary of diagnostic metrics
        """
        # Calculate mean returns and volatilities for each asset class
        asset_columns = ['interest_rate', 'stock_return', 'bond_return',
                        'real_estate_return', 'inflation', 'gdp_growth']

        mean_returns = {}
        volatilities = {}

        for col in asset_columns:
            mean_returns[col] = float(scenarios_df[col].mean())
            volatilities[col] = float(scenarios_df[col].std())

        # Calculate realized correlations
        corr_matrix = scenarios_df[asset_columns].corr()

        return {
            'mean_returns': mean_returns,
            'volatilities': volatilities,
            'correlations': corr_matrix,
            'num_scenarios': scenarios_df['scenario_id'].nunique(),
            'num_time_periods': len(scenarios_df['time_period'].unique()),
            'method': method
        }

    def _test_martingale(self, deflators: np.ndarray, rates: np.ndarray, dt: float) -> Dict:
        """
        Test martingale property of deflated assets.

        For risk-neutral pricing, deflated asset prices should be martingales.

        Args:
            deflators: Deflator array (n_scenarios, n_steps)
            rates: Forward rate array (n_scenarios, n_steps)
            dt: Time step

        Returns:
            Dictionary with martingale test results
        """
        n_scenarios, n_steps = deflators.shape

        # Test: E[D(t)] should equal 1.0 for all t under risk-neutral measure
        # In practice, we test E[D(t) * exp(integral r(s)ds)] = 1

        mean_deflator = deflators.mean(axis=0)
        expected_value = 1.0  # Should be 1.0 theoretically

        # Calculate deviation from martingale property
        deviations = np.abs(mean_deflator - expected_value)
        max_deviation = float(deviations.max())
        mean_deviation = float(deviations.mean())

        # Check if martingale property holds (within tolerance)
        tolerance = 0.05
        passes_test = max_deviation < tolerance

        return {
            'passes': passes_test,
            'max_deviation': max_deviation,
            'mean_deviation': mean_deviation,
            'tolerance': tolerance,
            'mean_final_deflator': float(mean_deflator[-1])
        }


# Convenience functions for backward compatibility
def generate_scenarios(config: Dict, random_seed: Optional[int] = None) -> Dict:
    """
    Generate economic scenarios (convenience function).

    Args:
        config: Configuration dictionary
        random_seed: Random seed for reproducibility

    Returns:
        Results dictionary with scenarios, deflators, metadata, diagnostics

    Example:
        >>> config = {'num_scenarios': 1000, 'time_horizon': 30, 'timestep': 1.0}
        >>> results = generate_scenarios(config)
    """
    generator = ScenarioGenerator(random_seed=random_seed)
    return generator.generate(config)


def quick_scenarios(num_scenarios: int = 1000, time_horizon: int = 30,
                   use_stochastic: bool = False) -> pd.DataFrame:
    """
    Quick scenario generation with default parameters.

    Args:
        num_scenarios: Number of scenarios to generate
        time_horizon: Time horizon in years
        use_stochastic: Use advanced stochastic models

    Returns:
        Scenarios DataFrame

    Example:
        >>> scenarios = quick_scenarios(1000, 30, use_stochastic=True)
    """
    config = {
        'num_scenarios': num_scenarios,
        'time_horizon': time_horizon,
        'timestep': 1.0,
        'use_stochastic': use_stochastic
    }

    generator = ScenarioGenerator()
    results = generator.generate(config)
    return results['scenarios']
