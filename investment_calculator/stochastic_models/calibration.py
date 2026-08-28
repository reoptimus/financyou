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

import warnings
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import interpolate
from scipy.optimize import brentq, minimize, minimize_scalar
from scipy.stats import norm

from investment_calculator.swaption_surface import (
    SwaptionSurface,
    SwaptionSurfaceSyntheticNotAllowedError,
    label_to_years,
)


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
        spot_rates: np.ndarray | None = None,
        maturities: np.ndarray | None = None,
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

        self.maturities: np.ndarray | None
        if maturities is None and spot_rates is not None:
            self.maturities = np.arange(1, len(spot_rates) + 1)
        else:
            self.maturities = maturities

        # Will be computed
        self.P0t: np.ndarray | None = None  # Zero-coupon bond prices
        self.f0t: np.ndarray | None = None  # Forward rates
        self.P0t_interp: np.ndarray | None = None  # Interpolated bond prices
        self.f0t_interp: np.ndarray | None = None  # Interpolated forward rates

    @classmethod
    def from_excel(
        cls,
        filepath: str,
        sheet_name: str = "RFR",
        country_column: int = 1,
        start_row: int = 1,
        end_row: int | None = None,
        dt: float = 0.5
    ) -> 'EIOPACalibrator':
        """
        Load EIOPA curve from Excel file.

        Les valeurs par défaut correspondent à la structure réelle des
        classeurs EIOPA tels que publiés (voir
        ``legacy/excel_files/EIOPA_avril_2018_FRANCE.xlsx``, feuille
        « RFR ») : une ligne d'en-tête (« BaseLine », « YCU », « YCD »...),
        puis une ligne par maturité de 1 à 150 ans, colonne 1 = courbe
        centrale sans ajustement de volatilité (« BaseLine »). Avant l'étape
        1.B.2, cette méthode n'avait jamais été appelée en pratique et ses
        anciens défauts (feuille « RFR_spot_no_VA », qui n'existe pas dans
        ce classeur ; colonne 2, qui pointe vers le choc de courbe « YCU »,
        pas la courbe centrale) en étaient la preuve.

        Args:
            filepath: Path to EIOPA Excel file
            sheet_name: Sheet name containing spot rates (default: "RFR")
            country_column: Column index for the curve à utiliser (0-indexed) —
                nommé « pays » car un fichier EIOPA est publié par pays, mais
                l'index sélectionne en réalité la VARIANTE de courbe dans ce
                fichier (BaseLine, YCU, YCD, avec/sans ajustement de
                volatilité), pas un pays différent.
            start_row: Starting row for data (0-indexed) ; 1 pour sauter la
                ligne d'en-tête.
            end_row: Ending row for data (0-indexed), exclusive. None pour
                lire jusqu'à la fin de la feuille.
            dt: Time step for interpolation

        Returns:
            EIOPACalibrator instance

        Raises:
            ValueError: fichier illisible, feuille absente, ou courbe vide
                une fois les valeurs non numériques retirées.
        """
        try:
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)

            # Extract spot rates
            spot_rates = df.iloc[start_row:end_row, country_column].to_numpy()

            # Convert to numeric, handling any errors
            spot_rates = pd.to_numeric(pd.Series(spot_rates), errors='coerce').to_numpy()

            # Remove NaN values
            valid_mask = ~np.isnan(spot_rates)
            spot_rates = spot_rates[valid_mask]

            if len(spot_rates) == 0:
                raise ValueError(
                    f"Aucun taux numérique trouvé dans {filepath!r}, feuille "
                    f"{sheet_name!r}, colonne {country_column}, lignes "
                    f"[{start_row}:{end_row}]. Vérifiez la structure du "
                    f"classeur (une ligne d'en-tête est généralement présente)."
                )

            # Maturities (1, 2, 3, ... years)
            maturities = np.arange(1, len(spot_rates) + 1)

            return cls(spot_rates=spot_rates, maturities=maturities, dt=dt)

        except Exception as e:
            raise ValueError(f"Error loading EIOPA data from Excel: {e}") from e

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
            raise ValueError(f"Error loading EIOPA data from CSV: {e}") from e

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

        Raises:
            ValueError: si aucune courbe EIOPA n'a été chargée.
        """
        # Garde explicite : `spot_rates` et `maturities` valent None tant qu'aucune
        # courbe n'a été fournie. Le contrôle est redondant avec celui de
        # calibrate(), mais il protège l'appel direct de cette méthode privée et
        # rend l'invariant visible pour le vérificateur de types.
        if self.spot_rates is None or self.maturities is None:
            raise ValueError(
                "spot_rates/maturities non renseignés : construisez le calibrateur "
                "avec EIOPACalibrator.from_excel() ou from_csv(), ou passez "
                "spot_rates au constructeur."
            )

        P0t = 1 / (1 + self.spot_rates) ** self.maturities

        # Include P(0,0) = 1
        P0t = np.concatenate([[1.0], P0t])

        return P0t

    def _interpolate_bond_prices(self) -> np.ndarray:
        """
        Interpolate bond prices to time step dt using spline.

        Returns:
            Interpolated bond prices

        Raises:
            ValueError: si les prix zéro-coupon n'ont pas encore été calculés.
        """
        # Garde explicite : `P0t` n'est peuplé que par _calculate_bond_prices(),
        # première étape de calibrate().
        if self.P0t is None:
            raise ValueError(
                "P0t non renseigné : appelez d'abord calibrate(), qui calcule "
                "les prix zéro-coupon avant de les interpoler."
            )

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
        # Garde explicite : `P0t_interp` n'est peuplé que par
        # _interpolate_bond_prices(), étape précédente de calibrate().
        if self.P0t_interp is None:
            raise ValueError(
                "P0t_interp non renseigné : appelez d'abord calibrate(), qui "
                "interpole les prix zéro-coupon avant de calculer les taux forward."
            )

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

        Raises:
            ValueError: si les taux forward interpolés n'ont pas été calculés.
        """
        # Garde explicite : `f0t_interp` n'est peuplé que par
        # _calculate_forward_rates(), troisième étape de calibrate().
        if self.f0t_interp is None:
            raise ValueError(
                "f0t_interp non renseigné : appelez d'abord calibrate(), qui "
                "calcule les taux forward interpolés avant de les lisser."
            )

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

    def get_forward_curve(self, n_steps: int | None = None) -> np.ndarray:
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

    def get_bond_prices(self, n_steps: int | None = None) -> np.ndarray:
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
            warnings.warn("matplotlib not installed, cannot plot curves", stacklevel=2)


def nelson_siegel_forward_curve(
    maturities: np.ndarray,
    beta0: float,
    beta1: float,
    beta2: float,
    lambda_param: float
) -> np.ndarray:
    """
    Taux forward instantané f(0,t) cohérent avec :func:`nelson_siegel_curve`
    (le taux zéro y(t) = (1/t)∫₀ᵗf(0,s)ds). Nécessaire pour la décomposition
    de Jamshidian (voir :class:`SwaptionCalibrator`), qui a besoin de f(0,t)
    en plus de P(0,t). Formule standard Nelson-Siegel :
    f(t) = β₀ + β₁·exp(-t/λ) + β₂·(t/λ)·exp(-t/λ).
    """
    m = np.asarray(maturities, dtype=float)
    x = m / lambda_param
    return beta0 + beta1 * np.exp(-x) + beta2 * x * np.exp(-x)


def nelson_siegel_curve_functions(
    beta0: float,
    beta1: float,
    beta2: float,
    lambda_param: float
) -> tuple[Callable[[np.ndarray], np.ndarray], Callable[[np.ndarray], np.ndarray]]:
    """
    Construire (P0, f0), les fonctions t → P(0,t) et t → f(0,t) d'une courbe
    Nelson-Siegel — utilisées par :class:`SwaptionCalibrator` pour pricer.

    Réservé à la reproduction des forwards ATM et des vérifications d'une
    surface de swaptions (voir ``SwaptionSurface.reference_curve``) : une
    calibration en production doit utiliser une vraie courbe
    (:func:`grid_curve_functions`, à partir de
    :class:`investment_calculator.yield_curve.YieldCurve`), pas cette
    paramétrisation lissée.
    """
    def P0(t: np.ndarray) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        safe_t = np.where(t <= 1e-12, 1e-12, t)
        y = nelson_siegel_curve(safe_t, beta0, beta1, beta2, lambda_param)
        price = np.exp(-y * safe_t)
        return np.where(t <= 1e-12, 1.0, price)

    def f0(t: np.ndarray) -> np.ndarray:
        return nelson_siegel_forward_curve(t, beta0, beta1, beta2, lambda_param)

    return P0, f0


def grid_curve_functions(
    P0t: np.ndarray,
    f0t: np.ndarray,
    dt: float
) -> tuple[Callable[[np.ndarray], np.ndarray], Callable[[np.ndarray], np.ndarray]]:
    """
    Construire (P0, f0) par interpolation linéaire d'une courbe discrétisée
    (grille de pas ``dt``, telle que produite par
    :class:`EIOPACalibrator`/:class:`investment_calculator.yield_curve.YieldCurve`),
    pour pricer des swaptions dont les échéances ne tombent pas exactement
    sur la grille. Interpolation linéaire sur P(0,t) directement (pas
    log-linéaire) : approximation simple, suffisante pour un ``dt`` fin
    (voir known_gaps de SwaptionCalibrator).
    """
    t_grid = np.arange(len(P0t)) * dt

    def P0(t: np.ndarray) -> np.ndarray:
        return np.interp(np.asarray(t, dtype=float), t_grid, P0t)

    def f0(t: np.ndarray) -> np.ndarray:
        return np.interp(np.asarray(t, dtype=float), t_grid, f0t)

    return P0, f0


def _hull_white_B(a: float, tau: np.ndarray | float) -> np.ndarray | float:
    """B(t,T) = (1 - exp(-a(T-t))) / a, avec tau = T - t."""
    return (1 - np.exp(-a * tau)) / a


def _hull_white_A(
    a: float,
    sigma: float,
    t: float,
    T: float,
    curve_p0: Callable[[np.ndarray], np.ndarray],
    curve_f0: Callable[[np.ndarray], np.ndarray],
) -> float:
    """
    A(t,T) du modèle Hull-White 1 facteur (Brigo-Mercurio, éq. 3.39) :
    P(t,T) = A(t,T)·exp(-B(t,T)·r(t)).
    """
    B = _hull_white_B(a, T - t)
    p0t = float(curve_p0(np.array([t]))[0])
    p0T = float(curve_p0(np.array([T]))[0])
    f0t = float(curve_f0(np.array([t]))[0])
    return (p0T / p0t) * np.exp(
        B * f0t - (sigma**2 / (4 * a)) * (1 - np.exp(-2 * a * t)) * B**2
    )


def hull_white_zero_coupon_bond_put_price(
    a: float,
    sigma: float,
    t: float,
    T: float,
    S: float,
    strike: float,
    curve_p0: Callable[[np.ndarray], np.ndarray],
) -> float:
    """
    Prix d'un put européen, maturité t=T, strike K, sur un zéro-coupon
    P(T,S) — formule fermée Hull-White 1 facteur (Brigo-Mercurio, éq. 3.41).
    Brique de la décomposition de Jamshidian utilisée par
    :class:`SwaptionCalibrator` pour pricer une swaption.
    """
    sigma_p = sigma * np.sqrt((1 - np.exp(-2 * a * (T - t))) / (2 * a)) * _hull_white_B(a, S - T)
    p0T = float(curve_p0(np.array([T]))[0])
    p0S = float(curve_p0(np.array([S]))[0])
    h = (1 / sigma_p) * np.log(p0S / (p0T * strike)) + sigma_p / 2
    return strike * p0T * norm.cdf(-h + sigma_p) - p0S * norm.cdf(-h)


def hull_white_payer_swaption_price(
    a: float,
    sigma: float,
    expiry_years: float,
    n_payments: int,
    fixed_rate: float,
    curve_p0: Callable[[np.ndarray], np.ndarray],
    curve_f0: Callable[[np.ndarray], np.ndarray],
) -> float:
    """
    Prix (en fraction du nominal) d'une swaption payeuse européenne, jambe
    fixe annuelle, sous Hull-White 1 facteur, par décomposition de
    Jamshidian : une swaption payeuse ≡ un put sur l'obligation à coupon de
    taux ``fixed_rate`` sous-jacente au swap, strike 1 (le nominal). Jamshidian
    exploite la monotonie de cette obligation en le taux court pour trouver
    r* tel que l'obligation vaille exactement 1 en r*, puis décompose le put
    sur obligation en une somme de puts sur zéro-coupon, chacun de strike
    A(T0,Tᵢ)·exp(-B(T0,Tᵢ)·r*) — voir Brigo-Mercurio, section 3.9.

    Méthodologie standard, mathématiquement équivalente (à la limite) au
    pricer Monte-Carlo du script R d'origine
    (legacy/R_scripts/Calib_Taux_Swaptions_V2.R), mais PAS un portage ligne à
    ligne : les deux scripts dont il dépendait pour le pricing
    (Prix_swaptions_M2_V2.R, Prix_swaption_Normal_Uniroot.R) sont absents de
    legacy/ — voir docs/journal-1b-calibration.md, point 8.

    Args:
        expiry_years: échéance de l'option T0, en années.
        n_payments: nombre de paiements annuels du swap sous-jacent (le
            ténor, en années, pour une jambe fixe annuelle).
        fixed_rate: taux fixe du swap (le strike de la swaption).
    """
    payment_times = expiry_years + np.arange(1, n_payments + 1)
    coupons = np.full(n_payments, fixed_rate)
    coupons[-1] += 1.0

    B = _hull_white_B(a, payment_times - expiry_years)
    A = np.array(
        [_hull_white_A(a, sigma, expiry_years, T, curve_p0, curve_f0) for T in payment_times]
    )

    def coupon_bond_price(r_star: float) -> float:
        return float(np.sum(coupons * A * np.exp(-B * r_star))) - 1.0

    r_star = brentq(coupon_bond_price, -2.0, 2.0)
    strikes = A * np.exp(-B * r_star)

    return float(sum(
        coupons[i] * hull_white_zero_coupon_bond_put_price(
            a, sigma, 0.0, expiry_years, payment_times[i], strikes[i], curve_p0
        )
        for i in range(n_payments)
    ))


@dataclass(frozen=True)
class SwaptionInstrument:
    """Une swaption ATM de la surface, avec son forward et son annuité déjà calculés."""

    expiry_label: str
    tenor_label: str
    expiry_years: float
    n_payments: int
    forward_rate: float
    annuity: float
    market_vol_bp: float


@dataclass(frozen=True)
class SwaptionCalibrationResult:
    """Résultat d'une calibration Hull-White sur une bande d'instruments."""

    a: float
    sigma: float
    sigma_bp: float
    rmse_bp: float
    max_error_bp: float
    n_instruments: int


class SwaptionCalibrator:
    """
    Calibrateur Hull-White 1 facteur sur une surface de swaptions ATM.

    Voir :func:`hull_white_payer_swaption_price` pour la méthodologie de
    pricing (Jamshidian) et ses limites. Limites propres au calibrateur,
    reprises de la surface (voir
    :class:`investment_calculator.swaption_surface.SwaptionSurface`) :
    swaptions payeuses À LA MONNAIE uniquement (pas de smile/skew), jambe
    fixe annuelle, convention de volatilité NORMALE (Bachelier).

    Suit la recommandation de HANDOFF_surface_swaptions.md (section 4) :
    calibrer ``a`` ET ``sigma`` conjointement sur le cube complet dégénère
    (``a`` s'effondre vers 0 — dégénérescence classique d'un modèle à un
    facteur, observée aussi sur données réelles). Le schéma recommandé pour
    la production est de FIXER ``a`` (voir le paramètre ``fixed_a`` de
    :meth:`calibrate`) et de ne calibrer que ``sigma``, sur une seule bande
    co-terminale correspondant à l'horizon du passif visé (voir
    :meth:`select_co_terminal_band`) — un choix qui reste à trancher par une
    personne (voir docs/journal-1b-calibration.md, point 8).
    """

    def __init__(
        self,
        surface: SwaptionSurface,
        curve_p0: Callable[[np.ndarray], np.ndarray],
        curve_f0: Callable[[np.ndarray], np.ndarray],
        *,
        allow_synthetic: bool = False,
    ):
        """
        Args:
            surface: surface de volatilité chargée (voir
                investment_calculator.swaption_surface.load_swaption_surface).
            curve_p0, curve_f0: fonctions t → P(0,t) et t → f(0,t), par
                exemple issues de :func:`nelson_siegel_curve_functions` (pour
                reproduire les vérifications fournies avec une surface) ou de
                :func:`grid_curve_functions` (pour une vraie courbe de
                production).
            allow_synthetic: doit valoir True pour calibrer sur une surface
                ``synthetic: true`` — même garde-fou qu'à l'étape de
                chargement (voir SwaptionSurfaceSyntheticNotAllowedError),
                répétée ici pour qu'un appelant qui construirait
                SwaptionSurface autrement qu'avec load_swaption_surface ne
                puisse pas non plus contourner l'interdiction.
        """
        if surface.synthetic and not allow_synthetic:
            raise SwaptionSurfaceSyntheticNotAllowedError(
                f"La surface {surface.id!r} est synthétique : interdiction d'en tirer une "
                f"calibration publiée ou affichée à un utilisateur. Passez "
                f"allow_synthetic=True si c'est un usage de développement/test assumé."
            )

        self.surface = surface
        self._curve_p0 = curve_p0
        self._curve_f0 = curve_f0
        self.instruments = self._build_instruments()

    def _build_instruments(self) -> list[SwaptionInstrument]:
        instruments = []
        for i, expiry_label in enumerate(self.surface.expiries):
            expiry_years = label_to_years(expiry_label)
            for j, tenor_label in enumerate(self.surface.tenors):
                n_payments = int(round(label_to_years(tenor_label)))
                forward, annuity = self._forward_and_annuity(expiry_years, n_payments)
                instruments.append(
                    SwaptionInstrument(
                        expiry_label=expiry_label,
                        tenor_label=tenor_label,
                        expiry_years=expiry_years,
                        n_payments=n_payments,
                        forward_rate=forward,
                        annuity=annuity,
                        market_vol_bp=float(self.surface.vol_grid[i, j]),
                    )
                )
        return instruments

    def _forward_and_annuity(self, expiry_years: float, n_payments: int) -> tuple[float, float]:
        """
        Taux swap forward et annuité, recalculés à partir de la courbe
        fournie au constructeur — jamais lus depuis un fichier de forwards
        figé, pour que le strike ATM reste cohérent avec CETTE courbe (voir
        SwaptionSurface.reference_curve et known_gaps : conserver des
        forwards figés donnerait des strikes qui ne sont plus à la monnaie).
        """
        payment_times = expiry_years + np.arange(1, n_payments + 1)
        discounts = self._curve_p0(payment_times)
        annuity = float(np.sum(discounts))
        p0_t0 = float(self._curve_p0(np.array([expiry_years]))[0])
        forward = (p0_t0 - float(discounts[-1])) / annuity
        return forward, annuity

    def model_price(self, a: float, sigma: float, instrument: SwaptionInstrument) -> float:
        """Prix modèle (fraction du nominal) d'un instrument, sous (a, sigma)."""
        return hull_white_payer_swaption_price(
            a, sigma, instrument.expiry_years, instrument.n_payments,
            instrument.forward_rate, self._curve_p0, self._curve_f0,
        )

    def model_vol_bp(self, a: float, sigma: float, instrument: SwaptionInstrument) -> float:
        """
        Volatilité normale implicite (bp) du prix modèle. Inversion directe
        (pas de recherche de racine) car toutes les swaptions de la surface
        sont à la monnaie : Bachelier ATM se réduit à
        prix = annuité·σ_n·√(T/2π).
        """
        price = self.model_price(a, sigma, instrument)
        return price / (instrument.annuity * np.sqrt(instrument.expiry_years / (2 * np.pi))) * 10000

    def select_co_terminal_band(self, target_years: float) -> list[SwaptionInstrument]:
        """
        Pour chaque échéance disponible, sélectionner le ténor de la grille
        qui rapproche le plus expiry+tenor de ``target_years`` (une bande
        « co-terminale », toutes les swaptions arrivant à peu près au même
        horizon absolu) — un point par échéance.
        """
        by_expiry: dict[str, list[SwaptionInstrument]] = {}
        for instrument in self.instruments:
            by_expiry.setdefault(instrument.expiry_label, []).append(instrument)

        band = []
        for candidates in by_expiry.values():
            best = min(
                candidates,
                key=lambda inst: abs(inst.expiry_years + inst.n_payments - target_years),
            )
            band.append(best)
        return sorted(band, key=lambda inst: inst.expiry_years)

    def _rmse(
        self, a: float, sigma: float, instruments: list[SwaptionInstrument]
    ) -> tuple[float, float]:
        errors = np.array(
            [self.model_vol_bp(a, sigma, inst) - inst.market_vol_bp for inst in instruments]
        )
        return float(np.sqrt(np.mean(errors**2))), float(np.max(np.abs(errors)))

    def calibrate(
        self,
        instruments: list[SwaptionInstrument] | None = None,
        *,
        fixed_a: float | None = None,
        initial_a: float = 0.05,
        initial_sigma_bp: float = 50.0,
        xatol: float = 1e-4,
        fatol: float = 1e-6,
        maxiter: int = 500,
    ) -> SwaptionCalibrationResult:
        """
        Calibrer (a, sigma), ou seulement sigma si ``fixed_a`` est fourni,
        par moindres carrés sur l'écart de volatilité normale implicite
        (bp) entre le modèle et le marché.

        Args:
            instruments: sous-ensemble à calibrer (voir
                :meth:`select_co_terminal_band`) ; par défaut, tous les
                points de la surface — déconseillé en production (voir la
                docstring de la classe : dégénère ``a`` vers 0).
            fixed_a: si fourni, ``a`` est fixé à cette valeur et seul
                ``sigma`` est calibré (schéma recommandé en production).
            xatol, fatol, maxiter: tolérances de Nelder-Mead (ignorées si
                ``fixed_a`` est fourni, auquel cas l'optimisation à 1
                paramètre converge de toute façon très vite). Les défauts
                privilégient la vitesse (chaque évaluation reprix toute la
                bande, avec une recherche de racine par instrument) plutôt
                qu'une précision au-delà du bp, largement suffisante ici.
        """
        insts = instruments if instruments is not None else self.instruments

        if fixed_a is not None:
            def objective_sigma(sigma_bp: float) -> float:
                if sigma_bp <= 0:
                    return 1e6
                rmse, _ = self._rmse(fixed_a, sigma_bp / 10000, insts)
                return rmse

            result = minimize_scalar(
                objective_sigma, bracket=(1.0, initial_sigma_bp, 500.0)
            )
            a, sigma_bp = fixed_a, float(result.x)
        else:
            def objective(params: np.ndarray) -> float:
                a_param, sigma_bp = params
                if a_param <= 1e-5 or sigma_bp <= 0:
                    return 1e6
                rmse, _ = self._rmse(a_param, sigma_bp / 10000, insts)
                return rmse

            result = minimize(
                objective, x0=[initial_a, initial_sigma_bp], method="Nelder-Mead",
                options={"xatol": xatol, "fatol": fatol, "maxiter": maxiter},
            )
            a, sigma_bp = float(result.x[0]), float(result.x[1])

        sigma = sigma_bp / 10000
        rmse_bp, max_error_bp = self._rmse(a, sigma, insts)
        return SwaptionCalibrationResult(
            a=a, sigma=sigma, sigma_bp=sigma_bp,
            rmse_bp=rmse_bp, max_error_bp=max_error_bp, n_instruments=len(insts),
        )


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
