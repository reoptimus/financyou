"""
Module 3: User Input & Investment Time Series

This module captures user profile from web UI, validates inputs, and creates
time-series investment plans with slicing capabilities.

INPUT STRUCTURE:
{
    'user_profile': {
        'personal_info': {
            'age': int,
            'retirement_age': int,
            'life_expectancy': int,
            'country': str,
            'currency': str
        },
        'financial_situation': {
            'current_savings': float,
            'annual_income': float,
            'annual_expenses': float,
            'debt': {
                'mortgage': float,
                'student_loans': float,
                'other': float
            }
        },
        'investment_preferences': {
            'risk_tolerance': str,      # 'conservative', 'moderate', 'aggressive'
            'investment_goal': str,     # 'retirement', 'wealth', 'income', 'education'
            'time_horizon': int,        # Years
            'esg_preferences': bool,    # Environmental/Social/Governance
            'liquidity_needs': float    # % of portfolio needed liquid
        },
        'constraints': {
            'max_equity_allocation': float,
            'min_bond_allocation': float,
            'exclude_sectors': list,
            'rebalancing_frequency': str
        }
    },
    'contribution_schedule': [
        {
            'start_year': int,
            'end_year': int,
            'monthly_amount': float,
            'annual_increase': float,
            'account_type': str
        }
    ],
    'withdrawal_schedule': [
        {
            'year': int,
            'amount': float,
            'purpose': str,
            'account_preference': str
        }
    ]
}

OUTPUT STRUCTURE:
{
    'validated_profile': dict,
    'investment_time_series': pd.DataFrame,
    'life_stages': dict,
    'risk_profile': dict,
    'sliced_plans': dict,              # Domain-specific slicing
    'time_series_slicer': TimeSeriesSlicer,  # General-purpose time series slicing
    'validation_warnings': list,
    'summary_statistics': dict
}

SLICING CAPABILITIES:
This module provides two types of slicing:

1. DOMAIN-SPECIFIC SLICING (sliced_plans):
   - By life stage (accumulation, transition, distribution)
   - By goal/purpose (retirement, education, home purchase, etc.)
   - By account type (taxable, tax-deferred, tax-free)

2. GENERAL TIME SERIES SLICING (time_series_slicer):
   - By time range (start/end dates)
   - By index (row numbers)
   - By window (rolling/sliding windows)
   - By ratio (train/test splitting)
   - By value (filter by contribution/withdrawal amounts)

Both are available in the output for maximum flexibility.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Iterator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

# Import from existing modules
from investment_calculator.personal_variables import (
    PersonalVariables,
    InvestmentProfile,
    RiskTolerance,
    InvestmentGoal
)

# Import time series slicer for general-purpose slicing
from time_series_slicer import TimeSeriesSlicer


class LifeStage(Enum):
    """Life stages for financial planning"""
    ACCUMULATION = "accumulation"  # Working years, building wealth
    TRANSITION = "transition"      # Pre-retirement, 5-10 years before
    DISTRIBUTION = "distribution"  # Retirement, drawing down


class RebalancingFrequency(Enum):
    """Portfolio rebalancing frequency"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    THRESHOLD_BASED = "threshold_based"


class UserProfileManager:
    """
    User Input & Investment Time Series Manager - Module 3

    Processes user input, validates data, creates investment time series,
    and provides slicing capabilities.

    Example:
        >>> config = {
        ...     'user_profile': {
        ...         'personal_info': {'age': 35, 'retirement_age': 65, ...},
        ...         'financial_situation': {...},
        ...         'investment_preferences': {...}
        ...     },
        ...     'contribution_schedule': [...]
        ... }
        >>> manager = UserProfileManager()
        >>> result = manager.process(config)
        >>> time_series = result['investment_time_series']
    """

    def __init__(self):
        """Initialize the User Profile Manager."""
        pass

    def process(self, config: Dict) -> Dict:
        """
        Process user input and generate investment time series.

        Args:
            config: Configuration dictionary (see module docstring)

        Returns:
            Dictionary with validated profile, time series, risk profile, etc.
        """
        # Step 1: Validate user profile
        validated_profile, warnings = self._validate_profile(config['user_profile'])

        # Step 2: Create time series from contribution/withdrawal schedules
        contribution_schedule = config.get('contribution_schedule', [])
        withdrawal_schedule = config.get('withdrawal_schedule', [])

        investment_time_series = self._create_time_series(
            validated_profile,
            contribution_schedule,
            withdrawal_schedule
        )

        # Step 3: Identify life stages
        life_stages = self._identify_life_stages(validated_profile)

        # Step 4: Calculate risk profile and recommended allocation
        risk_profile = self._calculate_risk_profile(validated_profile, life_stages)

        # Step 5: Create sliced plans
        sliced_plans = self._create_sliced_plans(
            investment_time_series,
            life_stages,
            validated_profile
        )

        # Step 6: Calculate summary statistics
        summary_stats = self._calculate_summary_statistics(
            investment_time_series,
            validated_profile
        )

        # Step 7: Create general-purpose time series slicer
        # This provides additional slicing capabilities beyond domain-specific slicing
        time_series_slicer = TimeSeriesSlicer(
            investment_time_series,
            time_column='period'  # Use 'period' column for time-based operations
        )

        return {
            'validated_profile': validated_profile,
            'investment_time_series': investment_time_series,
            'life_stages': life_stages,
            'risk_profile': risk_profile,
            'sliced_plans': sliced_plans,
            'time_series_slicer': time_series_slicer,  # General-purpose slicing
            'validation_warnings': warnings,
            'summary_statistics': summary_stats
        }

    def _validate_profile(self, user_profile: Dict) -> Tuple[Dict, List[str]]:
        """
        Validate and sanitize user profile.

        Args:
            user_profile: User profile dictionary

        Returns:
            Tuple of (validated_profile, warnings)
        """
        warnings = []
        validated = {}

        # Personal info
        personal_info = user_profile.get('personal_info', {})
        age = personal_info.get('age', 30)
        retirement_age = personal_info.get('retirement_age', 65)
        life_expectancy = personal_info.get('life_expectancy', 90)

        if age < 18 or age > 100:
            warnings.append(f"Age {age} outside reasonable range [18, 100], using 30")
            age = 30

        if retirement_age <= age:
            warnings.append(f"Retirement age {retirement_age} must be > current age {age}, using age+30")
            retirement_age = age + 30

        if life_expectancy <= retirement_age:
            warnings.append(f"Life expectancy {life_expectancy} must be > retirement age, using retirement_age+25")
            life_expectancy = retirement_age + 25

        validated['personal_info'] = {
            'age': age,
            'retirement_age': retirement_age,
            'life_expectancy': life_expectancy,
            'country': personal_info.get('country', 'US'),
            'currency': personal_info.get('currency', 'USD')
        }

        # Financial situation
        financial = user_profile.get('financial_situation', {})
        current_savings = max(0, financial.get('current_savings', 0))
        annual_income = max(0, financial.get('annual_income', 50000))
        annual_expenses = max(0, financial.get('annual_expenses', annual_income * 0.7))

        debt = financial.get('debt', {})
        total_debt = (
            debt.get('mortgage', 0) +
            debt.get('student_loans', 0) +
            debt.get('other', 0)
        )

        debt_to_income = total_debt / annual_income if annual_income > 0 else 0

        if debt_to_income > 0.5:
            warnings.append(f"High debt-to-income ratio: {debt_to_income:.1%}. Consider debt reduction first.")

        validated['financial_situation'] = {
            'current_savings': current_savings,
            'annual_income': annual_income,
            'annual_expenses': annual_expenses,
            'debt': {
                'mortgage': debt.get('mortgage', 0),
                'student_loans': debt.get('student_loans', 0),
                'other': debt.get('other', 0),
                'total': total_debt
            },
            'debt_to_income_ratio': debt_to_income
        }

        # Investment preferences
        preferences = user_profile.get('investment_preferences', {})

        risk_tolerance_str = preferences.get('risk_tolerance', 'moderate').lower()
        if risk_tolerance_str not in ['conservative', 'moderate', 'aggressive']:
            warnings.append(f"Unknown risk tolerance '{risk_tolerance_str}', using 'moderate'")
            risk_tolerance_str = 'moderate'

        validated['investment_preferences'] = {
            'risk_tolerance': risk_tolerance_str,
            'investment_goal': preferences.get('investment_goal', 'retirement'),
            'time_horizon': preferences.get('time_horizon', retirement_age - age),
            'esg_preferences': preferences.get('esg_preferences', False),
            'liquidity_needs': min(1.0, max(0.0, preferences.get('liquidity_needs', 0.05)))
        }

        # Constraints
        constraints = user_profile.get('constraints', {})

        max_equity = constraints.get('max_equity_allocation', 1.0)
        min_bond = constraints.get('min_bond_allocation', 0.0)

        if max_equity + min_bond > 1.0:
            warnings.append("Max equity + min bond > 100%, adjusting constraints")
            max_equity = 0.8
            min_bond = 0.1

        validated['constraints'] = {
            'max_equity_allocation': max_equity,
            'min_bond_allocation': min_bond,
            'exclude_sectors': constraints.get('exclude_sectors', []),
            'rebalancing_frequency': constraints.get('rebalancing_frequency', 'annual')
        }

        return validated, warnings

    def _create_time_series(
        self,
        profile: Dict,
        contribution_schedule: List[Dict],
        withdrawal_schedule: List[Dict]
    ) -> pd.DataFrame:
        """
        Create investment time series from schedules.

        Args:
            profile: Validated profile
            contribution_schedule: List of contribution periods
            withdrawal_schedule: List of withdrawals

        Returns:
            DataFrame with investment time series
        """
        age = profile['personal_info']['age']
        life_expectancy = profile['personal_info']['life_expectancy']
        time_horizon = life_expectancy - age

        # Create year-by-year time series
        years = list(range(time_horizon + 1))
        investor_ages = [age + y for y in years]

        # Initialize arrays
        contributions = np.zeros(time_horizon + 1)
        withdrawals = np.zeros(time_horizon + 1)
        account_types = [''] * (time_horizon + 1)
        purposes = [''] * (time_horizon + 1)

        # Fill in contributions from schedule
        if not contribution_schedule:
            # Default: contribute during working years
            retirement_age = profile['personal_info']['retirement_age']
            annual_income = profile['financial_situation']['annual_income']
            annual_expenses = profile['financial_situation']['annual_expenses']
            annual_contribution = max(0, annual_income - annual_expenses) * 0.1  # Save 10% of surplus

            for year_idx in range(time_horizon + 1):
                current_age = age + year_idx
                if current_age < retirement_age:
                    contributions[year_idx] = annual_contribution
                    account_types[year_idx] = 'tax_deferred'
                    purposes[year_idx] = 'retirement'
        else:
            # Use provided schedule
            for schedule in contribution_schedule:
                start_year = schedule.get('start_year', 0)
                end_year = schedule.get('end_year', time_horizon)
                monthly_amount = schedule.get('monthly_amount', 0)
                annual_increase = schedule.get('annual_increase', 0.02)  # 2% default
                account_type = schedule.get('account_type', 'tax_deferred')

                for year_idx in range(max(0, start_year), min(time_horizon + 1, end_year + 1)):
                    years_since_start = year_idx - start_year
                    annual_amount = monthly_amount * 12 * ((1 + annual_increase) ** years_since_start)
                    contributions[year_idx] += annual_amount
                    account_types[year_idx] = account_type
                    purposes[year_idx] = 'retirement'

        # Fill in withdrawals from schedule
        if not withdrawal_schedule:
            # Default: withdraw during retirement
            retirement_age = profile['personal_info']['retirement_age']
            annual_expenses = profile['financial_situation']['annual_expenses']

            for year_idx in range(time_horizon + 1):
                current_age = age + year_idx
                if current_age >= retirement_age:
                    withdrawals[year_idx] = annual_expenses
                    purposes[year_idx] = 'retirement_income'
        else:
            # Use provided schedule
            for withdrawal in withdrawal_schedule:
                year = withdrawal.get('year', 0)
                amount = withdrawal.get('amount', 0)
                purpose = withdrawal.get('purpose', 'withdrawal')

                if 0 <= year <= time_horizon:
                    withdrawals[year] += amount
                    purposes[year] = purpose

        # Calculate net flow
        net_flow = contributions - withdrawals

        # Create DataFrame
        time_series_df = pd.DataFrame({
            'period': years,
            'age': investor_ages,
            'contribution': contributions,
            'withdrawal': withdrawals,
            'net_flow': net_flow,
            'account_type': account_types,
            'purpose': purposes
        })

        return time_series_df

    def _identify_life_stages(self, profile: Dict) -> Dict:
        """
        Identify life stages based on age and retirement plans.

        Args:
            profile: Validated profile

        Returns:
            Dictionary with life stage boundaries
        """
        age = profile['personal_info']['age']
        retirement_age = profile['personal_info']['retirement_age']
        life_expectancy = profile['personal_info']['life_expectancy']

        # Transition starts 10 years before retirement
        transition_start = retirement_age - 10

        return {
            'accumulation': {
                'start': age,
                'end': transition_start,
                'duration': max(0, transition_start - age)
            },
            'transition': {
                'start': transition_start,
                'end': retirement_age,
                'duration': retirement_age - transition_start
            },
            'distribution': {
                'start': retirement_age,
                'end': life_expectancy,
                'duration': life_expectancy - retirement_age
            }
        }

    def _calculate_risk_profile(self, profile: Dict, life_stages: Dict) -> Dict:
        """
        Calculate risk profile and recommended allocation with glide path.

        Args:
            profile: Validated profile
            life_stages: Life stage boundaries

        Returns:
            Dictionary with risk score, allocation, and glide path
        """
        age = profile['personal_info']['age']
        risk_tolerance = profile['investment_preferences']['risk_tolerance']
        debt_ratio = profile['financial_situation']['debt_to_income_ratio']

        # Calculate base risk score (0-100)
        risk_scores = {
            'conservative': 30,
            'moderate': 60,
            'aggressive': 90
        }
        base_score = risk_scores.get(risk_tolerance, 60)

        # Adjust for age (rule of thumb: stocks = 110 - age)
        age_based_equity = max(20, min(100, 110 - age))

        # Adjust for debt
        debt_adjustment = max(-20, -debt_ratio * 30)

        # Final risk score
        risk_score = max(0, min(100, base_score + debt_adjustment))

        # Recommended allocation
        equity_pct = (risk_score / 100) * 0.8 + 0.2  # Min 20%, max 100%
        bond_pct = 1 - equity_pct

        recommended_allocation = {
            'stocks': equity_pct * 0.7,
            'bonds': bond_pct,
            'real_estate': equity_pct * 0.2,
            'cash': equity_pct * 0.1
        }

        # Create glide path (age-based allocation changes)
        retirement_age = profile['personal_info']['retirement_age']
        life_expectancy = profile['personal_info']['life_expectancy']

        ages = list(range(age, life_expectancy + 1))
        stock_allocation = []
        bond_allocation = []

        for a in ages:
            # Decrease equity allocation as approaching retirement
            equity_at_age = max(20, min(80, 110 - a)) / 100
            stock_allocation.append(equity_at_age)
            bond_allocation.append(1 - equity_at_age)

        glide_path = pd.DataFrame({
            'age': ages,
            'stocks': stock_allocation,
            'bonds': bond_allocation
        })

        return {
            'score': risk_score,
            'recommended_allocation': recommended_allocation,
            'glide_path': glide_path,
            'age_based_equity_pct': age_based_equity / 100
        }

    def _create_sliced_plans(
        self,
        time_series: pd.DataFrame,
        life_stages: Dict,
        profile: Dict
    ) -> Dict:
        """
        Create sliced investment plans by different dimensions.

        Args:
            time_series: Investment time series
            life_stages: Life stage boundaries
            profile: Validated profile

        Returns:
            Dictionary of sliced plans
        """
        age = profile['personal_info']['age']

        # Slice by life stage
        by_life_stage = {}

        for stage_name, stage_info in life_stages.items():
            start_age = stage_info['start']
            end_age = stage_info['end']

            sliced_df = time_series[
                (time_series['age'] >= start_age) &
                (time_series['age'] <= end_age)
            ].copy()

            by_life_stage[stage_name] = sliced_df

        # Slice by goal (from purpose column)
        by_goal = {}
        unique_purposes = time_series['purpose'].unique()

        for purpose in unique_purposes:
            if purpose:  # Skip empty strings
                by_goal[purpose] = time_series[time_series['purpose'] == purpose].copy()

        # Slice by account type
        by_account_type = {}
        unique_accounts = time_series['account_type'].unique()

        for account in unique_accounts:
            if account:  # Skip empty strings
                by_account_type[account] = time_series[time_series['account_type'] == account].copy()

        return {
            'by_life_stage': by_life_stage,
            'by_goal': by_goal,
            'by_account_type': by_account_type
        }

    def _calculate_summary_statistics(
        self,
        time_series: pd.DataFrame,
        profile: Dict
    ) -> Dict:
        """
        Calculate summary statistics for the investment plan.

        Args:
            time_series: Investment time series
            profile: Validated profile

        Returns:
            Dictionary of summary statistics
        """
        total_contributions = time_series['contribution'].sum()
        total_withdrawals = time_series['withdrawal'].sum()

        contribution_years = len(time_series[time_series['contribution'] > 0])
        withdrawal_years = len(time_series[time_series['withdrawal'] > 0])

        retirement_age = profile['personal_info']['retirement_age']
        life_expectancy = profile['personal_info']['life_expectancy']

        return {
            'total_contributions': total_contributions,
            'total_withdrawals': total_withdrawals,
            'contribution_years': contribution_years,
            'withdrawal_years': withdrawal_years,
            'retirement_duration': life_expectancy - retirement_age,
            'average_annual_contribution': total_contributions / max(1, contribution_years),
            'average_annual_withdrawal': total_withdrawals / max(1, withdrawal_years)
        }


# Convenience functions
def create_simple_profile(
    age: int,
    annual_income: float,
    current_savings: float = 0,
    risk_tolerance: str = 'moderate',
    retirement_age: int = 65
) -> Dict:
    """
    Create a simple user profile with defaults.

    Args:
        age: Current age
        annual_income: Annual income
        current_savings: Current savings
        risk_tolerance: Risk tolerance level
        retirement_age: Target retirement age

    Returns:
        Profile dictionary ready for processing

    Example:
        >>> profile = create_simple_profile(35, 75000, 10000, 'moderate', 65)
    """
    return {
        'user_profile': {
            'personal_info': {
                'age': age,
                'retirement_age': retirement_age,
                'life_expectancy': 90,
                'country': 'US',
                'currency': 'USD'
            },
            'financial_situation': {
                'current_savings': current_savings,
                'annual_income': annual_income,
                'annual_expenses': annual_income * 0.7,
                'debt': {'mortgage': 0, 'student_loans': 0, 'other': 0}
            },
            'investment_preferences': {
                'risk_tolerance': risk_tolerance,
                'investment_goal': 'retirement',
                'time_horizon': retirement_age - age,
                'esg_preferences': False,
                'liquidity_needs': 0.05
            },
            'constraints': {
                'max_equity_allocation': 0.9,
                'min_bond_allocation': 0.1,
                'exclude_sectors': [],
                'rebalancing_frequency': 'annual'
            }
        },
        'contribution_schedule': [],
        'withdrawal_schedule': []
    }
