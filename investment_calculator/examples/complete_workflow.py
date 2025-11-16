"""
Complete Investment Calculator Workflow Example

This example demonstrates the full workflow of the investment calculator:
1. Define personal variables and investment profile
2. Generate economic scenarios (GSE)
3. Apply tax calculations (GSE+)
4. Run portfolio optimization (MOCA)
5. Analyze results and generate reports
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from investment_calculator import (
    PersonalVariables,
    InvestmentProfile,
    GlobalScenarioEngine,
    TaxIntegratedScenarioEngine,
    TaxConfig,
    AccountType,
    MOCA,
    OptimizationMethod,
    RiskTolerance,
    InvestmentGoal,
)


def example_1_basic_workflow():
    """Example 1: Basic workflow with standard scenarios"""
    print("=" * 70)
    print("EXAMPLE 1: Basic Investment Analysis Workflow")
    print("=" * 70)

    # Step 1: Define personal variables
    print("\nStep 1: Define Personal Variables")
    print("-" * 70)

    personal_vars = PersonalVariables(
        age=35,
        annual_income=100000,
        current_savings=50000,
        monthly_contribution=1500,
        risk_tolerance=RiskTolerance.BALANCED,
        investment_horizon=30,
        tax_bracket=0.25,
        capital_gains_rate=0.15,
        has_tax_advantaged_account=True,
        emergency_fund_months=6,
        debt_to_income_ratio=0.2,
    )

    profile = InvestmentProfile(
        personal_vars=personal_vars,
        primary_goal=InvestmentGoal.RETIREMENT,
        target_retirement_income=80000,
    )

    print(profile.summary())

    # Step 2: Generate economic scenarios (GSE)
    print("\nStep 2: Generate Economic Scenarios (GSE)")
    print("-" * 70)

    gse = GlobalScenarioEngine(random_seed=42)
    scenarios = gse.generate_standard_scenarios(years=30)

    print(f"Generated {len(scenarios)} scenarios:")
    for scenario in scenarios:
        print(f"  - {scenario.scenario_id} ({scenario.scenario_type.value})")
        stats = scenario.get_summary_statistics()
        print(f"    Stock returns: {stats['stock_returns']['mean']:.2%} ± {stats['stock_returns']['std']:.2%}")
        print(f"    Bond returns:  {stats['bond_returns']['mean']:.2%} ± {stats['bond_returns']['std']:.2%}")

    # Step 3: Apply tax calculations (GSE+)
    print("\nStep 3: Apply Tax Calculations (GSE+)")
    print("-" * 70)

    tax_config = TaxConfig(
        country_code="US",
        ordinary_income_rate=personal_vars.tax_bracket,
        long_term_cap_gains_rate=personal_vars.capital_gains_rate,
        state_tax_rate=0.05,
    )

    gse_plus = TaxIntegratedScenarioEngine(tax_config=tax_config, gse=gse)

    # Generate tax-integrated scenarios for taxable account
    tax_scenarios = [
        gse_plus.generate_tax_integrated_scenario(scenario, AccountType.TAXABLE)
        for scenario in scenarios
    ]

    print(f"Applied tax calculations to {len(tax_scenarios)} scenarios")
    for tax_scenario in tax_scenarios:
        print(f"  - {tax_scenario.base_scenario.scenario_id}")
        print(f"    Effective tax rate: {tax_scenario.get_effective_tax_rate():.2%}")

    # Step 4: Run portfolio optimization (MOCA)
    print("\nStep 4: Run Portfolio Optimization (MOCA)")
    print("-" * 70)

    moca = MOCA(investment_profile=profile)

    # Test recommended allocation
    recommended_allocation = profile.get_recommended_asset_allocation()
    print(f"\nRecommended asset allocation based on risk profile:")
    for asset, weight in recommended_allocation.items():
        print(f"  {asset}: {weight:.1%}")

    # Run scenarios with recommended allocation
    results = moca.run_scenarios(tax_scenarios, recommended_allocation)

    # Calculate statistics
    stats = moca.calculate_statistics(target_balance=1000000)

    print(f"\nSimulation Results ({len(results)} scenarios):")
    print(f"  Expected Final Balance: ${stats.mean_final_balance:,.2f}")
    print(f"  Median Final Balance: ${stats.median_final_balance:,.2f}")
    print(f"  5th Percentile: ${stats.percentile_5:,.2f}")
    print(f"  95th Percentile: ${stats.percentile_95:,.2f}")
    print(f"  Expected Annual Return: {stats.mean_return:.2%}")
    print(f"  Return Volatility: {stats.std_return:.2%}")
    print(f"  Expected Sharpe Ratio: {stats.mean_sharpe:.2f}")
    print(f"  Probability of Loss: {stats.probability_of_loss:.1%}")
    print(f"  Probability of $1M+: {stats.probability_of_target:.1%}")

    # Step 5: Generate comprehensive report
    print("\nStep 5: Generate Comprehensive Report")
    print("-" * 70)
    print(moca.generate_report())


def example_2_portfolio_optimization():
    """Example 2: Compare different portfolio optimization methods"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Portfolio Optimization Comparison")
    print("=" * 70)

    # Define investor profile
    personal_vars = PersonalVariables(
        age=40,
        annual_income=150000,
        current_savings=200000,
        monthly_contribution=2500,
        risk_tolerance=RiskTolerance.AGGRESSIVE,
        investment_horizon=25,
        tax_bracket=0.32,
        capital_gains_rate=0.15,
    )

    profile = InvestmentProfile(
        personal_vars=personal_vars,
        primary_goal=InvestmentGoal.WEALTH_BUILDING,
    )

    # Generate Monte Carlo scenarios
    gse = GlobalScenarioEngine(random_seed=42)
    mc_scenarios = gse.generate_monte_carlo_scenarios(years=25, n_scenarios=100)

    # Apply taxes
    tax_config = TaxConfig(
        ordinary_income_rate=0.32,
        long_term_cap_gains_rate=0.15,
        state_tax_rate=0.06,
    )
    gse_plus = TaxIntegratedScenarioEngine(tax_config=tax_config)

    tax_scenarios = [
        gse_plus.generate_tax_integrated_scenario(scenario, AccountType.TAXABLE)
        for scenario in mc_scenarios[:50]  # Use subset for faster computation
    ]

    # Test different optimization methods
    moca = MOCA(investment_profile=profile)

    methods = [
        OptimizationMethod.MAX_SHARPE,
        OptimizationMethod.MIN_VOLATILITY,
        OptimizationMethod.RISK_PARITY,
        OptimizationMethod.EQUAL_WEIGHT,
    ]

    print("\nComparing Portfolio Optimization Methods:")
    print("-" * 70)

    results_comparison = []

    for method in methods:
        print(f"\nOptimizing using {method.value}...")

        optimal_allocation, stats = moca.optimize_portfolio(
            scenarios=tax_scenarios,
            method=method,
            asset_classes=["stocks", "bonds", "real_estate"],
        )

        print(f"\nOptimal Allocation ({method.value}):")
        for asset, weight in optimal_allocation.items():
            print(f"  {asset}: {weight:.1%}")

        print(f"\nExpected Outcomes:")
        print(f"  Final Balance: ${stats.mean_final_balance:,.2f}")
        print(f"  Annual Return: {stats.mean_return:.2%}")
        print(f"  Volatility: {stats.std_return:.2%}")
        print(f"  Sharpe Ratio: {stats.mean_sharpe:.2f}")
        print(f"  5th Percentile: ${stats.percentile_5:,.2f}")

        results_comparison.append({
            "method": method.value,
            "allocation": optimal_allocation,
            "mean_balance": stats.mean_final_balance,
            "mean_return": stats.mean_return,
            "sharpe": stats.mean_sharpe,
        })

    print("\n" + "=" * 70)
    print("SUMMARY: Best Method by Metric")
    print("=" * 70)

    best_balance = max(results_comparison, key=lambda x: x["mean_balance"])
    best_sharpe = max(results_comparison, key=lambda x: x["sharpe"])

    print(f"Highest Expected Balance: {best_balance['method']}")
    print(f"  ${best_balance['mean_balance']:,.2f}")

    print(f"\nBest Risk-Adjusted Returns (Sharpe): {best_sharpe['method']}")
    print(f"  Sharpe Ratio: {best_sharpe['sharpe']:.2f}")


def example_3_account_type_comparison():
    """Example 3: Compare different account types (Taxable, Tax-Deferred, Tax-Free)"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Account Type Comparison")
    print("=" * 70)

    # Setup
    personal_vars = PersonalVariables(
        age=30,
        annual_income=80000,
        current_savings=25000,
        monthly_contribution=1000,
        investment_horizon=35,
        tax_bracket=0.22,
        capital_gains_rate=0.15,
    )

    tax_config = TaxConfig(
        ordinary_income_rate=0.22,
        long_term_cap_gains_rate=0.15,
        state_tax_rate=0.04,
    )

    gse_plus = TaxIntegratedScenarioEngine(tax_config=tax_config)

    # Compare account types
    print("\nComparing account types over 35 years:")
    print("-" * 70)

    comparison = gse_plus.compare_account_types(
        years=35,
        initial_investment=25000,
        annual_contribution=12000,
        asset_allocation={"stocks": 0.8, "bonds": 0.15, "real_estate": 0.05},
    )

    print("\nResults by Account Type:")
    print(comparison.to_string(index=False))

    print("\n" + "=" * 70)
    print("Key Insights:")
    print("=" * 70)

    best_account = comparison.loc[comparison["after_withdrawal_tax"].idxmax()]
    tax_savings = (
        best_account["after_withdrawal_tax"]
        - comparison.loc[comparison["account_type"] == "taxable", "after_withdrawal_tax"].values[0]
    )

    print(f"\nBest Account Type: {best_account['account_type']}")
    print(f"Final Balance (after tax): ${best_account['after_withdrawal_tax']:,.2f}")
    print(f"Tax Savings vs. Taxable: ${tax_savings:,.2f}")


def example_4_retirement_planning():
    """Example 4: Comprehensive retirement planning scenario"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Comprehensive Retirement Planning")
    print("=" * 70)

    # Define retirement scenario
    personal_vars = PersonalVariables(
        age=45,
        annual_income=120000,
        current_savings=300000,
        monthly_contribution=2000,
        risk_tolerance=RiskTolerance.MODERATE,
        investment_horizon=20,  # Until age 65
        tax_bracket=0.28,
        capital_gains_rate=0.15,
        has_tax_advantaged_account=True,
        emergency_fund_months=8,
        debt_to_income_ratio=0.15,
    )

    profile = InvestmentProfile(
        personal_vars=personal_vars,
        primary_goal=InvestmentGoal.RETIREMENT,
        target_retirement_income=90000,  # 75% of current income
    )

    print(profile.summary())

    # Check if ready to invest
    ready, warnings = profile.is_ready_to_invest()

    if not ready:
        print("\n⚠ Investment Readiness Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("\n✓ Investor is ready to proceed with investment planning")

    # Generate scenarios
    print("\nGenerating retirement scenarios...")
    gse = GlobalScenarioEngine(random_seed=42)

    # Use Monte Carlo for more robust analysis
    scenarios = gse.generate_monte_carlo_scenarios(years=20, n_scenarios=500)

    # Apply taxes (tax-deferred account for retirement)
    tax_config = TaxConfig(
        ordinary_income_rate=0.28,
        long_term_cap_gains_rate=0.15,
        state_tax_rate=0.05,
    )
    gse_plus = TaxIntegratedScenarioEngine(tax_config=tax_config)

    tax_scenarios = [
        gse_plus.generate_tax_integrated_scenario(scenario, AccountType.TAX_DEFERRED)
        for scenario in scenarios[:100]  # Use subset
    ]

    # Optimize portfolio
    print("\nOptimizing retirement portfolio...")
    moca = MOCA(investment_profile=profile)

    optimal_allocation, stats = moca.optimize_portfolio(
        scenarios=tax_scenarios,
        method=OptimizationMethod.MAX_SHARPE,
        asset_classes=["stocks", "bonds", "real_estate"],
    )

    print("\n" + "=" * 70)
    print("RETIREMENT PLAN ANALYSIS")
    print("=" * 70)

    print("\nOptimal Asset Allocation:")
    for asset, weight in optimal_allocation.items():
        print(f"  {asset}: {weight:.1%}")

    print(f"\nProjected Retirement Savings (at age 65):")
    print(f"  Expected Balance: ${stats.mean_final_balance:,.2f}")
    print(f"  Conservative (5th %ile): ${stats.percentile_5:,.2f}")
    print(f"  Optimistic (95th %ile): ${stats.percentile_95:,.2f}")

    # Calculate sustainable withdrawal
    # Using 4% rule
    sustainable_withdrawal_expected = stats.mean_final_balance * 0.04
    sustainable_withdrawal_conservative = stats.percentile_5 * 0.04

    print(f"\nSustainable Annual Withdrawal (4% rule):")
    print(f"  Expected Scenario: ${sustainable_withdrawal_expected:,.2f}/year")
    print(f"  Conservative Scenario: ${sustainable_withdrawal_conservative:,.2f}/year")
    print(f"  Target Income: ${profile.target_retirement_income:,.2f}/year")

    # Check if goal is achievable
    if sustainable_withdrawal_conservative >= profile.target_retirement_income:
        print(f"\n✓ Retirement goal is achievable even in conservative scenarios!")
    elif sustainable_withdrawal_expected >= profile.target_retirement_income:
        print(f"\n⚠ Retirement goal is achievable in expected scenario, but risky in downturns")
        shortfall = profile.target_retirement_income - sustainable_withdrawal_conservative
        print(f"   Conservative shortfall: ${shortfall:,.2f}/year")
    else:
        print(f"\n✗ Retirement goal may not be achievable with current plan")
        shortfall = profile.target_retirement_income - sustainable_withdrawal_expected
        print(f"   Expected shortfall: ${shortfall:,.2f}/year")
        print(f"\n   Recommendations:")
        print(f"   - Increase monthly contributions")
        print(f"   - Extend working years")
        print(f"   - Adjust retirement income expectations")

    print("\n" + moca.generate_report())


if __name__ == "__main__":
    # Run all examples
    example_1_basic_workflow()
    print("\n" * 3)

    example_2_portfolio_optimization()
    print("\n" * 3)

    example_3_account_type_comparison()
    print("\n" * 3)

    example_4_retirement_planning()

    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)
