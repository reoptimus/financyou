"""
Example: Dual Slicing Capabilities in Module 3

This example demonstrates both domain-specific and general-purpose
time series slicing available in Module 3 (User Profile).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator.modules import user_profile


def main():
    """Demonstrate dual slicing capabilities."""
    print("=" * 70)
    print("MODULE 3: DUAL SLICING CAPABILITIES DEMONSTRATION")
    print("=" * 70)
    print("\nThis example shows two types of slicing:")
    print("1. DOMAIN-SPECIFIC SLICING (investment planning)")
    print("2. GENERAL TIME SERIES SLICING (generic operations)")
    print("=" * 70)

    # Create user profile
    manager = user_profile.UserProfileManager()

    config = user_profile.create_simple_profile(
        age=35,
        annual_income=75000,
        current_savings=50000,
        risk_tolerance='moderate',
        retirement_age=65
    )

    # Add custom contribution schedule
    config['contribution_schedule'] = [
        {
            'start_year': 0,
            'end_year': 20,
            'monthly_amount': 500,
            'annual_increase': 0.03,
            'account_type': 'tax_deferred'
        },
        {
            'start_year': 20,
            'end_year': 30,
            'monthly_amount': 1000,
            'annual_increase': 0.03,
            'account_type': 'tax_free'
        }
    ]

    print("\n" + "=" * 70)
    print("PROCESSING USER PROFILE")
    print("=" * 70)
    print(f"\nUser: 35 years old, retiring at 65")
    print(f"Income: $75,000/year")
    print(f"Initial contribution: $500/month (years 1-20)")
    print(f"Later contribution: $1,000/month (years 21-30)")

    results = manager.process(config)

    time_series = results['investment_time_series']
    print(f"\n✓ Generated {len(time_series)} year investment plan")

    # ========================================================================
    # PART 1: DOMAIN-SPECIFIC SLICING
    # ========================================================================
    print("\n" + "=" * 70)
    print("PART 1: DOMAIN-SPECIFIC SLICING")
    print("=" * 70)
    print("\nThese are investment planning-specific slices:")

    sliced_plans = results['sliced_plans']

    # 1. Slice by life stage
    print("\n1. SLICING BY LIFE STAGE:")
    print("-" * 50)

    for stage_name, stage_data in sliced_plans['by_life_stage'].items():
        if not stage_data.empty:
            total_contrib = stage_data['contribution'].sum()
            years = len(stage_data)
            print(f"\n{stage_name.upper()} Phase:")
            print(f"  Duration: {years} years")
            print(f"  Total contributions: ${total_contrib:,.0f}")
            print(f"  Average annual: ${total_contrib/max(1, years):,.0f}")

    # 2. Slice by goal
    print("\n2. SLICING BY GOAL/PURPOSE:")
    print("-" * 50)

    for goal, goal_data in sliced_plans['by_goal'].items():
        if not goal_data.empty and goal:
            total_contrib = goal_data['contribution'].sum()
            print(f"\n{goal.replace('_', ' ').title()}:")
            print(f"  Years: {len(goal_data)}")
            print(f"  Total contributions: ${total_contrib:,.0f}")

    # 3. Slice by account type
    print("\n3. SLICING BY ACCOUNT TYPE:")
    print("-" * 50)

    for account_type, account_data in sliced_plans['by_account_type'].items():
        if not account_data.empty and account_type:
            total_contrib = account_data['contribution'].sum()
            print(f"\n{account_type.replace('_', ' ').title()}:")
            print(f"  Years: {len(account_data)}")
            print(f"  Total contributions: ${total_contrib:,.0f}")

    # ========================================================================
    # PART 2: GENERAL TIME SERIES SLICING
    # ========================================================================
    print("\n" + "=" * 70)
    print("PART 2: GENERAL TIME SERIES SLICING")
    print("=" * 70)
    print("\nThese are generic time series operations:")

    slicer = results['time_series_slicer']

    # 1. Slice by index
    print("\n1. SLICING BY INDEX:")
    print("-" * 50)

    first_10_years = slicer.slice_by_index(0, 10)
    print(f"\nFirst 10 years:")
    print(f"  Total contributions: ${first_10_years['contribution'].sum():,.0f}")
    print(f"  Average annual: ${first_10_years['contribution'].mean():,.0f}")

    last_10_years = slicer.slice_by_index(-10, None)
    print(f"\nLast 10 years:")
    print(f"  Total contributions: ${last_10_years['contribution'].sum():,.0f}")
    print(f"  Average annual: ${last_10_years['contribution'].mean():,.0f}")

    # 2. Slice by value
    print("\n2. SLICING BY VALUE:")
    print("-" * 50)

    # High contribution years (> $8,000/year)
    high_contrib = slicer.slice_by_value('contribution', min_value=8000)
    print(f"\nHigh contribution years (>$8,000/year):")
    print(f"  Number of years: {len(high_contrib)}")
    print(f"  Total contributions: ${high_contrib['contribution'].sum():,.0f}")
    print(f"  Years: {high_contrib['period'].min():.0f} - {high_contrib['period'].max():.0f}")

    # Low contribution years (< $7,000/year)
    low_contrib = slicer.slice_by_value('contribution', max_value=7000)
    print(f"\nLow contribution years (<$7,000/year):")
    print(f"  Number of years: {len(low_contrib)}")
    print(f"  Total contributions: ${low_contrib['contribution'].sum():,.0f}")

    # 3. Rolling windows
    print("\n3. ROLLING WINDOWS (5-year windows):")
    print("-" * 50)

    window_results = []
    for i, window in enumerate(slicer.slice_by_window(window_size=5, overlap=False)):
        avg_contribution = window['contribution'].mean()
        window_results.append({
            'window': i + 1,
            'years': f"{window['period'].iloc[0]:.0f}-{window['period'].iloc[-1]:.0f}",
            'avg_contribution': avg_contribution
        })

    print(f"\n5-year rolling averages:")
    for result in window_results[:6]:  # Show first 6 windows
        print(f"  Window {result['window']} (years {result['years']}): "
              f"${result['avg_contribution']:,.0f}/year")

    # 4. Train/test split
    print("\n4. TRAIN/TEST SPLIT (70/30):")
    print("-" * 50)

    train_data, test_data = slicer.split_by_ratio([0.7, 0.3])

    print(f"\nTraining data:")
    print(f"  Years: {len(train_data)}")
    print(f"  Total contributions: ${train_data['contribution'].sum():,.0f}")
    print(f"  Average annual: ${train_data['contribution'].mean():,.0f}")

    print(f"\nTest data:")
    print(f"  Years: {len(test_data)}")
    print(f"  Total contributions: ${test_data['contribution'].sum():,.0f}")
    print(f"  Average annual: ${test_data['contribution'].mean():,.0f}")

    # ========================================================================
    # COMPARISON
    # ========================================================================
    print("\n" + "=" * 70)
    print("WHEN TO USE WHICH TYPE OF SLICING")
    print("=" * 70)

    print("\nDOMAIN-SPECIFIC SLICING (sliced_plans):")
    print("  ✓ Analyzing different life stages")
    print("  ✓ Comparing different investment goals")
    print("  ✓ Reviewing account type allocation")
    print("  ✓ Investment planning and strategy")

    print("\nGENERAL TIME SERIES SLICING (time_series_slicer):")
    print("  ✓ Statistical analysis (windows, train/test)")
    print("  ✓ Data exploration and filtering")
    print("  ✓ Backtesting and validation")
    print("  ✓ Generic time series operations")

    print("\n" + "=" * 70)
    print("EXAMPLE COMPLETE!")
    print("=" * 70)
    print("\nBoth slicing types are complementary:")
    print("  - Use domain-specific for investment planning insights")
    print("  - Use general slicing for data analysis and exploration")
    print("=" * 70)

    return results


if __name__ == '__main__':
    try:
        results = main()
        print("\n✓ Example completed successfully!")
    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
        import traceback
        traceback.print_exc()
