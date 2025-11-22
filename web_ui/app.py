"""
FinancYou Interactive Dashboard

A Streamlit web application for financial planning and portfolio optimization.
Provides an interactive interface to the FinancYou modular system.
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from investment_calculator.modules import (
    scenario_generator,
    tax_engine,
    user_profile,
    optimizer,
    reporting
)


# Page configuration
st.set_page_config(
    page_title="FinancYou - Financial Planning",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2ca02c;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'profile_config' not in st.session_state:
        st.session_state.profile_config = None


def create_personal_info_form():
    """Create personal information input form."""
    st.markdown('<div class="sub-header">Personal Information</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        age = st.number_input("Current Age", min_value=18, max_value=100, value=35, step=1)
        retirement_age = st.number_input("Retirement Age", min_value=age, max_value=100, value=65, step=1)

    with col2:
        life_expectancy = st.number_input("Life Expectancy", min_value=retirement_age, max_value=120, value=90, step=1)
        country = st.selectbox("Country", ["US", "FR", "UK", "DE", "CA"], index=0)

    with col3:
        currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "CAD"], index=0)

    return {
        'age': age,
        'retirement_age': retirement_age,
        'life_expectancy': life_expectancy,
        'country': country,
        'currency': currency
    }


def create_financial_situation_form():
    """Create financial situation input form."""
    st.markdown('<div class="sub-header">Financial Situation</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        current_savings = st.number_input("Current Savings ($)", min_value=0, value=50000, step=1000)
        annual_income = st.number_input("Annual Income ($)", min_value=0, value=75000, step=1000)
        annual_expenses = st.number_input("Annual Expenses ($)", min_value=0, value=55000, step=1000)

    with col2:
        st.markdown("**Debt**")
        mortgage = st.number_input("Mortgage ($)", min_value=0, value=200000, step=5000)
        student_loans = st.number_input("Student Loans ($)", min_value=0, value=0, step=1000)
        other_debt = st.number_input("Other Debt ($)", min_value=0, value=0, step=1000)

    return {
        'current_savings': current_savings,
        'annual_income': annual_income,
        'annual_expenses': annual_expenses,
        'debt': {
            'mortgage': mortgage,
            'student_loans': student_loans,
            'other': other_debt
        }
    }


def create_investment_preferences_form():
    """Create investment preferences input form."""
    st.markdown('<div class="sub-header">Investment Preferences</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        risk_tolerance = st.select_slider(
            "Risk Tolerance",
            options=["conservative", "moderate", "aggressive"],
            value="moderate"
        )

        investment_goal = st.selectbox(
            "Primary Investment Goal",
            ["retirement", "wealth", "income", "education"],
            index=0
        )

        time_horizon = st.number_input(
            "Investment Time Horizon (years)",
            min_value=1,
            max_value=50,
            value=30,
            step=1
        )

    with col2:
        esg_preferences = st.checkbox("ESG (Environmental/Social/Governance) Focus", value=False)

        liquidity_needs = st.slider(
            "Liquidity Needs (% of portfolio)",
            min_value=0.0,
            max_value=0.5,
            value=0.1,
            step=0.05,
            format="%.2f"
        )

    return {
        'risk_tolerance': risk_tolerance,
        'investment_goal': investment_goal,
        'time_horizon': time_horizon,
        'esg_preferences': esg_preferences,
        'liquidity_needs': liquidity_needs
    }


def create_constraints_form():
    """Create investment constraints form."""
    st.markdown('<div class="sub-header">Investment Constraints</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        max_equity = st.slider(
            "Maximum Equity Allocation (%)",
            min_value=0.0,
            max_value=1.0,
            value=0.80,
            step=0.05,
            format="%.2f"
        )

        min_bond = st.slider(
            "Minimum Bond Allocation (%)",
            min_value=0.0,
            max_value=1.0,
            value=0.15,
            step=0.05,
            format="%.2f"
        )

    with col2:
        rebalancing_frequency = st.selectbox(
            "Rebalancing Frequency",
            ["monthly", "quarterly", "semi-annual", "annual"],
            index=3
        )

    return {
        'max_equity_allocation': max_equity,
        'min_bond_allocation': min_bond,
        'exclude_sectors': [],
        'rebalancing_frequency': rebalancing_frequency
    }


def create_contribution_form():
    """Create contribution schedule form."""
    st.markdown('<div class="sub-header">Contribution Schedule</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        monthly_contribution = st.number_input(
            "Monthly Contribution ($)",
            min_value=0,
            value=1000,
            step=100
        )

    with col2:
        annual_increase = st.slider(
            "Annual Increase (%)",
            min_value=0.0,
            max_value=0.10,
            value=0.03,
            step=0.01,
            format="%.2f"
        )

    with col3:
        account_type = st.selectbox(
            "Account Type",
            ["tax_deferred", "taxable", "tax_free"],
            index=0
        )

    return [{
        'start_year': 0,
        'end_year': 30,
        'monthly_amount': monthly_contribution,
        'annual_increase': annual_increase,
        'account_type': account_type
    }]


def run_analysis(profile_config, jurisdiction, num_scenarios=100):
    """Run the complete financial planning analysis."""

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Step 1: Generate scenarios (20%)
        status_text.text("🎲 Generating economic scenarios...")
        scenario_config = {
            'num_scenarios': num_scenarios,
            'time_horizon': profile_config['user_profile']['investment_preferences']['time_horizon'],
            'timestep': 1.0,
            'use_stochastic': False,
            'currency': profile_config['user_profile']['personal_info']['currency']
        }

        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        scenario_results = gen.generate(scenario_config)
        progress_bar.progress(20)

        # Step 2: Apply taxes (40%)
        status_text.text("💰 Applying tax treatment...")
        tax_config = tax_engine.TaxConfigPreset.get_preset(jurisdiction)

        tax_allocation = {
            'stocks': {'taxable': 0.6, 'tax_deferred': 0.3, 'tax_free': 0.1},
            'bonds': {'taxable': 0.5, 'tax_deferred': 0.4, 'tax_free': 0.1},
            'real_estate': {'taxable': 0.7, 'tax_deferred': 0.2, 'tax_free': 0.1}
        }

        engine = tax_engine.TaxEngine()
        tax_results = engine.apply_taxes({
            'scenarios': scenario_results['scenarios'],
            'tax_config': tax_config,
            'investment_allocation': tax_allocation
        })
        progress_bar.progress(40)

        # Step 3: Process user profile (60%)
        status_text.text("👤 Processing user profile...")
        manager = user_profile.UserProfileManager()
        profile_results = manager.process(profile_config)
        progress_bar.progress(60)

        # Step 4: Optimize portfolio (80%)
        status_text.text("📊 Optimizing portfolio...")
        opt = optimizer.PortfolioOptimizer()
        optimizer_config = {
            'scenarios': tax_results['after_tax_scenarios'],
            'user_constraints': profile_config['user_profile']['constraints'],
            'investment_time_series': profile_results['investment_time_series'],
            'optimization_objective': 'max_sharpe'
        }

        optimization_results = opt.optimize(optimizer_config)
        progress_bar.progress(80)

        # Step 5: Generate report (100%)
        status_text.text("📄 Generating report...")
        reporter = reporting.ReportGenerator()
        report_config = {
            'scenarios': scenario_results['scenarios'],
            'tax_results': tax_results,
            'profile_results': profile_results,
            'optimization_results': optimization_results,
            'output_format': 'html'
        }

        report_results = reporter.generate(report_config)
        progress_bar.progress(100)

        status_text.text("✅ Analysis complete!")

        return {
            'scenarios': scenario_results,
            'tax': tax_results,
            'profile': profile_results,
            'optimization': optimization_results,
            'report': report_results
        }

    except Exception as e:
        status_text.text(f"❌ Error: {str(e)}")
        st.error(f"An error occurred during analysis: {str(e)}")
        return None


def display_results(results):
    """Display analysis results in tabs."""

    if results is None:
        return

    tabs = st.tabs(["📊 Overview", "💼 Portfolio", "📈 Projections", "🎯 Goals", "📄 Report"])

    with tabs[0]:
        display_overview(results)

    with tabs[1]:
        display_portfolio(results)

    with tabs[2]:
        display_projections(results)

    with tabs[3]:
        display_goals(results)

    with tabs[4]:
        display_report(results)


def display_overview(results):
    """Display overview tab."""
    st.markdown('<div class="sub-header">Analysis Overview</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    # Display key metrics
    profile = results['profile']
    optimization = results['optimization']

    with col1:
        st.metric(
            "Risk Score",
            f"{profile['risk_profile']['score']:.0f}/100"
        )

    with col2:
        if 'expected_return' in optimization['optimal_portfolio']:
            st.metric(
                "Expected Return",
                f"{optimization['optimal_portfolio']['expected_return']:.2%}"
            )

    with col3:
        if 'volatility' in optimization['optimal_portfolio']:
            st.metric(
                "Portfolio Risk",
                f"{optimization['optimal_portfolio']['volatility']:.2%}"
            )

    with col4:
        if 'sharpe_ratio' in optimization['optimal_portfolio']:
            st.metric(
                "Sharpe Ratio",
                f"{optimization['optimal_portfolio']['sharpe_ratio']:.2f}"
            )


def display_portfolio(results):
    """Display portfolio allocation tab."""
    st.markdown('<div class="sub-header">Optimal Portfolio Allocation</div>', unsafe_allow_html=True)

    weights = results['optimization']['optimal_portfolio']['weights']

    # Create pie chart
    df = pd.DataFrame({
        'Asset': list(weights.keys()),
        'Weight': list(weights.values())
    })

    st.bar_chart(df.set_index('Asset'))

    # Display weights table
    st.dataframe(df.style.format({'Weight': '{:.2%}'}))


def display_projections(results):
    """Display projections tab."""
    st.markdown('<div class="sub-header">Portfolio Projections</div>', unsafe_allow_html=True)

    # Display efficient frontier if available
    if 'efficient_frontier' in results['optimization']:
        frontier = results['optimization']['efficient_frontier']
        if len(frontier) > 0 and 'expected_return' in frontier.columns:
            st.line_chart(frontier.set_index('volatility')['expected_return'])


def display_goals(results):
    """Display goal analysis tab."""
    st.markdown('<div class="sub-header">Goal Achievement Analysis</div>', unsafe_allow_html=True)

    goal_analysis = results['optimization']['goal_analysis']

    if 'success_probability' in goal_analysis:
        st.metric(
            "Goal Success Probability",
            f"{goal_analysis['success_probability']:.1%}"
        )


def display_report(results):
    """Display full report tab."""
    st.markdown('<div class="sub-header">Comprehensive Report</div>', unsafe_allow_html=True)

    if 'report' in results and results['report'].get('html'):
        st.markdown(results['report']['html'], unsafe_allow_html=True)
    else:
        st.info("Report generation in progress...")


def main():
    """Main application function."""

    init_session_state()

    # Header
    st.markdown('<div class="main-header">💰 FinancYou</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="text-align: center; font-size: 1.2rem; color: #666;">Comprehensive Financial Planning & Portfolio Optimization</p>',
        unsafe_allow_html=True
    )

    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/300x100/1f77b4/ffffff?text=FinancYou", use_column_width=True)

        st.markdown("### Quick Actions")

        if st.button("📥 Load Example Profile"):
            # Load example aggressive profile
            example_path = Path(__file__).parent.parent / 'examples' / 'input_files' / 'user_profile_aggressive.json'
            if example_path.exists():
                with open(example_path, 'r') as f:
                    example_data = json.load(f)
                    st.session_state.profile_config = example_data
                    st.success("Example profile loaded!")

        st.markdown("---")

        st.markdown("### Settings")
        jurisdiction = st.selectbox("Tax Jurisdiction", ["US", "FR", "UK"], index=0)
        num_scenarios = st.slider("Number of Scenarios", 10, 500, 100, 10)

        st.markdown("---")
        st.markdown("### About")
        st.info("FinancYou provides comprehensive financial planning with tax-optimized portfolio recommendations.")

    # Main content
    with st.expander("📋 User Profile", expanded=True):
        personal_info = create_personal_info_form()
        financial_situation = create_financial_situation_form()
        investment_prefs = create_investment_preferences_form()
        constraints = create_constraints_form()
        contributions = create_contribution_form()

        # Compile profile
        profile_config = {
            'user_profile': {
                'personal_info': personal_info,
                'financial_situation': financial_situation,
                'investment_preferences': investment_prefs,
                'constraints': constraints
            },
            'contribution_schedule': contributions,
            'withdrawal_schedule': []
        }

        st.session_state.profile_config = profile_config

    # Run analysis button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            with st.spinner("Running comprehensive analysis..."):
                results = run_analysis(
                    st.session_state.profile_config,
                    jurisdiction,
                    num_scenarios
                )
                st.session_state.results = results

    # Display results
    if st.session_state.results:
        st.markdown("---")
        display_results(st.session_state.results)


if __name__ == "__main__":
    main()
