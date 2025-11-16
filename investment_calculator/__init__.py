"""
Investment Calculator Package

A comprehensive investment analysis and portfolio optimization toolkit that includes:
- GSE (Global Scenario Engine): Economic scenario generation and simulation
- GSE+ (Tax-Integrated Scenario Engine): Scenario calculations with tax considerations
- MOCA (Moteur de Calcul): Portfolio optimization and statistical analysis engine

This package helps investors make informed decisions by calculating optimal investment
strategies based on personal variables, economic scenarios, and tax implications.
"""

from .gse import GlobalScenarioEngine, EconomicScenario, ScenarioType
from .gse_plus import TaxIntegratedScenarioEngine, TaxConfig, AccountType, TaxTreatment
from .moca import MOCA, PortfolioOptimizer, InvestmentResult, PortfolioStatistics, OptimizationMethod
from .personal_variables import PersonalVariables, InvestmentProfile, RiskTolerance, InvestmentGoal
from .utils import validate_inputs, calculate_returns, validate_allocation

__version__ = "1.0.0"

__all__ = [
    # GSE exports
    "GlobalScenarioEngine",
    "EconomicScenario",
    "ScenarioType",

    # GSE+ exports
    "TaxIntegratedScenarioEngine",
    "TaxConfig",
    "AccountType",
    "TaxTreatment",

    # MOCA exports
    "MOCA",
    "PortfolioOptimizer",
    "InvestmentResult",
    "PortfolioStatistics",
    "OptimizationMethod",

    # Personal variables exports
    "PersonalVariables",
    "InvestmentProfile",
    "RiskTolerance",
    "InvestmentGoal",

    # Utilities
    "validate_inputs",
    "calculate_returns",
    "validate_allocation",
]
