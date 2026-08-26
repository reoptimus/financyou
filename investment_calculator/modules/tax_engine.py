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
    },

    'account_balances': {
        'taxable': pd.DataFrame,      # After-tax balances by scenario and time
        'tax_deferred': pd.DataFrame,
        'tax_free': pd.DataFrame,
        'total': pd.DataFrame         # Total across all accounts
    },

    'optimization_insights': {
        'tax_loss_harvesting_opportunities': list,
        'optimal_withdrawal_sequence': list,  # Which account to draw from first
        'roth_conversion_analysis': dict      # Tax-deferred to tax-free conversion
    }
}
"""

import copy
import json
import logging
import time
import warnings
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd

# Journalisation : logger nommé d'après le module, il hérite donc de la
# configuration posée par investment_calculator.logging_config.configure_logging().
logger = logging.getLogger(__name__)


class AccountType(Enum):
    """Types of investment accounts"""
    TAXABLE = "taxable"
    TAX_DEFERRED = "tax_deferred"
    TAX_FREE = "tax_free"


class TaxJurisdiction(Enum):
    """Supported tax jurisdictions"""
    US = "US"
    FR = "FR"
    UK = "UK"
    DE = "DE"
    CA = "CA"


@dataclass
class TaxConfigPreset:
    """
    Accès aux anciennes configurations fiscales par juridiction.

    .. deprecated::
        Cette classe ne survit que le temps de la transition. Les valeurs
        qu'elle sert proviennent désormais de
        ``investment_calculator/tax_regimes/_legacy_presets.json``, un fichier
        gelé qui reproduit à l'identique le dictionnaire autrefois codé en dur
        ici — erreurs comprises, notamment le double comptage du prélèvement
        forfaitaire et des prélèvements sociaux en France.

        Le contrat cible est :mod:`investment_calculator.tax_regime` : la
        fiscalité est une donnée d'entrée, décrite par pays et par millésime
        dans ``tax_regimes/*.json`` et validée par ``tax_regimes/schema.json``.
        Voir ``docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md``.

        Cette classe et son fichier de données disparaissent à la fin de
        l'étape 1.A, lorsque le moteur consommera directement les régimes.
    """

    #: Emplacement des valeurs héritées, gelées hors du code.
    LEGACY_DATA_PATH: ClassVar[Path] = (
        Path(__file__).resolve().parent.parent / "tax_regimes" / "_legacy_presets.json"
    )

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_legacy_presets() -> dict[str, dict[str, Any]]:
        """Lire une fois pour toutes le fichier de valeurs héritées."""
        path = TaxConfigPreset.LEGACY_DATA_PATH
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise FileNotFoundError(
                f"Fichier de configurations fiscales héritées introuvable : {path}. "
                f"Il fait partie des données du paquet et doit être installé avec lui."
            ) from exc

        # `json.loads` renvoie Any : on annote la variable intermédiaire pour que
        # le type de retour soit vérifié plutôt que propagé en Any.
        presets: dict[str, dict[str, Any]] = raw["presets"]
        # L'infini n'est pas représentable en JSON strict : il est stocké à null
        # et restauré ici, pour que le comportement reste celui de l'ancien code.
        for preset in presets.values():
            tax_free = preset.get("account_types", {}).get("tax_free", {})
            if tax_free.get("contribution_limit", 0) is None:
                tax_free["contribution_limit"] = float("inf")
        return presets

    @staticmethod
    def get_preset(jurisdiction: str) -> dict:
        """
        Configuration fiscale héritée pour une juridiction.

        .. deprecated::
            Utilisez :func:`investment_calculator.tax_regime.load_regime`.

        Args:
            jurisdiction: code pays, par exemple ``"FR"``.

        Returns:
            Le dictionnaire de configuration, dans sa forme historique.

        Raises:
            ValueError: la juridiction n'a pas de configuration héritée.
        """
        warnings.warn(
            "TaxConfigPreset.get_preset est obsolète : la fiscalité est une donnée "
            "d'entrée du modèle. Utilisez investment_calculator.tax_regime.load_regime, "
            "qui charge un régime validé par pays et par millésime.",
            DeprecationWarning,
            stacklevel=2,
        )
        presets = TaxConfigPreset._load_legacy_presets()
        if jurisdiction not in presets:
            raise ValueError(
                f"Unknown jurisdiction: {jurisdiction}. Supported: {list(presets.keys())}"
            )
        return copy.deepcopy(presets[jurisdiction])


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
        >>> tax_config = tax_engine.TaxConfigPreset.get_preset('US')
        >>> allocation = {'stocks': {'taxable': 0.6, 'tax_deferred': 0.3, 'tax_free': 0.1}}
        >>> results = tax_eng.apply_taxes({
        ...     'scenarios': scenarios['scenarios'],
        ...     'tax_config': tax_config,
        ...     'investment_allocation': allocation
        ... })
    """

    def __init__(self) -> None:
        """Initialize the Tax Engine."""
        pass

    def apply_taxes(self, config: dict) -> dict:
        """
        Apply tax treatment to economic scenarios.

        Args:
            config: Configuration dictionary (see module docstring)

        Returns:
            Dictionary with after-tax scenarios, tax tables, account balances, insights
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
        after_tax_scenarios = self._calculate_after_tax_scenarios(
            scenarios_df, tax_config, allocation
        )

        # Calculate tax tables
        tax_tables = self._calculate_tax_tables(
            scenarios_df, after_tax_scenarios, tax_config, allocation
        )

        # Simulate account balances
        account_balances = self._simulate_account_balances(
            after_tax_scenarios, allocation, tax_config
        )

        # Generate optimization insights
        insights = self._generate_optimization_insights(
            tax_tables, account_balances, tax_config
        )

        logger.info(
            "Fin de l'application du régime fiscal en %.3f s : %d lignes après impôt",
            time.perf_counter() - start_time,
            len(after_tax_scenarios),
        )

        return {
            'after_tax_scenarios': after_tax_scenarios,
            'tax_tables': tax_tables,
            'account_balances': account_balances,
            'optimization_insights': insights
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
            # Use default US configuration
            config['tax_config'] = TaxConfigPreset.get_preset('US')

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
        allocation: dict
    ) -> pd.DataFrame:
        """
        Calculate after-tax returns for all scenarios.

        Args:
            scenarios_df: Economic scenarios from Module 1
            tax_config: Tax configuration
            allocation: Asset allocation across account types

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
        dividend_yield = 0.02
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

        # Taxable: rental income (40%) + appreciation (60%)
        rental_portion = 0.4
        appreciation_portion = 0.6
        rental_tax = taxable_config['income_tax_rate'] + social_charges
        appreciation_tax = taxable_config['capital_gains_rate'] * 0.2  # Only 20% realized annually

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
        # Annual tax by account type
        annual_tax_list = []

        for scenario_id in pre_tax_df['scenario_id'].unique():
            scenario_pre = pre_tax_df[pre_tax_df['scenario_id'] == scenario_id]
            scenario_post = after_tax_df[after_tax_df['scenario_id'] == scenario_id]

            for idx, row_pre in scenario_pre.iterrows():
                row_post = scenario_post.iloc[idx - scenario_pre.index[0]]

                # Calculate tax per asset class
                stock_tax = (row_pre['stock_return'] - row_post['stock_return_after_tax'])
                bond_tax = (row_pre['bond_return'] - row_post['bond_return_after_tax'])
                re_tax = (row_pre['real_estate_return'] - row_post['real_estate_return_after_tax'])

                annual_tax_list.append({
                    'scenario_id': scenario_id,
                    'time_period': row_pre['time_period'],
                    'stock_tax': stock_tax,
                    'bond_tax': bond_tax,
                    'real_estate_tax': re_tax,
                    'total_tax': stock_tax + bond_tax + re_tax
                })

        annual_tax_df = pd.DataFrame(annual_tax_list)

        # Cumulative tax
        cumulative_tax_df = annual_tax_df.copy()
        cumulative_tax_df['cumulative_total_tax'] = (
            cumulative_tax_df.groupby('scenario_id')['total_tax'].cumsum()
        )

        # Tax drag (percentage)
        tax_drag_df = annual_tax_df.copy()
        total_return = (
            pre_tax_df['stock_return'] +
            pre_tax_df['bond_return'] +
            pre_tax_df['real_estate_return']
        ).reset_index(drop=True)

        tax_drag_df['tax_drag_pct'] = (
            tax_drag_df['total_tax'] / total_return.clip(lower=0.001)
        ) * 100

        # Effective tax rate per scenario
        effective_rates = []
        for scenario_id in pre_tax_df['scenario_id'].unique():
            scenario_pre = pre_tax_df[pre_tax_df['scenario_id'] == scenario_id]
            scenario_post = after_tax_df[after_tax_df['scenario_id'] == scenario_id]

            total_pre_tax = (
                scenario_pre['stock_return'].sum() +
                scenario_pre['bond_return'].sum() +
                scenario_pre['real_estate_return'].sum()
            )

            total_after_tax = (
                scenario_post['stock_return_after_tax'].sum() +
                scenario_post['bond_return_after_tax'].sum() +
                scenario_post['real_estate_return_after_tax'].sum()
            )

            if total_pre_tax > 0:
                effective_rate = (total_pre_tax - total_after_tax) / total_pre_tax
            else:
                effective_rate = 0.0

            effective_rates.append({
                'scenario_id': scenario_id,
                'effective_tax_rate': effective_rate,
                'total_pre_tax_return': total_pre_tax,
                'total_after_tax_return': total_after_tax,
                'total_taxes_paid': total_pre_tax - total_after_tax
            })

        effective_rate_df = pd.DataFrame(effective_rates)

        return {
            'annual_tax_by_account': annual_tax_df,
            'cumulative_tax': cumulative_tax_df,
            'tax_drag': tax_drag_df,
            'effective_tax_rate': effective_rate_df
        }

    def _simulate_account_balances(
        self,
        after_tax_df: pd.DataFrame,
        allocation: dict,
        tax_config: dict
    ) -> dict[str, pd.DataFrame]:
        """
        Simulate account balances over time.

        Args:
            after_tax_df: After-tax scenarios
            allocation: Asset allocation
            tax_config: Tax configuration

        Returns:
            Dictionary of balance DataFrames by account type
        """
        # For now, return placeholder
        # In full implementation, this would simulate actual account growth

        scenarios = after_tax_df['scenario_id'].unique()
        time_periods = sorted(after_tax_df['time_period'].unique())

        # Placeholder balances (would be calculated based on contributions, returns, etc.)
        taxable_balances = pd.DataFrame({
            'scenario_id': scenarios,
            **{f"t_{int(t)}": 0.0 for t in time_periods}
        })

        tax_deferred_balances = taxable_balances.copy()
        tax_free_balances = taxable_balances.copy()

        total_balances = taxable_balances.copy()

        return {
            'taxable': taxable_balances,
            'tax_deferred': tax_deferred_balances,
            'tax_free': tax_free_balances,
            'total': total_balances
        }

    def _generate_optimization_insights(
        self,
        tax_tables: dict,
        account_balances: dict,
        tax_config: dict
    ) -> dict:
        """
        Generate tax optimization insights.

        Args:
            tax_tables: Tax tables
            account_balances: Account balances
            tax_config: Tax configuration

        Returns:
            Dictionary of optimization insights
        """
        # Tax loss harvesting opportunities
        # (simplified - would analyze negative returns)
        tlh_opportunities: list = []

        # Optimal withdrawal sequence
        # Rule: withdraw from taxable first, then tax-deferred, then tax-free
        withdrawal_sequence = [
            {'rank': 1, 'account_type': 'taxable', 'reason': 'Lowest tax cost, no penalties'},
            {'rank': 2, 'account_type': 'tax_deferred', 'reason': 'Ordinary income tax only'},
            {'rank': 3, 'account_type': 'tax_free', 'reason': 'Preserve tax-free growth longest'}
        ]

        # Roth conversion analysis
        roth_conversion = {
            'recommended': False,
            'reason': 'Requires detailed income projection',
            'optimal_years': []
        }

        return {
            'tax_loss_harvesting_opportunities': tlh_opportunities,
            'optimal_withdrawal_sequence': withdrawal_sequence,
            'roth_conversion_analysis': roth_conversion
        }


# Convenience functions
def apply_taxes_simple(
    scenarios_df: pd.DataFrame,
    jurisdiction: str = 'US',
    allocation: dict | None = None
) -> dict:
    """
    Apply taxes with simple configuration.

    Args:
        scenarios_df: Scenarios DataFrame from Module 1
        jurisdiction: Tax jurisdiction ('US', 'FR', 'UK', etc.)
        allocation: Asset allocation (optional)

    Returns:
        Tax results dictionary

    Example:
        >>> results = apply_taxes_simple(scenarios_df, jurisdiction='FR')
    """
    tax_config = TaxConfigPreset.get_preset(jurisdiction)

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
