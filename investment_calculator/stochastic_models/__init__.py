"""
Stochastic Models Module for Financyou

This module contains advanced stochastic financial models for generating
economic scenarios, including:

- Hull-White interest rate model (short rate evolution)
- Correlated random variable generation (multi-asset correlation)
- Black-Scholes equity models
- Real estate models with stochastic rental income
- Leased property at fixed rent (rent leg + free value)
- Bond pricing models
- Calibration functions for EIOPA curves and market data

These models form the core of the Economic Scenario Generator (ESG).
"""

from .black_scholes import BlackScholesEquity
from .calibration import EIOPACalibrator
from .correlation import CorrelatedRandomGenerator
from .hull_white import HullWhiteModel
from .leased_property import FixedRentLease, LeasedPropertyPaths, leased_property_paths
from .real_estate import RealEstateModel

__all__ = [
    'HullWhiteModel',
    'CorrelatedRandomGenerator',
    'BlackScholesEquity',
    'RealEstateModel',
    'FixedRentLease',
    'LeasedPropertyPaths',
    'leased_property_paths',
    'EIOPACalibrator',
]

__version__ = '1.0.0'
