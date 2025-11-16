"""
Personal Variables Module

Defines personal investor characteristics and investment profiles used for
calculating optimal investment strategies.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum


class RiskTolerance(Enum):
    """Risk tolerance levels for investors"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    VERY_AGGRESSIVE = "very_aggressive"


class InvestmentGoal(Enum):
    """Common investment goals"""
    RETIREMENT = "retirement"
    WEALTH_BUILDING = "wealth_building"
    INCOME_GENERATION = "income_generation"
    CAPITAL_PRESERVATION = "capital_preservation"
    EDUCATION = "education"
    HOME_PURCHASE = "home_purchase"


@dataclass
class PersonalVariables:
    """
    Personal variables that influence investment decisions.

    Attributes:
        age (int): Current age of the investor
        annual_income (float): Annual gross income before taxes
        current_savings (float): Current investment savings/portfolio value
        monthly_contribution (float): Monthly amount available for investment
        risk_tolerance (RiskTolerance): Risk tolerance level
        investment_horizon (int): Investment time horizon in years
        tax_bracket (float): Marginal tax bracket (e.g., 0.25 for 25%)
        capital_gains_rate (float): Capital gains tax rate (e.g., 0.15 for 15%)
        country_code (str): Country code for tax calculations (e.g., "US", "FR", "UK")
        has_tax_advantaged_account (bool): Whether investor has tax-advantaged accounts
        emergency_fund_months (int): Months of expenses in emergency fund
        debt_to_income_ratio (float): Ratio of debt to income
        existing_portfolio (Optional[Dict[str, float]]): Current portfolio allocation
    """

    age: int
    annual_income: float
    current_savings: float = 0.0
    monthly_contribution: float = 0.0
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    investment_horizon: int = 30
    tax_bracket: float = 0.25
    capital_gains_rate: float = 0.15
    country_code: str = "US"
    has_tax_advantaged_account: bool = False
    emergency_fund_months: int = 6
    debt_to_income_ratio: float = 0.0
    existing_portfolio: Optional[Dict[str, float]] = None

    def __post_init__(self):
        """Validate personal variables after initialization"""
        if self.age < 18 or self.age > 100:
            raise ValueError("Age must be between 18 and 100")

        if self.annual_income < 0:
            raise ValueError("Annual income cannot be negative")

        if self.current_savings < 0:
            raise ValueError("Current savings cannot be negative")

        if self.monthly_contribution < 0:
            raise ValueError("Monthly contribution cannot be negative")

        if self.investment_horizon < 1:
            raise ValueError("Investment horizon must be at least 1 year")

        if not 0 <= self.tax_bracket <= 1:
            raise ValueError("Tax bracket must be between 0 and 1")

        if not 0 <= self.capital_gains_rate <= 1:
            raise ValueError("Capital gains rate must be between 0 and 1")

        if self.debt_to_income_ratio < 0:
            raise ValueError("Debt to income ratio cannot be negative")

    @property
    def retirement_age(self) -> int:
        """Calculate suggested retirement age (default 65)"""
        return 65

    @property
    def years_to_retirement(self) -> int:
        """Calculate years until retirement"""
        return max(0, self.retirement_age - self.age)

    @property
    def total_expected_contributions(self) -> float:
        """Calculate total expected contributions over investment horizon"""
        return self.monthly_contribution * 12 * self.investment_horizon

    def get_risk_score(self) -> float:
        """
        Calculate a numerical risk score (0-100) based on risk tolerance and other factors.

        Returns:
            float: Risk score from 0 (conservative) to 100 (very aggressive)
        """
        # Base score from risk tolerance
        risk_scores = {
            RiskTolerance.CONSERVATIVE: 20,
            RiskTolerance.MODERATE: 40,
            RiskTolerance.BALANCED: 60,
            RiskTolerance.AGGRESSIVE: 80,
            RiskTolerance.VERY_AGGRESSIVE: 100,
        }
        base_score = risk_scores[self.risk_tolerance]

        # Adjust based on investment horizon (longer = can take more risk)
        horizon_adjustment = min(20, self.investment_horizon / 2)

        # Adjust based on age (younger = can take more risk)
        age_adjustment = max(-20, (40 - self.age) / 2)

        # Adjust based on debt (higher debt = less risk)
        debt_adjustment = -self.debt_to_income_ratio * 10

        final_score = base_score + horizon_adjustment + age_adjustment + debt_adjustment
        return max(0, min(100, final_score))


@dataclass
class InvestmentProfile:
    """
    Complete investment profile combining personal variables with investment goals.

    Attributes:
        personal_vars (PersonalVariables): Personal financial variables
        primary_goal (InvestmentGoal): Primary investment goal
        secondary_goals (List[InvestmentGoal]): Secondary investment goals
        target_retirement_income (Optional[float]): Desired annual retirement income
        custom_constraints (Dict): Custom constraints for optimization
    """

    personal_vars: PersonalVariables
    primary_goal: InvestmentGoal = InvestmentGoal.WEALTH_BUILDING
    secondary_goals: List[InvestmentGoal] = field(default_factory=list)
    target_retirement_income: Optional[float] = None
    custom_constraints: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Set default target retirement income if not provided"""
        if self.target_retirement_income is None:
            # Default to 80% of final working income
            self.target_retirement_income = self.personal_vars.annual_income * 0.8

    def get_recommended_asset_allocation(self) -> Dict[str, float]:
        """
        Get recommended asset allocation based on profile.

        Returns a suggested allocation across major asset classes based on
        risk tolerance, age, and investment horizon.

        Returns:
            Dict[str, float]: Asset allocation percentages (sum to 1.0)
        """
        risk_score = self.personal_vars.get_risk_score()

        # Calculate stock/bond allocation using risk score
        # Higher risk score = more stocks
        stocks = risk_score / 100
        bonds = 1 - stocks

        # Further breakdown
        allocation = {
            "domestic_stocks": stocks * 0.6,
            "international_stocks": stocks * 0.3,
            "emerging_markets": stocks * 0.1,
            "government_bonds": bonds * 0.5,
            "corporate_bonds": bonds * 0.3,
            "real_estate": bonds * 0.15,
            "cash": bonds * 0.05,
        }

        return allocation

    def is_ready_to_invest(self) -> tuple[bool, List[str]]:
        """
        Check if investor is ready to invest based on financial health.

        Returns:
            tuple[bool, List[str]]: (ready status, list of warnings/recommendations)
        """
        warnings = []

        # Check emergency fund
        if self.personal_vars.emergency_fund_months < 3:
            warnings.append(
                f"Emergency fund only covers {self.personal_vars.emergency_fund_months} months. "
                "Recommended: 3-6 months of expenses."
            )

        # Check debt
        if self.personal_vars.debt_to_income_ratio > 0.4:
            warnings.append(
                f"High debt-to-income ratio: {self.personal_vars.debt_to_income_ratio:.1%}. "
                "Consider paying down high-interest debt first."
            )

        # Check if any contribution available
        if self.personal_vars.current_savings == 0 and self.personal_vars.monthly_contribution == 0:
            warnings.append(
                "No current savings or monthly contribution specified. "
                "Investment analysis may not be meaningful."
            )

        is_ready = len(warnings) == 0 or (
            self.personal_vars.emergency_fund_months >= 3 and
            self.personal_vars.debt_to_income_ratio <= 0.4
        )

        return is_ready, warnings

    def summary(self) -> str:
        """Generate a summary of the investment profile"""
        pv = self.personal_vars
        ready, warnings = self.is_ready_to_invest()

        summary_text = f"""
Investment Profile Summary
{'=' * 50}
Personal Information:
  Age: {pv.age}
  Investment Horizon: {pv.investment_horizon} years
  Years to Retirement: {pv.years_to_retirement} years
  Risk Tolerance: {pv.risk_tolerance.value}
  Risk Score: {pv.get_risk_score():.1f}/100

Financial Situation:
  Annual Income: ${pv.annual_income:,.2f}
  Current Savings: ${pv.current_savings:,.2f}
  Monthly Contribution: ${pv.monthly_contribution:,.2f}
  Tax Bracket: {pv.tax_bracket:.1%}
  Capital Gains Rate: {pv.capital_gains_rate:.1%}

Goals:
  Primary Goal: {self.primary_goal.value}
  Target Retirement Income: ${self.target_retirement_income:,.2f}/year

Investment Readiness: {'✓ Ready' if ready else '⚠ Review Needed'}
"""

        if warnings:
            summary_text += "\nWarnings/Recommendations:\n"
            for i, warning in enumerate(warnings, 1):
                summary_text += f"  {i}. {warning}\n"

        return summary_text
