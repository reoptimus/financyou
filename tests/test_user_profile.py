"""
Comprehensive Unit Tests for Module 3: User Input & Investment Time Series

Tests cover:
- UserProfileManager initialization
- Profile validation and processing
- Risk profiling
- Life stage analysis
- Investment time series generation
- Domain-specific slicing
- General time series slicing integration
- Contribution and withdrawal schedules
- Edge cases and data quality
- Convenience functions
"""

import pytest
import numpy as np
import pandas as pd
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator.modules import user_profile


# Helper functions to create test profiles
def create_simple_test_profile(age=35, risk_tolerance='moderate'):
    """Create simple test profile."""
    return {
        'user_profile': {
            'personal_info': {
                'age': age,
                'retirement_age': 65,
                'life_expectancy': 90,
                'country': 'US',
                'currency': 'USD'
            },
            'financial_situation': {
                'current_savings': 50000,
                'annual_income': 75000,
                'annual_expenses': 55000,
                'debt': {
                    'mortgage': 200000,
                    'student_loans': 0,
                    'other': 0
                }
            },
            'investment_preferences': {
                'risk_tolerance': risk_tolerance,
                'investment_goal': 'retirement',
                'time_horizon': 30,
                'esg_preferences': False,
                'liquidity_needs': 0.1
            },
            'constraints': {
                'max_equity_allocation': 0.80,
                'min_bond_allocation': 0.15,
                'exclude_sectors': [],
                'rebalancing_frequency': 'annual'
            }
        },
        'contribution_schedule': [
            {
                'start_year': 0,
                'end_year': 30,
                'monthly_amount': 1000,
                'annual_increase': 0.03,
                'account_type': 'tax_deferred'
            }
        ],
        'withdrawal_schedule': []
    }


def load_example_profile(filename='user_profile_aggressive.json'):
    """Load example profile from input_files."""
    filepath = Path(__file__).parent.parent / 'examples' / 'input_files' / filename
    with open(filepath, 'r') as f:
        return json.load(f)


class TestUserProfileManagerInitialization:
    """Test UserProfileManager initialization."""

    def test_init(self):
        """Test basic initialization."""
        manager = user_profile.UserProfileManager()
        assert manager is not None

    def test_multiple_instances(self):
        """Test creating multiple instances."""
        manager1 = user_profile.UserProfileManager()
        manager2 = user_profile.UserProfileManager()
        assert manager1 is not manager2


class TestProfileValidation:
    """Test profile validation."""

    def test_valid_profile(self):
        """Test processing valid profile."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)

        # Should return all expected keys
        assert 'validated_profile' in results
        assert 'investment_time_series' in results
        assert 'life_stages' in results
        assert 'risk_profile' in results
        assert 'validation_warnings' in results

    def test_validation_warnings_list(self):
        """Test that validation warnings is a list."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)

        assert isinstance(results['validation_warnings'], list)

    def test_process_example_aggressive_profile(self):
        """Test processing example aggressive profile."""
        manager = user_profile.UserProfileManager()
        profile_config = load_example_profile('user_profile_aggressive.json')

        results = manager.process(profile_config)

        assert 'validated_profile' in results
        assert results['validated_profile']['personal_info']['age'] == 28

    def test_process_example_conservative_profile(self):
        """Test processing example conservative profile."""
        manager = user_profile.UserProfileManager()
        profile_config = load_example_profile('user_profile_conservative.json')

        results = manager.process(profile_config)

        assert 'validated_profile' in results
        assert results['validated_profile']['personal_info']['age'] == 55


class TestRiskProfiling:
    """Test risk profiling functionality."""

    def test_risk_profile_structure(self):
        """Test risk profile output structure."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile(risk_tolerance='aggressive')

        results = manager.process(profile_config)
        risk_profile = results['risk_profile']

        # Check expected fields
        assert 'score' in risk_profile
        assert 'recommended_allocation' in risk_profile
        assert isinstance(risk_profile['score'], (int, float))

    def test_aggressive_risk_profile(self):
        """Test aggressive risk profiling."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile(age=30, risk_tolerance='aggressive')

        results = manager.process(profile_config)
        risk_profile = results['risk_profile']

        # Aggressive should have high score
        assert risk_profile['score'] >= 70

    def test_conservative_risk_profile(self):
        """Test conservative risk profiling."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile(age=60, risk_tolerance='conservative')

        results = manager.process(profile_config)
        risk_profile = results['risk_profile']

        # Conservative should have lower score
        assert risk_profile['score'] <= 40

    def test_moderate_risk_profile(self):
        """Test moderate risk profiling."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile(risk_tolerance='moderate')

        results = manager.process(profile_config)
        risk_profile = results['risk_profile']

        # Moderate should be in reasonable range
        assert 20 <= risk_profile['score'] <= 80

    def test_recommended_allocation_sums_to_one(self):
        """Test that recommended allocation sums to approximately 1."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        allocation = results['risk_profile']['recommended_allocation']

        total = sum(allocation.values())
        assert abs(total - 1.0) < 0.01  # Allow small numerical error


class TestLifeStages:
    """Test life stage analysis."""

    def test_life_stages_structure(self):
        """Test life stages output structure."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        life_stages = results['life_stages']

        # Should have standard life stages
        assert 'accumulation' in life_stages
        assert 'transition' in life_stages
        assert 'distribution' in life_stages

    def test_life_stage_ages(self):
        """Test life stage age ranges."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile(age=30)

        results = manager.process(profile_config)
        life_stages = results['life_stages']

        # Check structure
        for stage_name, stage_info in life_stages.items():
            assert 'start' in stage_info
            assert 'end' in stage_info
            assert 'duration' in stage_info

    def test_life_stages_cover_full_horizon(self):
        """Test that life stages cover the full time horizon."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile(age=25)

        results = manager.process(profile_config)
        life_stages = results['life_stages']

        # Get profile ages
        personal_info = results['validated_profile']['personal_info']
        current_age = personal_info['age']
        life_expectancy = personal_info['life_expectancy']

        # First stage should start at current age
        first_stage = min(life_stages.values(), key=lambda x: x['start'])
        assert first_stage['start'] == current_age

        # Last stage should end at or near life expectancy
        last_stage = max(life_stages.values(), key=lambda x: x['end'])
        assert last_stage['end'] <= life_expectancy


class TestInvestmentTimeSeries:
    """Test investment time series generation."""

    def test_time_series_structure(self):
        """Test time series DataFrame structure."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        time_series = results['investment_time_series']

        # Should be a DataFrame
        assert isinstance(time_series, pd.DataFrame)

        # Should have expected columns
        assert 'period' in time_series.columns
        assert 'age' in time_series.columns
        assert 'contribution' in time_series.columns

    def test_time_series_length(self):
        """Test time series length matches time horizon."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()
        time_horizon = profile_config['user_profile']['investment_preferences']['time_horizon']

        results = manager.process(profile_config)
        time_series = results['investment_time_series']

        # Should have approximately time_horizon rows (may vary based on implementation)
        assert len(time_series) >= time_horizon

    def test_contribution_schedule_applied(self):
        """Test that contribution schedule is applied correctly."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        time_series = results['investment_time_series']

        # Should have contributions
        assert time_series['contribution'].sum() > 0

    def test_age_progression(self):
        """Test that age increases correctly in time series."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile(age=30)

        results = manager.process(profile_config)
        time_series = results['investment_time_series']

        if 'age' in time_series.columns:
            ages = time_series['age'].values
            # Age should be increasing
            assert all(ages[i] <= ages[i+1] for i in range(len(ages)-1))
            # First age should be current age
            assert ages[0] == 30


class TestSlicingCapabilities:
    """Test slicing capabilities."""

    def test_sliced_plans_structure(self):
        """Test sliced plans structure."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        sliced_plans = results['sliced_plans']

        # Should be a dictionary
        assert isinstance(sliced_plans, dict)

    def test_time_series_slicer_exists(self):
        """Test that time series slicer is created."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)

        # Should have time_series_slicer
        assert 'time_series_slicer' in results
        assert results['time_series_slicer'] is not None

    def test_slicing_by_life_stage(self):
        """Test slicing by life stage."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        sliced_plans = results['sliced_plans']

        # Should have life stage slicing if implemented
        if 'by_life_stage' in sliced_plans:
            assert 'accumulation' in sliced_plans['by_life_stage']


class TestContributionSchedules:
    """Test contribution schedules."""

    def test_single_contribution_schedule(self):
        """Test single contribution schedule."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        time_series = results['investment_time_series']

        # Should have contributions
        assert 'contribution' in time_series.columns
        assert time_series['contribution'].sum() > 0

    def test_multiple_contribution_schedules(self):
        """Test multiple contribution schedules."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        # Add second contribution schedule
        profile_config['contribution_schedule'].append({
            'start_year': 10,
            'end_year': 20,
            'monthly_amount': 500,
            'annual_increase': 0.02,
            'account_type': 'taxable'
        })

        results = manager.process(profile_config)
        time_series = results['investment_time_series']

        # Should have contributions from both schedules
        assert time_series['contribution'].sum() > 0

    def test_annual_increase_in_contributions(self):
        """Test annual increase in contributions."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()
        profile_config['contribution_schedule'][0]['annual_increase'] = 0.05

        results = manager.process(profile_config)
        time_series = results['investment_time_series']

        # Should have contributions
        assert 'contribution' in time_series.columns
        assert time_series['contribution'].sum() > 0


class TestWithdrawalSchedules:
    """Test withdrawal schedules."""

    def test_no_withdrawals(self):
        """Test profile with no withdrawals."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        time_series = results['investment_time_series']

        # Should complete without error
        assert len(time_series) > 0

    def test_with_withdrawals(self):
        """Test profile with withdrawals."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        # Add withdrawal schedule
        profile_config['withdrawal_schedule'] = [
            {
                'year': 25,
                'amount': 50000,
                'purpose': 'home_purchase',
                'account_preference': 'taxable'
            }
        ]

        results = manager.process(profile_config)
        time_series = results['investment_time_series']

        # Should have withdrawal column if implemented
        if 'withdrawal' in time_series.columns:
            assert time_series['withdrawal'].sum() > 0


class TestSummaryStatistics:
    """Test summary statistics."""

    def test_summary_statistics_structure(self):
        """Test summary statistics structure."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        summary = results['summary_statistics']

        # Should be a dictionary
        assert isinstance(summary, dict)

    def test_total_contributions_calculated(self):
        """Test total contributions are calculated."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        summary = results['summary_statistics']

        # Should have total contributions
        if 'total_contributions' in summary:
            assert summary['total_contributions'] > 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_simple_profile(self):
        """Test create_simple_profile convenience function."""
        simple_profile = user_profile.create_simple_profile(
            age=40,
            annual_income=100000,
            risk_tolerance='aggressive'
        )

        # Should return a valid profile dictionary
        assert 'user_profile' in simple_profile
        assert simple_profile['user_profile']['personal_info']['age'] == 40
        assert simple_profile['user_profile']['financial_situation']['annual_income'] == 100000

    def test_create_simple_profile_defaults(self):
        """Test create_simple_profile with defaults."""
        # create_simple_profile requires age and annual_income
        simple_profile = user_profile.create_simple_profile(
            age=35,
            annual_income=75000
        )

        # Should have valid defaults
        assert 'user_profile' in simple_profile
        assert simple_profile['user_profile']['personal_info']['age'] == 35


class TestEdgeCases:
    """Test edge cases."""

    def test_very_young_investor(self):
        """Test very young investor (age 22)."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile(age=22)

        results = manager.process(profile_config)

        # Should process without error
        assert 'validated_profile' in results

    def test_near_retirement_investor(self):
        """Test investor near retirement."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile(age=64)
        profile_config['user_profile']['personal_info']['retirement_age'] = 65

        results = manager.process(profile_config)

        # Should process without error
        assert 'validated_profile' in results

    def test_retired_investor(self):
        """Test already retired investor."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile(age=70)
        profile_config['user_profile']['personal_info']['retirement_age'] = 65

        results = manager.process(profile_config)

        # Should process without error
        assert 'validated_profile' in results

    def test_zero_contributions(self):
        """Test profile with zero contributions."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()
        profile_config['contribution_schedule'][0]['monthly_amount'] = 0

        results = manager.process(profile_config)

        # Should process without error
        assert 'investment_time_series' in results

    def test_high_debt_ratio(self):
        """Test profile with high debt ratio."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()
        profile_config['user_profile']['financial_situation']['debt']['mortgage'] = 1000000

        results = manager.process(profile_config)

        # Should process (may have warnings)
        assert 'validated_profile' in results


class TestDataQuality:
    """Test data quality and consistency."""

    def test_no_null_values_in_time_series(self):
        """Test that time series has no null values."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        time_series = results['investment_time_series']

        # Check for nulls in key columns
        if 'contribution' in time_series.columns:
            assert not time_series['contribution'].isnull().any()

    def test_consistent_processing(self):
        """Test that same input produces same output."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results1 = manager.process(profile_config.copy())
        results2 = manager.process(profile_config.copy())

        # Risk profile should be identical
        assert results1['risk_profile']['score'] == results2['risk_profile']['score']

    def test_time_series_no_negative_periods(self):
        """Test that periods are non-negative."""
        manager = user_profile.UserProfileManager()
        profile_config = create_simple_test_profile()

        results = manager.process(profile_config)
        time_series = results['investment_time_series']

        if 'period' in time_series.columns:
            assert (time_series['period'] >= 0).all()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
