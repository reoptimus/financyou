"""
Stochastic Models Module for Financyou

This module contains advanced stochastic financial models for generating
economic scenarios, including:

- Hull-White interest rate model (short rate evolution)
- Correlated random variable generation (multi-asset correlation)
- Black-Scholes equity models
- Real estate models with stochastic rental income
- Bond pricing models
- Calibration functions for EIOPA curves and market data

These models form the core of the Economic Scenario Generator (ESG).
"""

from .hull_white import HullWhiteModel
from .correlation import CorrelatedRandomGenerator
from .black_scholes import BlackScholesEquity
from .real_estate import RealEstateModel
from .calibration import EIOPACalibrator

__all__ = [
    'HullWhiteModel',
    'CorrelatedRandomGenerator',
    'BlackScholesEquity',
    'RealEstateModel',
    'EIOPACalibrator',
]

__version__ = '1.0.0'
