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

Toute valeur absente de 'economic_params' est complétée par
investment_calculator.market_assumptions (étape 1.B.4), pas par un littéral
codé en dur : voir ScenarioGenerator.__init__. equity_drift et
real_estate_drift par défaut valent risk_free_proxy.mean + la prime de
risque monde réel correspondante (voir docs/validation/1b-hypotheses-monde-reel.md) ;
un economic_params['equity_drift'] fourni explicitement reste prioritaire.

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

import logging
import time
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

from investment_calculator.market_assumptions import load_market_assumptions

# Import from existing modules
from investment_calculator.stochastic_models import (
    BlackScholesEquity,
    CorrelatedRandomGenerator,
    EIOPACalibrator,
    HullWhiteModel,
    RealEstateModel,
)

# Journalisation : logger nommé d'après le module, il hérite donc de la
# configuration posée par investment_calculator.logging_config.configure_logging().
logger = logging.getLogger(__name__)


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

    def __init__(self, random_seed: int | None = None):
        """
        Initialize the Scenario Generator.

        Args:
            random_seed: Random seed for reproducibility
        """
        self.random_seed = random_seed
        if random_seed is not None:
            np.random.seed(random_seed)

        # Valeurs par défaut : données d'entrée versionnées (étape 1.B.4), plus
        # des littéraux codés en dur. Avant cette étape, equity_drift (0.10) et
        # real_estate_drift (0.08) étaient des constantes indépendantes du taux
        # sans risque ; elles sont désormais dérivées (taux sans risque + prime
        # de risque monde réel), pour rester cohérentes avec la séparation
        # risque-neutre/monde réel introduite à l'étape 1.B.3 même sur le
        # chemin de génération simple (qui n'a ni courbe EIOPA ni Hull-White).
        # Voir MarketAssumptions.equity_expected_return et
        # docs/journal-1b-calibration.md pour le détail. mean_reversion_speed
        # et hw_volatility restent un PLACEHOLDER non calibré (voir
        # rates.hull_white.status) tant que l'étape 1.B.5 n'est pas menée.
        assumptions = load_market_assumptions()
        self._market_assumptions_id = assumptions.id
        self.default_params = {
            'inflation_mean': assumptions.inflation_mean,
            'inflation_volatility': assumptions.inflation_volatility,
            'interest_mean': assumptions.risk_free_rate_mean,
            'interest_volatility': assumptions.risk_free_rate_volatility,
            'equity_drift': assumptions.equity_expected_return,
            'equity_volatility': assumptions.equity_volatility,
            'bond_return_mean': assumptions.bond_return_mean,
            'bond_return_std': assumptions.bond_return_volatility,
            'real_estate_drift': assumptions.real_estate_expected_return,
            'real_estate_volatility': assumptions.real_estate_volatility,
            'gdp_growth_mean': assumptions.gdp_growth_mean,
            'gdp_growth_std': assumptions.gdp_growth_volatility,
            # Advanced model parameters
            'mean_reversion_speed': assumptions.hull_white_mean_reversion_speed,
            'hw_volatility': assumptions.hull_white_volatility,
            'equity_dividend_yield': assumptions.dividend_yield,
            're_mean_reversion': assumptions.real_estate_mean_reversion,
            're_rental_yield': assumptions.real_estate_rental_yield,
            're_inflation_adj': assumptions.real_estate_inflation_adjustment,
        }

        # Défaut versionné (étape 1.B.4). Note : à l'écriture, aucun des deux
        # chemins de génération ne consomme validated['correlation_matrix']
        # (_generate_stochastic construit sa propre corrélation via
        # CorrelatedRandomGenerator, qui l'ignore) — voir known_gaps de
        # market_assumptions/default-2026.json et docs/journal-1b-calibration.md.
        self.default_correlations = assumptions.correlations

    def generate(self, config: dict) -> dict:
        """
        Generate economic scenarios based on configuration.

        Args:
            config: Configuration dictionary (see module docstring for structure)

        Returns:
            Dictionary with scenarios, deflators, metadata, and diagnostics
        """
        # Chronomètre pour tracer la durée de génération.
        start_time = time.perf_counter()

        # Validate and merge config with defaults
        validated_config = self._validate_config(config)

        n_scenarios = validated_config['num_scenarios']
        method = 'stochastique' if validated_config['use_stochastic'] else 'simple'
        logger.info(
            "Début de la génération de scénarios : %s scénarios, horizon %s ans, méthode %s",
            n_scenarios,
            validated_config['time_horizon'],
            method,
        )

        # Choose generation method
        if validated_config['use_stochastic']:
            results = self._generate_stochastic(validated_config)
        else:
            results = self._generate_simple(validated_config)

        logger.info(
            "Fin de la génération de scénarios : %s scénarios produits en %.3f s (méthode %s)",
            n_scenarios,
            time.perf_counter() - start_time,
            method,
        )

        return results

    def _validate_config(self, config: dict) -> dict:
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
            'yield_curve_id': config.get('yield_curve_id'),
            'correlation_matrix': config.get('correlation_matrix', {}),
            'economic_params': {}
        }

        # Merge economic parameters with defaults
        user_params = config.get('economic_params', {})
        validated['economic_params'] = {**self.default_params, **user_params}

        # Merge correlations with defaults
        validated['correlation_matrix'] = {
            **self.default_correlations,
            **validated['correlation_matrix'],
        }

        return validated

    def _generate_simple(self, config: dict) -> dict:
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
                'calibration_date': config['calibration_date'],
                # Les constantes par défaut de ce chemin (taux, primes de
                # risque, volatilités) sont une donnée d'entrée versionnée
                # depuis l'étape 1.B.4 : traçabilité au même titre que
                # yield_curve_id pour le chemin stochastique.
                'market_assumptions_id': self._market_assumptions_id,
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

    def _generate_stochastic(self, config: dict) -> dict:
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

        # Step 1: Load the yield curve — une donnée d'entrée versionnée (voir
        # investment_calculator.yield_curve), pas une formule dans le moteur.
        yield_curve_id, curve_vintage, f0t, P0t = self._load_yield_curve(
            config['yield_curve_id'], config['currency'], dt, n_steps
        )

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

        # Deux univers, explicitement séparés (étape 1.B.3) : le monde réel
        # (taux sans risque + prime de risque) alimente les scénarios
        # projetés à l'utilisateur ; le risque-neutre (prime nulle) n'existe
        # que pour le test de martingalité, jamais pour une projection —
        # voir docs/validation/1b-hypotheses-monde-reel.md.
        assumptions = load_market_assumptions()

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
            equity_shocks=equity_shocks,
            risk_premium=assumptions.equity_risk_premium,
        )
        # Même diffusion (equity_shocks), prime nulle : sert uniquement au
        # test de martingalité ci-dessous, jamais à une projection.
        equity_results_rn = equity_model.generate_returns(
            hw_results['Rt'],
            equity_shocks=equity_shocks,
            risk_premium=0.0,
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
            re_rental_shocks=re_rental_shocks,
            risk_premium=assumptions.real_estate_risk_premium,
        )
        # Risque-neutre, mêmes chocs : voir la réserve dans
        # RealEstateModel.generate_returns — n'apporte pas de propriété de
        # martingale tant que le bug documenté n'est pas corrigé, mais garde
        # l'interface cohérente avec les actions.
        re_results_rn = re_model.generate_returns(
            hw_results['Rt'],
            f0t,
            re_price_shocks=re_price_shocks,
            re_rental_shocks=re_rental_shocks,
            risk_premium=0.0,
        )

        # Step 6: Generate bond returns (simplified - use interest rates)
        # Bond returns approximately = forward rate - duration * rate change
        bond_returns = hw_results['Rt'].copy()  # Simplified: use forward rates

        # Step 7: Generate inflation (from correlated shocks)
        inflation_shocks = corr_gen.get_asset_shocks(corr_results['shocks'], 'inflation')
        inflation_rates = (
            params['inflation_mean'] + params['inflation_volatility'] * inflation_shocks
        )

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

        # Indices de rendement total RISQUE-NEUTRES (dividendes/loyers
        # réinvestis, prime de risque nulle), normalisés à 1 en t=0, mêmes
        # conventions d'indexation que les déflateurs. Construits à partir de
        # equity_results_rn / re_results_rn, PAS des séries monde réel
        # utilisées dans scenarios_df : un indice qui inclut une prime de
        # risque n'a aucune raison d'être martingale une fois déflaté (voir
        # _test_martingale et docs/validation/1b-hypotheses-monde-reel.md).
        equity_index = np.exp(np.cumsum(equity_results_rn['total_returns'], axis=1))
        real_estate_index = np.exp(np.cumsum(re_results_rn['total_returns'], axis=1))

        diagnostics['martingale_test'] = self._test_martingale(
            hw_results['deflators'],
            P0t,
            equity_index=equity_index,
            real_estate_index=real_estate_index,
        )

        # Metadata
        metadata = {
            'generation_timestamp': datetime.now(),
            'calibration_info': {
                'method': 'stochastic',
                'currency': config['currency'],
                'calibration_date': config['calibration_date'],
                # Le millésime de la courbe est une donnée d'entrée : une
                # simulation archivée doit pouvoir être rejouée en
                # référençant l'identifiant exact de la courbe utilisée
                # (voir investment_calculator.yield_curve).
                'yield_curve_id': yield_curve_id,
                'yield_curve_vintage_date': curve_vintage,
                'forward_curve_range': (float(f0t.min()), float(f0t.max())),
                # Les rendements projetés (scenarios_df) sont monde réel :
                # taux sans risque + cette prime. Voir
                # docs/validation/1b-hypotheses-monde-reel.md.
                'market_assumptions_id': assumptions.id,
                'equity_risk_premium': assumptions.equity_risk_premium,
                'real_estate_risk_premium': assumptions.real_estate_risk_premium,
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

    #: Courbe réelle par défaut, utilisée quand l'appelant n'en spécifie pas.
    #: Seule une courbe France/EUR est disponible aujourd'hui — voir
    #: investment_calculator/yield_curves/README.md. Un autre millésime ou
    #: un autre pays s'ajoute en déposant un nouveau fichier là-bas, jamais
    #: en modifiant cette constante pour pointer ailleurs en place.
    DEFAULT_YIELD_CURVE_ID = "eiopa-fr-2018-04"

    def _load_yield_curve(
        self,
        yield_curve_id: str | None,
        currency: str,
        dt: float,
        n_steps: int,
    ) -> tuple[str, str | None, np.ndarray, np.ndarray]:
        """
        Charger la courbe des taux à utiliser pour cette simulation.

        Priorité :
        1. ``yield_curve_id`` explicite (voir
           ``investment_calculator.yield_curve.list_yield_curves`` pour ce
           qui est disponible) — permet de fournir une courbe courante sans
           modifier le code, exactement comme un régime fiscal.
        2. La courbe réelle par défaut (France/EUR, avril 2018) si la devise
           demandée est EUR.
        3. À défaut d'une courbe réelle pour la devise demandée, la formule
           synthétique historique — un repli explicite et journalisé, pas
           un silence : voir ``_create_yield_curve``.

        Returns:
            Tuple ``(yield_curve_id, vintage_date, f0t, P0t)``.
            ``vintage_date`` vaut ``None`` pour la courbe synthétique : elle
            ne correspond à aucun millésime réel, ce serait mentir que de
            lui en inventer un.
        """
        from investment_calculator.yield_curve import load_yield_curve

        curve_id = yield_curve_id or (
            self.DEFAULT_YIELD_CURVE_ID if currency == 'EUR' else None
        )

        if curve_id is not None:
            curve = load_yield_curve(curve_id, dt=dt)
            return (
                curve.id,
                curve.vintage_date,
                curve.get_forward_curve(n_steps=n_steps),
                curve.get_bond_prices(n_steps=n_steps),
            )

        warnings.warn(
            f"Aucune courbe des taux réelle disponible pour la devise {currency!r} : "
            f"repli sur une courbe synthétique (formule paramétrique, aucun millésime "
            f"réel). Fournissez yield_curve_id pour utiliser une courbe réelle — voir "
            f"investment_calculator.yield_curve.list_yield_curves().",
            stacklevel=3,
        )
        spot_rates = self._create_yield_curve(currency)
        calibrator = EIOPACalibrator(spot_rates=spot_rates, dt=dt)
        calibrator.calibrate()
        return (
            "synthetic-nelson-siegel",
            None,
            calibrator.get_forward_curve(n_steps=n_steps),
            calibrator.get_bond_prices(n_steps=n_steps),
        )

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
            warnings.warn(f"Unknown currency {currency}, using EUR curve", stacklevel=2)
            spot_rates = 0.015 + 0.020 * (1 - np.exp(-maturities / 10))

        return np.asarray(spot_rates)

    def _calculate_diagnostics(self, scenarios_df: pd.DataFrame, method: str) -> dict:
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

    def _test_martingale(
        self,
        deflators: np.ndarray,
        P0t: np.ndarray,
        equity_index: np.ndarray | None = None,
        real_estate_index: np.ndarray | None = None,
        tolerance: float = 0.01,
    ) -> dict:
        """
        Test the martingale property of deflated assets under the risk-neutral measure.

        Le déflateur D(t) = exp(-∫₀ᵗ r(s)ds) n'est pas un actif : c'est le prix
        d'une obligation zéro-coupon virtuelle de maturité t. Son espérance sous
        la mesure risque-neutre vaut donc P(0,t), le prix de marché de cette
        obligation aujourd'hui — **pas 1**, sauf trivialement à t=0. C'est la
        définition même du pricing risque-neutre : P(0,t) = E^Q[D(t)]. Comparer
        E[D(t)] à 1 pour tout t>0 fait donc échouer le test dès que la courbe des
        taux est positive, quelle que soit la qualité du modèle : ce n'est pas un
        test de martingalité, c'est un test structurellement faux au-delà de t=0
        (voir docs/validation/1b-hypotheses-monde-reel.md pour le détail).

        Pour un actif risqué (action, immobilier), la propriété testée est
        différente : c'est D(t)*Actif(t) qui doit être martingale, donc son
        espérance doit rester égale à Actif(0) (normalisé à 1 ici) pour tout t —
        pas à P(0,t), qui n'a rien à voir avec un actif risqué.

        Args:
            deflators: D(t), (n_scenarios, n_steps). La colonne i vaut D(i*dt) ;
                en particulier deflators[:, 0] == 1 pour tout scénario (D(0)=1).
            P0t: prix zéro-coupon P(0,t), même convention d'indexation que
                deflators (P0t[i] == P(0, i*dt)) — typiquement
                EIOPACalibrator.get_bond_prices(), sourcé de la même courbe que
                celle utilisée pour calibrer le modèle de taux.
            equity_index: indice de rendement total actions (dividendes
                réinvestis), normalisé à 1 en t=0, même convention
                d'indexation. Optionnel : composant ignoré si absent.
            real_estate_index: idem pour l'immobilier (loyers réinvestis).
            tolerance: écart relatif maximal toléré, par composant.

        Returns:
            Un sous-résultat par composant testé (« rates », et « equity » /
            « real_estate » si les index correspondants sont fournis), plus un
            indicateur global ``passes``.
        """
        n_scenarios, n_steps = deflators.shape
        p0t = np.asarray(P0t, dtype=float)[:n_steps]

        result: dict = {
            'rates': self._martingale_deviation(deflators.mean(axis=0), p0t)
        }

        if equity_index is not None:
            deflated_equity = (deflators * equity_index).mean(axis=0)
            target = np.full(n_steps, float(equity_index[:, 0].mean()))
            result['equity'] = self._martingale_deviation(deflated_equity, target)

        if real_estate_index is not None:
            deflated_re = (deflators * real_estate_index).mean(axis=0)
            target = np.full(n_steps, float(real_estate_index[:, 0].mean()))
            result['real_estate'] = self._martingale_deviation(deflated_re, target)

        for component in result.values():
            component['tolerance'] = tolerance
            component['passes'] = component['max_relative_deviation'] < tolerance

        result['tolerance'] = tolerance
        result['passes'] = all(
            component['passes'] for component in result.values() if isinstance(component, dict)
        )
        return result

    @staticmethod
    def _martingale_deviation(mean_process: np.ndarray, target: np.ndarray) -> dict:
        """Écart entre un processus déflaté moyen et sa cible théorique, terme à terme."""
        absolute = np.abs(mean_process - target)
        relative = absolute / np.abs(target)
        return {
            'max_absolute_deviation': float(absolute.max()),
            'max_relative_deviation': float(relative.max()),
            'mean_relative_deviation': float(relative.mean()),
            'final_value': float(mean_process[-1]),
            'final_target': float(target[-1]),
        }


# Convenience functions for backward compatibility
def generate_scenarios(config: dict, random_seed: int | None = None) -> dict:
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
