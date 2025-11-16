"""
Core time series slicing functionality.
"""

from typing import List, Union, Tuple, Optional, Iterator
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class TimeSeriesSlicer:
    """
    A class for slicing time series data using various strategies.

    Attributes:
        data: pandas DataFrame or Series containing the time series data
        time_column: Name of the column containing timestamps (if DataFrame)
    """

    def __init__(self, data: Union[pd.DataFrame, pd.Series], time_column: Optional[str] = None):
        """
        Initialize the TimeSeriesSlicer.

        Args:
            data: Time series data as pandas DataFrame or Series
            time_column: Name of the time column (required for DataFrame without DatetimeIndex)

        Raises:
            ValueError: If data format is invalid or time_column is missing when required
        """
        self.data = data
        self.time_column = time_column

        # Validate input
        if isinstance(data, pd.DataFrame):
            if not isinstance(data.index, pd.DatetimeIndex) and time_column is None:
                raise ValueError("DataFrame must have DatetimeIndex or time_column must be specified")
            if time_column and time_column not in data.columns:
                raise ValueError(f"Column '{time_column}' not found in DataFrame")
        elif isinstance(data, pd.Series):
            if not isinstance(data.index, pd.DatetimeIndex):
                raise ValueError("Series must have DatetimeIndex")
        else:
            raise ValueError("Data must be pandas DataFrame or Series")

    def slice_by_time(
        self,
        start: Optional[Union[str, datetime]] = None,
        end: Optional[Union[str, datetime]] = None
    ) -> Union[pd.DataFrame, pd.Series]:
        """
        Slice time series by start and end timestamps.

        Args:
            start: Start timestamp (inclusive)
            end: End timestamp (inclusive)

        Returns:
            Sliced time series data
        """
        if isinstance(self.data, pd.Series) or isinstance(self.data.index, pd.DatetimeIndex):
            return self.data.loc[start:end]
        else:
            mask = pd.Series([True] * len(self.data), index=self.data.index)
            if start:
                mask &= self.data[self.time_column] >= pd.to_datetime(start)
            if end:
                mask &= self.data[self.time_column] <= pd.to_datetime(end)
            return self.data[mask]

    def slice_by_index(
        self,
        start_idx: Optional[int] = None,
        end_idx: Optional[int] = None
    ) -> Union[pd.DataFrame, pd.Series]:
        """
        Slice time series by integer indices.

        Args:
            start_idx: Start index (inclusive)
            end_idx: End index (exclusive)

        Returns:
            Sliced time series data
        """
        return self.data.iloc[start_idx:end_idx]

    def slice_by_window(
        self,
        window_size: Union[int, timedelta],
        step_size: Optional[Union[int, timedelta]] = None,
        overlap: bool = False
    ) -> Iterator[Union[pd.DataFrame, pd.Series]]:
        """
        Slice time series into windows of fixed size.

        Args:
            window_size: Size of each window (int for row count, timedelta for duration)
            step_size: Step size between windows (defaults to window_size if not overlapping)
            overlap: Whether to allow overlapping windows

        Yields:
            Windows of time series data
        """
        if isinstance(window_size, int):
            # Integer-based windows
            if step_size is None:
                step_size = 1 if overlap else window_size
            elif not isinstance(step_size, int):
                raise ValueError("step_size must be int when window_size is int")

            for i in range(0, len(self.data) - window_size + 1, step_size):
                yield self.data.iloc[i:i + window_size]

        elif isinstance(window_size, timedelta):
            # Time-based windows
            if step_size is None:
                step_size = timedelta(seconds=1) if overlap else window_size
            elif not isinstance(step_size, timedelta):
                raise ValueError("step_size must be timedelta when window_size is timedelta")

            time_index = self._get_time_index()
            start_time = time_index.min()
            end_time = time_index.max()

            current_start = start_time
            while current_start <= end_time:
                current_end = current_start + window_size
                if current_end > end_time:
                    break

                yield self.slice_by_time(current_start, current_end)
                current_start += step_size
        else:
            raise ValueError("window_size must be int or timedelta")

    def split_by_ratio(
        self,
        ratios: List[float],
        shuffle: bool = False,
        random_state: Optional[int] = None
    ) -> List[Union[pd.DataFrame, pd.Series]]:
        """
        Split time series data by ratio (e.g., train/test split).

        Args:
            ratios: List of ratios that sum to 1.0 (e.g., [0.7, 0.3] for 70/30 split)
            shuffle: Whether to shuffle data before splitting
            random_state: Random seed for reproducibility

        Returns:
            List of data splits
        """
        if not np.isclose(sum(ratios), 1.0):
            raise ValueError("Ratios must sum to 1.0")

        data = self.data.copy()
        if shuffle:
            data = data.sample(frac=1, random_state=random_state)

        splits = []
        start_idx = 0
        total_len = len(data)

        for ratio in ratios[:-1]:
            split_size = int(total_len * ratio)
            splits.append(data.iloc[start_idx:start_idx + split_size])
            start_idx += split_size

        # Add remaining data to last split
        splits.append(data.iloc[start_idx:])

        return splits

    def slice_by_value(
        self,
        column: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> Union[pd.DataFrame, pd.Series]:
        """
        Slice time series based on value thresholds.

        Args:
            column: Column name to filter on (for DataFrame)
            min_value: Minimum value threshold
            max_value: Maximum value threshold

        Returns:
            Filtered time series data
        """
        if isinstance(self.data, pd.Series):
            data_to_filter = self.data
        else:
            if column not in self.data.columns:
                raise ValueError(f"Column '{column}' not found in DataFrame")
            data_to_filter = self.data[column]

        mask = pd.Series([True] * len(self.data), index=self.data.index)

        if min_value is not None:
            mask &= data_to_filter >= min_value
        if max_value is not None:
            mask &= data_to_filter <= max_value

        return self.data[mask]

    def _get_time_index(self) -> pd.DatetimeIndex:
        """Get the datetime index from the data."""
        if isinstance(self.data.index, pd.DatetimeIndex):
            return self.data.index
        elif self.time_column:
            return pd.DatetimeIndex(self.data[self.time_column])
        else:
            raise ValueError("Cannot determine time index")


# Convenience functions
def slice_by_time(
    data: Union[pd.DataFrame, pd.Series],
    start: Optional[Union[str, datetime]] = None,
    end: Optional[Union[str, datetime]] = None,
    time_column: Optional[str] = None
) -> Union[pd.DataFrame, pd.Series]:
    """
    Convenience function to slice time series by time range.

    Args:
        data: Time series data
        start: Start timestamp
        end: End timestamp
        time_column: Name of time column (for DataFrame)

    Returns:
        Sliced time series data
    """
    slicer = TimeSeriesSlicer(data, time_column)
    return slicer.slice_by_time(start, end)


def slice_by_index(
    data: Union[pd.DataFrame, pd.Series],
    start_idx: Optional[int] = None,
    end_idx: Optional[int] = None
) -> Union[pd.DataFrame, pd.Series]:
    """
    Convenience function to slice time series by index.

    Args:
        data: Time series data
        start_idx: Start index
        end_idx: End index

    Returns:
        Sliced time series data
    """
    slicer = TimeSeriesSlicer(data)
    return slicer.slice_by_index(start_idx, end_idx)


def slice_by_window(
    data: Union[pd.DataFrame, pd.Series],
    window_size: Union[int, timedelta],
    step_size: Optional[Union[int, timedelta]] = None,
    overlap: bool = False,
    time_column: Optional[str] = None
) -> Iterator[Union[pd.DataFrame, pd.Series]]:
    """
    Convenience function to slice time series into windows.

    Args:
        data: Time series data
        window_size: Size of each window
        step_size: Step size between windows
        overlap: Whether to allow overlapping windows
        time_column: Name of time column (for DataFrame)

    Yields:
        Windows of time series data
    """
    slicer = TimeSeriesSlicer(data, time_column)
    return slicer.slice_by_window(window_size, step_size, overlap)
