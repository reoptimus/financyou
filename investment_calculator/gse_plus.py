"""
GSE+ (Tax-Integrated Scenario Engine)

Extends GSE economic scenarios with tax calculations to provide after-tax
investment returns. Includes:
- Income tax calculations
- Capital gains tax
- Dividend tax
- Tax-advantaged account handling
- Country-specific tax rules
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

from .gse import EconomicScenario, GlobalScenarioEngine


class AccountType(Enum):
    """Types of investment accounts"""
    TAXABLE = "taxable"
    TAX_DEFERRED = "tax_deferred"  # e.g., Traditional IRA, 401k
    TAX_FREE = "tax_free"  # e.g., Roth IRA
    TAX_ADVANTAGED_EDUCATION = "tax_advantaged_education"  # e.g., 529 plan


class TaxTreatment(Enum):
    """Tax treatment for different income types"""
    ORDINARY_INCOME = "ordinary_income"
    LONG_TERM_CAPITAL_GAINS = "long_term_capital_gains"
    SHORT_TERM_CAPITAL_GAINS = "short_term_capital_gains"
    QUALIFIED_DIVIDENDS = "qualified_dividends"
    NON_QUALIFIED_DIVIDENDS = "non_qualified_dividends"


@dataclass
class TaxConfig:
    """
    Tax configuration for different jurisdictions and scenarios.

    Attributes:
        country_code (str): Country code (e.g., "US", "FR", "UK")
        ordinary_income_rate (float): Marginal tax rate for ordinary income
        long_term_cap_gains_rate (float): Long-term capital gains tax rate
        short_term_cap_gains_rate (float): Short-term capital gains tax rate (usually = ordinary)
        qualified_dividend_rate (float): Tax rate on qualified dividends
        non_qualified_dividend_rate (float): Tax rate on non-qualified dividends
        state_tax_rate (float): State/local tax rate
        social_security_rate (float): Social security/payroll tax rate
        medicare_rate (float): Medicare tax rate
        wealth_tax_rate (float): Wealth/net worth tax rate (if applicable)
        tax_deferred_withdrawal_rate (float): Tax rate on tax-deferred withdrawals
        early_withdrawal_penalty (float): Penalty for early withdrawal from retirement accounts
        standard_deduction (float): Standard deduction amount
    """

    country_code: str = "US"
    ordinary_income_rate: float = 0.25
    long_term_cap_gains_rate: float = 0.15
    short_term_cap_gains_rate: Optional[float] = None
    qualified_dividend_rate: float = 0.15
    non_qualified_dividend_rate: Optional[float] = None
    state_tax_rate: float = 0.05
    social_security_rate: float = 0.062
    medicare_rate: float = 0.0145
    wealth_tax_rate: float = 0.0
    tax_deferred_withdrawal_rate: Optional[float] = None
    early_withdrawal_penalty: float = 0.10
    standard_deduction: float = 13850.0  # US 2023 single filer

    def __post_init__(self):
        """Set default values for unspecified rates"""
        if self.short_term_cap_gains_rate is None:
            self.short_term_cap_gains_rate = self.ordinary_income_rate

        if self.non_qualified_dividend_rate is None:
            self.non_qualified_dividend_rate = self.ordinary_income_rate

        if self.tax_deferred_withdrawal_rate is None:
            self.tax_deferred_withdrawal_rate = self.ordinary_income_rate

    @property
    def total_payroll_tax_rate(self) -> float:
        """Calculate total payroll tax rate"""
        return self.social_security_rate + self.medicare_rate

    @property
    def effective_ordinary_rate(self) -> float:
        """Calculate effective rate including state taxes"""
        return self.ordinary_income_rate + self.state_tax_rate

    @property
    def effective_ltcg_rate(self) -> float:
        """Calculate effective long-term capital gains rate including state"""
        return self.long_term_cap_gains_rate + self.state_tax_rate


@dataclass
class TaxIntegratedScenario:
    """
    Economic scenario with tax calculations applied.

    Attributes:
        base_scenario (EconomicScenario): Underlying economic scenario
        tax_config (TaxConfig): Tax configuration
        account_type (AccountType): Type of investment account
        after_tax_stock_returns (np.ndarray): Stock returns after taxes
        after_tax_bond_returns (np.ndarray): Bond returns after taxes
        after_tax_real_estate_returns (np.ndarray): Real estate returns after taxes
        tax_drag (np.ndarray): Annual tax drag (difference between pre-tax and after-tax)
        cumulative_taxes_paid (np.ndarray): Cumulative taxes paid over time
    """

    base_scenario: EconomicScenario
    tax_config: TaxConfig
    account_type: AccountType
    after_tax_stock_returns: np.ndarray = field(init=False)
    after_tax_bond_returns: np.ndarray = field(init=False)
    after_tax_real_estate_returns: np.ndarray = field(init=False)
    tax_drag: np.ndarray = field(init=False)
    cumulative_taxes_paid: np.ndarray = field(init=False)

    def __post_init__(self):
        """Calculate after-tax returns based on account type and tax config"""
        self._calculate_after_tax_returns()

    def _calculate_after_tax_returns(self):
        """Calculate after-tax returns for each asset class"""
        years = self.base_scenario.years

        if self.account_type == AccountType.TAX_FREE:
            # Roth IRA - no taxes on gains
            self.after_tax_stock_returns = self.base_scenario.stock_returns.copy()
            self.after_tax_bond_returns = self.base_scenario.bond_returns.copy()
            self.after_tax_real_estate_returns = self.base_scenario.real_estate_returns.copy()
            self.tax_drag = np.zeros(years)

        elif self.account_type == AccountType.TAX_DEFERRED:
            # Traditional IRA/401k - taxes paid on withdrawal, not annually
            # For annual calculations, we keep pre-tax returns but note tax liability
            self.after_tax_stock_returns = self.base_scenario.stock_returns.copy()
            self.after_tax_bond_returns = self.base_scenario.bond_returns.copy()
            self.after_tax_real_estate_returns = self.base_scenario.real_estate_returns.copy()
            self.tax_drag = np.zeros(years)  # Tax paid later

        else:  # TAXABLE account
            # Stocks: combination of dividends (2% yield) and capital gains
            dividend_yield = 0.02
            dividend_tax = self.tax_config.qualified_dividend_rate
            ltcg_tax = self.tax_config.effective_ltcg_rate

            # Assume dividends taxed annually, capital gains deferred
            # Simplified: annual tax on dividends only
            stock_dividend_drag = dividend_yield * dividend_tax
            self.after_tax_stock_returns = self.base_scenario.stock_returns - stock_dividend_drag

            # Bonds: interest taxed as ordinary income
            bond_tax = self.tax_config.effective_ordinary_rate
            self.after_tax_bond_returns = self.base_scenario.bond_returns * (1 - bond_tax)

            # Real estate: rental income + appreciation, taxed as ordinary and LTCG
            # Simplified: 40% of return is rental income (ordinary), 60% is appreciation (LTCG)
            rental_portion = 0.4
            appreciation_portion = 0.6
            rental_tax = self.tax_config.effective_ordinary_rate
            appreciation_tax = self.tax_config.effective_ltcg_rate * 0.2  # Only realized portion

            real_estate_drag = (
                self.base_scenario.real_estate_returns * rental_portion * rental_tax
                + self.base_scenario.real_estate_returns * appreciation_portion * appreciation_tax
            )
            self.after_tax_real_estate_returns = self.base_scenario.real_estate_returns - real_estate_drag

            # Calculate total tax drag
            self.tax_drag = np.array([
                stock_dividend_drag
                + (self.base_scenario.bond_returns[i] * bond_tax)
                + real_estate_drag[i]
                for i in range(years)
            ])

        # Calculate cumulative taxes
        self.cumulative_taxes_paid = np.cumsum(self.tax_drag)

    def calculate_withdrawal_tax(
        self,
        withdrawal_amount: float,
        is_qualified_withdrawal: bool = True,
    ) -> float:
        """
        Calculate tax on withdrawal from the account.

        Args:
            withdrawal_amount (float): Amount to withdraw
            is_qualified_withdrawal (bool): Whether withdrawal is qualified (no penalty)

        Returns:
            float: Total tax on withdrawal
        """
        if self.account_type == AccountType.TAX_FREE:
            # Roth IRA - qualified withdrawals are tax-free
            return 0.0 if is_qualified_withdrawal else withdrawal_amount * self.tax_config.early_withdrawal_penalty

        elif self.account_type == AccountType.TAX_DEFERRED:
            # Traditional IRA - pay ordinary income tax
            tax = withdrawal_amount * self.tax_config.tax_deferred_withdrawal_rate
            if not is_qualified_withdrawal:
                tax += withdrawal_amount * self.tax_config.early_withdrawal_penalty
            return tax

        else:  # TAXABLE
            # For taxable accounts, assume withdrawal is from gains (LTCG)
            tax = withdrawal_amount * self.tax_config.effective_ltcg_rate
            return tax

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert tax-integrated scenario to DataFrame.

        Returns:
            pd.DataFrame: Scenario data with both pre-tax and after-tax returns
        """
        df = self.base_scenario.to_dataframe()

        # Add after-tax columns
        df["after_tax_stock_return"] = self.after_tax_stock_returns
        df["after_tax_bond_return"] = self.after_tax_bond_returns
        df["after_tax_real_estate_return"] = self.after_tax_real_estate_returns
        df["tax_drag"] = self.tax_drag
        df["cumulative_taxes"] = self.cumulative_taxes_paid

        return df

    def get_effective_tax_rate(self) -> float:
        """
        Calculate the effective tax rate across all returns.

        Returns:
            float: Effective tax rate
        """
        total_pre_tax_return = (
            np.sum(self.base_scenario.stock_returns)
            + np.sum(self.base_scenario.bond_returns)
            + np.sum(self.base_scenario.real_estate_returns)
        )

        total_after_tax_return = (
            np.sum(self.after_tax_stock_returns)
            + np.sum(self.after_tax_bond_returns)
            + np.sum(self.after_tax_real_estate_returns)
        )

        if total_pre_tax_return == 0:
            return 0.0

        return (total_pre_tax_return - total_after_tax_return) / total_pre_tax_return


class TaxIntegratedScenarioEngine:
    """
    GSE+ (Tax-Integrated Scenario Engine)

    Wraps the Global Scenario Engine and applies tax calculations to all scenarios.
    """

    def __init__(
        self,
        tax_config: TaxConfig,
        gse: Optional[GlobalScenarioEngine] = None,
    ):
        """
        Initialize the Tax-Integrated Scenario Engine.

        Args:
            tax_config (TaxConfig): Tax configuration to apply
            gse (Optional[GlobalScenarioEngine]): Underlying GSE (creates new if not provided)
        """
        self.tax_config = tax_config
        self.gse = gse if gse is not None else GlobalScenarioEngine()

    def generate_tax_integrated_scenario(
        self,
        scenario: EconomicScenario,
        account_type: AccountType,
    ) -> TaxIntegratedScenario:
        """
        Apply tax calculations to an economic scenario.

        Args:
            scenario (EconomicScenario): Base economic scenario
            account_type (AccountType): Type of investment account

        Returns:
            TaxIntegratedScenario: Scenario with tax calculations applied
        """
        return TaxIntegratedScenario(
            base_scenario=scenario,
            tax_config=self.tax_config,
            account_type=account_type,
        )

    def generate_all_account_scenarios(
        self,
        years: int,
        scenario_type: str = "baseline",
    ) -> Dict[AccountType, TaxIntegratedScenario]:
        """
        Generate scenarios for all account types.

        Args:
            years (int): Number of years to simulate
            scenario_type (str): Type of scenario ("baseline", "optimistic", "pessimistic")

        Returns:
            Dict[AccountType, TaxIntegratedScenario]: Scenarios for each account type
        """
        # Generate base scenario
        if scenario_type == "optimistic":
            base = self.gse.generate_optimistic_scenario(years)
        elif scenario_type == "pessimistic":
            base = self.gse.generate_pessimistic_scenario(years)
        else:
            base = self.gse.generate_baseline_scenario(years)

        # Create tax-integrated scenarios for each account type
        return {
            AccountType.TAXABLE: self.generate_tax_integrated_scenario(base, AccountType.TAXABLE),
            AccountType.TAX_DEFERRED: self.generate_tax_integrated_scenario(base, AccountType.TAX_DEFERRED),
            AccountType.TAX_FREE: self.generate_tax_integrated_scenario(base, AccountType.TAX_FREE),
        }

    def compare_account_types(
        self,
        years: int,
        initial_investment: float,
        annual_contribution: float = 0.0,
        asset_allocation: Optional[Dict[str, float]] = None,
    ) -> pd.DataFrame:
        """
        Compare investment growth across different account types.

        Args:
            years (int): Number of years to simulate
            initial_investment (float): Initial investment amount
            annual_contribution (float): Annual contribution
            asset_allocation (Optional[Dict]): Asset allocation (stocks, bonds, real_estate)

        Returns:
            pd.DataFrame: Comparison of account types
        """
        if asset_allocation is None:
            asset_allocation = {"stocks": 0.7, "bonds": 0.25, "real_estate": 0.05}

        scenarios = self.generate_all_account_scenarios(years)

        results = []
        for account_type, scenario in scenarios.items():
            # Simulate portfolio growth
            balance = initial_investment
            total_contributions = initial_investment
            balances = []

            for year in range(years):
                # Calculate weighted return
                weighted_return = (
                    asset_allocation["stocks"] * scenario.after_tax_stock_returns[year]
                    + asset_allocation["bonds"] * scenario.after_tax_bond_returns[year]
                    + asset_allocation["real_estate"] * scenario.after_tax_real_estate_returns[year]
                )

                # Apply return
                balance *= (1 + weighted_return)

                # Add annual contribution
                balance += annual_contribution
                total_contributions += annual_contribution

                balances.append(balance)

            final_balance = balances[-1]
            total_gains = final_balance - total_contributions

            # Calculate withdrawal tax
            withdrawal_tax = scenario.calculate_withdrawal_tax(final_balance, is_qualified_withdrawal=True)
            after_tax_balance = final_balance - withdrawal_tax

            results.append({
                "account_type": account_type.value,
                "final_balance": final_balance,
                "after_withdrawal_tax": after_tax_balance,
                "total_contributions": total_contributions,
                "total_gains": total_gains,
                "effective_tax_rate": scenario.get_effective_tax_rate(),
                "cumulative_taxes_paid": scenario.cumulative_taxes_paid[-1],
                "withdrawal_tax": withdrawal_tax,
                "net_benefit": after_tax_balance - total_contributions,
            })

        return pd.DataFrame(results)
