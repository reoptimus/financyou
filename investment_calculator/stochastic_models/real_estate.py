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

import warnings

import numpy as np


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
        re_price_shocks: np.ndarray | None = None,
        re_rental_shocks: np.ndarray | None = None,
        risk_premium: float = 0.0,
        drift: np.ndarray | None = None,
    ) -> dict[str, np.ndarray]:
        """
        Generate real estate return scenarios.

        Args:
            short_rates: Short rate paths from Hull-White (n_scenarios × n_steps)
            f0t: Forward rate curve for calibration (n_steps,)
            re_price_shocks: Optional pre-generated price shocks (n_scenarios × n_steps)
            re_rental_shocks: Optional pre-generated rental shocks (n_scenarios × n_steps)
            risk_premium: prime de risque immobilière ajoutée au drift de
                prix (monde réel), sur le même principe que
                ``BlackScholesEquity.generate_returns``. 0 (défaut) =
                risque-neutre.

                ATTENTION — ``sigma`` est la volatilité du rendement
                instantané r2(t), pas celle du prix : le calibrage R
                (``legacy/R_data/Param_immo2.Rda``) donne sigma = 3,7 % et
                a = 0,5. Avec une volatilité de prix (12 %) à la place,
                l'indice diverge. Voir docs/journal-1b-calibration.md, point 1.
            drift: drift de chaque période, (n_steps - 1,), en remplacement
                de ``k(t)*dt``. ``None`` (défaut) garde le drift d'ImmoHW_V2.R ;
                ``risk_neutral_drift`` donne celui qui rend l'indice déflaté
                martingale.

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
                f"({self.n_scenarios}, {self.n_steps}). Using input shape.",
                stacklevel=2,
            )

        # Generate or use provided shocks
        if re_price_shocks is None:
            re_price_shocks = np.random.normal(0, 1, (n_scenarios, n_steps))

        if re_rental_shocks is None:
            re_rental_shocks = np.random.normal(0, 1, (n_scenarios, n_steps))

        # Processus auxiliaire r2(t), rendement instantané de l'immobilier.
        r2 = self._generate_auxiliary_rates(short_rates, f0t, re_rental_shocks)

        # Comme dans ImmoHW_V2.R, la diffusion Hull-White donne le rendement
        # TOTAL (loyers compris) ; le loyer en est une part, et le prix le
        # reste : RdtImmoP = RdtImmo - RdtImmoL. Le loyer ne s'ajoute pas au
        # total, sinon il serait compté deux fois.
        total_returns = self._generate_price_returns(
            short_rates, f0t, r2, re_price_shocks, risk_premium, drift
        )
        rental_returns = self._generate_rental_returns(n_scenarios, n_steps)
        price_returns = total_returns - rental_returns

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
        K2T_t2a = (1 - np.exp(-2 * self.a * self.dt)) / (2 * self.a)

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
        shocks: np.ndarray,
        risk_premium: float = 0.0,
        drift: np.ndarray | None = None,
    ) -> np.ndarray:
        """
        Rendement total de l'immobilier, loyers compris (``RdtImmo`` d'ImmoHW_V2.R).

        Rendement de la période ``t`` (de ``t*dt`` à ``(t+1)*dt``) :
            (k(t) + risk_premium)*dt + (r2(t) - k(t))*K(dt) + η*ε(t)

        Le nom est conservé pour l'interface ; la valeur est le rendement total.
        Convention commune aux actions et aux taux : la colonne ``i`` porte le
        rendement de la période qui se termine en ``i*dt``, et la colonne 0 vaut
        0 (l'indice vaut 1 en t = 0).

        risk_premium (0 par défaut = risque-neutre) est un taux annualisé,
        mis à l'échelle par dt comme k(t).

        Args:
            short_rates: Short rate paths (n_scenarios × n_steps)
            f0t: Forward rate curve (n_steps,)
            r2: Auxiliary rates (n_scenarios × n_steps)
            shocks: Random shocks (n_scenarios × n_steps)
            risk_premium: prime de risque immobilière annualisée (monde réel).
            drift: drift de chaque période remplaçant ``k(t)*dt`` (voir
                ``generate_returns``).

        Returns:
            Rendements totaux (n_scenarios × n_steps)
        """
        n_scenarios, n_steps = short_rates.shape
        total_returns = np.zeros((n_scenarios, n_steps))

        K2T_t = (1 - np.exp(-self.a * self.dt)) / self.a
        K2T_t2a = (1 - np.exp(-2 * self.a * self.dt)) / (2 * self.a)
        eta2 = (self.sigma / self.a) * (
            self.dt - 2 * K2T_t + K2T_t2a
        ) ** 0.5

        if drift is not None and len(drift) != n_steps - 1:
            raise ValueError(
                f"Le drift doit compter une valeur par période ({n_steps - 1}), "
                f"il en compte {len(drift)} : le calculer avec risk_neutral_drift "
                "sur le même nombre de pas."
            )

        for t in range(n_steps - 1):
            kimmo = f0t[t] if t < len(f0t) else f0t[-1]
            # ImmoHW_V2.R : RdtImmo[,i]<-kimmo*delta_t+(r0_2-kimmo)*K2T_t+eta2*alea_R2[,i]
            period_drift = kimmo * self.dt if drift is None else drift[t]
            mean_reversion = (r2[:, t] - kimmo) * K2T_t
            diffusion = eta2 * shocks[:, t]
            total_returns[:, t + 1] = (
                period_drift + risk_premium * self.dt + mean_reversion + diffusion
            )

        return total_returns

    def _generate_rental_returns(
        self,
        n_scenarios: int,
        n_steps: int
    ) -> np.ndarray:
        """
        Part du loyer dans le rendement total (``RdtImmoL`` d'ImmoHW_V2.R).

        Formule R : ``RdtImmoL[,i] <- L0_P0 + i*Infl``, avec
        ``L0_P0 = log(1 + rental_yield)*dt`` et ``Infl = inflation_adjustment*dt``.
        Le R fixe ``Infl`` à 0 (« loyers fixes et inflation loyers flat »). Avec
        une valeur non nulle, la part du loyer croît linéairement d'une période
        à l'autre : seul le partage entre loyer et prix en dépend, pas le
        rendement total ni l'indice.

        Returns:
            Part du loyer (n_scenarios × n_steps), colonne 0 nulle.
        """
        rental_returns = np.zeros((n_scenarios, n_steps))
        base_rental = np.log(1 + self.rental_yield) * self.dt
        inflation_adj = self.inflation_adjustment * self.dt
        for t in range(1, n_steps):
            rental_returns[:, t] = base_rental + t * inflation_adj
        return rental_returns

    def log_index_loadings(self, n_steps: int) -> tuple[np.ndarray, np.ndarray]:
        """
        Sensibilités du log de l'indice total aux chocs, en forme fermée.

        La partie aléatoire de ``Σ_{s <= t} total_returns[:, s]`` vaut
        ``Σ_j A_price[t, j] * re_price_shocks[:, j]
        + Σ_j A_aux[t, j] * re_rental_shocks[:, j]``.

        Returns:
            (A_price, A_aux), deux matrices (n_steps × n_steps).
        """
        K2T_t = (1 - np.exp(-self.a * self.dt)) / self.a
        K2T_t2a = (1 - np.exp(-2 * self.a * self.dt)) / (2 * self.a)
        eta2 = (self.sigma / self.a) * (self.dt - 2 * K2T_t + K2T_t2a) ** 0.5
        decay = np.exp(-self.a * self.dt)

        t = np.arange(n_steps)[:, None]
        j = np.arange(n_steps)[None, :]
        # Le choc de prix de la colonne j entre dans le rendement j + 1.
        price = np.where(j <= t - 1, eta2, 0.0)
        # Le choc de r2 de la colonne j entre dans r2[j + 1], qui pèse
        # K2T_t * decay**(u - 1 - j) dans le rendement u + 1, pour u > j.
        lag = np.clip(t - 1 - j, 0, None)
        aux = K2T_t * self.sigma * K2T_t2a**0.5 * (1 - decay**lag) / (1 - decay)
        return price, aux

    def risk_neutral_drift(
        self,
        f0t: np.ndarray,
        P0t: np.ndarray,
        n_steps: int,
        rate_loadings: np.ndarray,
        shock_covariances: np.ndarray,
    ) -> np.ndarray:
        """
        Drift de chaque période qui rend ``D(t) * Indice(t)`` martingale.

        Le drift d'ImmoHW_V2.R (``k(t)*dt``) ne corrige ni la convexité ni la
        covariance avec les taux. Tout le modèle étant linéaire dans des chocs
        gaussiens, log(D(t) * Indice(t)) est gaussien, et E[D(t) * Indice(t)] = 1
        impose, avec E[D(t)] = P(0, t) :

            E[log Indice(t)] = -log P(0, t) - Var(log Indice(t)) / 2
                               - Cov(log Indice(t), log D(t))

        Les variances et covariances sont calculées exactement à partir des
        sensibilités des deux modèles, pas estimées sur les scénarios.

        Args:
            f0t: courbe des taux forward, celle passée à ``generate_returns``.
            P0t: prix zéro-coupon, ``P0t[i] = P(0, i*dt)``.
            n_steps: nombre de pas.
            rate_loadings: ``HullWhiteModel.log_deflator_loadings()``.
            shock_covariances: (n_steps × 3 × 3), covariance par colonne du
                résidu de taux, du choc de prix et du choc de r2, dans cet ordre.

        Returns:
            Drift de chaque période, (n_steps - 1,), à passer à ``generate_returns``.
        """
        if len(P0t) < n_steps:
            raise ValueError(
                f"La courbe zéro-coupon couvre {len(P0t)} pas, il en faut {n_steps} : "
                "allonger la courbe ou réduire l'horizon."
            )
        price, aux = self.log_index_loadings(n_steps)
        index_loadings = np.stack([np.zeros_like(price), price, aux], axis=-1)
        rate = np.stack(
            [rate_loadings, np.zeros_like(price), np.zeros_like(price)], axis=-1
        )
        variance = np.einsum('tjk,jkl,tjl->t', index_loadings, shock_covariances, index_loadings)
        covariance = np.einsum('tjk,jkl,tjl->t', index_loadings, shock_covariances, rate)
        target_mean = -np.log(np.asarray(P0t[:n_steps], dtype=float)) - variance / 2 - covariance

        # Espérance de r2 : même récurrence que _generate_auxiliary_rates, sans choc.
        kimmo = np.array([f0t[t] if t < len(f0t) else f0t[-1] for t in range(n_steps)])
        decay = np.exp(-self.a * self.dt)
        mean_r2 = np.empty(n_steps)
        mean_r2[0] = f0t[0] if len(f0t) > 0 else 0.0
        for t in range(n_steps - 1):
            mean_r2[t + 1] = mean_r2[t] * decay + kimmo[t] * (1 - decay)
        K2T_t = (1 - decay) / self.a

        return np.diff(target_mean) - (mean_r2[:-1] - kimmo[:-1]) * K2T_t

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
    ) -> tuple[float, float, float]:
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


def calibrate_from_annual_returns(annual_returns: np.ndarray) -> tuple[float, float]:
    """
    Calage de ``a`` et ``sigma`` de :class:`RealEstateModel` sur des rendements annuels.

    Méthode des moments, au pas d'un an : dans le modèle, l'autocorrélation
    d'ordre 1 des rendements annuels ne dépend que de ``a``, et leur variance
    est proportionnelle à ``sigma²``. On résout la première pour ``a``, puis la
    seconde pour ``sigma``. (``Script_calibrage_immo.R`` ne calculait que
    l'écart-type des résidus d'un AR(1), sans ``a``.)

    Returns:
        ``(a, sigma)``.

    Raises:
        ValueError: série trop courte, ou autocorrélation hors de ]0, 1[, que
            ce modèle ne peut pas reproduire.
    """
    from scipy.optimize import brentq

    x = np.asarray(annual_returns, dtype=float)
    if x.size < 3:
        raise ValueError("Au moins trois rendements annuels sont nécessaires au calage.")
    centered = x - x.mean()
    rho = float(centered[1:] @ centered[:-1] / (centered @ centered))

    def moments(a: float) -> tuple[float, float]:
        k = (1 - np.exp(-a)) / a
        k2 = (1 - np.exp(-2 * a)) / (2 * a)
        eta2 = (1 - 2 * k + k2) / a**2
        r2_variance = 1 / (2 * a)
        gamma0 = k**2 * r2_variance + eta2
        return gamma0, k**2 * np.exp(-a) * r2_variance / gamma0

    low, high = 1e-4, 50.0
    if not moments(high)[1] < rho < moments(low)[1]:
        raise ValueError(
            f"Autocorrélation des rendements annuels de {rho:.3f} : le modèle ne "
            "reproduit qu'une autocorrélation positive et inférieure à 1. Vérifiez "
            "que la série est bien une suite de rendements annuels."
        )
    a = brentq(lambda a: moments(a)[1] - rho, low, high)
    sigma = float(np.sqrt(x.var(ddof=1) / moments(a)[0]))
    return float(a), sigma


def calibrate_real_estate_parameters(
    historical_prices: np.ndarray,
    historical_rents: np.ndarray,
    dt: float = 1.0
) -> tuple[float, float, float]:
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
