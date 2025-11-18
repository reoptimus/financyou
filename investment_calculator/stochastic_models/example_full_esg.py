"""
Complete Economic Scenario Generator (ESG) Example

This example demonstrates the full workflow for generating multi-asset
economic scenarios using the Financyou stochastic models:

1. Load and calibrate EIOPA yield curves
2. Generate Hull-White stochastic interest rates
3. Generate correlated shocks for multiple asset classes
4. Generate equity returns (Black-Scholes)
5. Generate real estate returns
6. Analyze and visualize results

This replicates the functionality of the R legacy code but with modern Python.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from investment_calculator.stochastic_models import (
    HullWhiteModel,
    CorrelatedRandomGenerator,
    BlackScholesEquity,
    RealEstateModel,
    EIOPACalibrator
)


class EconomicScenarioGenerator:
    """
    Complete Economic Scenario Generator (ESG).

    Generates consistent multi-asset scenarios for:
    - Interest rates (Hull-White model)
    - Equities (Black-Scholes model)
    - Real estate
    - Inflation (optional)
    - Corporate bonds (optional)
    """

    def __init__(
        self,
        n_scenarios: int = 1000,
        T: int = 30,
        dt: float = 0.5,
        random_seed: int = None
    ):
        """
        Initialize ESG.

        Args:
            n_scenarios: Number of Monte Carlo scenarios
            T: Time horizon in years
            dt: Time step in years
            random_seed: Random seed for reproducibility
        """
        self.n_scenarios = n_scenarios
        self.T = T
        self.dt = dt
        self.n_steps = int(T / dt)
        self.random_seed = random_seed

        if random_seed is not None:
            np.random.seed(random_seed)

        # Will be populated by calibrate()
        self.f0t = None
        self.P0t = None
        self.hw_params = None

        # Will be populated by generate()
        self.results = {}

    def calibrate_from_eiopa(
        self,
        spot_rates: np.ndarray,
        hw_a: float = 0.1,
        hw_sigma: float = 0.01
    ):
        """
        Calibrate models using EIOPA yield curve.

        Args:
            spot_rates: EIOPA spot rates (zero-coupon yields)
            hw_a: Hull-White mean reversion speed
            hw_sigma: Hull-White volatility
        """
        # Create calibrator
        calibrator = EIOPACalibrator(
            spot_rates=spot_rates,
            dt=self.dt
        )

        # Calibrate
        calibrator.calibrate()

        # Extract calibrated curves
        self.f0t = calibrator.get_forward_curve(n_steps=self.n_steps)
        self.P0t = calibrator.get_bond_prices(n_steps=self.n_steps)

        # Store Hull-White parameters
        self.hw_params = {'a': hw_a, 'sigma': hw_sigma}

        print(f"✓ Calibrated to EIOPA curves")
        print(f"  Forward rate range: {self.f0t.min():.4f} to {self.f0t.max():.4f}")
        print(f"  Hull-White parameters: a={hw_a}, σ={hw_sigma}")

    def generate_scenarios(
        self,
        equity_sigma: float = 0.18,
        equity_dividend_yield: float = 0.02,
        re_a: float = 0.15,
        re_sigma: float = 0.12,
        re_rental_yield: float = 0.03,
        re_inflation: float = 0.02
    ):
        """
        Generate all asset class scenarios.

        Args:
            equity_sigma: Equity volatility
            equity_dividend_yield: Dividend yield
            re_a: Real estate mean reversion
            re_sigma: Real estate volatility
            re_rental_yield: Rental yield
            re_inflation: Rental inflation adjustment
        """
        if self.f0t is None:
            raise ValueError("Must call calibrate_from_eiopa() first")

        print("\n" + "="*60)
        print("GENERATING ECONOMIC SCENARIOS")
        print("="*60)

        # Step 1: Generate Hull-White interest rate scenarios
        print("\n[1/4] Generating interest rate scenarios (Hull-White)...")
        hw_model = HullWhiteModel(
            a=self.hw_params['a'],
            sigma=self.hw_params['sigma'],
            f0t=self.f0t,
            P0t=self.P0t,
            dt=self.dt,
            n_scenarios=self.n_scenarios,
            T=self.T
        )

        hw_results = hw_model.generate_scenarios()

        self.results['rates'] = {
            'short_rate': hw_results['rt'],
            'forward_rate': hw_results['Rt'],
            'deflators': hw_results['deflators'],
            'residuals': hw_results['residuals']
        }

        print(f"  ✓ Generated {self.n_scenarios} scenarios over {self.T} years")
        print(f"    Mean short rate: {hw_results['rt'].mean():.4f}")
        print(f"    Volatility: {hw_results['rt'].std():.4f}")

        # Step 2: Generate correlated shocks for all asset classes
        print("\n[2/4] Generating correlated random shocks...")
        corr_gen = CorrelatedRandomGenerator(
            n_scenarios=self.n_scenarios,
            n_steps=self.n_steps,
            random_seed=self.random_seed
        )

        corr_results = corr_gen.generate(rate_residuals=hw_results['residuals'])

        print(f"  ✓ Generated correlated shocks for {corr_gen.n_assets} asset classes")

        # Step 3: Generate equity returns
        print("\n[3/4] Generating equity returns (Black-Scholes)...")
        equity_model = BlackScholesEquity(
            sigma=equity_sigma,
            dividend_yield=equity_dividend_yield,
            dt=self.dt,
            n_scenarios=self.n_scenarios,
            T=self.T
        )

        equity_shocks = corr_gen.get_asset_shocks(corr_results['shocks'], 'equity')
        equity_results = equity_model.generate_returns(
            hw_results['Rt'],
            equity_shocks=equity_shocks
        )

        self.results['equity'] = equity_results

        # Calculate equity prices
        equity_prices = equity_model.simulate_prices(
            equity_results['total_returns'],
            initial_price=100.0
        )

        self.results['equity']['prices'] = equity_prices

        mean_total_return = np.mean(equity_results['total_returns']) * (1 / self.dt)  # Annualized
        print(f"  ✓ Generated equity scenarios")
        print(f"    Annualized mean return: {mean_total_return:.2%}")
        print(f"    Final price (median): ${np.median(equity_prices[:, -1]):.2f}")

        # Step 4: Generate real estate returns
        print("\n[4/4] Generating real estate returns...")
        re_model = RealEstateModel(
            a=re_a,
            sigma=re_sigma,
            rental_yield=re_rental_yield,
            inflation_adjustment=re_inflation,
            dt=self.dt,
            n_scenarios=self.n_scenarios,
            T=self.T
        )

        re_price_shocks = corr_gen.get_asset_shocks(corr_results['shocks'], 'real_estate')
        re_rental_shocks = corr_gen.get_asset_shocks(corr_results['shocks'], 'inflation')

        re_results = re_model.generate_returns(
            hw_results['Rt'],
            self.f0t,
            re_price_shocks=re_price_shocks,
            re_rental_shocks=re_rental_shocks
        )

        self.results['real_estate'] = re_results

        mean_re_return = np.mean(re_results['total_returns']) * (1 / self.dt)  # Annualized
        print(f"  ✓ Generated real estate scenarios")
        print(f"    Annualized mean return: {mean_re_return:.2%}")

        print("\n" + "="*60)
        print("SCENARIO GENERATION COMPLETE")
        print("="*60)

        return self.results

    def get_summary_statistics(self) -> pd.DataFrame:
        """
        Calculate summary statistics for all asset classes.

        Returns:
            DataFrame with summary stats
        """
        if not self.results:
            raise ValueError("Must call generate_scenarios() first")

        stats = []

        # Interest rates
        rates = self.results['rates']['forward_rate']
        stats.append({
            'Asset': 'Interest Rates',
            'Mean (ann)': rates.mean() * (1 / self.dt),
            'Volatility (ann)': rates.std() * np.sqrt(1 / self.dt),
            '5th %ile': np.percentile(rates, 5),
            '50th %ile': np.percentile(rates, 50),
            '95th %ile': np.percentile(rates, 95)
        })

        # Equity
        equity_returns = self.results['equity']['total_returns']
        stats.append({
            'Asset': 'Equity',
            'Mean (ann)': equity_returns.mean() * (1 / self.dt),
            'Volatility (ann)': equity_returns.std() * np.sqrt(1 / self.dt),
            '5th %ile': np.percentile(equity_returns, 5),
            '50th %ile': np.percentile(equity_returns, 50),
            '95th %ile': np.percentile(equity_returns, 95)
        })

        # Real Estate
        re_returns = self.results['real_estate']['total_returns']
        stats.append({
            'Asset': 'Real Estate',
            'Mean (ann)': re_returns.mean() * (1 / self.dt),
            'Volatility (ann)': re_returns.std() * np.sqrt(1 / self.dt),
            '5th %ile': np.percentile(re_returns, 5),
            '50th %ile': np.percentile(re_returns, 50),
            '95th %ile': np.percentile(re_returns, 95)
        })

        return pd.DataFrame(stats)

    def plot_scenarios(self, n_scenarios_to_plot: int = 100):
        """
        Plot scenario fan charts for all asset classes.

        Args:
            n_scenarios_to_plot: Number of scenarios to plot
        """
        if not self.results:
            raise ValueError("Must call generate_scenarios() first")

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        time_grid = np.arange(self.n_steps) * self.dt

        # Plot 1: Interest rates
        ax = axes[0, 0]
        rates = self.results['rates']['forward_rate'][:n_scenarios_to_plot, :]
        for i in range(min(50, n_scenarios_to_plot)):
            ax.plot(time_grid, rates[i, :] * 100, alpha=0.1, color='blue')

        # Add percentiles
        for pct, color, label in [(5, 'red', '5th %ile'), (50, 'black', 'Median'), (95, 'red', '95th %ile')]:
            ax.plot(time_grid, np.percentile(rates, pct, axis=0) * 100, color=color, linewidth=2, label=label)

        ax.set_xlabel('Time (years)')
        ax.set_ylabel('Interest Rate (%)')
        ax.set_title('Interest Rate Scenarios (Hull-White)')
        ax.legend()
        ax.grid(True)

        # Plot 2: Equity prices
        ax = axes[0, 1]
        prices = self.results['equity']['prices'][:n_scenarios_to_plot, :]
        for i in range(min(50, n_scenarios_to_plot)):
            ax.plot(time_grid, prices[i, :], alpha=0.1, color='green')

        for pct, color, label in [(5, 'red', '5th %ile'), (50, 'black', 'Median'), (95, 'red', '95th %ile')]:
            ax.plot(time_grid, np.percentile(prices, pct, axis=0), color=color, linewidth=2, label=label)

        ax.set_xlabel('Time (years)')
        ax.set_ylabel('Price ($)')
        ax.set_title('Equity Price Scenarios (Black-Scholes)')
        ax.legend()
        ax.grid(True)

        # Plot 3: Real estate cumulative returns
        ax = axes[1, 0]
        re_cumulative = np.cumsum(self.results['real_estate']['total_returns'][:n_scenarios_to_plot, :], axis=1)
        for i in range(min(50, n_scenarios_to_plot)):
            ax.plot(time_grid, re_cumulative[i, :] * 100, alpha=0.1, color='brown')

        for pct, color, label in [(5, 'red', '5th %ile'), (50, 'black', 'Median'), (95, 'red', '95th %ile')]:
            ax.plot(time_grid, np.percentile(re_cumulative, pct, axis=0) * 100, color=color, linewidth=2, label=label)

        ax.set_xlabel('Time (years)')
        ax.set_ylabel('Cumulative Return (%)')
        ax.set_title('Real Estate Cumulative Returns')
        ax.legend()
        ax.grid(True)

        # Plot 4: Correlation matrix
        ax = axes[1, 1]

        # Stack all returns and calculate correlation
        rates_flat = self.results['rates']['forward_rate'].flatten()
        equity_flat = self.results['equity']['total_returns'].flatten()
        re_flat = self.results['real_estate']['total_returns'].flatten()

        all_returns = np.vstack([rates_flat, equity_flat, re_flat])
        corr_matrix = np.corrcoef(all_returns)

        im = ax.imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
        ax.set_xticks([0, 1, 2])
        ax.set_yticks([0, 1, 2])
        ax.set_xticklabels(['Rates', 'Equity', 'Real Estate'])
        ax.set_yticklabels(['Rates', 'Equity', 'Real Estate'])
        ax.set_title('Realized Correlation Matrix')

        # Add correlation values
        for i in range(3):
            for j in range(3):
                text = ax.text(j, i, f'{corr_matrix[i, j]:.2f}',
                             ha="center", va="center", color="black")

        plt.colorbar(im, ax=ax)

        plt.tight_layout()
        plt.savefig('esg_scenarios.png', dpi=150)
        print("\n✓ Plots saved to 'esg_scenarios.png'")
        plt.show()


def main():
    """Run complete ESG example."""
    print("\n" + "="*60)
    print("FINANCYOU - ECONOMIC SCENARIO GENERATOR (ESG)")
    print("="*60)
    print("\nThis example demonstrates the complete workflow for generating")
    print("multi-asset economic scenarios using stochastic models.")
    print("="*60)

    # Initialize ESG
    esg = EconomicScenarioGenerator(
        n_scenarios=1000,
        T=30,
        dt=0.5,
        random_seed=42
    )

    # Create synthetic EIOPA curve
    maturities = np.arange(1, 61)
    spot_rates = 0.02 + 0.015 * (1 - np.exp(-maturities / 10))

    # Calibrate
    print("\nCalibrating models...")
    esg.calibrate_from_eiopa(
        spot_rates=spot_rates,
        hw_a=0.1,
        hw_sigma=0.01
    )

    # Generate scenarios
    results = esg.generate_scenarios(
        equity_sigma=0.18,
        equity_dividend_yield=0.02,
        re_a=0.15,
        re_sigma=0.12,
        re_rental_yield=0.03,
        re_inflation=0.02
    )

    # Print summary statistics
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    summary = esg.get_summary_statistics()
    print("\n" + summary.to_string(index=False))

    # Create visualizations
    print("\n" + "="*60)
    print("Creating visualizations...")
    print("="*60)
    try:
        esg.plot_scenarios(n_scenarios_to_plot=100)
    except Exception as e:
        print(f"Could not create plots: {e}")

    print("\n" + "="*60)
    print("ESG EXAMPLE COMPLETE")
    print("="*60)
    print("\nYou can now use these scenarios for:")
    print("  - Portfolio optimization")
    print("  - Risk analysis")
    print("  - Asset-liability modeling")
    print("  - Retirement planning")
    print("  - Insurance pricing")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
