"""
Investment Calculator Package

A comprehensive investment analysis and portfolio optimization toolkit that includes:
- GSE (Global Scenario Engine): Economic scenario generation and simulation
- GSE+ (Tax-Integrated Scenario Engine): Scenario calculations with tax considerations
- MOCA (Moteur de Calcul): Portfolio optimization and statistical analysis engine

This package helps investors make informed decisions by calculating optimal investment
strategies based on personal variables, economic scenarios, and tax implications.
"""

from .gse import EconomicScenario, GlobalScenarioEngine, ScenarioType
from .gse_plus import AccountType, TaxConfig, TaxIntegratedScenarioEngine, TaxTreatment
from .moca import (
    MOCA,
    InvestmentResult,
    OptimizationMethod,
    PortfolioOptimizer,
    PortfolioStatistics,
)
from .personal_variables import InvestmentGoal, InvestmentProfile, PersonalVariables, RiskTolerance
from .utils import calculate_returns, validate_allocation, validate_inputs

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
