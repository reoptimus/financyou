"""
Complete Workflow Example - All 5 Modules

This example demonstrates the full FinancYou pipeline:
1. Generate economic scenarios
2. Apply tax treatment
3. Process user profile
4. Optimize portfolio
5. Generate reports

Run this example to see all modules working together.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator.modules import (
    scenario_generator,
    tax_engine,
    user_profile,
    optimizer,
    reporting
)


def main():
    """Run complete workflow."""
    print("=" * 70)
    print("FINANCYOU - COMPLETE WORKFLOW DEMONSTRATION")
    print("=" * 70)
    print("\nThis example demonstrates all 5 modules working together:")
    print("1. Economic Scenario Generator (GSE)")
    print("2. Tax-Integrated Scenarios (GSE+)")
    print("3. User Input & Investment Time Series")
    print("4. Portfolio Optimization (MOCA)")
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
    # STEP 2: APPLY TAX TREATMENT
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 2: APPLYING TAX TREATMENT")
    print("=" * 70)

    engine = tax_engine.TaxEngine()

    # Use US tax configuration
    tax_config = tax_engine.TaxConfigPreset.get_preset('US')
    print(f"\nUsing tax jurisdiction: {tax_config['jurisdiction']}")
    print(f"  Dividend tax rate: {tax_config['account_types']['taxable']['dividend_tax_rate']:.1%}")
    print(f"  Capital gains rate: {tax_config['account_types']['taxable']['capital_gains_rate']:.1%}")

    # Define investment allocation across account types
    allocation = {
        'stocks': {
            'taxable': 0.6,
            'tax_deferred': 0.3,
            'tax_free': 0.1
        },
        'bonds': {
            'taxable': 0.4,
            'tax_deferred': 0.5,
            'tax_free': 0.1
        },
        'real_estate': {
            'taxable': 0.7,
            'tax_deferred': 0.2,
            'tax_free': 0.1
        }
    }

    print("\nAsset allocation across account types:")
    print("  Stocks: 60% taxable, 30% tax-deferred, 10% tax-free")
    print("  Bonds: 40% taxable, 50% tax-deferred, 10% tax-free")
    print("  Real Estate: 70% taxable, 20% tax-deferred, 10% tax-free")

    tax_results = engine.apply_taxes({
        'scenarios': scenarios_df,
        'tax_config': tax_config,
        'investment_allocation': allocation
    })

    after_tax_scenarios = tax_results['after_tax_scenarios']
    print(f"\n✓ Calculated after-tax returns")
    print(f"  Average tax drag: {after_tax_scenarios['annual_tax_drag'].mean():.2%}")

    # Show effective tax rates
    effective_rates = tax_results['tax_tables']['effective_tax_rate']
    if not effective_rates.empty:
        print(f"  Mean effective tax rate: {effective_rates['effective_tax_rate'].mean():.1%}")
        print(f"  Min effective tax rate: {effective_rates['effective_tax_rate'].min():.1%}")
        print(f"  Max effective tax rate: {effective_rates['effective_tax_rate'].max():.1%}")

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
    # STEP 4: OPTIMIZE PORTFOLIO
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 4: OPTIMIZING PORTFOLIO")
    print("=" * 70)

    opt = optimizer.PortfolioOptimizer()

    optimization_config = {
        'scenarios': after_tax_scenarios,
        'user_constraints': profile_results['validated_profile']['constraints'],
        'investment_time_series': profile_results['investment_time_series'],
        'optimization_objective': 'max_sharpe',
        'optimization_params': {
            'target_return': 0.08,
            'risk_aversion': 5.0,
            'confidence_level': 0.95,
            'min_weight': 0.0,
            'max_weight': 1.0,
            'rebalancing_threshold': 0.05
        },
        'goal_amount': 2000000  # $2M retirement goal
    }

    print(f"\nOptimization objective: {optimization_config['optimization_objective']}")
    print(f"Goal amount: ${optimization_config['goal_amount']:,}")

    optimization_results = opt.optimize(optimization_config)

    print(f"\n✓ Optimization complete")
    print(f"\nOptimal Portfolio:")
    for asset, weight in optimization_results['optimal_portfolio']['weights'].items():
        print(f"  {asset}: {weight:.1%}")

    portfolio_stats = optimization_results['optimal_portfolio']
    print(f"\nExpected Performance:")
    print(f"  Expected return: {portfolio_stats['expected_return']:.2%}")
    print(f"  Expected volatility: {portfolio_stats['expected_volatility']:.2%}")
    print(f"  Sharpe ratio: {portfolio_stats['sharpe_ratio']:.2f}")
    print(f"  Max drawdown: {portfolio_stats['max_drawdown']:.1%}")

    # Simulation results
    sim_stats = optimization_results['simulation_results']['statistics']
    print(f"\nMonte Carlo Simulation Results ({scenario_config['num_scenarios']} scenarios):")
    print(f"  Median terminal wealth: ${sim_stats['median_terminal_wealth']:,.0f}")
    print(f"  Mean terminal wealth: ${sim_stats['mean_terminal_wealth']:,.0f}")
    print(f"\nPercentiles:")
    print(f"  5th percentile: ${sim_stats['percentiles']['5']:,.0f}")
    print(f"  25th percentile: ${sim_stats['percentiles']['25']:,.0f}")
    print(f"  75th percentile: ${sim_stats['percentiles']['75']:,.0f}")
    print(f"  95th percentile: ${sim_stats['percentiles']['95']:,.0f}")

    print(f"\nRisk Metrics:")
    print(f"  VaR (95%): ${sim_stats['var_95']:,.0f}")
    print(f"  CVaR (95%): ${sim_stats['cvar_95']:,.0f}")

    # Goal analysis
    goal_analysis = optimization_results['goal_analysis']
    print(f"\nGoal Analysis:")
    print(f"  Target amount: ${goal_analysis['goal_amount']:,.0f}")
    print(f"  Probability of achieving: {goal_analysis['probability_of_achieving']:.1%}")
    print(f"  Expected surplus/deficit: ${goal_analysis['expected_surplus_deficit']:,.0f}")

    # ========================================================================
    # STEP 5: GENERATE REPORTS
    # ========================================================================
    print("\n" + "=" * 70)
    print("STEP 5: GENERATING REPORTS & VISUALIZATIONS")
    print("=" * 70)

    reporter = reporting.ReportGenerator()

    report_config = {
        'scenarios': scenario_results,
        'tax_results': tax_results,
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
                'monte_carlo_histogram',
                'tax_impact_waterfall'
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
    print("  ✓ Module 2: Tax treatment applied")
    print("  ✓ Module 3: User profile processed")
    print("  ✓ Module 4: Portfolio optimized")
    print("  ✓ Module 5: Reports generated")

    print("\n" + "=" * 70)
    print("Next steps:")
    print("  - Review the generated figures")
    print("  - Adjust user profile parameters")
    print("  - Try different optimization objectives")
    print("  - Experiment with tax jurisdictions")
    print("  - Generate more scenarios for higher accuracy")
    print("=" * 70)

    return {
        'scenarios': scenario_results,
        'tax_results': tax_results,
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
