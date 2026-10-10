"""
FinancYou Modules Package

This package contains the 5 core modules of the FinancYou system:

1. scenario_generator - Economic Scenario Generator (GSE)
2. tax_engine - Tax-Integrated Scenarios (GSE+)
3. user_profile - User Input & Investment Time Series
4. placements, net_returns, placement_optimizer, wealth_simulation,
   placement_plan - GSE+ par placement, GSE++ net de frais et d'impôts,
   Markowitz par horizon et projection du patrimoine (ADR 0002)
5. reporting - Visualization & Reporting

Each module has clear input/output structures documented in ARCHITECTURE.md

Example usage:
    >>> from investment_calculator.modules import scenario_generator, tax_engine
    >>> gen = scenario_generator.ScenarioGenerator()
    >>> results = gen.generate({'num_scenarios': 1000, 'time_horizon': 30, 'timestep': 1.0})

For a complete workflow example, see examples/complete_workflow_modules.py
"""

from investment_calculator.modules import (
    net_returns,
    placement_optimizer,
    placement_plan,
    placements,
    reporting,
    scenario_generator,
    tax_engine,
    user_profile,
    wealth_simulation,
)

__all__ = [
    'scenario_generator',
    'tax_engine',
    'user_profile',
    'placements',
    'net_returns',
    'placement_optimizer',
    'wealth_simulation',
    'placement_plan',
    'reporting'
]

__version__ = '2.0.0'

# Module descriptions for documentation
MODULE_DESCRIPTIONS = {
    'scenario_generator': 'Generate Monte Carlo economic scenarios for all asset classes',
    'tax_engine': 'Apply tax treatment to economic scenarios based on jurisdiction',
    'user_profile': 'Process user input and create investment time series',
    'placements': 'GSE+ : rendement de chaque placement, net de frais annuels',
    'net_returns': "GSE++ : rendement net de frais et d'impôts, par horizon",
    'placement_optimizer': 'Markowitz par horizon sous les plafonds des enveloppes',
    'wealth_simulation': 'Projection du patrimoine net des versements',
    'placement_plan': 'Chaîne complète au format du rapport',
    'reporting': 'Generate comprehensive reports and visualizations'
}
