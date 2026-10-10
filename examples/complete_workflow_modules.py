"""
Complete Workflow Example - All 5 Modules

This example demonstrates the full FinancYou pipeline:
1. Generate economic scenarios
2. Build GSE+ (gross returns of the household placements)
3. Process user profile
4. Build GSE++ (net of fees and taxes) and optimize the placements
5. Generate reports

Run this example to see all modules working together.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator.modules import (
    scenario_generator,
    user_profile,
    reporting
)
from investment_calculator.modules.placement_plan import plan_placements
from investment_calculator.modules.placements import build_gross_placements
from investment_calculator.placement_catalog import load_placement_catalog


def main():
    """Run complete workflow."""
    print("=" * 70)
    print("FINANCYOU - COMPLETE WORKFLOW DEMONSTRATION")
    print("=" * 70)
    print("\nThis example demonstrates all 5 modules working together:")
    print("1. Economic Scenario Generator (GSE)")
    print("2. Household placements (GSE+)")
    print("3. User Input & Investment Time Series")
    print("4. Returns net of fees and taxes (GSE++) and Markowitz by placement")
    print("5. Visualization & Reporting")
    print("=" * 70)

    # ========================================================================
    # STEP 1: GENERATE ECONOMIC SCENARIOS
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 1: GENERATING ECONOMIC SCENARIOS")
    print("=" * 70)

    gen = scenario_generator.ScenarioGenerator(random_seed=42)

    scenario_config = {
        'num_scenarios': 100,  # Using 100 for faster demonstration
        'time_horizon': 30,
        'timestep': 1.0,
        'use_stochastic': False,  # Using simple mode for faster execution
        'currency': 'USD',
        'economic_params': {
            'equity_drift': 0.10,
            'equity_volatility': 0.18,
            'bond_return_mean': 0.05,
            'inflation_mean': 0.025
        }
    }

    print(f"\nGenerating {scenario_config['num_scenarios']} scenarios over "
          f"{scenario_config['time_horizon']} years...")

    scenario_results = gen.generate(scenario_config)

    scenarios_df = scenario_results['scenarios']
    print(f"✓ Generated {len(scenarios_df)} scenario data points")
    print(f"  Scenarios: {scenarios_df['scenario_id'].nunique()}")
    print(f"  Time periods: {scenarios_df['time_period'].nunique()}")
    print(f"\nDiagnostics:")
    print(f"  Mean stock return: {scenario_results['diagnostics']['mean_returns']['stock_return']:.2%}")
    print(f"  Mean bond return: {scenario_results['diagnostics']['mean_returns']['bond_return']:.2%}")
    print(f"  Stock volatility: {scenario_results['diagnostics']['volatilities']['stock_return']:.2%}")

    # ========================================================================
    # STEP 2: BUILD GSE+ (HOUSEHOLD PLACEMENTS)
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 2: BUILDING GSE+ (HOUSEHOLD PLACEMENTS)")
    print("=" * 70)

    # Le catalogue décrit les placements accessibles au foyer et porte le régime
    # fiscal de son pays et de son millésime.
    catalog = load_placement_catalog('fr-2026')
    gross = build_gross_placements(scenarios_df, catalog)

    print(f"\nCatalog {catalog.id}, tax regime {catalog.regime.id}")
    print("Mean annual return net of annual fees, before tax:")
    for placement_id, mean in gross.mean().items():
        print(f"  {placement_id}: {mean:.2%}")

    # ========================================================================
    # STEP 3: PROCESS USER PROFILE
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 3: PROCESSING USER PROFILE & INVESTMENT PLAN")
    print("=" * 70)

    manager = user_profile.UserProfileManager()

    # Create user profile
    user_config = {
        'user_profile': {
            'personal_info': {
                'age': 35,
                'retirement_age': 65,
                'life_expectancy': 90,
                'country': 'US',
                'currency': 'USD'
            },
            'financial_situation': {
                'current_savings': 50000,
                'annual_income': 75000,
                'annual_expenses': 50000,
                'debt': {
                    'mortgage': 200000,
                    'student_loans': 0,
                    'other': 0
                }
            },
            'investment_preferences': {
                'risk_tolerance': 'moderate',
                'investment_goal': 'retirement',
                'time_horizon': 30,
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
        'contribution_schedule': [
            {
                'start_year': 0,
                'end_year': 30,
                'monthly_amount': 500,
                'annual_increase': 0.03,
                'account_type': 'tax_deferred'
            }
        ],
        'withdrawal_schedule': []
    }

    print("\nUser Profile:")
    print(f"  Age: {user_config['user_profile']['personal_info']['age']}")
    print(f"  Retirement age: {user_config['user_profile']['personal_info']['retirement_age']}")
    print(f"  Annual income: ${user_config['user_profile']['financial_situation']['annual_income']:,}")
    print(f"  Current savings: ${user_config['user_profile']['financial_situation']['current_savings']:,}")
    print(f"  Risk tolerance: {user_config['user_profile']['investment_preferences']['risk_tolerance']}")
    print(f"  Monthly contribution: ${user_config['contribution_schedule'][0]['monthly_amount']}")

    profile_results = manager.process(user_config)

    print(f"\n✓ Processed user profile")
    print(f"  Risk score: {profile_results['risk_profile']['score']:.1f}/100")
    print(f"  Validation warnings: {len(profile_results['validation_warnings'])}")

    if profile_results['validation_warnings']:
        for warning in profile_results['validation_warnings']:
            print(f"    - {warning}")

    print(f"\nRecommended allocation:")
    for asset, weight in profile_results['risk_profile']['recommended_allocation'].items():
        print(f"  {asset}: {weight:.1%}")

    print(f"\nLife stages:")
    for stage, info in profile_results['life_stages'].items():
        print(f"  {stage.capitalize()}: Age {info['start']} - {info['end']} ({info['duration']} years)")

    print(f"\nInvestment plan summary:")
    stats = profile_results['summary_statistics']
    print(f"  Total contributions: ${stats['total_contributions']:,.0f}")
    print(f"  Contribution years: {stats['contribution_years']}")
    print(f"  Average annual contribution: ${stats['average_annual_contribution']:,.0f}")

    # ========================================================================
    # STEP 4: BUILD GSE++ AND OPTIMIZE PLACEMENTS
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 4: BUILDING GSE++ AND OPTIMIZING PLACEMENTS")
    print("=" * 70)

    horizon = user_config['user_profile']['investment_preferences']['time_horizon']
    goal_amount = 2000000
    print(f"\nObjective: mean_variance (risk aversion 5.0), horizon {horizon} years")
    print(f"Goal amount: {goal_amount:,}")

    optimization_results = plan_placements(
        scenarios_df,
        catalog,
        profile_results['investment_time_series'],
        horizon=horizon,
        objective='mean_variance',
        risk_aversion=5.0,
        risk_free_placement='livret_a',
        goal_amount=goal_amount,
    )

    print(f"\n✓ Optimization complete")
    print(f"\nOptimal allocation between placements:")
    for placement_id, weight in optimization_results['optimal_portfolio']['weights'].items():
        print(f"  {placement_id}: {weight:.1%}")

    portfolio_stats = optimization_results['optimal_portfolio']
    print(f"\nExpected Performance (net of fees and taxes, annualized over {horizon} years):")
    print(f"  Expected return: {portfolio_stats['expected_return']:.2%}")
    print(f"  Expected volatility: {portfolio_stats['expected_volatility']:.2%}")
    print(f"  Sharpe ratio: {portfolio_stats['sharpe_ratio']:.2f}")
    print(f"  Max drawdown: {portfolio_stats['max_drawdown']:.1%}")

    # Simulation results
    sim_stats = optimization_results['simulation_results']['statistics']
    print(f"\nMonte Carlo Simulation Results ({scenario_config['num_scenarios']} scenarios, "
          f"after exit tax):")
    print(f"  Median terminal wealth: {sim_stats['median_terminal_wealth']:,.0f}")
    print(f"  Mean terminal wealth: {sim_stats['mean_terminal_wealth']:,.0f}")
    print(f"\nPercentiles:")
    print(f"  5th percentile: {sim_stats['percentiles']['5']:,.0f}")
    print(f"  25th percentile: {sim_stats['percentiles']['25']:,.0f}")
    print(f"  75th percentile: {sim_stats['percentiles']['75']:,.0f}")
    print(f"  95th percentile: {sim_stats['percentiles']['95']:,.0f}")

    print(f"\nRisk Metrics:")
    print(f"  VaR (95%): {sim_stats['var_95']:,.0f}")
    print(f"  CVaR (95%): {sim_stats['cvar_95']:,.0f}")

    # Goal analysis
    goal_analysis = optimization_results['goal_analysis']
    print(f"\nGoal Analysis:")
    print(f"  Target amount: {goal_analysis['goal_amount']:,.0f}")
    print(f"  Probability of achieving: {goal_analysis['probability_of_achieving']:.1%}")
    print(f"  Expected surplus/deficit: {goal_analysis['expected_surplus']:,.0f}")

    # ========================================================================
    # STEP 5: GENERATE REPORTS
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 5: GENERATING REPORTS & VISUALIZATIONS")
    print("=" * 70)

    reporter = reporting.ReportGenerator()

    report_config = {
        'scenarios': scenario_results,
        'tax_results': {},
        'user_profile': profile_results,
        'optimization_results': optimization_results,
        'report_config': {
            'report_type': 'detailed',
            'language': 'en',
            'format': 'html',
            'charts': [
                'wealth_trajectories',
                'efficient_frontier',
                'allocation_pie',
                'monte_carlo_histogram'
            ],
            'include_sections': ['summary', 'optimization', 'risk', 'tax', 'recommendations']
        },
        'visualization_preferences': {
            'color_scheme': 'default',
            'chart_style': 'modern',
            'interactive': False,
            'save_figures': False,
            'figure_dpi': 100
        }
    }

    print("\nGenerating comprehensive report...")

    report = reporter.generate(report_config)

    print(f"\n✓ Report generated")
    print(f"  Figures created: {len(report['figures'])}")
    print(f"  Tables created: {len(report['tables'])}")

    print(f"\nGenerated figures:")
    for figure_name in report['figures'].keys():
        print(f"  - {figure_name}")

    print(f"\nGenerated tables:")
    for table_name in report['tables'].keys():
        print(f"  - {table_name}")

    # ========================================================================
    # DISPLAY EXECUTIVE SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("EXECUTIVE SUMMARY")
    print("=" * 70)

    exec_summary = report['executive_summary']
    print(f"\n{exec_summary['one_page_summary']}")

    print("\nKey Findings:")
    for i, finding in enumerate(exec_summary['key_findings'], 1):
        print(f"  {i}. {finding}")

    print("\nRecommendations:")
    for i, rec in enumerate(exec_summary['recommendations'], 1):
        print(f"  {i}. {rec}")

    print("\nRisks & Warnings:")
    for i, risk in enumerate(exec_summary['risks_and_warnings'], 1):
        print(f"  {i}. {risk}")

    # ========================================================================
    # WORKFLOW COMPLETE
    # ========================================================================
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE!")
    print("=" * 70)
    print("\nAll 5 modules executed successfully:")
    print("  ✓ Module 1: Economic scenarios generated")
    print("  ✓ Module 2: Household placements built (GSE+)")
    print("  ✓ Module 3: User profile processed")
    print("  ✓ Module 4: Placements optimized on GSE++")
    print("  ✓ Module 5: Reports generated")

    print("\n" + "=" * 70)
    print("Next steps:")
    print("  - Review the generated figures")
    print("  - Adjust user profile parameters")
    print("  - Try different optimization objectives")
    print("  - Try another placement catalog")
    print("  - Generate more scenarios for higher accuracy")
    print("=" * 70)

    return {
        'scenarios': scenario_results,
        'catalog': catalog.id,
        'profile_results': profile_results,
        'optimization_results': optimization_results,
        'report': report
    }


if __name__ == '__main__':
    try:
        results = main()
        print("\n✓ Example completed successfully!")
    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
        import traceback
        traceback.print_exc()
