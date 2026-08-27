"""
Comprehensive Unit Tests for Module 2: Tax-Integrated Scenario Engine

Tests cover:
- Tax configuration built from investment_calculator.tax_regime
- Tax configuration validation
- After-tax scenario generation
- Tax tables and metrics
- Account balance simulation
- Optimization insights
- Different asset allocations
- Edge cases
- Convenience functions

Depuis l'étape 1.A.5, ce moteur ne contient plus aucun taux fiscal en dur :
il consomme investment_calculator.tax_regime.load_regime. Voir
docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md et
tests/test_tax_regime_contract.py pour le contrat qui rend cela exécutoire.
Seule la France est un régime vérifié aujourd'hui ; les tests qui portaient
sur les États-Unis et le Royaume-Uni testaient un dictionnaire hérité, pas
un régime réel, et ont été retirés avec lui.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator.modules import scenario_generator, tax_engine
from investment_calculator.tax_regime import load_regime


# Helper function to create simple test scenarios
def create_test_scenarios(num_scenarios=10, time_horizon=5):
    """Create simple test scenarios for tax engine testing."""
    gen = scenario_generator.ScenarioGenerator(random_seed=42)
    config = {
        'num_scenarios': num_scenarios,
        'time_horizon': time_horizon,
        'timestep': 1.0,
        'use_stochastic': False
    }
    results = gen.generate(config)
    return results['scenarios']


class TestTaxConfigFromRegime:
    """Test the bridge from a TaxRegime to the engine's legacy tax_config shape."""

    def test_default_tax_config_is_the_french_regime(self):
        config = tax_engine._default_tax_config()

        assert config['jurisdiction'] == 'FR'
        assert 'account_types' in config
        assert 'taxable' in config['account_types']
        assert 'tax_deferred' in config['account_types']
        assert 'tax_free' in config['account_types']
        assert 'social_charges' in config
        assert 'wealth_tax' in config

    def test_france_social_charges_and_wealth_tax(self):
        regime = load_regime('FR')
        config = regime.to_scenario_tax_config(reference_household_income=50_000)

        assert config['social_charges'] == 0.172  # Prélèvements sociaux
        assert config['wealth_tax']['enabled'] is True
        assert config['wealth_tax']['threshold'] == 1_300_000

    def test_unknown_jurisdiction_raises_a_clear_error(self):
        from investment_calculator.tax_regime import RegimeNotFoundError

        with pytest.raises(RegimeNotFoundError, match="Disponibles"):
            load_regime('XYZ')

    def test_taxable_account_fields(self):
        regime = load_regime('FR')
        config = regime.to_scenario_tax_config(reference_household_income=50_000)
        taxable = config['account_types']['taxable']

        assert 'income_tax_rate' in taxable
        assert 'capital_gains_rate' in taxable
        assert 'dividend_tax_rate' in taxable
        assert 'interest_tax_rate' in taxable

        # Check values are reasonable
        assert 0 <= taxable['income_tax_rate'] <= 1
        assert 0 <= taxable['capital_gains_rate'] <= 1

    def test_tax_deferred_account_fields(self):
        regime = load_regime('FR')
        config = regime.to_scenario_tax_config(reference_household_income=50_000)
        tax_deferred = config['account_types']['tax_deferred']

        assert 'contribution_deduction' in tax_deferred
        assert 'withdrawal_tax_rate' in tax_deferred
        assert isinstance(tax_deferred['contribution_deduction'], bool)
        assert 0 <= tax_deferred['withdrawal_tax_rate'] <= 1

    def test_le_double_comptage_du_prelevement_forfaitaire_a_disparu(self):
        """
        Régression du défaut le plus coûteux de l'ancien moteur, vérifiée au
        niveau du moteur lui-même (pas seulement de TaxRegime).

        L'ancien TaxConfigPreset.get_preset('FR') portait un
        dividend_tax_rate de 0.30 (déjà le taux global du PFU), auquel le
        moteur ajoutait ensuite social_charges (0.172), portant le taux
        effectif à 47,2 % au lieu de 30 %. Le pont TaxRegime.to_scenario_tax_config
        doit fournir la part impôt sur le revenu seule (12,8 %), pas le taux
        global, pour que l'addition faite par le moteur retombe sur 30 %.
        """
        regime = load_regime('FR')
        config = regime.to_scenario_tax_config(reference_household_income=50_000)

        effective_pfu_rate = (
            config['account_types']['taxable']['dividend_tax_rate'] + config['social_charges']
        )
        assert effective_pfu_rate == pytest.approx(0.30)
        assert effective_pfu_rate < 0.40, "47,2 % ne doit plus jamais réapparaître ici."


class TestTaxEngineInitialization:
    """Test TaxEngine initialization."""

    def test_init(self):
        """Test basic initialization."""
        engine = tax_engine.TaxEngine()
        assert engine is not None

    def test_multiple_instances(self):
        """Test creating multiple instances."""
        engine1 = tax_engine.TaxEngine()
        engine2 = tax_engine.TaxEngine()

        assert engine1 is not engine2


class TestConfigurationValidation:
    """Test configuration validation."""

    def test_validate_minimal_config(self):
        """Test validation with minimal configuration."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        config = {'scenarios': scenarios_df}
        validated = engine._validate_config(config)

        # Should add default tax_config and allocation
        assert 'scenarios' in validated
        assert 'tax_config' in validated
        assert 'investment_allocation' in validated

    def test_validate_missing_scenarios(self):
        """Test that missing scenarios raises error."""
        engine = tax_engine.TaxEngine()

        with pytest.raises(ValueError, match="Missing required field: scenarios"):
            engine._validate_config({})

    def test_validate_custom_tax_config(self):
        """Test validation with custom tax config."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        custom_tax_config = load_regime('FR').to_scenario_tax_config(
            reference_household_income=50_000
        )
        config = {
            'scenarios': scenarios_df,
            'tax_config': custom_tax_config
        }

        validated = engine._validate_config(config)
        assert validated['tax_config']['jurisdiction'] == 'FR'

    def test_validate_custom_allocation(self):
        """Test validation with custom allocation."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        custom_allocation = {
            'stocks': {'taxable': 0.5, 'tax_deferred': 0.3, 'tax_free': 0.2}
        }

        config = {
            'scenarios': scenarios_df,
            'investment_allocation': custom_allocation
        }

        validated = engine._validate_config(config)
        assert validated['investment_allocation']['stocks']['taxable'] == 0.5

    def test_default_allocation_structure(self):
        """Test that default allocation has correct structure."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        config = {'scenarios': scenarios_df}
        validated = engine._validate_config(config)

        allocation = validated['investment_allocation']

        # Check all asset classes present
        assert 'stocks' in allocation
        assert 'bonds' in allocation
        assert 'real_estate' in allocation

        # Check all account types present for stocks
        assert 'taxable' in allocation['stocks']
        assert 'tax_deferred' in allocation['stocks']
        assert 'tax_free' in allocation['stocks']


class TestAfterTaxScenarios:
    """Test after-tax scenario calculations."""

    def test_basic_after_tax_calculation(self):
        """Test basic after-tax scenario generation."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        tax_config = load_regime('FR').to_scenario_tax_config(reference_household_income=50_000)
        allocation = {
            'stocks': {'taxable': 0.6, 'tax_deferred': 0.3, 'tax_free': 0.1},
            'bonds': {'taxable': 0.6, 'tax_deferred': 0.3, 'tax_free': 0.1},
            'real_estate': {'taxable': 0.6, 'tax_deferred': 0.3, 'tax_free': 0.1}
        }

        results = engine.apply_taxes({
            'scenarios': scenarios_df,
            'tax_config': tax_config,
            'investment_allocation': allocation
        })

        after_tax_df = results['after_tax_scenarios']

        # Check structure
        assert isinstance(after_tax_df, pd.DataFrame)
        assert len(after_tax_df) == len(scenarios_df)

    def test_after_tax_columns(self):
        """Test that after-tax DataFrame has correct columns."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})
        after_tax_df = results['after_tax_scenarios']

        # Check for after-tax columns
        assert 'stock_return_after_tax' in after_tax_df.columns
        assert 'bond_return_after_tax' in after_tax_df.columns
        assert 'real_estate_return_after_tax' in after_tax_df.columns
        assert 'annual_tax_drag' in after_tax_df.columns

    def test_after_tax_returns_lower(self):
        """Test that after-tax returns are generally lower than pre-tax."""
        scenarios_df = create_test_scenarios(num_scenarios=100)
        engine = tax_engine.TaxEngine()

        allocation = {
            'stocks': {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0},
            'bonds': {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0},
            'real_estate': {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0}
        }

        results = engine.apply_taxes({
            'scenarios': scenarios_df,
            'investment_allocation': allocation
        })

        after_tax_df = results['after_tax_scenarios']

        # After-tax should be lower when all in taxable account (on average for positive returns)
        # Filter for positive returns to avoid edge cases with negative returns
        positive_stock = scenarios_df['stock_return'] > 0.05
        if positive_stock.sum() > 10:  # Ensure we have enough positive return periods
            assert (after_tax_df.loc[positive_stock, 'stock_return_after_tax'].mean() <=
                   scenarios_df.loc[positive_stock, 'stock_return'].mean())

    def test_tax_free_account_no_tax(self):
        """Test that tax-free accounts have no tax drag."""
        scenarios_df = create_test_scenarios(num_scenarios=50)
        engine = tax_engine.TaxEngine()

        # All in tax-free account
        allocation = {
            'stocks': {'taxable': 0.0, 'tax_deferred': 0.0, 'tax_free': 1.0},
            'bonds': {'taxable': 0.0, 'tax_deferred': 0.0, 'tax_free': 1.0},
            'real_estate': {'taxable': 0.0, 'tax_deferred': 0.0, 'tax_free': 1.0}
        }

        results = engine.apply_taxes({
            'scenarios': scenarios_df,
            'investment_allocation': allocation
        })

        after_tax_df = results['after_tax_scenarios']

        # Should be equal (or very close) to pre-tax returns
        np.testing.assert_array_almost_equal(
            after_tax_df['stock_return_after_tax'].values,
            scenarios_df['stock_return'].values,
            decimal=5
        )

    def test_tax_drag_calculation(self):
        """Test tax drag calculation."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})
        after_tax_df = results['after_tax_scenarios']

        # Tax drag column should exist
        assert 'annual_tax_drag' in after_tax_df.columns
        # Tax drag should be finite
        assert np.isfinite(after_tax_df['annual_tax_drag']).all()


class TestTaxTables:
    """Test tax table generation."""

    def test_tax_tables_structure(self):
        """Test tax tables have correct structure."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})
        tax_tables = results['tax_tables']

        # Check all expected tables present
        assert 'annual_tax_by_account' in tax_tables
        assert 'cumulative_tax' in tax_tables
        assert 'tax_drag' in tax_tables
        assert 'effective_tax_rate' in tax_tables

    def test_annual_tax_table(self):
        """Test annual tax by account table."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})
        annual_tax_df = results['tax_tables']['annual_tax_by_account']

        # Check columns
        assert 'scenario_id' in annual_tax_df.columns
        assert 'time_period' in annual_tax_df.columns
        assert 'stock_tax' in annual_tax_df.columns
        assert 'bond_tax' in annual_tax_df.columns
        assert 'real_estate_tax' in annual_tax_df.columns
        assert 'total_tax' in annual_tax_df.columns

    def test_cumulative_tax_table(self):
        """Test cumulative tax table."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})
        cumulative_tax_df = results['tax_tables']['cumulative_tax']

        # Check cumulative column exists
        assert 'cumulative_total_tax' in cumulative_tax_df.columns

        # Check that cumulative values are finite
        assert np.isfinite(cumulative_tax_df['cumulative_total_tax']).all()

    def test_effective_tax_rate_table(self):
        """Test effective tax rate table."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})
        effective_rate_df = results['tax_tables']['effective_tax_rate']

        # Check columns
        assert 'scenario_id' in effective_rate_df.columns
        assert 'effective_tax_rate' in effective_rate_df.columns
        assert 'total_pre_tax_return' in effective_rate_df.columns
        assert 'total_after_tax_return' in effective_rate_df.columns
        assert 'total_taxes_paid' in effective_rate_df.columns

        # Check effective rates are finite
        assert np.isfinite(effective_rate_df['effective_tax_rate']).all()
        # Most rates should be in reasonable range (some edge cases may exist)
        reasonable_rates = (effective_rate_df['effective_tax_rate'] >= -0.1) & \
                          (effective_rate_df['effective_tax_rate'] <= 1)
        assert reasonable_rates.mean() > 0.8  # At least 80% should be reasonable


class TestAccountBalances:
    """Test account balance simulation."""

    def test_account_balances_structure(self):
        """Test account balances have correct structure."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})
        balances = results['account_balances']

        # Check all account types present
        assert 'taxable' in balances
        assert 'tax_deferred' in balances
        assert 'tax_free' in balances
        assert 'total' in balances

    def test_account_balance_dataframes(self):
        """Test account balance DataFrames."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})
        taxable_balances = results['account_balances']['taxable']

        # Should be a DataFrame
        assert isinstance(taxable_balances, pd.DataFrame)
        assert 'scenario_id' in taxable_balances.columns


class TestOptimizationInsights:
    """Test optimization insights generation."""

    def test_insights_structure(self):
        """Test optimization insights structure."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})
        insights = results['optimization_insights']

        # Check expected fields
        assert 'tax_loss_harvesting_opportunities' in insights
        assert 'optimal_withdrawal_sequence' in insights
        assert 'roth_conversion_analysis' in insights

    def test_withdrawal_sequence(self):
        """Test optimal withdrawal sequence."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})
        withdrawal_seq = results['optimization_insights']['optimal_withdrawal_sequence']

        # Should be a list
        assert isinstance(withdrawal_seq, list)
        assert len(withdrawal_seq) > 0

        # Check structure
        for item in withdrawal_seq:
            assert 'rank' in item
            assert 'account_type' in item
            assert 'reason' in item


class TestJurisdictions:
    """
    Test des juridictions disponibles.

    Seule la France a un régime vérifié aujourd'hui (voir
    investment_calculator/tax_regimes/README.md) : il n'y a donc plus de
    comparaison US/FR/UK à tester ici, seulement le comportement attendu
    face à une juridiction absente.
    """

    def test_une_juridiction_sans_regime_leve_une_erreur_claire(self):
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        with pytest.raises(Exception, match="Disponibles"):
            engine.apply_taxes({
                'scenarios': scenarios_df,
                'tax_config': load_regime('UK').to_scenario_tax_config(
                    reference_household_income=50_000
                ),
            })


class TestDifferentAllocations:
    """Test different asset allocations."""

    def test_all_taxable_allocation(self):
        """Test allocation with everything in taxable account."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        allocation = {
            'stocks': {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0},
            'bonds': {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0},
            'real_estate': {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0}
        }

        results = engine.apply_taxes({
            'scenarios': scenarios_df,
            'investment_allocation': allocation
        })

        # Should have highest tax burden
        avg_rate = results['tax_tables']['effective_tax_rate']['effective_tax_rate'].mean()
        assert avg_rate > 0.05  # At least some tax

    def test_all_tax_free_allocation(self):
        """Test allocation with everything in tax-free account."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        allocation = {
            'stocks': {'taxable': 0.0, 'tax_deferred': 0.0, 'tax_free': 1.0},
            'bonds': {'taxable': 0.0, 'tax_deferred': 0.0, 'tax_free': 1.0},
            'real_estate': {'taxable': 0.0, 'tax_deferred': 0.0, 'tax_free': 1.0}
        }

        results = engine.apply_taxes({
            'scenarios': scenarios_df,
            'investment_allocation': allocation
        })

        # Should have very low/no tax burden
        avg_rate = results['tax_tables']['effective_tax_rate']['effective_tax_rate'].mean()
        assert avg_rate < 0.01  # Minimal tax

    def test_mixed_allocation(self):
        """Test mixed allocation across account types."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        allocation = {
            'stocks': {'taxable': 0.5, 'tax_deferred': 0.3, 'tax_free': 0.2},
            'bonds': {'taxable': 0.3, 'tax_deferred': 0.5, 'tax_free': 0.2},
            'real_estate': {'taxable': 0.7, 'tax_deferred': 0.2, 'tax_free': 0.1}
        }

        results = engine.apply_taxes({
            'scenarios': scenarios_df,
            'investment_allocation': allocation
        })

        # Should be between all-taxable and all-tax-free
        avg_rate = results['tax_tables']['effective_tax_rate']['effective_tax_rate'].mean()
        assert 0.01 < avg_rate < 0.20


class TestEdgeCases:
    """Test edge cases."""

    def test_single_scenario(self):
        """Test with single scenario."""
        scenarios_df = create_test_scenarios(num_scenarios=1)
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})

        assert len(results['after_tax_scenarios']) == len(scenarios_df)

    def test_single_time_period(self):
        """Test with single time period."""
        scenarios_df = create_test_scenarios(num_scenarios=10, time_horizon=1)
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})

        assert len(results['after_tax_scenarios']) == 10

    def test_zero_allocation_asset_class(self):
        """Test with an asset class having zero allocation."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        allocation = {
            'stocks': {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0},
            'bonds': {'taxable': 0.0, 'tax_deferred': 0.0, 'tax_free': 0.0},  # Zero allocation
            'real_estate': {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0}
        }

        results = engine.apply_taxes({
            'scenarios': scenarios_df,
            'investment_allocation': allocation
        })

        # Should complete without errors
        assert 'after_tax_scenarios' in results


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_apply_taxes_simple_default_jurisdiction_is_fr(self):
        """FR est la seule juridiction vérifiée : c'est le défaut de la fonction."""
        scenarios_df = create_test_scenarios()

        results = tax_engine.apply_taxes_simple(scenarios_df)

        assert 'after_tax_scenarios' in results
        assert 'tax_tables' in results
        assert 'account_balances' in results

    def test_apply_taxes_simple_fr(self):
        """Test apply_taxes_simple with French jurisdiction."""
        scenarios_df = create_test_scenarios()

        results = tax_engine.apply_taxes_simple(scenarios_df, jurisdiction='FR')

        assert 'after_tax_scenarios' in results

    def test_apply_taxes_simple_custom_allocation(self):
        """Test apply_taxes_simple with custom allocation."""
        scenarios_df = create_test_scenarios()

        custom_allocation = {
            'stocks': {'taxable': 0.8, 'tax_deferred': 0.1, 'tax_free': 0.1},
            'bonds': {'taxable': 0.2, 'tax_deferred': 0.6, 'tax_free': 0.2},
            'real_estate': {'taxable': 0.9, 'tax_deferred': 0.05, 'tax_free': 0.05}
        }

        results = tax_engine.apply_taxes_simple(
            scenarios_df,
            jurisdiction='FR',
            allocation=custom_allocation
        )

        assert 'after_tax_scenarios' in results


class TestDataQuality:
    """Test data quality and consistency."""

    def test_no_null_values(self):
        """Test that results have no null values."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})

        # Check after-tax scenarios
        assert not results['after_tax_scenarios'].isnull().any().any()

        # Check tax tables
        assert not results['tax_tables']['annual_tax_by_account'].isnull().any().any()

    def test_no_infinite_values(self):
        """Test that results have no infinite values."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        results = engine.apply_taxes({'scenarios': scenarios_df})

        after_tax_df = results['after_tax_scenarios']

        # Check numeric columns
        numeric_cols = ['stock_return_after_tax', 'bond_return_after_tax',
                       'real_estate_return_after_tax', 'annual_tax_drag']

        for col in numeric_cols:
            if col in after_tax_df.columns:
                assert not np.isinf(after_tax_df[col]).any()

    def test_consistency_across_runs(self):
        """Test that same inputs produce same outputs."""
        scenarios_df = create_test_scenarios()
        engine = tax_engine.TaxEngine()

        config = {
            'scenarios': scenarios_df,
            'tax_config': load_regime('FR').to_scenario_tax_config(
                reference_household_income=50_000
            )
        }

        results1 = engine.apply_taxes(config.copy())
        results2 = engine.apply_taxes(config.copy())

        # Should be identical
        pd.testing.assert_frame_equal(
            results1['after_tax_scenarios'],
            results2['after_tax_scenarios']
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
