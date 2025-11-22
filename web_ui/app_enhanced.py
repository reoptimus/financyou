"""
FinancYou Enhanced Dashboard

Comprehensive multi-page Streamlit application inspired by R Shiny interface.
Includes: Profile, Assets, Projects, Projections, and Analysis sections.
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

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
    page_title="FinancYou - Comprehensive Financial Planning",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Initialize session state
def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        'user_data': {},
        'assets': [],
        'projects': [],
        'results': None,
        'authenticated': True,  # Skip login for now
        'page': 'Home'
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# Sidebar navigation
def render_sidebar():
    """Render sidebar with navigation."""
    with st.sidebar:
        st.image("https://via.placeholder.com/250x80/1f77b4/ffffff?text=FinancYou", use_column_width=True)

        st.markdown("---")
        st.markdown("### 📋 Navigation")

        pages = {
            "🏠 Home": "Home",
            "👤 Your Profile": "Profile",
            "💼 Your Assets": "Assets",
            "🎯 Your Projects": "Projects",
            "📊 Projections": "Projections",
            "📈 Analysis": "Analysis"
        }

        for label, page in pages.items():
            if st.button(label, use_container_width=True, key=f"nav_{page}"):
                st.session_state.page = page
                st.rerun()

        st.markdown("---")
        st.markdown("### ⚙️ Settings")

        st.session_state.jurisdiction = st.selectbox(
            "Tax Jurisdiction",
            ["US", "FR", "UK"],
            key="jurisdiction_select"
        )

        st.session_state.num_scenarios = st.slider(
            "Monte Carlo Scenarios",
            10, 500, 100, 10,
            key="scenarios_slider"
        )


# Page: Home
def page_home():
    """Home page with overview and quick actions."""
    st.markdown("# 💰 FinancYou")
    st.markdown("### Comprehensive Financial Planning & Portfolio Optimization")

    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🎯 Quick Start")
        st.markdown("""
        1. **Enter your profile** → Personal & financial info
        2. **Add your assets** → Current investments
        3. **Define projects** → Future goals
        4. **Run analysis** → Get optimized recommendations
        """)

    with col2:
        st.markdown("### 📊 Key Features")
        st.markdown("""
        - Multi-jurisdiction tax optimization
        - Monte Carlo simulations
        - Goal-based planning
        - Risk profiling
        - Efficient frontier analysis
        """)

    with col3:
        st.markdown("### 🚀 Get Started")
        if st.button("📝 Complete Your Profile", use_container_width=True):
            st.session_state.page = "Profile"
            st.rerun()

        if st.button("📥 Load Example", use_container_width=True):
            load_example_profile()
            st.success("Example profile loaded!")

    # Display summary if data exists
    if st.session_state.user_data:
        st.markdown("---")
        st.markdown("### 📌 Your Summary")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Age", st.session_state.user_data.get('age', 'N/A'))
        with col2:
            st.metric("Assets", f"{len(st.session_state.assets)}")
        with col3:
            st.metric("Projects", f"{len(st.session_state.projects)}")
        with col4:
            if st.session_state.results:
                st.metric("Status", "✅ Analyzed")
            else:
                st.metric("Status", "⏳ Pending")


# Page: Profile
def page_profile():
    """User profile page - comprehensive personal and financial information."""
    st.markdown("# 👤 Your Profile")

    tabs = st.tabs([
        "👨‍👩‍👧‍👦 Personal Info",
        "💵 Income & Expenses",
        "🏠 Housing",
        "👔 Professional",
        "🎯 Investment Preferences"
    ])

    # Tab 1: Personal Information
    with tabs[0]:
        st.markdown("### Personal Information")

        col1, col2, col3 = st.columns(3)

        with col1:
            age = st.number_input("Current Age", 18, 100,
                                 st.session_state.user_data.get('age', 35))
            retirement_age = st.number_input("Retirement Age", age, 100,
                                           st.session_state.user_data.get('retirement_age', 65))

        with col2:
            life_expectancy = st.number_input("Life Expectancy", retirement_age, 120,
                                            st.session_state.user_data.get('life_expectancy', 90))
            num_dependents = st.number_input("Number of Dependents", 0, 10, 0)

        with col3:
            country = st.selectbox("Country", ["US", "FR", "UK", "DE", "CA"],
                                  index=0)
            currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "CAD"],
                                   index=0)

        # Children ages
        if num_dependents > 0:
            st.markdown("#### Children Ages")
            children_ages = []
            cols = st.columns(min(num_dependents, 3))
            for i in range(num_dependents):
                with cols[i % 3]:
                    age_child = st.number_input(f"Child {i+1}", 0, 25, 0, key=f"child_{i}")
                    children_ages.append(age_child)

    # Tab 2: Income & Expenses
    with tabs[1]:
        st.markdown("### Income & Expenses")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Income")
            annual_income = st.number_input("Annual Income ($)", 0, 1000000, 75000, 1000)

            num_earners = st.radio("Number of Earners", [1, 2], horizontal=True)

            if num_earners == 2:
                annual_income_2 = st.number_input("Partner's Annual Income ($)", 0, 1000000, 60000, 1000)

            income_growth = st.slider("Expected Annual Salary Growth (%)", 0.0, 10.0, 3.0, 0.5)

        with col2:
            st.markdown("#### Expenses & Savings")
            annual_expenses = st.number_input("Annual Expenses ($)", 0, 500000, 55000, 1000)

            savings_rate = st.slider("Target Savings Rate (%)", 0.0, 50.0, 15.0, 1.0)

            st.metric("Monthly Savings", f"${(annual_income - annual_expenses) / 12:,.0f}")

    # Tab 3: Housing
    with tabs[2]:
        st.markdown("### Housing Situation")

        housing_status = st.radio(
            "Housing Status",
            ["Owner (No Mortgage)", "Owner (With Mortgage)", "Renter"],
            horizontal=True
        )

        if housing_status == "Owner (No Mortgage)":
            property_value = st.number_input("Property Value ($)", 0, 10000000, 300000, 10000)

        elif housing_status == "Owner (With Mortgage)":
            col1, col2 = st.columns(2)
            with col1:
                property_value = st.number_input("Property Value ($)", 0, 10000000, 300000, 10000)
                mortgage_remaining = st.number_input("Remaining Mortgage ($)", 0, property_value, 200000, 5000)

            with col2:
                mortgage_years_total = st.number_input("Total Mortgage Term (years)", 1, 40, 30)
                mortgage_years_remaining = st.number_input("Years Remaining", 1, mortgage_years_total, 25)
                mortgage_rate = st.slider("Mortgage Interest Rate (%)", 0.0, 10.0, 3.5, 0.1)
                monthly_payment = st.number_input("Monthly Payment ($)", 0, 10000, 1500, 50)

        else:  # Renter
            monthly_rent = st.number_input("Monthly Rent ($)", 0, 10000, 1500, 50)

    # Tab 4: Professional
    with tabs[3]:
        st.markdown("### Professional Situation")

        col1, col2 = st.columns(2)

        with col1:
            profession = st.selectbox(
                "Profession Category",
                ["Employee", "Self-Employed", "Executive", "Retired", "Other"]
            )

            years_to_retirement = retirement_age - age
            st.metric("Years to Retirement", years_to_retirement)

        with col2:
            if profession != "Retired":
                job_security = st.select_slider(
                    "Job Security",
                    options=["Low", "Medium", "High"],
                    value="Medium"
                )

    # Tab 5: Investment Preferences
    with tabs[4]:
        st.markdown("### Investment Preferences")

        col1, col2 = st.columns(2)

        with col1:
            risk_tolerance = st.select_slider(
                "Risk Tolerance",
                options=["conservative", "moderate", "aggressive"],
                value="moderate"
            )

            investment_goal = st.selectbox(
                "Primary Goal",
                ["retirement", "wealth accumulation", "income generation", "education", "major purchase"]
            )

        with col2:
            max_equity = st.slider("Maximum Equity Allocation (%)", 0, 100, 80, 5)
            min_bonds = st.slider("Minimum Bond Allocation (%)", 0, 100, 15, 5)

        esg_focus = st.checkbox("ESG (Environmental/Social/Governance) Focus")

    # Save button
    st.markdown("---")
    if st.button("💾 Save Profile", type="primary", use_container_width=True):
        st.session_state.user_data = {
            'age': age,
            'retirement_age': retirement_age,
            'life_expectancy': life_expectancy,
            'annual_income': annual_income,
            'annual_expenses': annual_expenses,
            'risk_tolerance': risk_tolerance,
            'investment_goal': investment_goal,
            'max_equity': max_equity / 100,
            'min_bonds': min_bonds / 100,
            'country': country,
            'currency': currency
        }
        st.success("✅ Profile saved successfully!")


# Page: Assets
def page_assets():
    """Asset management page."""
    st.markdown("# 💼 Your Assets")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Current Portfolio")

        if st.session_state.assets:
            df = pd.DataFrame(st.session_state.assets)
            st.dataframe(df, use_container_width=True)

            # Asset allocation pie chart
            fig = px.pie(
                df,
                values='value',
                names='asset_type',
                title='Asset Allocation'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No assets added yet. Add your first asset using the form →")

    with col2:
        st.markdown("### Add Asset")

        with st.form("add_asset"):
            asset_type = st.selectbox(
                "Asset Type",
                ["Stocks", "Bonds", "Real Estate", "Cash", "Alternative"]
            )

            asset_name = st.text_input("Asset Name", "e.g., S&P 500 Index Fund")

            value = st.number_input("Current Value ($)", 0, 10000000, 10000, 1000)

            account_type = st.selectbox(
                "Account Type",
                ["Taxable", "Tax-Deferred (401k/IRA)", "Tax-Free (Roth)"]
            )

            if st.form_submit_button("➕ Add Asset", use_container_width=True):
                st.session_state.assets.append({
                    'asset_type': asset_type,
                    'name': asset_name,
                    'value': value,
                    'account_type': account_type,
                    'date_added': datetime.now().strftime("%Y-%m-%d")
                })
                st.success(f"✅ Added {asset_name}")
                st.rerun()


# Page: Projects
def page_projects():
    """Project planning page."""
    st.markdown("# 🎯 Your Projects")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Planned Projects")

        if st.session_state.projects:
            df = pd.DataFrame(st.session_state.projects)
            st.dataframe(df, use_container_width=True)

            # Project timeline
            if 'year' in df.columns and 'amount' in df.columns:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df['year'],
                    y=df['amount'],
                    name='Project Cost',
                    text=df['name'],
                    textposition='auto'
                ))
                fig.update_layout(title='Project Timeline', xaxis_title='Year', yaxis_title='Amount ($)')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No projects planned yet. Add your first project using the form →")

    with col2:
        st.markdown("### Add Project")

        with st.form("add_project"):
            project_type = st.selectbox(
                "Project Type",
                ["Vacation", "Home Purchase", "Education", "Car", "Wedding", "Renovation", "Other"]
            )

            project_name = st.text_input("Project Name", f"My {project_type}")

            amount = st.number_input("Estimated Cost ($)", 0, 1000000, 5000, 1000)

            year = st.number_input("Target Year", 2024, 2050, 2025)

            priority = st.select_slider("Priority", options=["Low", "Medium", "High"])

            if st.form_submit_button("➕ Add Project", use_container_width=True):
                st.session_state.projects.append({
                    'type': project_type,
                    'name': project_name,
                    'amount': amount,
                    'year': year,
                    'priority': priority,
                    'date_added': datetime.now().strftime("%Y-%m-%d")
                })
                st.success(f"✅ Added project: {project_name}")
                st.rerun()


# Page: Projections
def page_projections():
    """Projections and analysis page."""
    st.markdown("# 📊 Projections")

    if not st.session_state.user_data:
        st.warning("⚠️ Please complete your profile first!")
        if st.button("Go to Profile"):
            st.session_state.page = "Profile"
            st.rerun()
        return

    col1, col2, col3 = st.columns(3)

    with col2:
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            with st.spinner("Running comprehensive analysis..."):
                results = run_comprehensive_analysis()
                st.session_state.results = results
                st.rerun()

    if st.session_state.results:
        display_projection_results(st.session_state.results)
    else:
        st.info("Click 'Run Analysis' to generate projections based on your profile, assets, and projects.")


def display_projection_results(results):
    """Display projection results."""
    tabs = st.tabs(["📈 Reference", "🎯 With Projects", "📊 Comparison", "📋 Details"])

    with tabs[0]:
        st.markdown("### Reference Projections (Without Projects)")

        col1, col2, col3, col4 = st.columns(4)

        portfolio = results['optimization']['optimal_portfolio']

        with col1:
            if 'expected_return' in portfolio:
                st.metric("Expected Return", f"{portfolio['expected_return']:.2%}")

        with col2:
            if 'volatility' in portfolio:
                st.metric("Portfolio Risk", f"{portfolio['volatility']:.2%}")

        with col3:
            if 'sharpe_ratio' in portfolio:
                st.metric("Sharpe Ratio", f"{portfolio['sharpe_ratio']:.2f}")

        with col4:
            st.metric("Time Horizon", f"{results['profile']['validated_profile']['personal_info']['life_expectancy'] - results['profile']['validated_profile']['personal_info']['age']} years")

    with tabs[1]:
        st.markdown("### Projections Including Your Projects")
        st.info("Project-adjusted projections will be displayed here after incorporating project costs and timing.")

    with tabs[2]:
        st.markdown("### Comparison: With vs. Without Projects")
        st.info("Side-by-side comparison of scenarios.")

    with tabs[3]:
        st.markdown("### Detailed Analysis")

        if st.checkbox("Show Optimal Portfolio Weights"):
            weights = results['optimization']['optimal_portfolio']['weights']
            df = pd.DataFrame({
                'Asset': list(weights.keys()),
                'Weight': list(weights.values())
            })
            st.dataframe(df.style.format({'Weight': '{:.2%}'}))


# Page: Analysis
def page_analysis():
    """Advanced analysis page."""
    st.markdown("# 📈 Advanced Analysis")

    if not st.session_state.results:
        st.warning("⚠️ Please run projections first!")
        return

    st.markdown("### Analysis Tools")

    analysis_type = st.selectbox(
        "Select Analysis",
        [
            "Efficient Frontier",
            "Risk Analysis",
            "Sensitivity Analysis",
            "Goal Achievement Probability",
            "Tax Impact Analysis"
        ]
    )

    if analysis_type == "Efficient Frontier":
        if 'efficient_frontier' in st.session_state.results['optimization']:
            frontier = st.session_state.results['optimization']['efficient_frontier']
            if len(frontier) > 0:
                fig = px.scatter(
                    frontier,
                    x='volatility',
                    y='expected_return',
                    title='Efficient Frontier',
                    labels={'volatility': 'Risk (Volatility)', 'expected_return': 'Expected Return'}
                )
                st.plotly_chart(fig, use_container_width=True)


def run_comprehensive_analysis():
    """Run the complete analysis pipeline."""
    try:
        # Build configuration from session state
        user_data = st.session_state.user_data

        profile_config = {
            'user_profile': {
                'personal_info': {
                    'age': user_data.get('age', 35),
                    'retirement_age': user_data.get('retirement_age', 65),
                    'life_expectancy': user_data.get('life_expectancy', 90),
                    'country': user_data.get('country', 'US'),
                    'currency': user_data.get('currency', 'USD')
                },
                'financial_situation': {
                    'current_savings': sum([a['value'] for a in st.session_state.assets]) if st.session_state.assets else 50000,
                    'annual_income': user_data.get('annual_income', 75000),
                    'annual_expenses': user_data.get('annual_expenses', 55000),
                    'debt': {'mortgage': 0, 'student_loans': 0, 'other': 0}
                },
                'investment_preferences': {
                    'risk_tolerance': user_data.get('risk_tolerance', 'moderate'),
                    'investment_goal': user_data.get('investment_goal', 'retirement'),
                    'time_horizon': user_data.get('retirement_age', 65) - user_data.get('age', 35),
                    'esg_preferences': False,
                    'liquidity_needs': 0.1
                },
                'constraints': {
                    'max_equity_allocation': user_data.get('max_equity', 0.8),
                    'min_bond_allocation': user_data.get('min_bonds', 0.15),
                    'exclude_sectors': [],
                    'rebalancing_frequency': 'annual'
                }
            },
            'contribution_schedule': [{
                'start_year': 0,
                'end_year': user_data.get('retirement_age', 65) - user_data.get('age', 35),
                'monthly_amount': 1000,
                'annual_increase': 0.03,
                'account_type': 'tax_deferred'
            }],
            'withdrawal_schedule': []
        }

        # Run pipeline
        gen = scenario_generator.ScenarioGenerator(random_seed=42)
        scenario_results = gen.generate({
            'num_scenarios': st.session_state.get('num_scenarios', 100),
            'time_horizon': profile_config['user_profile']['investment_preferences']['time_horizon'],
            'timestep': 1.0,
            'use_stochastic': False
        })

        tax_eng = tax_engine.TaxEngine()
        tax_results = tax_eng.apply_taxes({
            'scenarios': scenario_results['scenarios'],
            'tax_config': tax_engine.TaxConfigPreset.get_preset(st.session_state.get('jurisdiction', 'US')),
            'investment_allocation': {
                'stocks': {'taxable': 0.6, 'tax_deferred': 0.3, 'tax_free': 0.1},
                'bonds': {'taxable': 0.5, 'tax_deferred': 0.4, 'tax_free': 0.1},
                'real_estate': {'taxable': 0.7, 'tax_deferred': 0.2, 'tax_free': 0.1}
            }
        })

        manager = user_profile.UserProfileManager()
        profile_results = manager.process(profile_config)

        opt = optimizer.PortfolioOptimizer()
        optimization_results = opt.optimize({
            'scenarios': tax_results['after_tax_scenarios'],
            'user_constraints': profile_config['user_profile']['constraints'],
            'investment_time_series': profile_results['investment_time_series'],
            'optimization_objective': 'max_sharpe'
        })

        return {
            'scenarios': scenario_results,
            'tax': tax_results,
            'profile': profile_results,
            'optimization': optimization_results
        }

    except Exception as e:
        st.error(f"Error during analysis: {str(e)}")
        return None


def load_example_profile():
    """Load an example profile."""
    st.session_state.user_data = {
        'age': 35,
        'retirement_age': 65,
        'life_expectancy': 90,
        'annual_income': 75000,
        'annual_expenses': 55000,
        'risk_tolerance': 'moderate',
        'investment_goal': 'retirement',
        'max_equity': 0.8,
        'min_bonds': 0.15,
        'country': 'US',
        'currency': 'USD'
    }


def main():
    """Main application function."""
    init_session_state()
    render_sidebar()

    # Route to appropriate page
    page = st.session_state.get('page', 'Home')

    if page == 'Home':
        page_home()
    elif page == 'Profile':
        page_profile()
    elif page == 'Assets':
        page_assets()
    elif page == 'Projects':
        page_projects()
    elif page == 'Projections':
        page_projections()
    elif page == 'Analysis':
        page_analysis()


if __name__ == "__main__":
    main()
