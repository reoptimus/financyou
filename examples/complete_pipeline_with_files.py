"""
Complete FinancYou Pipeline with JSON Input Files

This example demonstrates the COMPLETE workflow from economic scenarios
to portfolio optimization using JSON configuration files.

WHAT THIS DOES:
1. Loads configuration from JSON files
2. Generates 1000 economic scenarios
3. Applies tax treatment
4. Processes user profile
5. Optimizes portfolio
6. Generates comprehensive report
7. Saves all results

RUNTIME: ~2 minutes
OUTPUT: HTML report + charts + JSON results

USAGE:
    python examples/complete_pipeline_with_files.py

CUSTOMIZATION:
    Edit JSON files in examples/input_files/ to customize:
    - scenario_config.json - Economic assumptions
    - tax_config_us.json - Tax configuration
    - user_profile_aggressive.json - Investor profile
    - optimization_config.json - Optimization parameters
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator.modules import (
    scenario_generator,
    tax_engine,
    user_profile,
    optimizer,
    reporting
)


def load_json_config(filename):
    """Load JSON configuration file."""
    filepath = Path(__file__).parent / 'input_files' / filename
    with open(filepath, 'r') as f:
        config = json.load(f)
    # Remove comment fields
    return {k: v for k, v in config.items() if not k.startswith('_')}


def save_results(results, output_dir='outputs'):
    """Save results to files."""
    output_path = Path(__file__).parent.parent / output_dir
    output_path.mkdir(exist_ok=True)

    # Save HTML report
    if 'report' in results and results['report'].get('html'):
        with open(output_path / 'investment_report.html', 'w') as f:
            f.write(results['report']['html'])
        print(f"  ✓ Saved: {output_path / 'investment_report.html'}")

    # Save portfolio as JSON
    if 'optimal_portfolio' in results:
        with open(output_path / 'optimal_portfolio.json', 'w') as f:
            json.dump(results['optimal_portfolio'], f, indent=2)
        print(f"  ✓ Saved: {output_path / 'optimal_portfolio.json'}")

    # Save figures
    if 'figures' in results:
        for name, fig_data in results['figures'].items():
            if 'figure' in fig_data:
                fig_path = output_path / f"{name}.png"
                fig_data['figure'].savefig(fig_path, dpi=150, bbox_inches='tight')
                print(f"  ✓ Saved: {fig_path}")


def print_section(title):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"{title}")
    print("=" * 70)


def main():
    """Run complete pipeline."""
    start_time = datetime.now()

    print("=" * 70)
    print("FINANCYOU - COMPLETE PIPELINE WITH JSON INPUT FILES")
    print("=" * 70)
    print(f"\nStarted at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis pipeline will:")
    print("  1. Load configuration from JSON files")
    print("  2. Generate economic scenarios")
    print("  3. Apply tax treatment")
    print("  4. Process user profile")
    print("  5. Optimize portfolio")
    print("  6. Generate comprehensive report")
    print("  7. Save all results to 'outputs/' directory")

    # ========================================================================
    # STEP 1: LOAD CONFIGURATIONS
    # ========================================================================
    print_section("STEP 1: LOADING CONFIGURATIONS")

    print("\nLoading JSON configuration files...")

    # Load all configs
    scenario_config = load_json_config('scenario_config.json')
    tax_config_data = load_json_config('tax_config_us.json')
    user_profile_data = load_json_config('user_profile_aggressive.json')
    optimization_config = load_json_config('optimization_config.json')

    print(f"  ✓ scenario_config.json")
    print(f"  ✓ tax_config_us.json")
    print(f"  ✓ user_profile_aggressive.json")
    print(f"  ✓ optimization_config.json")

    print(f"\nConfiguration summary:")
    print(f"  Scenarios to generate: {scenario_config['num_scenarios']}")
    print(f"  Time horizon: {scenario_config['time_horizon']} years")
    print(f"  Tax jurisdiction: {tax_config_data['jurisdiction']}")
    print(f"  Investor age: {user_profile_data['user_profile']['personal_info']['age']}")
    print(f"  Risk tolerance: {user_profile_data['user_profile']['investment_preferences']['risk_tolerance']}")
    print(f"  Optimization objective: {optimization_config['optimization_objective']}")

    # ========================================================================
    # STEP 2: GENERATE ECONOMIC SCENARIOS
    # ========================================================================
    print_section("STEP 2: GENERATING ECONOMIC SCENARIOS")

    print(f"\nGenerating {scenario_config['num_scenarios']} scenarios...")

    gen = scenario_generator.ScenarioGenerator(random_seed=42)
    scenario_results = gen.generate(scenario_config)

    scenarios_df = scenario_results['scenarios']
    diagnostics = scenario_results['diagnostics']

    print(f"✓ Generated {scenarios_df['scenario_id'].nunique()} scenarios")
    print(f"\nDiagnostics:")
    print(f"  Mean stock return: {diagnostics['mean_returns']['stock_return']:.2%}")
    print(f"  Mean bond return: {diagnostics['mean_returns']['bond_return']:.2%}")
    print(f"  Mean real estate return: {diagnostics['mean_returns']['real_estate_return']:.2%}")
    print(f"  Stock volatility: {diagnostics['volatilities']['stock_return']:.2%}")
    print(f"  Stock-bond correlation: {diagnostics['correlations'].loc['stock_return', 'bond_return']:.2f}")

    # ========================================================================
    # STEP 3: APPLY TAX TREATMENT
    # ========================================================================
    print_section("STEP 3: APPLYING TAX TREATMENT")

    print(f"\nApplying {tax_config_data['jurisdiction']} tax rules...")

    engine = tax_engine.TaxEngine()

    # Get preset tax configuration for jurisdiction
    tax_config_preset = tax_engine.TaxConfigPreset.get_preset(tax_config_data['jurisdiction'])

    # Apply taxes
    tax_results = engine.apply_taxes({
        'scenarios': scenarios_df,
        'tax_config': tax_config_preset,
        'investment_allocation': tax_config_data['investment_allocation']
    })

    after_tax_scenarios = tax_results['after_tax_scenarios']

    print(f"✓ Calculated after-tax returns")

    if 'tax_tables' in tax_results and 'effective_tax_rate' in tax_results['tax_tables']:
        effective_rates = tax_results['tax_tables']['effective_tax_rate']
        if not effective_rates.empty:
            print(f"\nTax Impact:")
            print(f"  Mean effective tax rate: {effective_rates['effective_tax_rate'].mean():.1%}")
            print(f"  Tax drag on returns: {after_tax_scenarios['annual_tax_drag'].mean():.2%}")

    print(f"\nAllocation across account types:")
    for asset, allocation in tax_config_data['investment_allocation'].items():
        print(f"  {asset}:")
        for account_type, pct in allocation.items():
            print(f"    {account_type}: {pct:.0%}")

    # ========================================================================
    # STEP 4: PROCESS USER PROFILE
    # ========================================================================
    print_section("STEP 4: PROCESSING USER PROFILE")

    manager = user_profile.UserProfileManager()

    print(f"\nProcessing user profile...")

    profile_results = manager.process(user_profile_data)

    validated = profile_results['validated_profile']
    risk_prof = profile_results['risk_profile']
    life_stages = profile_results['life_stages']
    summary_stats = profile_results['summary_statistics']

    print(f"✓ Profile processed and validated")

    if profile_results['validation_warnings']:
        print(f"\nWarnings:")
        for warning in profile_results['validation_warnings']:
            print(f"  ⚠ {warning}")

    print(f"\nRisk Profile:")
    print(f"  Risk score: {risk_prof['score']:.0f}/100")
    print(f"  Recommended allocation:")
    for asset, weight in risk_prof['recommended_allocation'].items():
        print(f"    {asset}: {weight:.1%}")

    print(f"\nLife Stages:")
    for stage, info in life_stages.items():
        print(f"  {stage.capitalize()}: Age {info['start']}-{info['end']} ({info['duration']} years)")

    print(f"\nInvestment Plan:")
    print(f"  Total contributions: ${summary_stats['total_contributions']:,.0f}")
    print(f"  Contribution years: {summary_stats['contribution_years']}")
    print(f"  Average annual: ${summary_stats['average_annual_contribution']:,.0f}")

    # ========================================================================
    # STEP 5: OPTIMIZE PORTFOLIO
    # ========================================================================
    print_section("STEP 5: OPTIMIZING PORTFOLIO")

    print(f"\nOptimizing with objective: {optimization_config['optimization_objective']}")

    opt = optimizer.PortfolioOptimizer()

    # Build optimization config
    opt_config = {
        'scenarios': after_tax_scenarios,
        'user_constraints': validated['constraints'],
        'investment_time_series': profile_results['investment_time_series'],
        'optimization_objective': optimization_config['optimization_objective'],
        'optimization_params': optimization_config['optimization_params'],
        'goal_amount': optimization_config['goal_amount']
    }

    optimization_results = opt.optimize(opt_config)

    optimal = optimization_results['optimal_portfolio']
    sim_stats = optimization_results['simulation_results']['statistics']
    goal_analysis = optimization_results['goal_analysis']

    print(f"✓ Optimization complete")

    print(f"\nOptimal Portfolio:")
    for asset, weight in optimal['weights'].items():
        print(f"  {asset}: {weight:.1%}")

    print(f"\nExpected Performance:")
    print(f"  Expected return: {optimal['expected_return']:.2%}")
    print(f"  Expected volatility: {optimal['expected_volatility']:.2%}")
    print(f"  Sharpe ratio: {optimal['sharpe_ratio']:.2f}")
    print(f"  Max drawdown: {optimal['max_drawdown']:.1%}")

    print(f"\nMonte Carlo Simulation ({scenario_config['num_scenarios']} scenarios):")
    print(f"  Median terminal wealth: ${sim_stats['median_terminal_wealth']:,.0f}")
    print(f"  Mean terminal wealth: ${sim_stats['mean_terminal_wealth']:,.0f}")
    print(f"  5th percentile: ${sim_stats['percentiles']['5']:,.0f}")
    print(f"  95th percentile: ${sim_stats['percentiles']['95']:,.0f}")

    print(f"\nGoal Analysis:")
    print(f"  Target: ${goal_analysis['goal_amount']:,.0f}")
    print(f"  Probability of achieving: {goal_analysis['probability_of_achieving']:.1%}")

    # ========================================================================
    # STEP 6: GENERATE REPORT
    # ========================================================================
    print_section("STEP 6: GENERATING COMPREHENSIVE REPORT")

    print(f"\nGenerating visualizations and report...")

    reporter = reporting.ReportGenerator()

    report_results = reporter.generate({
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
            ]
        },
        'visualization_preferences': {
            'color_scheme': 'default',
            'save_figures': True,
            'figure_dpi': 150
        }
    })

    print(f"✓ Report generated")
    print(f"\nGenerated charts:")
    for chart_name in report_results['figures'].keys():
        print(f"  ✓ {chart_name}")

    print(f"\nGenerated tables:")
    for table_name in report_results['tables'].keys():
        print(f"  ✓ {table_name}")

    # ========================================================================
    # STEP 7: SAVE RESULTS
    # ========================================================================
    print_section("STEP 7: SAVING RESULTS")

    print(f"\nSaving all results to 'outputs/' directory...")

    # Combine results for saving
    all_results = {
        'report': report_results['report'],
        'figures': report_results['figures'],
        'optimal_portfolio': optimal,
        'simulation_statistics': sim_stats,
        'goal_analysis': goal_analysis
    }

    save_results(all_results)

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print_section("EXECUTIVE SUMMARY")

    exec_summary = report_results['executive_summary']

    print(f"\n{exec_summary['one_page_summary']}")

    print(f"\nKey Findings:")
    for i, finding in enumerate(exec_summary['key_findings'], 1):
        print(f"  {i}. {finding}")

    print(f"\nRecommendations:")
    for i, rec in enumerate(exec_summary['recommendations'], 1):
        print(f"  {i}. {rec}")

    print(f"\nRisks & Warnings:")
    for i, risk in enumerate(exec_summary['risks_and_warnings'], 1):
        print(f"  {i}. {risk}")

    # ========================================================================
    # COMPLETION
    # ========================================================================
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print_section("PIPELINE COMPLETE!")

    print(f"\n✓ All 5 modules executed successfully")
    print(f"✓ All results saved to 'outputs/' directory")
    print(f"\nTotal runtime: {duration:.1f} seconds")
    print(f"\nNext steps:")
    print(f"  1. Open outputs/investment_report.html in your browser")
    print(f"  2. Review the charts in outputs/ directory")
    print(f"  3. Check outputs/optimal_portfolio.json for raw data")
    print(f"\nTo customize:")
    print(f"  - Edit files in examples/input_files/")
    print(f"  - Run this script again")

    print("\n" + "=" * 70)

    return all_results


if __name__ == '__main__':
    try:
        results = main()
        print("\n✓ Pipeline completed successfully!")
        print("\nOutput files created:")
        print("  - outputs/investment_report.html")
        print("  - outputs/optimal_portfolio.json")
        print("  - outputs/*.png (charts)")
    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
