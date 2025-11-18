"""
Real Estate Model

This module implements real estate returns using Hull-White stochastic dynamics
for property prices with separate rental income component.

The model separates total real estate returns into:
1. Property price appreciation (capital gains)
2. Rental income (yield)

Property prices evolve according to a Hull-White-like process:
    dP/P = [k(t) - a*r(t)]dt + σ*dW(t)

where:
    k(t) = time-dependent drift (calibrated to market)
    a = mean reversion speed
    σ = real estate volatility
    r(t) = auxiliary stochastic process

Rental income includes:
- Base rental yield
- Inflation adjustment
- Stochastic components

Key Features:
- Integration with Hull-White interest rates
- Correlation with other asset classes
- Separate tracking of rental income and price appreciation
- Inflation indexation of rents
"""

import numpy as np
from typing import Dict, Optional, Tuple
import warnings


class RealEstateModel:
    """
    Real estate model with stochastic price dynamics and rental income.

    This class generates real estate return scenarios that include both
    price appreciation and rental income, calibrated to market data.

    Attributes:
        a: Mean reversion speed for property prices
        sigma: Real estate price volatility
        rental_yield: Base rental yield (as decimal, e.g., 0.01 for 1%)
        inflation_adjustment: Annual inflation adjustment for rents
        dt: Time step in years
        n_scenarios: Number of Monte Carlo scenarios
        n_steps: Number of time steps
    """

    def __init__(
        self,
        a: float,
        sigma: float,
        rental_yield: float = 0.01,
        inflation_adjustment: float = 0.0,
        dt: float = 0.5,
        n_scenarios: int = 1000,
        T: int = 60
    ):
        """
        Initialize real estate model.

        Args:
            a: Mean reversion speed (e.g., 0.1 to 0.3)
            sigma: Property price volatility (e.g., 0.10 to 0.15)
            rental_yield: Base rental yield as fraction of property value (default: 1%)
            inflation_adjustment: Annual inflation adjustment for rents (default: 0%)
            dt: Time step in years (default: 0.5 = semi-annual)
            n_scenarios: Number of scenarios to generate
            T: Time horizon in years
        """
        self.a = a
        self.sigma = sigma
        self.rental_yield = rental_yield
        self.inflation_adjustment = inflation_adjustment
        self.dt = dt
        self.n_scenarios = n_scenarios
        self.T = T
        self.n_steps = int(T / dt)

        # Validate parameters
        self._validate_parameters()

    def _validate_parameters(self):
        """Validate model parameters."""
        if self.a <= 0:
            raise ValueError(f"Mean reversion speed a must be positive, got {self.a}")
        if self.sigma <= 0:
            raise ValueError(f"Volatility sigma must be positive, got {self.sigma}")
        if self.rental_yield < 0:
            raise ValueError(f"Rental yield must be non-negative, got {self.rental_yield}")
        if self.dt <= 0:
            raise ValueError(f"Time step dt must be positive, got {self.dt}")

    def generate_returns(
        self,
        short_rates: np.ndarray,
        f0t: np.ndarray,
        re_price_shocks: Optional[np.ndarray] = None,
        re_rental_shocks: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        Generate real estate return scenarios.

        Args:
            short_rates: Short rate paths from Hull-White (n_scenarios × n_steps)
            f0t: Forward rate curve for calibration (n_steps,)
            re_price_shocks: Optional pre-generated price shocks (n_scenarios × n_steps)
            re_rental_shocks: Optional pre-generated rental shocks (n_scenarios × n_steps)

        Returns:
            Dictionary containing:
                - 'total_returns': Total real estate returns (n_scenarios × n_steps)
                - 'price_returns': Price appreciation only (n_scenarios × n_steps)
                - 'rental_returns': Rental income component (n_scenarios × n_steps)
                - 'auxiliary_rates': Auxiliary rate process r2(t) (n_scenarios × n_steps)
        """
        n_scenarios, n_steps = short_rates.shape

        if n_scenarios != self.n_scenarios or n_steps != self.n_steps:
            warnings.warn(
                f"Input shape ({n_scenarios}, {n_steps}) differs from initialized "
                f"({self.n_scenarios}, {self.n_steps}). Using input shape."
            )

        # Generate or use provided shocks
        if re_price_shocks is None:
            re_price_shocks = np.random.normal(0, 1, (n_scenarios, n_steps))

        if re_rental_shocks is None:
            re_rental_shocks = np.random.normal(0, 1, (n_scenarios, n_steps))

        # Generate auxiliary rate process r2(t)
        r2 = self._generate_auxiliary_rates(short_rates, f0t, re_rental_shocks)

        # Generate price returns
        price_returns = self._generate_price_returns(short_rates, f0t, r2, re_price_shocks)

        # Generate rental returns
        rental_returns = self._generate_rental_returns(n_scenarios, n_steps)

        # Total returns = price + rental
        total_returns = price_returns + rental_returns

        return {
            'total_returns': total_returns,
            'price_returns': price_returns,
            'rental_returns': rental_returns,
            'auxiliary_rates': r2
        }

    def _generate_auxiliary_rates(
        self,
        short_rates: np.ndarray,
        f0t: np.ndarray,
        shocks: np.ndarray
    ) -> np.ndarray:
        """
        Generate auxiliary stochastic rate process r2(t).

        This follows a Hull-White-like dynamics:
            dr2 = [k(t) - a*r2(t)]dt + σ*dW(t)

        Args:
            short_rates: Short rate paths (n_scenarios × n_steps)
            f0t: Forward rate curve (n_steps,)
            shocks: Random shocks (n_scenarios × n_steps)

        Returns:
            Auxiliary rates r2(t) (n_scenarios × n_steps)
        """
        n_scenarios, n_steps = short_rates.shape
        r2 = np.zeros((n_scenarios, n_steps))

        # Initial value
        r2[:, 0] = f0t[0] if len(f0t) > 0 else 0.0

        # Precompute coefficients
        exp_a_dt = np.exp(-self.a * self.dt)
        K2T_t = (1 - exp_a_dt) / self.a
        K2T_t2a = (1 - np.exp(-2 * self.a * self.dt)) / (2 * self.a)
        eta2 = (self.sigma / self.a) * (
            self.dt - 2 * K2T_t + K2T_t2a
        ) ** 0.5

        # Generate auxiliary rate process
        for t in range(n_steps - 1):
            # Drift term (calibrated to forward curve)
            kimmo = f0t[t] if t < len(f0t) else f0t[-1]

            # Hull-White dynamics for r2
            r2[:, t + 1] = (
                r2[:, t] * exp_a_dt +
                kimmo * (1 - exp_a_dt) +
                self.sigma * K2T_t2a**0.5 * shocks[:, t]
            )

        return r2

    def _generate_price_returns(
        self,
        short_rates: np.ndarray,
        f0t: np.ndarray,
        r2: np.ndarray,
        shocks: np.ndarray
    ) -> np.ndarray:
        """
        Generate real estate price returns.

        Price dynamics:
            dP/P = [k(t)*dt + (r2(t) - k(t))*K(dt) + η*dW(t)]

        Args:
            short_rates: Short rate paths (n_scenarios × n_steps)
            f0t: Forward rate curve (n_steps,)
            r2: Auxiliary rates (n_scenarios × n_steps)
            shocks: Random shocks (n_scenarios × n_steps)

        Returns:
            Price returns (n_scenarios × n_steps)
        """
        n_scenarios, n_steps = short_rates.shape
        price_returns = np.zeros((n_scenarios, n_steps))

        # Precompute coefficients
        K2T_t = (1 - np.exp(-self.a * self.dt)) / self.a
        K2T_t2a = (1 - np.exp(-2 * self.a * self.dt)) / (2 * self.a)
        eta2 = (self.sigma / self.a) * (
            self.dt - 2 * K2T_t + K2T_t2a
        ) ** 0.5

        for t in range(n_steps):
            # Drift calibration
            kimmo = f0t[t] if t < len(f0t) else f0t[-1]

            # Price return formula (from R code ImmoHW_V2.R:114)
            drift = kimmo * self.dt
            mean_reversion = (r2[:, t] - kimmo) * K2T_t
            diffusion = eta2 * shocks[:, t]

            price_returns[:, t] = drift + mean_reversion + diffusion

        return price_returns

    def _generate_rental_returns(
        self,
        n_scenarios: int,
        n_steps: int
    ) -> np.ndarray:
        """
        Generate rental income returns.

        Rental yield is typically constant as a percentage of property value,
        with inflation adjustments over time.

        Formula (from R code ImmoHW_V2.R:116):
            rental_return[t] = log(1 + rental_yield) + t * inflation_adjustment

        Args:
            n_scenarios: Number of scenarios
            n_steps: Number of time steps

        Returns:
            Rental returns (n_scenarios × n_steps)
        """
        rental_returns = np.zeros((n_scenarios, n_steps))

        # Base rental yield (in continuous terms)
        base_rental = np.log(1 + self.rental_yield) * self.dt

        # Inflation adjustment (in continuous terms)
        inflation_adj = self.inflation_adjustment * self.dt

        for t in range(n_steps):
            # Rental income with inflation indexation
            rental_returns[:, t] = base_rental + t * inflation_adj

        return rental_returns

    def calculate_cap_rate(
        self,
        rental_income: float,
        property_value: float
    ) -> float:
        """
        Calculate capitalization rate (cap rate).

        Cap Rate = Net Operating Income / Property Value

        Args:
            rental_income: Annual net operating income
            property_value: Current property value

        Returns:
            Capitalization rate
        """
        return rental_income / property_value

    def calculate_price_to_rent_ratio(
        self,
        property_value: float,
        annual_rent: float
    ) -> float:
        """
        Calculate price-to-rent ratio.

        Args:
            property_value: Current property value
            annual_rent: Annual rental income

        Returns:
            Price-to-rent ratio
        """
        return property_value / annual_rent


class CommercialRealEstate(RealEstateModel):
    """
    Commercial real estate model with vacancy and operating expenses.

    Extends the base real estate model to include:
    - Vacancy rates
    - Operating expenses
    - Lease terms
    - Tenant improvements
    """

    def __init__(
        self,
        a: float,
        sigma: float,
        rental_yield: float = 0.06,
        vacancy_rate: float = 0.05,
        operating_expense_ratio: float = 0.30,
        inflation_adjustment: float = 0.02,
        dt: float = 0.5,
        n_scenarios: int = 1000,
        T: int = 60
    ):
        """
        Initialize commercial real estate model.

        Args:
            a: Mean reversion speed
            sigma: Volatility
            rental_yield: Gross rental yield (before vacancy and expenses)
            vacancy_rate: Expected vacancy rate (default: 5%)
            operating_expense_ratio: Operating expenses as fraction of gross rent (default: 30%)
            inflation_adjustment: Annual inflation adjustment
            dt: Time step
            n_scenarios: Number of scenarios
            T: Time horizon
        """
        # Adjust rental yield for vacancy and expenses
        net_rental_yield = rental_yield * (1 - vacancy_rate) * (1 - operating_expense_ratio)

        super().__init__(
            a=a,
            sigma=sigma,
            rental_yield=net_rental_yield,
            inflation_adjustment=inflation_adjustment,
            dt=dt,
            n_scenarios=n_scenarios,
            T=T
        )

        self.vacancy_rate = vacancy_rate
        self.operating_expense_ratio = operating_expense_ratio
        self.gross_rental_yield = rental_yield

    def calculate_noi(
        self,
        property_value: float
    ) -> Tuple[float, float, float]:
        """
        Calculate Net Operating Income.

        Args:
            property_value: Current property value

        Returns:
            Tuple of (gross_income, operating_expenses, noi)
        """
        # Gross potential income
        gross_income = property_value * self.gross_rental_yield

        # Effective gross income (after vacancy)
        effective_income = gross_income * (1 - self.vacancy_rate)

        # Operating expenses
        operating_expenses = effective_income * self.operating_expense_ratio

        # Net operating income
        noi = effective_income - operating_expenses

        return gross_income, operating_expenses, noi


class ResidentialRealEstate(RealEstateModel):
    """
    Residential real estate model.

    Tailored for residential properties with typical parameters.
    """

    def __init__(
        self,
        location: str = "urban",
        dt: float = 0.5,
        n_scenarios: int = 1000,
        T: int = 60
    ):
        """
        Initialize residential real estate model.

        Args:
            location: Property location ("urban", "suburban", "rural")
            dt: Time step
            n_scenarios: Number of scenarios
            T: Time horizon
        """
        # Set parameters based on location
        if location == "urban":
            a = 0.15
            sigma = 0.12
            rental_yield = 0.035
        elif location == "suburban":
            a = 0.12
            sigma = 0.10
            rental_yield = 0.040
        else:  # rural
            a = 0.10
            sigma = 0.08
            rental_yield = 0.045

        super().__init__(
            a=a,
            sigma=sigma,
            rental_yield=rental_yield,
            inflation_adjustment=0.02,
            dt=dt,
            n_scenarios=n_scenarios,
            T=T
        )

        self.location = location


def calibrate_real_estate_parameters(
    historical_prices: np.ndarray,
    historical_rents: np.ndarray,
    dt: float = 1.0
) -> Tuple[float, float, float]:
    """
    Calibrate real estate model parameters from historical data.

    Args:
        historical_prices: Historical property price index
        historical_rents: Historical rental income
        dt: Time step of historical data (default: 1 year)

    Returns:
        Tuple of (a, sigma, rental_yield)
    """
    # Calculate price returns
    price_returns = np.diff(np.log(historical_prices))

    # Estimate volatility
    sigma = np.std(price_returns) / np.sqrt(dt)

    # Estimate mean reversion (simplified)
    # Fit AR(1) model: r[t] = α + β*r[t-1] + ε
    # Then a = -log(β) / dt
    if len(price_returns) > 1:
        beta = np.corrcoef(price_returns[:-1], price_returns[1:])[0, 1]
        a = -np.log(max(beta, 0.01)) / dt
        a = max(0.05, min(a, 0.5))  # Bounds
    else:
        a = 0.1

    # Calculate average rental yield
    if len(historical_rents) > 0 and len(historical_prices) > 0:
        rental_yield = np.mean(historical_rents / historical_prices)
    else:
        rental_yield = 0.03

    return a, sigma, rental_yield
