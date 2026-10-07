"""
Module 2: Tax-Integrated Scenario Engine (GSE+)

This module applies tax treatment to economic scenarios based on account types
and jurisdiction rules.

INPUT STRUCTURE:
{
    'scenarios': pd.DataFrame,      # From Module 1

    'tax_config': {
        'jurisdiction': str,        # Country code (e.g., 'FR', 'US', 'UK')
        'account_types': {
            'taxable': {
                'income_tax_rate': float,         # e.g., 0.30
                'capital_gains_rate': float,      # e.g., 0.15
                'dividend_tax_rate': float,       # e.g., 0.25
                'interest_tax_rate': float        # e.g., 0.30
            },
            'tax_deferred': {
                'contribution_deduction': bool,   # Tax deduction on contributions
                'withdrawal_tax_rate': float      # Tax on withdrawals
            },
            'tax_free': {
                'contribution_limit': float,      # Annual limit
                'age_restrictions': dict          # Withdrawal rules
            }
        },
        'social_charges': float,    # Social security taxes (e.g., 0.172 for France)
        'wealth_tax': {
            'enabled': bool,
            'threshold': float,     # Wealth tax threshold
            'rate': float          # Wealth tax rate
        }
    },

    'investment_allocation': {
        'stocks': {'taxable': float, 'tax_deferred': float, 'tax_free': float},
        'bonds': {...},
        'real_estate': {...}
    }
}

OUTPUT STRUCTURE:
{
    'after_tax_scenarios': pd.DataFrame,  # Same structure as scenarios but after-tax
                                         # Columns include original + '_after_tax' versions

    'tax_tables': {
        'annual_tax_by_account': pd.DataFrame,  # Annual taxes paid per account type
        'cumulative_tax': pd.DataFrame,         # Cumulative tax burden over time
        'tax_drag': pd.DataFrame,              # Performance drag due to taxes
        'effective_tax_rate': pd.DataFrame     # Effective tax rate per scenario
    }
}

Les soldes par type de compte et les « conseils d'optimisation fiscale »
(séquence de retrait, conversion Roth) ont été retirés à l'étape 1.C.2 : les
soldes valaient 0 et les conseils étaient des textes figés, sans calcul. Une
fonctionnalité absente vaut mieux qu'une fonctionnalité qui ment.
"""

import logging
import time
from enum import Enum

import pandas as pd

from investment_calculator.market_assumptions import (
    MarketAssumptions,
    load_market_assumptions,
)
from investment_calculator.tax_regime import load_regime

# Journalisation : logger nommé d'après le module, il hérite donc de la
# configuration posée par investment_calculator.logging_config.configure_logging().
logger = logging.getLogger(__name__)


class AccountType(Enum):
    """Types of investment accounts"""
    TAXABLE = "taxable"
    TAX_DEFERRED = "tax_deferred"
    TAX_FREE = "tax_free"


def _default_tax_config() -> dict:
    """
    Configuration fiscale par défaut : le régime français le plus récent disponible.

    La France est aujourd'hui le seul pays dont le régime a été confronté à
    des cas d'or — voir ``investment_calculator/tax_regimes/README.md``. Un
    autre pays devient disponible en y déposant un régime, pas en modifiant
    cette fonction.
    """
    regime = load_regime("FR")
    reference_income = load_market_assumptions().reference_household_income
    return regime.to_scenario_tax_config(reference_household_income=reference_income)


class TaxEngine:
    """
    Tax-Integrated Scenario Engine (GSE+) - Module 2

    Applies tax treatment to economic scenarios from Module 1.

    Example:
        >>> from investment_calculator.modules import scenario_generator, tax_engine
        >>> # Generate scenarios
        >>> gen = scenario_generator.ScenarioGenerator()
        >>> scenarios = gen.generate({'num_scenarios': 100, 'time_horizon': 30, 'timestep': 1.0})
        >>> # Apply taxes
        >>> tax_eng = tax_engine.TaxEngine()
        >>> from investment_calculator.tax_regime import load_regime
        >>> tax_config = load_regime('FR').to_scenario_tax_config(reference_household_income=50_000)
        >>> allocation = {'stocks': {'taxable': 0.6, 'tax_deferred': 0.3, 'tax_free': 0.1}}
        >>> results = tax_eng.apply_taxes({
        ...     'scenarios': scenarios['scenarios'],
        ...     'tax_config': tax_config,
        ...     'investment_allocation': allocation
        ... })
    """

    def __init__(self) -> None:
        """Initialize the Tax Engine."""

    def apply_taxes(self, config: dict) -> dict:
        """
        Apply tax treatment to economic scenarios.

        Args:
            config: Configuration dictionary (see module docstring)

        Returns:
            Dictionary with after-tax scenarios and tax tables
        """
        # Chronomètre pour tracer la durée du traitement fiscal.
        start_time = time.perf_counter()

        # Validate configuration
        validated_config = self._validate_config(config)

        scenarios_df = validated_config['scenarios']
        tax_config = validated_config['tax_config']
        allocation = validated_config['investment_allocation']

        logger.info(
            "Début de l'application du régime fiscal sur %d lignes de scénarios",
            len(scenarios_df),
        )

        # Calculate after-tax returns for each account type
        market_assumptions = load_market_assumptions()
        after_tax_scenarios = self._calculate_after_tax_scenarios(
            scenarios_df, tax_config, allocation, market_assumptions
        )

        # Calculate tax tables
        tax_tables = self._calculate_tax_tables(
            scenarios_df, after_tax_scenarios, tax_config, allocation
        )

        logger.info(
            "Fin de l'application du régime fiscal en %.3f s : %d lignes après impôt",
            time.perf_counter() - start_time,
            len(after_tax_scenarios),
        )

        return {
            'after_tax_scenarios': after_tax_scenarios,
            'tax_tables': tax_tables,
        }

    def _validate_config(self, config: dict) -> dict:
        """
        Validate and complete configuration.

        Args:
            config: User configuration

        Returns:
            Validated configuration
        """
        if 'scenarios' not in config:
            raise ValueError("Missing required field: scenarios")

        if 'tax_config' not in config:
            config['tax_config'] = _default_tax_config()

        if 'investment_allocation' not in config:
            # Default: all in taxable account
            config['investment_allocation'] = {
                'stocks': {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0},
                'bonds': {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0},
                'real_estate': {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0}
            }

        return config

    def _calculate_after_tax_scenarios(
        self,
        scenarios_df: pd.DataFrame,
        tax_config: dict,
        allocation: dict,
        market_assumptions: MarketAssumptions,
    ) -> pd.DataFrame:
        """
        Calculate after-tax returns for all scenarios.

        Args:
            scenarios_df: Economic scenarios from Module 1
            tax_config: Tax configuration
            allocation: Asset allocation across account types
            market_assumptions: hypothèses de marché et de comportement
                (rendement du dividende, répartition loyer/appréciation,
                fraction de plus-value réalisée annuellement) — voir
                investment_calculator.market_assumptions. Ce ne sont pas des
                paramètres fiscaux.

        Returns:
            DataFrame with after-tax return columns added
        """
        # Create a copy
        result_df = scenarios_df.copy()

        # Get tax rates for different account types
        taxable_config = tax_config['account_types']['taxable']
        social_charges = tax_config['social_charges']

        # Calculate after-tax returns for each asset class

        # 1. STOCKS
        stock_allocation = allocation.get(
            'stocks', {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0}
        )

        # Taxable: dividends taxed annually, capital gains deferred
        dividend_yield = market_assumptions.dividend_yield
        dividend_tax = taxable_config['dividend_tax_rate'] + social_charges
        stock_taxable_drag = dividend_yield * dividend_tax

        # Weighted after-tax stock return
        stock_after_tax = (
            scenarios_df['stock_return'] * stock_allocation['taxable']
            * (
                1 - stock_taxable_drag
                / scenarios_df['stock_return'].clip(lower=0.01)
            ) +
            scenarios_df['stock_return'] * stock_allocation['tax_deferred'] +  # No annual tax
            scenarios_df['stock_return'] * stock_allocation['tax_free']  # No tax
        )

        result_df['stock_return_after_tax'] = stock_after_tax

        # 2. BONDS
        bond_allocation = allocation.get(
            'bonds', {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0}
        )

        # Taxable: interest taxed as ordinary income
        interest_tax = taxable_config['interest_tax_rate'] + social_charges

        bond_after_tax = (
            scenarios_df['bond_return'] * bond_allocation['taxable'] * (1 - interest_tax) +
            scenarios_df['bond_return'] * bond_allocation['tax_deferred'] +
            scenarios_df['bond_return'] * bond_allocation['tax_free']
        )

        result_df['bond_return_after_tax'] = bond_after_tax

        # 3. REAL ESTATE
        re_allocation = allocation.get(
            'real_estate', {'taxable': 1.0, 'tax_deferred': 0.0, 'tax_free': 0.0}
        )

        # Taxable: rental income + appreciation, split per market_assumptions
        rental_portion = market_assumptions.rental_income_share
        appreciation_portion = market_assumptions.appreciation_share
        rental_tax = taxable_config['income_tax_rate'] + social_charges
        appreciation_tax = (
            taxable_config['capital_gains_rate'] * market_assumptions.annual_realized_fraction
        )

        re_taxable_drag = (
            rental_portion * rental_tax +
            appreciation_portion * appreciation_tax
        )

        re_after_tax = (
            scenarios_df['real_estate_return'] * re_allocation['taxable'] * (1 - re_taxable_drag) +
            scenarios_df['real_estate_return'] * re_allocation['tax_deferred'] +
            scenarios_df['real_estate_return'] * re_allocation['tax_free']
        )

        result_df['real_estate_return_after_tax'] = re_after_tax

        # 4. INTEREST RATE AND INFLATION (not taxed directly)
        result_df['interest_rate_after_tax'] = scenarios_df['interest_rate']
        result_df['inflation_after_tax'] = scenarios_df['inflation']
        result_df['gdp_growth_after_tax'] = scenarios_df['gdp_growth']

        # Calculate tax drag per row
        stock_drag = scenarios_df['stock_return'] - result_df['stock_return_after_tax']
        bond_drag = scenarios_df['bond_return'] - result_df['bond_return_after_tax']
        re_drag = scenarios_df['real_estate_return'] - result_df['real_estate_return_after_tax']

        result_df['annual_tax_drag'] = stock_drag + bond_drag + re_drag

        return result_df

    def _calculate_tax_tables(
        self,
        pre_tax_df: pd.DataFrame,
        after_tax_df: pd.DataFrame,
        tax_config: dict,
        allocation: dict
    ) -> dict[str, pd.DataFrame]:
        """
        Calculate detailed tax tables.

        Args:
            pre_tax_df: Pre-tax scenarios
            after_tax_df: After-tax scenarios
            tax_config: Tax configuration
            allocation: Asset allocation

        Returns:
            Dictionary of tax-related DataFrames
        """
        # Calcul vectorisé : les deux tableaux sont alignés ligne à ligne
        # (after_tax_df est construit comme une copie de pre_tax_df).
        if len(pre_tax_df) != len(after_tax_df):
            raise ValueError(
                "Scénarios avant et après impôt de tailles différentes : "
                f"{len(pre_tax_df)} contre {len(after_tax_df)} lignes."
            )
        pre = pre_tax_df.reset_index(drop=True)
        post = after_tax_df.reset_index(drop=True)

        # Annual tax per asset class
        annual_tax_df = pd.DataFrame({
            'scenario_id': pre['scenario_id'],
            'time_period': pre['time_period'],
            'stock_tax': pre['stock_return'] - post['stock_return_after_tax'],
            'bond_tax': pre['bond_return'] - post['bond_return_after_tax'],
            'real_estate_tax': pre['real_estate_return'] - post['real_estate_return_after_tax'],
        })
        annual_tax_df['total_tax'] = (
            annual_tax_df['stock_tax'] + annual_tax_df['bond_tax']
            + annual_tax_df['real_estate_tax']
        )

        # Cumulative tax
        cumulative_tax_df = annual_tax_df.copy()
        cumulative_tax_df['cumulative_total_tax'] = (
            cumulative_tax_df.groupby('scenario_id')['total_tax'].cumsum()
        )

        # Tax drag (percentage)
        tax_drag_df = annual_tax_df.copy()
        total_return = pre['stock_return'] + pre['bond_return'] + pre['real_estate_return']

        tax_drag_df['tax_drag_pct'] = (
            tax_drag_df['total_tax'] / total_return.clip(lower=0.001)
        ) * 100

        # Effective tax rate per scenario
        totals = pd.DataFrame({
            'scenario_id': pre['scenario_id'],
            'total_pre_tax_return': (
                pre['stock_return'] + pre['bond_return'] + pre['real_estate_return']
            ),
            'total_after_tax_return': (
                post['stock_return_after_tax'] + post['bond_return_after_tax']
                + post['real_estate_return_after_tax']
            ),
        }).groupby('scenario_id', sort=False).sum().reset_index()

        totals['total_taxes_paid'] = (
            totals['total_pre_tax_return'] - totals['total_after_tax_return']
        )
        positive = totals['total_pre_tax_return'] > 0
        totals['effective_tax_rate'] = (
            totals['total_taxes_paid'].where(positive, 0.0)
            / totals['total_pre_tax_return'].where(positive, 1.0)
        )
        effective_rate_df = totals[[
            'scenario_id', 'effective_tax_rate', 'total_pre_tax_return',
            'total_after_tax_return', 'total_taxes_paid',
        ]]

        return {
            'annual_tax_by_account': annual_tax_df,
            'cumulative_tax': cumulative_tax_df,
            'tax_drag': tax_drag_df,
            'effective_tax_rate': effective_rate_df
        }


# Convenience functions
def apply_taxes_simple(
    scenarios_df: pd.DataFrame,
    jurisdiction: str = 'FR',
    allocation: dict | None = None,
    reference_household_income: float | None = None,
) -> dict:
    """
    Apply taxes with simple configuration.

    Args:
        scenarios_df: Scenarios DataFrame from Module 1
        jurisdiction: Tax jurisdiction — see
            investment_calculator.tax_regime.list_regimes for what is
            actually available. Only 'FR' is validated today.
        allocation: Asset allocation (optional)
        reference_household_income: revenu de foyer utilisé pour réduire le
            barème progressif à un taux moyen — voir
            TaxRegime.to_scenario_tax_config. Par défaut, celui des
            hypothèses de marché (investment_calculator.market_assumptions).

    Returns:
        Tax results dictionary

    Example:
        >>> results = apply_taxes_simple(scenarios_df, jurisdiction='FR')
    """
    if reference_household_income is None:
        reference_household_income = load_market_assumptions().reference_household_income

    regime = load_regime(jurisdiction)
    tax_config = regime.to_scenario_tax_config(
        reference_household_income=reference_household_income
    )

    if allocation is None:
        allocation = {
            'stocks': {'taxable': 0.7, 'tax_deferred': 0.2, 'tax_free': 0.1},
            'bonds': {'taxable': 0.5, 'tax_deferred': 0.4, 'tax_free': 0.1},
            'real_estate': {'taxable': 0.8, 'tax_deferred': 0.1, 'tax_free': 0.1}
        }

    engine = TaxEngine()
    return engine.apply_taxes({
        'scenarios': scenarios_df,
        'tax_config': tax_config,
        'investment_allocation': allocation
    })
