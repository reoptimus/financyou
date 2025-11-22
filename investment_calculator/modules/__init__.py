"""
FinancYou Modules Package

This package contains the 5 core modules of the FinancYou system:

1. scenario_generator - Economic Scenario Generator (GSE)
2. tax_engine - Tax-Integrated Scenarios (GSE+)
3. user_profile - User Input & Investment Time Series
4. optimizer - Portfolio Optimization (MOCA)
5. reporting - Visualization & Reporting

Each module has clear input/output structures documented in ARCHITECTURE.md

Example usage:
    >>> from investment_calculator.modules import scenario_generator, tax_engine
    >>> gen = scenario_generator.ScenarioGenerator()
    >>> results = gen.generate({'num_scenarios': 1000, 'time_horizon': 30, 'timestep': 1.0})

For a complete workflow example, see examples/complete_workflow_modules.py
"""

from investment_calculator.modules import (
    scenario_generator,
    tax_engine,
    user_profile,
    optimizer,
    reporting
)

__all__ = [
    'scenario_generator',
    'tax_engine',
    'user_profile',
    'optimizer',
    'reporting'
]

__version__ = '2.0.0'

# Module descriptions for documentation
MODULE_DESCRIPTIONS = {
    'scenario_generator': 'Generate Monte Carlo economic scenarios for all asset classes',
    'tax_engine': 'Apply tax treatment to economic scenarios based on jurisdiction',
    'user_profile': 'Process user input and create investment time series',
    'optimizer': 'Optimize portfolio allocation and simulate outcomes',
    'reporting': 'Generate comprehensive reports and visualizations'
}
