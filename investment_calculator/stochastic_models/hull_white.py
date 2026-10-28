"""
Hull-White Interest Rate Model

This module implements the Hull-White one-factor short rate model:
    dr(t) = [θ(t) - a*r(t)]dt + σ*dW(t)

The model generates stochastic risk-free interest rate paths and deflators
calibrated to market yield curves (e.g., EIOPA regulatory curves).

Key Features:
- Risk-neutral interest rate simulation
- Calibration to forward rate curves
- Deflator (discount factor) calculation
- Antithetic variance reduction
- Explosive scenario filtering

References:
- Hull, J., & White, A. (1990). Pricing Interest-Rate-Derivative Securities.
  The Review of Financial Studies, 3(4), 573-592.
"""

import logging
import warnings

import numpy as np

logger = logging.getLogger(__name__)


class HullWhiteModel:
    """
    Hull-White one-factor interest rate model.

    The Hull-White model is a single-factor, no-arbitrage model of the short rate.
    It extends the Vasicek model by making the mean reversion level time-dependent
    to fit the initial term structure of interest rates.

    Attributes:
        a: Mean reversion speed parameter (> 0)
        sigma: Volatility parameter (> 0)
        f0t: Forward rate curve f(0,t) at time 0
        P0t: Zero-coupon bond prices P(0,t) at time 0
        dt: Time step for discretization
        n_scenarios: Number of Monte Carlo scenarios
        T: Time horizon (in years)
    """

    def __init__(
        self,
        a: float,
        sigma: float,
        f0t: np.ndarray,
        P0t: np.ndarray,
        dt: float = 0.5,
        n_scenarios: int = 1000,
        T: int = 60
    ):
        """
        Initialize Hull-White model.

        Args:
            a: Mean reversion speed (e.g., 0.05 to 0.3)
            sigma: Instantaneous volatility (e.g., 0.01 to 0.03)
            f0t: Forward rate curve (array of shape (n_steps,))
            P0t: Zero-coupon bond prices (array of shape (n_steps,))
            dt: Time step in years (default: 0.5 = semi-annual)
            n_scenarios: Number of scenarios to generate
            T: Time horizon in years
        """
        self.a = a
        self.sigma = sigma
        self.f0t = f0t
        self.P0t = P0t
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
        if self.dt <= 0:
            raise ValueError(f"Time step dt must be positive, got {self.dt}")
        if self.n_scenarios <= 0:
            raise ValueError(f"Number of scenarios must be positive, got {self.n_scenarios}")
        if len(self.f0t) < self.n_steps:
            raise ValueError(
                f"Forward curve length ({len(self.f0t)}) is shorter than required "
                f"steps ({self.n_steps})"
            )
        if len(self.P0t) < self.n_steps:
            raise ValueError(
                f"Bond price curve length ({len(self.P0t)}) is shorter than required "
                f"steps ({self.n_steps})"
            )

    @staticmethod
    def K(t: float, a: float) -> float:
        """
        Hull-White K function: K(t) = (1 - exp(-a*t)) / a

        This function appears in the bond price formula and represents
        the integrated effect of the short rate.

        Args:
            t: Time
            a: Mean reversion speed

        Returns:
            K(t) value
        """
        if a == 0:
            return t
        return (1 - np.exp(-a * t)) / a

    @staticmethod
    def L(t: float, sigma: float, a: float) -> float:
        """
        Hull-White L function: L(t) = σ² / (2*a) * (1 - exp(-2*a*t))

        This function represents the variance of the short rate process.

        Args:
            t: Time
            sigma: Volatility
            a: Mean reversion speed

        Returns:
            L(t) value
        """
        if a == 0:
            return sigma**2 * t
        return (sigma**2 / (2 * a)) * (1 - np.exp(-2 * a * t))

    def generate_scenarios(
        self,
        lim_high: float = 0.1,
        lim_low: float = -0.05,
        max_retries: int = 50,
        use_antithetic: bool = True,
        filter_explosive: bool = True,
    ) -> dict[str, np.ndarray]:
        """
        Generate interest rate scenarios using Hull-White model.

        This method simulates the short rate r(t) and the instantaneous forward
        rate Rt using the Hull-White dynamics. It also computes deflators for
        discounting cash flows.

        Args:
            lim_high: Upper limit for continuous rates (to filter explosive scenarios)
            lim_low: Lower limit for continuous rates (to filter explosive scenarios)
            max_retries: Maximum percentage of scenarios to retry if filtered (0-50)
            use_antithetic: Whether to use antithetic variates for variance reduction
            filter_explosive: retirer et régénérer les chemins qui sortent de
                [lim_low, lim_high]. Ce tri tronque la distribution des taux et
                casse les paires antithétiques ; ``False`` garde tous les chemins
                (le modèle est gaussien, un taux négatif n'est pas aberrant) et
                se contente de compter ceux qui sortent des bornes.

        Returns:
            Dictionary containing:
                - 'rt': Short rate paths (n_scenarios × n_steps)
                - 'Rt': Instantaneous forward rates (n_scenarios × n_steps)
                - 'deflators': Deflator paths (n_scenarios × n_steps)
                - 'residuals': Extracted residuals for correlation (n_scenarios × n_steps)
                - 'n_out_of_bounds': nombre de chemins tirés qui sortent des
                  bornes (retirés si ``filter_explosive``, gardés sinon)
        """
        # Ensure even number of scenarios for antithetic variates
        n_sim = self.n_scenarios // 2 * 2 if use_antithetic else self.n_scenarios

        # Initialize matrices
        rt = np.zeros((n_sim, self.n_steps))
        Rt = np.zeros((n_sim, self.n_steps))

        # Set initial values
        rt[:, 0] = self.f0t[0]

        # Time indices
        Tp = self.dt
        tp = 0.0

        # Generate scenarios
        for i in range(self.n_steps - 1):
            # Generate random shocks with antithetic variates
            if use_antithetic:
                shocks_half = np.random.normal(0, 1, n_sim // 2)
                shocks = np.concatenate([shocks_half, -shocks_half])
            else:
                shocks = np.random.normal(0, 1, n_sim)

            # Hull-White dynamics for r(t)
            # dr = [θ(t) - a*r(t)]dt + σ*dW
            # Discretized version (exact solution):
            K_Tp = self.K(Tp, self.a)
            K_tp = self.K(tp, self.a)
            L_tp = self.L(tp, self.sigma, self.a)
            L_dt = self.L(self.dt, self.sigma, self.a)

            drift = (
                rt[:, i] * np.exp(-self.a * self.dt) +
                self.f0t[i + 1] - self.f0t[i] * np.exp(-self.a * self.dt) +
                (self.sigma**2 / 2) * (K_Tp**2 - np.exp(-self.a * self.dt) * K_tp**2)
            )

            diffusion = np.sqrt(L_dt) * shocks

            rt[:, i + 1] = drift + diffusion

            # Calculate instantaneous forward rate Rt
            # Rt = -log(P(t, t+dt)/P(t-dt, t)) + adjustments
            if i < len(self.P0t) - 1:
                log_ratio = -np.log(self.P0t[i + 1] / self.P0t[i])
            else:
                log_ratio = Rt[:, i]  # Use previous value if beyond curve

            Rt[:, i + 1] = (
                log_ratio +
                (self.K(self.dt, self.a)**2 / 2) * L_tp -
                self.K(self.dt, self.a) * (self.f0t[i] - rt[:, i])
            )

            Tp += self.dt
            tp += self.dt

        n_out_of_bounds = int(
            np.sum(self._out_of_bounds(Rt, np.log(1 + lim_high), np.log(1 + lim_low)))
        )
        if filter_explosive:
            Rt, rt = self._filter_explosive_scenarios(
                Rt, rt, lim_high, lim_low, max_retries, use_antithetic
            )
        elif n_out_of_bounds:
            logger.info(
                "%d chemin(s) de taux sur %d sortent de [%.1f %% ; %.1f %%], gardés "
                "(filtre des taux explosifs désactivé)",
                n_out_of_bounds, len(Rt), 100 * lim_low, 100 * lim_high,
            )

        # Calculate deflators
        deflators = self._calculate_deflators(Rt)

        # Extract residuals for correlation with other assets
        residuals = self._extract_residuals(rt)

        return {
            'rt': rt,
            'Rt': Rt,
            'deflators': deflators,
            'residuals': residuals,
            'n_out_of_bounds': n_out_of_bounds,
        }

    def log_deflator_loadings(self) -> np.ndarray:
        """
        Sensibilités de log D(t) aux résidus de taux, en forme fermée.

        Le modèle est linéaire dans les chocs : la partie aléatoire de
        ``log(deflators[:, t])`` vaut ``Σ_j B[t, j] * residuals[:, j]``, où
        ``residuals`` est la sortie ``'residuals'`` de ``generate_scenarios``
        (colonne 0 nulle). Sert à corriger exactement le drift des actifs
        corrélés aux taux, sans Monte-Carlo.

        Returns:
            B, matrice (n_steps × n_steps).
        """
        decay = np.exp(-self.a * self.dt)
        scale = -self.K(self.dt, self.a) * np.sqrt(self.L(self.dt, self.sigma, self.a))
        t = np.arange(self.n_steps)[:, None]
        j = np.arange(self.n_steps)[None, :]
        # rt[i] dépend de residuals[j] pour 1 <= j <= i, avec le poids
        # decay**(i - j) ; Rt[i + 1] dépend de rt[i] avec le poids K(dt), et
        # log D(t) = -Σ_{i <= t} Rt[i]. D'où Σ_{i=j+1}^{t} decay**(i-1-j).
        lag = np.clip(t - j, 0, None)
        if decay == 1.0:
            weight = lag.astype(float)
        else:
            weight = (1 - decay ** lag) / (1 - decay)
        loadings = scale * weight
        loadings[:, 0] = 0.0
        return loadings

    @staticmethod
    def _out_of_bounds(Rt: np.ndarray, high: float, low: float) -> np.ndarray:
        """Chemins dont un taux de période sort de [low, high] (taux continus)."""
        mask: np.ndarray = np.any(Rt > high, axis=1) | np.any(Rt < low, axis=1)
        return mask

    def _filter_explosive_scenarios(
        self,
        Rt: np.ndarray,
        rt: np.ndarray,
        lim_high: float,
        lim_low: float,
        max_retries: int,
        use_antithetic: bool
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Filter out scenarios with explosive interest rates.

        Args:
            Rt: Instantaneous forward rates
            rt: Short rates
            lim_high: Upper limit (continuous rate)
            lim_low: Lower limit (continuous rate)
            max_retries: Maximum retry percentage
            use_antithetic: Whether to use antithetic variates

        Returns:
            Filtered Rt and rt arrays
        """
        # Convert limits to continuous rates
        lim_high_cont = np.log(1 + lim_high)
        lim_low_cont = np.log(1 + lim_low)

        # Find scenarios exceeding limits
        bad_scenarios = self._out_of_bounds(Rt, lim_high_cont, lim_low_cont)

        n_bad = np.sum(bad_scenarios)
        pct_removed = n_bad / len(Rt) * 100

        if n_bad > 0:
            warnings.warn(
                f"Filtered {n_bad} ({pct_removed:.1f}%) scenarios with explosive rates",
                stacklevel=2,
            )

        # Remove bad scenarios
        Rt = Rt[~bad_scenarios]
        rt = rt[~bad_scenarios]

        # Regenerate removed scenarios if below 50% threshold
        n_needed = self.n_scenarios - len(Rt)

        if n_needed > 0 and pct_removed >= max_retries:
            raise RuntimeError(
                f"{pct_removed:.1f} % des chemins de taux sortent des bornes, au-delà du "
                f"seuil de régénération ({max_retries} %) : la dynamique Hull-White "
                f"(a={self.a}, sigma={self.sigma}) est incompatible avec ces bornes. "
                f"Élargissez lim_high/lim_low ou passez filter_explosive=False."
            )

        if n_needed > 0:
            # Recursively generate replacement scenarios
            Rt_new, rt_new = self._generate_replacement_scenarios(
                n_needed, lim_high_cont, lim_low_cont, use_antithetic
            )
            Rt = np.vstack([Rt, Rt_new])
            rt = np.vstack([rt, rt_new])

        # Trim to exact number of scenarios
        if len(Rt) > self.n_scenarios:
            Rt = Rt[:self.n_scenarios]
            rt = rt[:self.n_scenarios]

        return Rt, rt

    def _generate_replacement_scenarios(
        self,
        n_needed: int,
        lim_high: float,
        lim_low: float,
        use_antithetic: bool,
        max_attempts: int = 10
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate replacement scenarios for filtered explosive paths."""
        # Arrondi au pair supérieur : arrondi vers le bas, un nombre impair de
        # scénarios à remplacer n'était jamais atteint, et il en manquait un.
        n_sim = (n_needed + 1) // 2 * 2 if use_antithetic else n_needed

        for _attempt in range(max_attempts):
            rt_new = np.zeros((n_sim, self.n_steps))
            Rt_new = np.zeros((n_sim, self.n_steps))
            rt_new[:, 0] = self.f0t[0]

            Tp = self.dt
            tp = 0.0

            for i in range(self.n_steps - 1):
                if use_antithetic:
                    shocks_half = np.random.normal(0, 1, n_sim // 2)
                    shocks = np.concatenate([shocks_half, -shocks_half])
                else:
                    shocks = np.random.normal(0, 1, n_sim)

                K_Tp = self.K(Tp, self.a)
                K_tp = self.K(tp, self.a)
                L_tp = self.L(tp, self.sigma, self.a)
                L_dt = self.L(self.dt, self.sigma, self.a)

                drift = (
                    rt_new[:, i] * np.exp(-self.a * self.dt) +
                    self.f0t[i + 1] - self.f0t[i] * np.exp(-self.a * self.dt) +
                    (self.sigma**2 / 2) * (K_Tp**2 - np.exp(-self.a * self.dt) * K_tp**2)
                )

                rt_new[:, i + 1] = drift + np.sqrt(L_dt) * shocks

                if i < len(self.P0t) - 1:
                    log_ratio = -np.log(self.P0t[i + 1] / self.P0t[i])
                else:
                    log_ratio = Rt_new[:, i]

                Rt_new[:, i + 1] = (
                    log_ratio +
                    (self.K(self.dt, self.a)**2 / 2) * L_tp -
                    self.K(self.dt, self.a) * (self.f0t[i] - rt_new[:, i])
                )

                Tp += self.dt
                tp += self.dt

            # Check for explosive scenarios
            high_mask = np.any(Rt_new > lim_high, axis=1)
            low_mask = np.any(Rt_new < lim_low, axis=1)
            good_scenarios = ~(high_mask | low_mask)

            if np.sum(good_scenarios) >= n_needed:
                return Rt_new[good_scenarios][:n_needed], rt_new[good_scenarios][:n_needed]

        raise RuntimeError(
            f"Impossible de régénérer {n_needed} chemin(s) de taux dans les bornes en "
            f"{max_attempts} tentatives : la dynamique Hull-White (a={self.a}, "
            f"sigma={self.sigma}) sort trop souvent de [lim_low, lim_high]. Élargissez "
            f"les bornes ou passez filter_explosive=False."
        )

    def _calculate_deflators(self, Rt: np.ndarray) -> np.ndarray:
        """
        Calculate deflators (discount factors) from short rates.

        Deflator D(t) = exp(-∫₀ᵗ r(s)ds)

        Args:
            Rt: Instantaneous forward rates (n_scenarios × n_steps)

        Returns:
            Deflators (n_scenarios × n_steps)
        """
        # Cumulative sum of rates
        cumulative_rates = np.cumsum(Rt, axis=1)

        # Calculate deflators
        deflators = np.exp(-cumulative_rates)

        return deflators

    def _extract_residuals(self, rt: np.ndarray) -> np.ndarray:
        """
        Extract residuals from short rate paths for correlation with other assets.

        This reverse-engineers the random shocks from the simulated paths,
        which can then be correlated with other asset class shocks.

        Args:
            rt: Short rate paths (n_scenarios × n_steps)

        Returns:
            Residuals (n_scenarios × n_steps)
        """
        residuals = np.zeros_like(rt)

        for i in range(self.n_steps - 1):
            # Calculate expected drift
            drift = (
                rt[:, i] * np.exp(-self.a * self.dt) +
                self.f0t[i + 1] - self.f0t[i] * np.exp(-self.a * self.dt) +
                (self.sigma**2 / 2) * (
                    self.K(self.dt * (i + 1), self.a)**2 -
                    np.exp(-self.a * self.dt) * self.K(self.dt * i, self.a)**2
                )
            )

            # Extract residual: (rt[i+1] - drift) / sqrt(L(dt))
            L_dt = self.L(self.dt, self.sigma, self.a)
            residuals[:, i + 1] = (rt[:, i + 1] - drift) / np.sqrt(L_dt)

        return residuals

    def zero_coupon_prices(self, rt: np.ndarray, i: int, n_maturities: int) -> np.ndarray:
        """
        Prix zéro-coupon P(t_i, t_i + k·dt), k = 1 à n_maturities, en forme fermée.

        ln P(t, T) = ln(P(0, T) / P(0, t)) + B·f(0, t) - L(t)/2·B² - B·r(t),
        avec B = K(T - t). C'est la formule dont ``Rt`` est le cas k = 1 :
        ``Rt[:, i + 1] = -ln P(t_i, t_{i+1})``, donc ces prix sont cohérents
        avec les déflateurs (E[D(t)·P(t, T)] = P(0, T)).

        Args:
            rt: taux court r(t_i), un par scénario.
            i: indice de t_i sur la grille (t_i = i·dt).
            n_maturities: nombre de maturités, en pas de temps.

        Returns:
            Prix (n_scénarios × n_maturities).

        Raises:
            ValueError: la courbe initiale ne couvre pas t_i + n_maturities·dt.
        """
        if i + n_maturities >= len(self.P0t):
            raise ValueError(
                f"La courbe initiale compte {len(self.P0t)} points : il en faut "
                f"{i + n_maturities + 1} pour valoriser {n_maturities} pas après t_{i}. "
                f"Chargez la courbe sur un horizon plus long."
            )
        k = np.arange(1, n_maturities + 1)
        B = (1 - np.exp(-self.a * k * self.dt)) / self.a if self.a != 0 else k * self.dt
        log_ratio = np.log(self.P0t[i + 1:i + n_maturities + 1] / self.P0t[i])
        L_t = self.L(i * self.dt, self.sigma, self.a)
        log_prices = (
            log_ratio + B * self.f0t[i] - 0.5 * L_t * B**2
        )[None, :] - np.outer(rt, B)
        prices: np.ndarray = np.exp(log_prices)
        return prices

    def bond_fund_returns(
        self, rt: np.ndarray, maturity_steps: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Rendement d'un fonds obligataire à maturité constante, sans risque de crédit.

        Chaque période, le fonds achète au pair une obligation de maturité
        ``maturity_steps`` pas, à coupon de pair, et la revend une période plus
        tard (portage d'``Oblig_V1.R``). Rendement simple de la période
        ]t_{i-1}, t_i] : coupon + prix de l'obligation en t_i - 1.

        Args:
            rt: taux courts (n_scénarios × n_steps), sortie ``'rt'`` de
                ``generate_scenarios``.
            maturity_steps: maturité de l'obligation achetée, en pas de temps (≥ 1).

        Returns:
            ``(total_returns, coupons)``, chacun (n_scénarios × n_steps), rendements
            simples de période, colonne 0 nulle (instant t = 0). Le coupon est la
            part distribuée ; le reste est la variation de prix.
        """
        if maturity_steps < 1:
            raise ValueError(
                f"La maturité du fonds obligataire doit valoir au moins un pas, "
                f"reçu {maturity_steps}. Corrigez bond.fund_maturity_years."
            )
        n_scenarios, n_steps = rt.shape
        total_returns = np.zeros((n_scenarios, n_steps))
        coupons = np.zeros((n_scenarios, n_steps))
        m = maturity_steps
        for i in range(1, n_steps):
            issue = self.zero_coupon_prices(rt[:, i - 1], i - 1, m)
            coupon = (1 - issue[:, -1]) / issue.sum(axis=1)
            value = coupon + 1.0  # une obligation d'un pas rembourse le pair
            if m > 1:
                later = self.zero_coupon_prices(rt[:, i], i, m - 1)
                value = coupon + coupon * later.sum(axis=1) + later[:, -1]
            total_returns[:, i] = value - 1.0
            coupons[:, i] = coupon
        return total_returns, coupons

    def bond_price(self, t: float, T: float, rt: float) -> float:
        """
        Calculate zero-coupon bond price P(t, T) given short rate r(t).

        P(t,T) = A(t,T) * exp(-B(t,T) * r(t))

        where:
            B(t,T) = (1 - exp(-a*(T-t))) / a
            A(t,T) = exp(integral of drift adjustment)

        Args:
            t: Current time
            T: Maturity time
            rt: Short rate at time t

        Returns:
            Bond price
        """
        tau = T - t
        B = self.K(tau, self.a)

        # Simplified A(t,T) calculation
        # In practice, this should integrate the forward curve
        A = np.exp(-B * self.f0t[int(t / self.dt)] + 0.5 * self.sigma**2 * B**2 * tau)

        return A * np.exp(-B * rt)


def calibrate_hull_white(
    yield_curve: np.ndarray,
    maturities: np.ndarray,
    market_swaptions: np.ndarray | None = None
) -> tuple[float, float]:
    """
    Calibrate Hull-White parameters (a, sigma) to market data.

    Heuristique de repli quand aucune surface de swaptions n'est disponible :
    ``a`` reste une valeur typique en dur, ``sigma`` est estimé grossièrement
    depuis la seule volatilité de la courbe des taux (``market_swaptions``
    n'est en réalité pas utilisé). Quand une surface de swaptions EST
    disponible (voir investment_calculator.swaption_surface), utiliser
    investment_calculator.stochastic_models.calibration.SwaptionCalibrator à
    la place : il price réellement des swaptions sous Hull-White
    (décomposition de Jamshidian) et calibre (a, sigma) par moindres carrés
    sur les volatilités de marché, au lieu de cette approximation.

    Args:
        yield_curve: Market yields
        maturities: Corresponding maturities
        market_swaptions: Optional swaption volatilities for calibration
            (non utilisé par cette heuristique — voir SwaptionCalibrator)

    Returns:
        Tuple of (a, sigma)
    """
    # Typical mean reversion speed: 0.05 to 0.3
    a = 0.1

    # Estimate sigma from yield curve volatility
    if len(yield_curve) > 1:
        yield_changes = np.diff(yield_curve)
        sigma = float(np.std(yield_changes)) * 0.5  # Scale factor
        sigma = max(0.005, min(sigma, 0.05))  # Bounds
    else:
        sigma = 0.01

    return a, sigma
