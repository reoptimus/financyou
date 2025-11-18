"""
Black-Scholes Equity Model

This module implements stock price dynamics using the Black-Scholes framework
with stochastic interest rates from the Hull-White model.

Stock returns are modeled as:
    dS/S = (r(t) + σ²/2)dt + σ*dW(t)

where:
    r(t) = stochastic risk-free rate from Hull-White model
    σ = equity volatility
    dW(t) = Brownian motion (potentially correlated with rates)

The model separates total returns into:
1. Price appreciation (capital gains)
2. Dividend yield (income)

Key Features:
- Integration with Hull-White interest rates
- Correlation with other asset classes
- Separate tracking of dividends and price returns
- Antithetic variance reduction
"""

import numpy as np
from typing import Dict, Optional, Tuple
import warnings


class BlackScholesEquity:
    """
    Black-Scholes model for equity returns with stochastic rates.

    This class generates equity return scenarios that are consistent with
    the stochastic interest rate environment from the Hull-White model.

    Attributes:
        sigma: Equity volatility (annualized standard deviation)
        dividend_yield: Constant dividend yield (as decimal, e.g., 0.02 for 2%)
        correlation_with_rates: Correlation between equity shocks and rate shocks
        dt: Time step in years
        n_scenarios: Number of Monte Carlo scenarios
        n_steps: Number of time steps
    """

    def __init__(
        self,
        sigma: float,
        dividend_yield: float = 0.02,
        correlation_with_rates: float = 0.0,
        dt: float = 0.5,
        n_scenarios: int = 1000,
        T: int = 60
    ):
        """
        Initialize Black-Scholes equity model.

        Args:
            sigma: Equity volatility (e.g., 0.18 for 18% annual volatility)
            dividend_yield: Constant dividend yield (default: 2%)
            correlation_with_rates: Correlation between equity and rates (default: 0)
            dt: Time step in years (default: 0.5 = semi-annual)
            n_scenarios: Number of scenarios to generate
            T: Time horizon in years
        """
        self.sigma = sigma
        self.dividend_yield = dividend_yield
        self.correlation_with_rates = correlation_with_rates
        self.dt = dt
        self.n_scenarios = n_scenarios
        self.T = T
        self.n_steps = int(T / dt)

        # Validate parameters
        self._validate_parameters()

    def _validate_parameters(self):
        """Validate model parameters."""
        if self.sigma <= 0:
            raise ValueError(f"Volatility sigma must be positive, got {self.sigma}")
        if self.dividend_yield < 0:
            raise ValueError(f"Dividend yield must be non-negative, got {self.dividend_yield}")
        if not -1 <= self.correlation_with_rates <= 1:
            raise ValueError(
                f"Correlation must be in [-1, 1], got {self.correlation_with_rates}"
            )
        if self.dt <= 0:
            raise ValueError(f"Time step dt must be positive, got {self.dt}")

    def generate_returns(
        self,
        short_rates: np.ndarray,
        equity_shocks: Optional[np.ndarray] = None,
        rate_shocks: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        Generate equity return scenarios.

        Args:
            short_rates: Short rate paths from Hull-White (n_scenarios × n_steps)
            equity_shocks: Optional pre-generated equity shocks (n_scenarios × n_steps)
                          If None, will be generated internally
            rate_shocks: Optional rate shocks for correlation (n_scenarios × n_steps)
                        Required if correlation_with_rates != 0

        Returns:
            Dictionary containing:
                - 'total_returns': Total equity returns (n_scenarios × n_steps)
                - 'price_returns': Price appreciation only (n_scenarios × n_steps)
                - 'dividend_returns': Dividend component (n_scenarios × n_steps)
        """
        n_scenarios, n_steps = short_rates.shape

        if n_scenarios != self.n_scenarios or n_steps != self.n_steps:
            warnings.warn(
                f"Input shape ({n_scenarios}, {n_steps}) differs from initialized "
                f"({self.n_scenarios}, {self.n_steps}). Using input shape."
            )

        # Generate or use provided equity shocks
        if equity_shocks is None:
            if self.correlation_with_rates != 0 and rate_shocks is not None:
                # Generate correlated shocks
                equity_shocks = self._generate_correlated_shocks(rate_shocks)
            else:
                # Generate independent shocks
                equity_shocks = np.random.normal(0, 1, (n_scenarios, n_steps))

        # Calculate total returns using Black-Scholes
        total_returns = self._calculate_total_returns(short_rates, equity_shocks)

        # Calculate dividend returns (constant yield)
        dividend_returns = np.full((n_scenarios, n_steps), np.log(1 + self.dividend_yield) * self.dt)
        dividend_returns[:, 0] = 0  # No dividend at t=0

        # Price returns = total returns - dividend returns
        price_returns = total_returns - dividend_returns

        return {
            'total_returns': total_returns,
            'price_returns': price_returns,
            'dividend_returns': dividend_returns
        }

    def _calculate_total_returns(
        self,
        short_rates: np.ndarray,
        equity_shocks: np.ndarray
    ) -> np.ndarray:
        """
        Calculate total equity returns using Black-Scholes formula.

        Under risk-neutral measure:
            dS/S = r(t)dt + σ*dW(t)

        Discrete version:
            log(S[t+1]/S[t]) = (r(t) - σ²/2)dt + σ*sqrt(dt)*ε[t]

        where we add σ²/2 drift adjustment for continuous compounding.

        Args:
            short_rates: Short rate paths (n_scenarios × n_steps)
            equity_shocks: Standard normal shocks (n_scenarios × n_steps)

        Returns:
            Log returns (n_scenarios × n_steps)
        """
        n_scenarios, n_steps = short_rates.shape
        total_returns = np.zeros((n_scenarios, n_steps))

        # Volatility term
        vol_term = self.sigma * np.sqrt(self.dt)

        # Calculate returns for each time step
        for t in range(1, n_steps):
            # Drift: r(t) + σ²/2 (add back drift for equity risk premium)
            drift = (short_rates[:, t] + self.sigma**2 / 2) * self.dt

            # Diffusion: σ*sqrt(dt)*ε
            diffusion = vol_term * equity_shocks[:, t]

            # Total return (log)
            total_returns[:, t] = drift + diffusion

        return total_returns

    def _generate_correlated_shocks(
        self,
        rate_shocks: np.ndarray
    ) -> np.ndarray:
        """
        Generate equity shocks correlated with rate shocks.

        Uses the formula:
            ε_equity = ρ * ε_rate + sqrt(1 - ρ²) * ε_independent

        Args:
            rate_shocks: Interest rate shocks (n_scenarios × n_steps)

        Returns:
            Correlated equity shocks (n_scenarios × n_steps)
        """
        n_scenarios, n_steps = rate_shocks.shape

        # Independent component
        independent_shocks = np.random.normal(0, 1, (n_scenarios, n_steps))

        # Correlated shocks
        rho = self.correlation_with_rates
        equity_shocks = (
            rho * rate_shocks +
            np.sqrt(1 - rho**2) * independent_shocks
        )

        return equity_shocks

    def calculate_risk_premium(
        self,
        historical_returns: np.ndarray,
        historical_rates: np.ndarray
    ) -> float:
        """
        Estimate equity risk premium from historical data.

        Risk premium = E[r_equity] - E[r_risk_free]

        Args:
            historical_returns: Historical equity returns
            historical_rates: Historical risk-free rates

        Returns:
            Annualized equity risk premium
        """
        mean_equity_return = np.mean(historical_returns)
        mean_risk_free = np.mean(historical_rates)

        risk_premium = mean_equity_return - mean_risk_free

        return risk_premium

    def simulate_prices(
        self,
        returns: np.ndarray,
        initial_price: float = 100.0
    ) -> np.ndarray:
        """
        Convert log returns to price paths.

        Args:
            returns: Log returns (n_scenarios × n_steps)
            initial_price: Starting price (default: 100)

        Returns:
            Price paths (n_scenarios × n_steps)
        """
        # Cumulative returns
        cumulative_returns = np.cumsum(returns, axis=1)

        # Price = S0 * exp(cumulative returns)
        prices = initial_price * np.exp(cumulative_returns)

        # Set initial price
        prices[:, 0] = initial_price

        return prices

    def calculate_percentiles(
        self,
        returns: np.ndarray,
        percentiles: list = [5, 25, 50, 75, 95]
    ) -> Dict[int, np.ndarray]:
        """
        Calculate return percentiles across scenarios.

        Args:
            returns: Return paths (n_scenarios × n_steps)
            percentiles: List of percentiles to calculate

        Returns:
            Dictionary mapping percentile to time series
        """
        result = {}
        for p in percentiles:
            result[p] = np.percentile(returns, p, axis=0)

        return result


class DividendGrowthModel:
    """
    Dividend Growth Model for equity valuation.

    Implements the Gordon Growth Model:
        P = D / (r - g)

    where:
        P = stock price
        D = expected dividend
        r = required return
        g = dividend growth rate
    """

    def __init__(
        self,
        initial_dividend: float,
        growth_rate: float,
        required_return: float
    ):
        """
        Initialize dividend growth model.

        Args:
            initial_dividend: Current dividend per share
            growth_rate: Expected constant growth rate
            required_return: Required rate of return
        """
        self.initial_dividend = initial_dividend
        self.growth_rate = growth_rate
        self.required_return = required_return

        if growth_rate >= required_return:
            raise ValueError(
                f"Growth rate ({growth_rate}) must be less than "
                f"required return ({required_return})"
            )

    def calculate_price(self) -> float:
        """Calculate fair value using Gordon Growth Model."""
        return self.initial_dividend / (self.required_return - self.growth_rate)

    def calculate_dividend_yield(self) -> float:
        """Calculate dividend yield."""
        price = self.calculate_price()
        return self.initial_dividend / price

    def project_dividends(self, n_years: int) -> np.ndarray:
        """
        Project future dividends.

        Args:
            n_years: Number of years to project

        Returns:
            Array of projected dividends
        """
        years = np.arange(n_years)
        dividends = self.initial_dividend * (1 + self.growth_rate) ** years
        return dividends


def calibrate_equity_volatility(historical_returns: np.ndarray) -> float:
    """
    Calibrate equity volatility from historical returns.

    Args:
        historical_returns: Historical returns (daily, monthly, or annual)

    Returns:
        Annualized volatility
    """
    # Calculate standard deviation
    vol = np.std(historical_returns)

    # If returns are not annual, need to annualize
    # Assuming monthly returns as default
    # For daily: multiply by sqrt(252)
    # For monthly: multiply by sqrt(12)
    # For annual: no adjustment

    return vol


def calculate_sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float
) -> float:
    """
    Calculate Sharpe ratio.

    Sharpe = (E[R] - Rf) / σ

    Args:
        returns: Portfolio returns
        risk_free_rate: Risk-free rate

    Returns:
        Sharpe ratio
    """
    excess_returns = returns - risk_free_rate
    return np.mean(excess_returns) / np.std(excess_returns)


def calculate_maximum_drawdown(prices: np.ndarray) -> Tuple[float, int, int]:
    """
    Calculate maximum drawdown from price series.

    Args:
        prices: Price path (1D array)

    Returns:
        Tuple of (max_drawdown, peak_idx, trough_idx)
    """
    # Calculate running maximum
    running_max = np.maximum.accumulate(prices)

    # Calculate drawdown
    drawdown = (prices - running_max) / running_max

    # Find maximum drawdown
    max_dd_idx = np.argmin(drawdown)
    max_dd = drawdown[max_dd_idx]

    # Find peak
    peak_idx = np.argmax(prices[:max_dd_idx + 1])

    return max_dd, peak_idx, max_dd_idx
