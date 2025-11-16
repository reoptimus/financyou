"""
Time Series Slicer - A Python library for slicing and segmenting time series data.
"""

__version__ = "0.1.0"
__author__ = "Time Series Slicer Contributors"

from .slicer import TimeSeriesSlicer, slice_by_time, slice_by_index, slice_by_window

__all__ = [
    "TimeSeriesSlicer",
    "slice_by_time",
    "slice_by_index",
    "slice_by_window",
]
