"""
Comprehensive Unit Tests for Module 1: Economic Scenario Generator

Tests cover:
- ScenarioGenerator initialization
- Configuration validation
- Simple scenario generation (fast mode)
- Stochastic scenario generation (advanced mode)
- Input validation and error handling
- Output structure validation
- Diagnostics accuracy
- Different currencies and parameters
- Edge cases
- Convenience functions
"""

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator.modules import scenario_generator


class TestScenarioGeneratorInitialization:
    """Test ScenarioGenerator initialization."""

    def test_init_without_seed(self):
        """Test initialization without random seed."""
        gen = scenario_generator.ScenarioGenerator()
        assert gen.random_seed is None
        assert hasattr(gen, 'default_params')
        assert hasattr(gen, 'default_correlations')

    def test_init_with_seed(self):
        """Test initialization with random seed."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        assert gen.random_seed == 42

    def test_reproducibility_with_seed(self):
        """Test that same seed produces same results."""
        config = {
            'num_scenarios': 10,
            'time_horizon': 5,
            'timestep': 1.0,
            'use_stochastic': False
        }

        gen1 = scenario_generator.ScenarioGenerator(random_seed=42)
        results1 = gen1.generate(config)

        gen2 = scenario_generator.ScenarioGenerator(random_seed=42)
        results2 = gen2.generate(config)

        pd.testing.assert_frame_equal(results1['scenarios'], results2['scenarios'])

    def test_default_parameters(self):
        """Test that default parameters are properly set."""
        gen = scenario_generator.ScenarioGenerator()

        assert 'inflation_mean' in gen.default_params
        assert 'equity_drift' in gen.default_params
        assert 'bond_return_mean' in gen.default_params
        assert gen.default_params['inflation_mean'] > 0
        assert gen.default_params['equity_drift'] > gen.default_params['inflation_mean']

    def test_default_correlations(self):
        """Test that default correlations are properly set."""
        gen = scenario_generator.ScenarioGenerator()

        assert len(gen.default_correlations) > 0
        # Check correlations are in valid range
        for corr_value in gen.default_correlations.values():
            assert -1 <= corr_value <= 1

    def test_default_drifts_derive_du_taux_sans_risque_et_de_la_prime_de_risque(self):
        """
        Étape 1.B.4 : avant cette étape, equity_drift (0.10) et
        real_estate_drift (0.08) étaient des littéraux indépendants. Ils
        doivent désormais valoir risk_free_proxy.mean + la prime de risque
        monde réel correspondante (voir
        investment_calculator.market_assumptions.MarketAssumptions et
        docs/validation/1b-hypotheses-monde-reel.md), pour rester cohérents
        avec la séparation risque-neutre/monde réel du chemin stochastique.
        """
        from investment_calculator.market_assumptions import load_market_assumptions

        assumptions = load_market_assumptions()
        gen = scenario_generator.ScenarioGenerator()

        assert gen.default_params['equity_drift'] == pytest.approx(
            assumptions.risk_free_rate_mean + assumptions.equity_risk_premium
        )
        assert gen.default_params['real_estate_drift'] == pytest.approx(
            assumptions.risk_free_rate_mean + assumptions.real_estate_risk_premium
        )

    def test_default_params_sont_une_donnee_versionnee_pas_un_litteral(self):
        """Les valeurs par défaut viennent de market_assumptions, pas d'un dict codé en dur."""
        from investment_calculator.market_assumptions import load_market_assumptions

        assumptions = load_market_assumptions()
        gen = scenario_generator.ScenarioGenerator()

        assert gen.default_params['inflation_mean'] == assumptions.inflation_mean
        assert gen.default_params['mean_reversion_speed'] == (
            assumptions.hull_white_mean_reversion_speed
        )
        assert gen.default_params['hw_volatility'] == assumptions.hull_white_volatility
        assert gen._market_assumptions_id == assumptions.id


class TestConfigurationValidation:
    """Test configuration validation."""

    def test_valid_minimal_config(self):
        """Test minimal valid configuration."""
        gen = scenario_generator.ScenarioGenerator()
        config = {
            'num_scenarios': 100,
            'time_horizon': 10,
            'timestep': 1.0
        }

        validated = gen._validate_config(config)
        assert validated['num_scenarios'] == 100
        assert validated['time_horizon'] == 10
        assert validated['timestep'] == 1.0
        assert 'use_stochastic' in validated
        assert 'currency' in validated
        assert 'economic_params' in validated

    def test_missing_required_field(self):
        """Test that missing required fields raise error."""
        gen = scenario_generator.ScenarioGenerator()

        with pytest.raises(ValueError, match="Missing required field"):
            gen._validate_config({'num_scenarios': 100})

        with pytest.raises(ValueError, match="Missing required field"):
            gen._validate_config({'time_horizon': 10, 'timestep': 1.0})

    def test_config_type_conversion(self):
        """Test that config types are properly converted."""
        gen = scenario_generator.ScenarioGenerator()
        config = {
            'num_scenarios': '100',  # String instead of int
            'time_horizon': 10.5,    # Float instead of int
            'timestep': '1.0'        # String instead of float
        }

        validated = gen._validate_config(config)
        assert isinstance(validated['num_scenarios'], int)
        assert isinstance(validated['time_horizon'], int)
        assert isinstance(validated['timestep'], float)

    def test_default_values(self):
        """Test that default values are applied."""
        gen = scenario_generator.ScenarioGenerator()
        config = {
            'num_scenarios': 100,
            'time_horizon': 10,
            'timestep': 1.0
        }

        validated = gen._validate_config(config)
        assert validated['use_stochastic'] is False
        assert validated['currency'] == 'USD'
        assert validated['calibration_date'] == '2025-01-01'

    def test_custom_economic_params(self):
        """Test that custom economic params override defaults."""
        gen = scenario_generator.ScenarioGenerator()
        config = {
            'num_scenarios': 100,
            'time_horizon': 10,
            'timestep': 1.0,
            'economic_params': {
                'equity_drift': 0.15,
                'inflation_mean': 0.03
            }
        }

        validated = gen._validate_config(config)
        assert validated['economic_params']['equity_drift'] == 0.15
        assert validated['economic_params']['inflation_mean'] == 0.03
        # Check that other defaults are still present
        assert 'bond_return_mean' in validated['economic_params']


class TestSimpleScenarioGeneration:
    """Test simple (fast) scenario generation."""

    def test_simple_generation_basic(self):
        """Test basic simple scenario generation."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 100,
            'time_horizon': 10,
            'timestep': 1.0,
            'use_stochastic': False
        }

        results = gen.generate(config)

        # Check structure
        assert 'scenarios' in results
        assert 'deflators' in results
        assert 'metadata' in results
        assert 'diagnostics' in results

    def test_simple_metadata_trace_le_jeu_d_hypotheses_utilise(self):
        """
        Étape 1.B.4 : le chemin simple dépend désormais de market_assumptions
        (taux, primes, volatilités) au même titre que le chemin stochastique
        dépend d'une courbe de taux (yield_curve_id) — une simulation
        archivée doit pouvoir identifier quel jeu d'hypothèses l'a produite.
        """
        from investment_calculator.market_assumptions import load_market_assumptions

        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 5,
            'time_horizon': 3,
            'timestep': 1.0,
            'use_stochastic': False,
        }

        results = gen.generate(config)
        assert (
            results['metadata']['calibration_info']['market_assumptions_id']
            == load_market_assumptions().id
        )

    def test_simple_scenarios_dataframe_structure(self):
        """Test scenarios DataFrame structure."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 50,
            'time_horizon': 10,
            'timestep': 1.0,
            'use_stochastic': False
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        # Check DataFrame properties
        assert isinstance(scenarios_df, pd.DataFrame)
        assert len(scenarios_df) == 50 * 10  # num_scenarios * time_steps

        # Check required columns
        required_cols = ['scenario_id', 'time_period', 'interest_rate',
                        'stock_return', 'bond_return', 'real_estate_return',
                        'inflation', 'gdp_growth']
        for col in required_cols:
            assert col in scenarios_df.columns

    def test_simple_scenarios_ids(self):
        """Test scenario ID formatting."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 5,
            'time_horizon': 3,
            'timestep': 1.0,
            'use_stochastic': False
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        unique_ids = scenarios_df['scenario_id'].unique()
        assert len(unique_ids) == 5
        assert 'scenario_0001' in unique_ids
        assert 'scenario_0005' in unique_ids

    def test_simple_scenarios_time_periods(self):
        """Test time period values."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 10,
            'time_horizon': 5,
            'timestep': 1.0,
            'use_stochastic': False
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        # Check one scenario's time periods
        scenario_1 = scenarios_df[scenarios_df['scenario_id'] == 'scenario_0001']
        time_periods = scenario_1['time_period'].values

        expected = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        np.testing.assert_array_almost_equal(time_periods, expected)

    def test_simple_scenarios_timestep(self):
        """Test different timestep values."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 10,
            'time_horizon': 2,
            'timestep': 0.25,  # Quarterly
            'use_stochastic': False
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        # Should have 2 / 0.25 = 8 time periods per scenario
        scenario_1 = scenarios_df[scenarios_df['scenario_id'] == 'scenario_0001']
        assert len(scenario_1) == 8

        # Check time periods
        expected = np.array([0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0])
        np.testing.assert_array_almost_equal(scenario_1['time_period'].values, expected)

    def test_simple_deflators_structure(self):
        """Test deflators DataFrame structure."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 50,
            'time_horizon': 10,
            'timestep': 1.0,
            'use_stochastic': False
        }

        results = gen.generate(config)
        deflators_df = results['deflators']

        assert isinstance(deflators_df, pd.DataFrame)
        assert len(deflators_df) == 50  # One row per scenario
        assert 'scenario_id' in deflators_df.columns

        # Should have time columns t_1, t_2, ..., t_10
        time_cols = [col for col in deflators_df.columns if col.startswith('t_')]
        assert len(time_cols) == 10

    def test_simple_deflators_properties(self):
        """Test deflators mathematical properties."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 100,
            'time_horizon': 10,
            'timestep': 1.0,
            'use_stochastic': False
        }

        results = gen.generate(config)
        deflators_df = results['deflators']

        # Deflators should be positive
        time_cols = [col for col in deflators_df.columns if col.startswith('t_')]
        for col in time_cols:
            assert (deflators_df[col] > 0).all()

        # Deflators should generally decrease over time (discounting)
        # Mean deflator at t_10 should be less than at t_1
        assert deflators_df['t_10'].mean() < deflators_df['t_1'].mean()


class TestStochasticScenarioGeneration:
    """Test stochastic (advanced) scenario generation."""

    def test_stochastic_generation_basic(self):
        """Test basic stochastic scenario generation."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 50,
            'time_horizon': 5,
            'timestep': 1.0,
            'use_stochastic': True
        }

        results = gen.generate(config)

        # Check structure
        assert 'scenarios' in results
        assert 'deflators' in results
        assert 'metadata' in results
        assert 'diagnostics' in results

    def test_stochastic_scenarios_structure(self):
        """Test stochastic scenarios DataFrame structure."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 50,
            'time_horizon': 10,
            'timestep': 1.0,
            'use_stochastic': True
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        # Same structure as simple scenarios
        assert isinstance(scenarios_df, pd.DataFrame)
        assert len(scenarios_df) == 50 * 10

        required_cols = ['scenario_id', 'time_period', 'interest_rate',
                        'stock_return', 'bond_return', 'real_estate_return',
                        'inflation', 'gdp_growth']
        for col in required_cols:
            assert col in scenarios_df.columns

    def test_stochastic_premiere_periode_simulee(self):
        """
        Régression : la première période valait 0 dans tous les scénarios.

        Les modèles indexent leurs sorties par date (colonne i = t = i*dt) ;
        la colonne 0 est t = 0, sans rendement. Elle était reprise comme
        période 1 : taux, actions, obligations et immobilier nuls en première
        année, et la dernière année simulée perdue. Le déflateur de fin de
        période 1 valait D(0) = 1.
        """
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 50,
            'time_horizon': 5,
            'timestep': 1.0,
            'use_stochastic': True,
            'currency': 'EUR',
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']
        first = scenarios_df[scenarios_df['time_period'] == 1.0]

        assert len(first) == 50
        for col in ('interest_rate', 'stock_return', 'bond_return', 'real_estate_return'):
            assert (first[col] != 0.0).all(), f"{col} est nul en période 1"
        for col in ('stock_return', 'real_estate_return'):
            assert first[col].std() > 0.0, f"{col} n'a aucune dispersion en période 1"
        # Le taux de la première période est connu en t = 0 : D(1) = P(0, 1),
        # identique dans tous les scénarios, et le taux vaut -log P(0, 1).
        d1 = results['deflators']['t_1'].to_numpy()
        np.testing.assert_allclose(d1, d1[0])
        assert d1[0] != 1.0
        np.testing.assert_allclose(first['interest_rate'], -np.log(d1[0]))
        assert sorted(scenarios_df['time_period'].unique()) == [1.0, 2.0, 3.0, 4.0, 5.0]

    def test_stochastic_remplacement_d_un_nombre_impair_de_scenarios(self):
        """
        Régression : quand le filtre des taux explosifs retirait un nombre
        impair de scénarios, le remplacement (variables antithétiques, donc par
        paires) en tirait un de moins, et la génération échouait sur des
        tableaux de tailles différentes. Avec la graine 1, la courbe
        synthétique en USD retire un nombre impair de scénarios.
        """
        gen = scenario_generator.ScenarioGenerator(random_seed=1)
        config = {
            'num_scenarios': 100,
            'time_horizon': 10,
            'timestep': 1.0,
            'use_stochastic': True,
        }

        results = gen.generate(config)

        assert results['scenarios']['scenario_id'].nunique() == 100
        assert len(results['deflators']) == 100

    def test_stochastic_martingale_test_structure(self):
        """La sortie du test de martingalité porte un sous-résultat par composant."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 100,
            'time_horizon': 10,
            'timestep': 1.0,
            'use_stochastic': True
        }

        results = gen.generate(config)
        diagnostics = results['diagnostics']

        mt = diagnostics['martingale_test']
        assert 'passes' in mt
        for component in ('rates', 'equity', 'real_estate'):
            assert component in mt
            assert 'max_relative_deviation' in mt[component]
            assert 'passes' in mt[component]

    def test_martingale_rates_sous_demi_pourcent_a_30_ans(self):
        """
        Régression du bug corrigé à l'étape 1.B.1 : le test de martingalité
        comparait E[D(t)] à 1,0 pour tout t. C'est faux — la valeur théorique
        est P(0,t), le prix zéro-coupon, qui décroît avec t. Comparer à 1
        faisait donc échouer le test par construction dès que t>0 et le taux
        est positif, quel que soit le modèle sous-jacent.

        Objectif explicite de l'étape 1.B.1 : une fois comparé à P(0,t), l'écart
        doit rester sous 0,5 % à 30 ans. Vérifié stable sur 5 graines
        différentes avant d'écrire ce test (0,23 % à 0,40 %) ; 10 000
        scénarios et un pas semestriel de 0,25 an suffisent, sans avoir besoin
        d'un Monte-Carlo massif.
        """
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 10_000,
            'time_horizon': 30,
            'timestep': 0.25,
            'use_stochastic': True,
            'currency': 'EUR',
        }

        results = gen.generate(config)
        rates = results['diagnostics']['martingale_test']['rates']

        assert rates['max_relative_deviation'] < 0.005, (
            f"E[D(t)] s'écarte de P(0,t) de {rates['max_relative_deviation']:.4%} "
            f"au pire point de la courbe : au-delà de l'objectif de 0,5 % à 30 ans."
        )

    def test_martingale_equity_est_risque_neutre(self):
        """
        Régression du bug corrigé à l'étape 1.B.3 : black_scholes.py utilisait
        un drift ``r(t)+σ²/2`` pour l'indice actions total-return (au lieu de
        ``r(t)-σ²/2``), ET multipliait ``short_rates[:, t]`` par ``dt`` alors
        qu'il s'agit déjà d'un rendement de période — deux bugs cumulés,
        présentés comme « risque-neutre » alors qu'ils ne l'étaient pas.
        L'indice déflaté dérivait d'environ 18 % à 30 ans (voir
        docs/journal-1b-calibration.md) au lieu de rester à 1.

        Précision atteinte après correction : la volatilité actions (18 %)
        est bien plus élevée que celle des taux (1 %), donc l'estimateur
        Monte-Carlo de E[D(t)*Index(t)] est plus bruité à N égal — sur 5
        graines à 20 000 scénarios, l'écart va de 0,46 % à 2,36 % (vérifié
        avant d'écrire ce test). Le seuil ci-dessous (1 %) est calibré sur la
        graine fixe utilisée par ce test précisément, pas sur n'importe
        quelle graine : ce n'est pas un objectif de précision universel comme
        celui du test de taux.
        """
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 20_000,
            'time_horizon': 30,
            'timestep': 0.25,
            'use_stochastic': True,
            'currency': 'EUR',
        }

        results = gen.generate(config)
        equity = results['diagnostics']['martingale_test']['equity']

        assert equity['max_relative_deviation'] < 0.01, (
            f"D(t)*Index_actions(t) s'écarte de 1 de {equity['max_relative_deviation']:.4%} "
            f"au pire point : l'indice actions n'est pas risque-neutre."
        )

    def test_martingale_immobilier_est_risque_neutre(self):
        """
        L'indice immobilier déflaté reste égal à 1 en espérance (martingale).

        Avant la correction du drift, il s'écartait de 36 % à 30 ans. L'erreur
        type Monte-Carlo de E[D(t)*Indice(t)] vaut 1,6 % à 30 ans pour 10 000
        scénarios (variance de log Indice ≈ 1,3 avec le calage France) : un
        seuil de 0,5 % n'est pas atteignable à ce nombre de scénarios, quel que
        soit le drift. Sur 16 graines, l'écart va de 0,25 % à 3,4 %, et il est
        de 0,93 % sur la graine 42 ; sur 100 000 scénarios, il tombe à 0,24 %,
        soit 0,5 erreur type. L'exactitude du drift lui-même est vérifiée sans
        bruit par ``test_drift_immobilier_exact``.
        """
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 10_000,
            'time_horizon': 30,
            'timestep': 0.25,
            'use_stochastic': True,
            'currency': 'EUR',
        }

        results = gen.generate(config)
        real_estate = results['diagnostics']['martingale_test']['real_estate']

        assert real_estate['max_relative_deviation'] < 0.02, (
            f"D(t)*Index_immo(t) s'écarte de 1 de "
            f"{real_estate['max_relative_deviation']:.4%} au pire point : "
            f"l'indice immobilier n'est pas risque-neutre."
        )

    def test_stochastic_different_currency(self):
        """Test stochastic generation with different currencies."""
        currencies = ['USD', 'EUR', 'GBP']

        for currency in currencies:
            gen = scenario_generator.ScenarioGenerator(random_seed=42)
            config = {
                'num_scenarios': 20,
                'time_horizon': 5,
                'timestep': 1.0,
                'use_stochastic': True,
                'currency': currency
            }

            results = gen.generate(config)
            assert results['metadata']['calibration_info']['currency'] == currency


class TestMetadataAndDiagnostics:
    """Test metadata and diagnostics output."""

    def test_metadata_structure(self):
        """Test metadata dictionary structure."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 50,
            'time_horizon': 10,
            'timestep': 1.0
        }

        results = gen.generate(config)
        metadata = results['metadata']

        assert 'generation_timestamp' in metadata
        assert 'calibration_info' in metadata
        assert 'model_versions' in metadata
        assert 'random_seed' in metadata

        assert isinstance(metadata['generation_timestamp'], datetime)
        assert metadata['random_seed'] == 42

    def test_metadata_calibration_info(self):
        """Test calibration info in metadata."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 50,
            'time_horizon': 10,
            'timestep': 1.0,
            'currency': 'EUR',
            'calibration_date': '2025-06-01'
        }

        results = gen.generate(config)
        calib_info = results['metadata']['calibration_info']

        assert calib_info['currency'] == 'EUR'
        assert calib_info['calibration_date'] == '2025-06-01'

    def test_diagnostics_structure(self):
        """Test diagnostics dictionary structure."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 100,
            'time_horizon': 10,
            'timestep': 1.0
        }

        results = gen.generate(config)
        diagnostics = results['diagnostics']

        assert 'mean_returns' in diagnostics
        assert 'volatilities' in diagnostics
        assert 'correlations' in diagnostics
        assert 'num_scenarios' in diagnostics
        assert 'num_time_periods' in diagnostics
        assert 'method' in diagnostics

    def test_diagnostics_mean_returns(self):
        """Test mean returns diagnostics."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 1000,
            'time_horizon': 30,
            'timestep': 1.0,
            'use_stochastic': False
        }

        results = gen.generate(config)
        mean_returns = results['diagnostics']['mean_returns']

        # Check all asset classes are present
        assert 'stock_return' in mean_returns
        assert 'bond_return' in mean_returns
        assert 'real_estate_return' in mean_returns
        assert 'inflation' in mean_returns

        # Check values are reasonable
        assert isinstance(mean_returns['stock_return'], float)
        # Stocks should have higher return than bonds (generally)
        assert mean_returns['stock_return'] > mean_returns['bond_return']

    def test_diagnostics_volatilities(self):
        """Test volatilities diagnostics."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 1000,
            'time_horizon': 30,
            'timestep': 1.0
        }

        results = gen.generate(config)
        volatilities = results['diagnostics']['volatilities']

        # Check all asset classes are present
        assert 'stock_return' in volatilities
        assert 'bond_return' in volatilities

        # Check values are reasonable
        assert volatilities['stock_return'] > 0
        # Stocks should be more volatile than bonds
        assert volatilities['stock_return'] > volatilities['bond_return']

    def test_diagnostics_correlations(self):
        """Test correlations diagnostics."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 1000,
            'time_horizon': 30,
            'timestep': 1.0
        }

        results = gen.generate(config)
        correlations = results['diagnostics']['correlations']

        # Should be a correlation matrix
        assert isinstance(correlations, pd.DataFrame)

        # Diagonal should be 1.0
        for col in correlations.columns:
            if col in correlations.index:
                assert abs(correlations.loc[col, col] - 1.0) < 0.001

        # All correlations should be in [-1, 1]
        assert (correlations >= -1).all().all()
        assert (correlations <= 1).all().all()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_scenario(self):
        """Test generation with single scenario."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 1,
            'time_horizon': 10,
            'timestep': 1.0
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        assert len(scenarios_df) == 10
        assert scenarios_df['scenario_id'].nunique() == 1

    def test_single_time_period(self):
        """Test generation with single time period."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 100,
            'time_horizon': 1,
            'timestep': 1.0
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        assert len(scenarios_df) == 100
        assert all(scenarios_df['time_period'] == 1.0)

    def test_very_small_timestep(self):
        """Test generation with very small timestep (daily)."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 10,
            'time_horizon': 1,
            'timestep': 1/252,  # Daily (252 trading days)
            'use_stochastic': False
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        # Should have ~252 time periods
        scenario_1 = scenarios_df[scenarios_df['scenario_id'] == 'scenario_0001']
        assert len(scenario_1) == 252

    def test_long_time_horizon(self):
        """Test generation with very long time horizon."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 50,
            'time_horizon': 100,  # 100 years
            'timestep': 1.0,
            'use_stochastic': False
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        assert len(scenarios_df) == 50 * 100
        assert scenarios_df['time_period'].max() == 100.0


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_generate_scenarios_function(self):
        """Test generate_scenarios convenience function."""
        config = {
            'num_scenarios': 50,
            'time_horizon': 10,
            'timestep': 1.0
        }

        results = scenario_generator.generate_scenarios(config, random_seed=42)

        assert 'scenarios' in results
        assert 'deflators' in results
        assert isinstance(results['scenarios'], pd.DataFrame)

    def test_quick_scenarios_function(self):
        """Test quick_scenarios convenience function."""
        scenarios_df = scenario_generator.quick_scenarios(
            num_scenarios=50,
            time_horizon=10,
            use_stochastic=False
        )

        assert isinstance(scenarios_df, pd.DataFrame)
        assert len(scenarios_df) == 50 * 10
        assert 'scenario_id' in scenarios_df.columns

    def test_quick_scenarios_stochastic(self):
        """Test quick_scenarios with stochastic mode."""
        scenarios_df = scenario_generator.quick_scenarios(
            num_scenarios=20,
            time_horizon=5,
            use_stochastic=True
        )

        assert isinstance(scenarios_df, pd.DataFrame)
        assert len(scenarios_df) == 20 * 5


class TestDataQuality:
    """Test data quality and consistency."""

    def test_no_null_values(self):
        """Test that generated scenarios have no null values."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 100,
            'time_horizon': 30,
            'timestep': 1.0
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        assert not scenarios_df.isnull().any().any()

    def test_no_infinite_values(self):
        """Test that generated scenarios have no infinite values."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 100,
            'time_horizon': 30,
            'timestep': 1.0
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        numeric_cols = ['interest_rate', 'stock_return', 'bond_return',
                       'real_estate_return', 'inflation', 'gdp_growth']

        for col in numeric_cols:
            assert not np.isinf(scenarios_df[col]).any()

    def test_realistic_value_ranges(self):
        """Test that values are in realistic ranges."""
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        config = {
            'num_scenarios': 1000,
            'time_horizon': 30,
            'timestep': 1.0,
            'use_stochastic': False
        }

        results = gen.generate(config)
        scenarios_df = results['scenarios']

        # Interest rates should generally be positive and reasonable
        assert scenarios_df['interest_rate'].mean() > -0.05
        assert scenarios_df['interest_rate'].mean() < 0.20

        # Stock returns should be reasonable (not 1000% or -100%)
        assert scenarios_df['stock_return'].mean() > -0.50
        assert scenarios_df['stock_return'].mean() < 0.50

        # Inflation should be reasonable
        assert scenarios_df['inflation'].mean() > -0.10
        assert scenarios_df['inflation'].mean() < 0.15

    def test_consistency_across_runs(self):
        """Test that same config produces consistent structure across runs."""
        config = {
            'num_scenarios': 100,
            'time_horizon': 10,
            'timestep': 1.0
        }

        # Different seeds, but structure should be identical
        gen1 = scenario_generator.ScenarioGenerator(random_seed=42)
        results1 = gen1.generate(config)

        gen2 = scenario_generator.ScenarioGenerator(random_seed=123)
        results2 = gen2.generate(config)

        # Same structure
        assert results1['scenarios'].shape == results2['scenarios'].shape
        assert list(results1['scenarios'].columns) == list(results2['scenarios'].columns)
        assert results1['deflators'].shape == results2['deflators'].shape


class TestYieldCurveGeneration:
    """Test yield curve generation."""

    def test_yield_curve_eur(self):
        """Test EUR yield curve generation."""
        gen = scenario_generator.ScenarioGenerator()
        curve = gen._create_yield_curve('EUR')

        assert isinstance(curve, np.ndarray)
        assert len(curve) == 60
        assert all(curve > 0)

    def test_yield_curve_usd(self):
        """Test USD yield curve generation."""
        gen = scenario_generator.ScenarioGenerator()
        curve = gen._create_yield_curve('USD')

        assert isinstance(curve, np.ndarray)
        assert len(curve) == 60
        assert all(curve > 0)

    def test_yield_curve_different_currencies(self):
        """Test that different currencies produce different curves."""
        gen = scenario_generator.ScenarioGenerator()

        curve_eur = gen._create_yield_curve('EUR')
        curve_usd = gen._create_yield_curve('USD')
        curve_gbp = gen._create_yield_curve('GBP')

        # Curves should be different
        assert not np.array_equal(curve_eur, curve_usd)
        assert not np.array_equal(curve_usd, curve_gbp)

    def test_yield_curve_unknown_currency(self):
        """Test warning for unknown currency."""
        gen = scenario_generator.ScenarioGenerator()

        with pytest.warns(UserWarning, match="Unknown currency"):
            curve = gen._create_yield_curve('XYZ')

        # Should still return a valid curve (default to EUR)
        assert isinstance(curve, np.ndarray)
        assert len(curve) == 60


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


def test_drift_immobilier_exact():
    """
    Les moments analytiques du drift immobilier sont ceux des scénarios.

    Le drift risque-neutre impose E[log Indice(t)] = -log P(0, t) - V(t)/2 - C(t),
    avec V la variance de log Indice et C sa covariance avec log D, calculées
    en forme fermée. Les chocs étant antithétiques, la moyenne empirique de
    log Indice est exactement la moyenne analytique ; V et C sont comparées
    à leurs estimateurs empiriques.
    """
    from investment_calculator.market_assumptions import load_market_assumptions
    from investment_calculator.stochastic_models import (
        CorrelatedRandomGenerator,
        HullWhiteModel,
        RealEstateModel,
    )

    np.random.seed(7)
    n_scenarios, horizon, dt = 20_000, 30, 0.25
    n_steps = int(horizon / dt)
    generator = scenario_generator.ScenarioGenerator(random_seed=7)
    _, _, f0t, P0t = generator._load_yield_curve(None, 'EUR', dt, n_steps)
    params = generator.default_params
    assumptions = load_market_assumptions()

    rates = HullWhiteModel(
        a=params['mean_reversion_speed'], sigma=params['hw_volatility'],
        f0t=f0t, P0t=P0t, dt=dt, n_scenarios=n_scenarios, T=horizon,
    )
    rate_results = rates.generate_scenarios()
    correlation = CorrelatedRandomGenerator(n_scenarios=n_scenarios, n_steps=n_steps)
    shocks = correlation.generate(rate_residuals=rate_results['residuals'])['shocks']
    real_estate = RealEstateModel(
        a=assumptions.real_estate_mean_reversion,
        sigma=assumptions.real_estate_instantaneous_volatility,
        rental_yield=params['re_rental_yield'], dt=dt,
        n_scenarios=n_scenarios, T=horizon,
    )
    covariances = correlation.shock_covariances(['short_rate', 'real_estate', 'inflation'])
    drift = real_estate.risk_neutral_drift(
        f0t, P0t, n_steps, rates.log_deflator_loadings(), covariances
    )
    returns = real_estate.generate_returns(
        rate_results['Rt'], f0t,
        re_price_shocks=correlation.get_asset_shocks(shocks, 'real_estate'),
        re_rental_shocks=correlation.get_asset_shocks(shocks, 'inflation'),
        drift=drift,
    )['total_returns']

    log_index = np.cumsum(returns, axis=1)
    log_deflator = np.log(rate_results['deflators'])
    price, aux = real_estate.log_index_loadings(n_steps)
    index_loadings = np.stack([np.zeros_like(price), price, aux], axis=-1)
    rate_loadings = np.stack(
        [rates.log_deflator_loadings(), np.zeros_like(price), np.zeros_like(price)], axis=-1
    )
    variance = np.einsum('tjk,jkl,tjl->t', index_loadings, covariances, index_loadings)
    covariance = np.einsum('tjk,jkl,tjl->t', index_loadings, covariances, rate_loadings)
    expected_mean = -np.log(P0t[:n_steps]) - variance / 2 - covariance

    np.testing.assert_allclose(log_index.mean(axis=0), expected_mean, atol=1e-9)
    last = n_steps - 1
    assert log_index[:, last].var() == pytest.approx(variance[last], rel=0.03)
    empirical_covariance = np.cov(log_index[:, last], log_deflator[:, last])[0, 1]
    assert empirical_covariance == pytest.approx(covariance[last], rel=0.05)
    # La covariance avec les taux n'est pas négligeable devant la convexité.
    assert abs(covariance[last]) > 0.1 * variance[last] / 2
