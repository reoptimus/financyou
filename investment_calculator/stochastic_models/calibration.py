"""
Calibration Module for Financial Models

This module handles calibration of financial models to market data, including:
1. EIOPA (European Insurance and Occupational Pensions Authority) yield curves
2. Forward rate curve construction
3. Zero-coupon bond prices
4. Swaption volatilities
5. Historical market data integration

The EIOPA curves are regulatory risk-free interest rate term structures
used by European insurance companies for Solvency II calculations.

Key Features:
- EIOPA curve loading from Excel/CSV
- Forward rate (f(0,t)) calculation from spot rates
- Zero-coupon bond price (P(0,t)) calculation
- Curve interpolation and smoothing
- Multi-country support
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict
from scipy import interpolate
from scipy.optimize import minimize
import warnings


class EIOPACalibrator:
    """
    Calibrator for EIOPA regulatory yield curves.

    EIOPA provides risk-free interest rate term structures for various
    currencies and jurisdictions. This class processes these curves to
    extract forward rates and bond prices needed for Hull-White calibration.

    Attributes:
        spot_rates: EIOPA spot rates (zero-coupon yields)
        maturities: Corresponding maturities in years
        country: Country/currency code
        dt: Time step for interpolation
    """

    def __init__(
        self,
        spot_rates: Optional[np.ndarray] = None,
        maturities: Optional[np.ndarray] = None,
        country: str = "France",
        dt: float = 0.5
    ):
        """
        Initialize EIOPA calibrator.

        Args:
            spot_rates: EIOPA spot rates (if None, will need to load from file)
            maturities: Maturities in years (if None, assumes 1, 2, 3, ...)
            country: Country identifier
            dt: Time step for interpolation
        """
        self.spot_rates = spot_rates
        self.country = country
        self.dt = dt

        if maturities is None and spot_rates is not None:
            self.maturities = np.arange(1, len(spot_rates) + 1)
        else:
            self.maturities = maturities

        # Will be computed
        self.P0t = None  # Zero-coupon bond prices
        self.f0t = None  # Forward rates
        self.P0t_interp = None  # Interpolated bond prices
        self.f0t_interp = None  # Interpolated forward rates

    @classmethod
    def from_excel(
        cls,
        filepath: str,
        sheet_name: str = "RFR_spot_no_VA",
        country_column: int = 2,
        start_row: int = 10,
        end_row: int = 160,
        dt: float = 0.5
    ) -> 'EIOPACalibrator':
        """
        Load EIOPA curve from Excel file.

        Args:
            filepath: Path to EIOPA Excel file
            sheet_name: Sheet name containing spot rates (default: "RFR_spot_no_VA")
            country_column: Column index for the country (0-indexed)
            start_row: Starting row for data (0-indexed)
            end_row: Ending row for data (0-indexed)
            dt: Time step for interpolation

        Returns:
            EIOPACalibrator instance
        """
        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)

            # Extract spot rates
            spot_rates = df.iloc[start_row:end_row, country_column].values

            # Convert to numeric, handling any errors
            spot_rates = pd.to_numeric(spot_rates, errors='coerce')

            # Remove NaN values
            valid_mask = ~np.isnan(spot_rates)
            spot_rates = spot_rates[valid_mask]

            # Maturities (1, 2, 3, ... years)
            maturities = np.arange(1, len(spot_rates) + 1)

            return cls(spot_rates=spot_rates, maturities=maturities, dt=dt)

        except Exception as e:
            raise ValueError(f"Error loading EIOPA data from Excel: {e}")

    @classmethod
    def from_csv(
        cls,
        filepath: str,
        country_column: str = "France",
        dt: float = 0.5
    ) -> 'EIOPACalibrator':
        """
        Load EIOPA curve from CSV file.

        Args:
            filepath: Path to CSV file
            country_column: Column name for the country
            dt: Time step for interpolation

        Returns:
            EIOPACalibrator instance
        """
        try:
            df = pd.read_csv(filepath, index_col=0)
            spot_rates = df[country_column].values

            # Convert to numeric
            spot_rates = pd.to_numeric(spot_rates, errors='coerce')

            # Remove NaN
            valid_mask = ~np.isnan(spot_rates)
            spot_rates = spot_rates[valid_mask]

            maturities = np.arange(1, len(spot_rates) + 1)

            return cls(spot_rates=spot_rates, maturities=maturities, dt=dt)

        except Exception as e:
            raise ValueError(f"Error loading EIOPA data from CSV: {e}")

    def calibrate(self, smoothing_start: int = 60, smoothing_window: int = 20):
        """
        Calibrate forward rates and bond prices from EIOPA spot rates.

        This method:
        1. Calculates zero-coupon bond prices from spot rates
        2. Interpolates to desired time step
        3. Extracts forward rates from bond prices
        4. Smooths forward rates for long maturities

        Args:
            smoothing_start: Year at which to start smoothing (default: 60)
            smoothing_window: Window for rolling average smoothing (default: 20)
        """
        if self.spot_rates is None:
            raise ValueError("No spot rates loaded. Use from_excel() or from_csv()")

        # Step 1: Calculate zero-coupon bond prices from spot rates
        # P(0,T) = 1 / (1 + r(T))^T
        self.P0t = self._calculate_bond_prices()

        # Step 2: Interpolate bond prices to time step dt
        self.P0t_interp = self._interpolate_bond_prices()

        # Step 3: Calculate forward rates from interpolated bond prices
        self.f0t_interp = self._calculate_forward_rates()

        # Step 4: Smooth forward rates for long maturities
        self.f0t = self._smooth_forward_rates(smoothing_start, smoothing_window)

    def _calculate_bond_prices(self) -> np.ndarray:
        """
        Calculate zero-coupon bond prices from spot rates.

        P(0,T) = 1 / (1 + spot_rate(T))^T

        Returns:
            Bond prices P(0,t)
        """
        P0t = 1 / (1 + self.spot_rates) ** self.maturities

        # Include P(0,0) = 1
        P0t = np.concatenate([[1.0], P0t])

        return P0t

    def _interpolate_bond_prices(self) -> np.ndarray:
        """
        Interpolate bond prices to time step dt using spline.

        Returns:
            Interpolated bond prices
        """
        # Time grid for interpolation
        T_max = len(self.P0t) - 1  # Maximum maturity
        t_interp = np.arange(0, T_max + self.dt, self.dt)

        # Original time grid
        t_original = np.arange(len(self.P0t))

        # Spline interpolation (natural cubic spline)
        # Using scipy's UnivariateSpline with smoothing
        spline = interpolate.UnivariateSpline(
            t_original, self.P0t, s=0, k=3  # s=0 means no smoothing, k=3 is cubic
        )

        P0t_interp = spline(t_interp)

        # Ensure P(0,0) = 1
        P0t_interp[0] = 1.0

        return P0t_interp

    def _calculate_forward_rates(self) -> np.ndarray:
        """
        Calculate instantaneous forward rates from bond prices.

        f(0,t) = -d/dt log(P(0,t))

        Discrete approximation using centered differences.

        Returns:
            Forward rates f(0,t)
        """
        # Log of bond prices
        log_P = np.log(self.P0t_interp)

        # Calculate derivative using centered differences
        # f(0,t) ≈ -(log(P(0,t+dt)) - log(P(0,t-dt))) / (2*dt)

        n = len(log_P)
        f0t = np.zeros(n)

        # Forward difference for first point
        f0t[0] = -(log_P[1] - log_P[0]) / self.dt

        # Centered differences for interior points
        for i in range(1, n - 1):
            f0t[i] = -(log_P[i + 1] - log_P[i - 1]) / (2 * self.dt)

        # Backward difference for last point
        f0t[-1] = -(log_P[-1] - log_P[-2]) / self.dt

        return f0t

    def _smooth_forward_rates(
        self,
        smoothing_start: int,
        smoothing_window: int
    ) -> np.ndarray:
        """
        Smooth forward rates for long maturities using rolling average.

        Args:
            smoothing_start: Year at which to start smoothing
            smoothing_window: Window size for rolling average

        Returns:
            Smoothed forward rates
        """
        f0t_smooth = self.f0t_interp.copy()

        # Convert smoothing_start to index
        start_idx = int(smoothing_start / self.dt)
        window_size = int(smoothing_window / self.dt)

        if start_idx < len(f0t_smooth):
            # Apply rolling average from smoothing_start onward
            for i in range(start_idx, len(f0t_smooth) - window_size):
                # Calculate average over window
                window_avg = np.mean(f0t_smooth[i:i + window_size + 1])
                f0t_smooth[i] = window_avg

            # Extend last smoothed value to the end
            if len(f0t_smooth) - window_size > start_idx:
                last_smooth = f0t_smooth[len(f0t_smooth) - window_size]
                f0t_smooth[len(f0t_smooth) - window_size + 1:] = last_smooth

        return f0t_smooth

    def get_forward_curve(self, n_steps: Optional[int] = None) -> np.ndarray:
        """
        Get forward rate curve.

        Args:
            n_steps: Number of steps to return (if None, returns all)

        Returns:
            Forward rate array
        """
        if self.f0t is None:
            raise ValueError("Must call calibrate() first")

        if n_steps is None:
            return self.f0t
        else:
            return self.f0t[:n_steps]

    def get_bond_prices(self, n_steps: Optional[int] = None) -> np.ndarray:
        """
        Get zero-coupon bond prices.

        Args:
            n_steps: Number of steps to return (if None, returns all)

        Returns:
            Bond price array
        """
        if self.P0t_interp is None:
            raise ValueError("Must call calibrate() first")

        if n_steps is None:
            return self.P0t_interp
        else:
            return self.P0t_interp[:n_steps]

    def plot_curves(self):
        """
        Plot the calibrated curves.

        Requires matplotlib to be installed.
        """
        try:
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(2, 2, figsize=(12, 10))

            # Original spot rates
            axes[0, 0].plot(self.maturities, self.spot_rates * 100, 'o-')
            axes[0, 0].set_xlabel('Maturity (years)')
            axes[0, 0].set_ylabel('Spot Rate (%)')
            axes[0, 0].set_title('EIOPA Spot Rates')
            axes[0, 0].grid(True)

            # Bond prices
            t_grid = np.arange(len(self.P0t_interp)) * self.dt
            axes[0, 1].plot(t_grid, self.P0t_interp)
            axes[0, 1].set_xlabel('Maturity (years)')
            axes[0, 1].set_ylabel('Price')
            axes[0, 1].set_title('Zero-Coupon Bond Prices P(0,t)')
            axes[0, 1].grid(True)

            # Forward rates (unsmoothed)
            axes[1, 0].plot(t_grid, self.f0t_interp * 100)
            axes[1, 0].set_xlabel('Time (years)')
            axes[1, 0].set_ylabel('Forward Rate (%)')
            axes[1, 0].set_title('Instantaneous Forward Rates f(0,t) - Unsmoothed')
            axes[1, 0].grid(True)

            # Forward rates (smoothed)
            axes[1, 1].plot(t_grid, self.f0t * 100)
            axes[1, 1].set_xlabel('Time (years)')
            axes[1, 1].set_ylabel('Forward Rate (%)')
            axes[1, 1].set_title('Instantaneous Forward Rates f(0,t) - Smoothed')
            axes[1, 1].grid(True)

            plt.tight_layout()
            plt.show()

        except ImportError:
            warnings.warn("matplotlib not installed, cannot plot curves")


class SwaptionCalibrator:
    """
    Calibrator for swaption volatilities.

    Swaptions are options on interest rate swaps. Their market prices
    can be used to calibrate the volatility parameter σ in the Hull-White model.
    """

    def __init__(self, market_vols: Dict[Tuple[int, int], float]):
        """
        Initialize swaption calibrator.

        Args:
            market_vols: Dictionary mapping (option_maturity, swap_tenor) to
                        implied volatility. E.g., {(1, 5): 0.20} means a 1-year
                        option on a 5-year swap has 20% implied volatility.
        """
        self.market_vols = market_vols

    def calibrate_hull_white_sigma(
        self,
        a: float,
        f0t: np.ndarray,
        P0t: np.ndarray
    ) -> float:
        """
        Calibrate σ to match market swaption volatilities.

        This is a simplified calibration using least squares.

        Args:
            a: Hull-White mean reversion parameter (assumed known)
            f0t: Forward rate curve
            P0t: Bond price curve

        Returns:
            Calibrated σ parameter
        """
        def objective(sigma):
            """Minimize squared difference between model and market vols."""
            total_error = 0

            for (T_option, T_swap), market_vol in self.market_vols.items():
                model_vol = self._hw_swaption_vol(
                    T_option, T_swap, a, sigma, f0t, P0t
                )
                total_error += (model_vol - market_vol) ** 2

            return total_error

        # Optimize
        result = minimize(objective, x0=0.01, bounds=[(0.001, 0.1)])

        if result.success:
            return result.x[0]
        else:
            warnings.warn("Swaption calibration did not converge")
            return 0.01

    def _hw_swaption_vol(
        self,
        T_option: float,
        T_swap: float,
        a: float,
        sigma: float,
        f0t: np.ndarray,
        P0t: np.ndarray
    ) -> float:
        """
        Calculate Hull-White swaption volatility (simplified).

        This is a placeholder for the full Hull-White swaption pricing formula.

        Args:
            T_option: Option maturity
            T_swap: Swap tenor
            a: Mean reversion
            sigma: Volatility
            f0t: Forward curve
            P0t: Bond prices

        Returns:
            Implied volatility
        """
        # Simplified approximation
        # In practice, would use full Hull-White swaption formula
        variance = (sigma**2 / (2 * a)) * (1 - np.exp(-2 * a * T_option))
        vol = np.sqrt(variance / T_option)

        return vol


def bootstrap_spot_curve(
    bond_prices: np.ndarray,
    maturities: np.ndarray
) -> np.ndarray:
    """
    Bootstrap spot rate curve from bond prices.

    Args:
        bond_prices: Zero-coupon bond prices
        maturities: Corresponding maturities

    Returns:
        Spot rates
    """
    spot_rates = (1 / bond_prices) ** (1 / maturities) - 1
    return spot_rates


def nelson_siegel_curve(
    maturities: np.ndarray,
    beta0: float,
    beta1: float,
    beta2: float,
    lambda_param: float
) -> np.ndarray:
    """
    Generate yield curve using Nelson-Siegel parametrization.

    y(m) = β₀ + β₁ * (1 - exp(-m/λ))/(m/λ) + β₂ * ((1 - exp(-m/λ))/(m/λ) - exp(-m/λ))

    Args:
        maturities: Maturity grid
        beta0: Level parameter
        beta1: Slope parameter
        beta2: Curvature parameter
        lambda_param: Decay parameter

    Returns:
        Yield curve
    """
    m = maturities
    term1 = beta0
    term2 = beta1 * (1 - np.exp(-m / lambda_param)) / (m / lambda_param)
    term3 = beta2 * (
        (1 - np.exp(-m / lambda_param)) / (m / lambda_param) - np.exp(-m / lambda_param)
    )

    yields = term1 + term2 + term3
    return yields
