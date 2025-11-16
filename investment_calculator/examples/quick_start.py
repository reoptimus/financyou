"""
Quick Start Example

A minimal example to get started with the investment calculator quickly.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from investment_calculator import (
    PersonalVariables,
    InvestmentProfile,
    GlobalScenarioEngine,
    TaxIntegratedScenarioEngine,
    TaxConfig,
    AccountType,
    MOCA,
    RiskTolerance,
    InvestmentGoal,
)


def main():
    """Quick start example"""

    # 1. Define your personal information
    personal_vars = PersonalVariables(
        age=30,
        annual_income=75000,
        current_savings=20000,
        monthly_contribution=1000,
        risk_tolerance=RiskTolerance.MODERATE,
        investment_horizon=30,
        tax_bracket=0.22,
        capital_gains_rate=0.15,
    )

    profile = InvestmentProfile(
        personal_vars=personal_vars,
        primary_goal=InvestmentGoal.RETIREMENT,
    )

    # 2. Generate economic scenarios
    gse = GlobalScenarioEngine(random_seed=42)
    scenarios = gse.generate_standard_scenarios(years=30)

    # 3. Apply tax calculations
    tax_config = TaxConfig(
        ordinary_income_rate=0.22,
        long_term_cap_gains_rate=0.15,
    )
    gse_plus = TaxIntegratedScenarioEngine(tax_config=tax_config)

    tax_scenarios = [
        gse_plus.generate_tax_integrated_scenario(scenario, AccountType.TAXABLE)
        for scenario in scenarios
    ]

    # 4. Run investment analysis
    moca = MOCA(investment_profile=profile)

    # Use recommended allocation
    allocation = profile.get_recommended_asset_allocation()

    # Run simulations
    results = moca.run_scenarios(tax_scenarios, allocation)

    # 5. View results
    print(moca.generate_report())


if __name__ == "__main__":
    main()
