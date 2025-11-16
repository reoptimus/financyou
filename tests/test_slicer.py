"""
Unit tests for time_series_slicer.slicer module.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from time_series_slicer import TimeSeriesSlicer, slice_by_time, slice_by_index, slice_by_window


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame with DatetimeIndex."""
    dates = pd.date_range('2024-01-01', periods=100, freq='H')
    data = pd.DataFrame({
        'value': range(100),
        'temperature': [20 + i * 0.1 for i in range(100)]
    }, index=dates)
    return data


@pytest.fixture
def sample_series():
    """Create a sample Series with DatetimeIndex."""
    dates = pd.date_range('2024-01-01', periods=100, freq='H')
    data = pd.Series(range(100), index=dates, name='value')
    return data


@pytest.fixture
def sample_dataframe_with_time_column():
    """Create a sample DataFrame with time column (no DatetimeIndex)."""
    dates = pd.date_range('2024-01-01', periods=100, freq='H')
    data = pd.DataFrame({
        'timestamp': dates,
        'value': range(100)
    })
    return data


class TestTimeSeriesSlicerInit:
    """Test TimeSeriesSlicer initialization."""

    def test_init_with_dataframe_datetime_index(self, sample_dataframe):
        """Test initialization with DataFrame having DatetimeIndex."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        assert slicer.data.equals(sample_dataframe)
        assert slicer.time_column is None

    def test_init_with_series_datetime_index(self, sample_series):
        """Test initialization with Series having DatetimeIndex."""
        slicer = TimeSeriesSlicer(sample_series)
        assert slicer.data.equals(sample_series)

    def test_init_with_dataframe_time_column(self, sample_dataframe_with_time_column):
        """Test initialization with DataFrame having time column."""
        slicer = TimeSeriesSlicer(sample_dataframe_with_time_column, time_column='timestamp')
        assert slicer.time_column == 'timestamp'

    def test_init_without_datetime_index_or_column(self):
        """Test that initialization fails without proper time information."""
        data = pd.DataFrame({'value': [1, 2, 3]})
        with pytest.raises(ValueError, match="DatetimeIndex or time_column"):
            TimeSeriesSlicer(data)

    def test_init_with_invalid_time_column(self, sample_dataframe):
        """Test that initialization fails with invalid time column."""
        with pytest.raises(ValueError, match="not found in DataFrame"):
            TimeSeriesSlicer(sample_dataframe, time_column='nonexistent')

    def test_init_with_invalid_data_type(self):
        """Test that initialization fails with invalid data type."""
        with pytest.raises(ValueError, match="must be pandas DataFrame or Series"):
            TimeSeriesSlicer([1, 2, 3])


class TestSliceByTime:
    """Test time-based slicing functionality."""

    def test_slice_by_time_with_both_bounds(self, sample_dataframe):
        """Test slicing with both start and end times."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        result = slicer.slice_by_time('2024-01-01 10:00:00', '2024-01-01 20:00:00')
        assert len(result) == 11  # Inclusive of both bounds
        assert result.index[0] == pd.Timestamp('2024-01-01 10:00:00')
        assert result.index[-1] == pd.Timestamp('2024-01-01 20:00:00')

    def test_slice_by_time_start_only(self, sample_dataframe):
        """Test slicing with only start time."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        result = slicer.slice_by_time(start='2024-01-01 10:00:00')
        assert len(result) == 90
        assert result.index[0] == pd.Timestamp('2024-01-01 10:00:00')

    def test_slice_by_time_end_only(self, sample_dataframe):
        """Test slicing with only end time."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        result = slicer.slice_by_time(end='2024-01-01 10:00:00')
        assert len(result) == 11
        assert result.index[-1] == pd.Timestamp('2024-01-01 10:00:00')

    def test_slice_by_time_with_series(self, sample_series):
        """Test slicing with Series data."""
        slicer = TimeSeriesSlicer(sample_series)
        result = slicer.slice_by_time('2024-01-01 10:00:00', '2024-01-01 20:00:00')
        assert len(result) == 11

    def test_slice_by_time_convenience_function(self, sample_dataframe):
        """Test the convenience function slice_by_time."""
        result = slice_by_time(sample_dataframe, '2024-01-01 10:00:00', '2024-01-01 20:00:00')
        assert len(result) == 11


class TestSliceByIndex:
    """Test index-based slicing functionality."""

    def test_slice_by_index_with_both_bounds(self, sample_dataframe):
        """Test slicing with both start and end indices."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        result = slicer.slice_by_index(10, 20)
        assert len(result) == 10
        assert result['value'].iloc[0] == 10
        assert result['value'].iloc[-1] == 19

    def test_slice_by_index_start_only(self, sample_dataframe):
        """Test slicing with only start index."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        result = slicer.slice_by_index(90)
        assert len(result) == 10
        assert result['value'].iloc[0] == 90

    def test_slice_by_index_end_only(self, sample_dataframe):
        """Test slicing with only end index."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        result = slicer.slice_by_index(end_idx=10)
        assert len(result) == 10
        assert result['value'].iloc[-1] == 9

    def test_slice_by_index_negative_indices(self, sample_dataframe):
        """Test slicing with negative indices."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        result = slicer.slice_by_index(-10)
        assert len(result) == 10
        assert result['value'].iloc[0] == 90

    def test_slice_by_index_convenience_function(self, sample_dataframe):
        """Test the convenience function slice_by_index."""
        result = slice_by_index(sample_dataframe, 10, 20)
        assert len(result) == 10


class TestSliceByWindow:
    """Test window-based slicing functionality."""

    def test_slice_by_window_fixed_size_no_overlap(self, sample_dataframe):
        """Test fixed-size windows without overlap."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        windows = list(slicer.slice_by_window(window_size=10))
        assert len(windows) == 10
        assert all(len(w) == 10 for w in windows)

    def test_slice_by_window_fixed_size_with_overlap(self, sample_dataframe):
        """Test fixed-size windows with overlap."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        windows = list(slicer.slice_by_window(window_size=10, step_size=5, overlap=True))
        assert len(windows) > 10  # More windows due to overlap
        assert all(len(w) == 10 for w in windows)

    def test_slice_by_window_time_based(self, sample_dataframe):
        """Test time-based windows."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        windows = list(slicer.slice_by_window(
            window_size=timedelta(hours=10),
            step_size=timedelta(hours=10)
        ))
        assert len(windows) > 0
        # Each window should have approximately 10 hours of data (11 points)
        assert all(len(w) == 11 for w in windows)

    def test_slice_by_window_time_based_overlap(self, sample_dataframe):
        """Test time-based windows with overlap."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        windows = list(slicer.slice_by_window(
            window_size=timedelta(hours=10),
            step_size=timedelta(hours=5),
            overlap=True
        ))
        assert len(windows) > 0

    def test_slice_by_window_invalid_step_size_type(self, sample_dataframe):
        """Test that mismatched window_size and step_size types raise error."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        with pytest.raises(ValueError, match="step_size must be int"):
            list(slicer.slice_by_window(window_size=10, step_size=timedelta(hours=1)))

    def test_slice_by_window_invalid_window_size_type(self, sample_dataframe):
        """Test that invalid window_size type raises error."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        with pytest.raises(ValueError, match="window_size must be int or timedelta"):
            list(slicer.slice_by_window(window_size="invalid"))

    def test_slice_by_window_convenience_function(self, sample_dataframe):
        """Test the convenience function slice_by_window."""
        windows = list(slice_by_window(sample_dataframe, window_size=10))
        assert len(windows) == 10


class TestSplitByRatio:
    """Test ratio-based splitting functionality."""

    def test_split_by_ratio_two_way(self, sample_dataframe):
        """Test 70/30 split."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        train, test = slicer.split_by_ratio([0.7, 0.3])
        assert len(train) == 70
        assert len(test) == 30

    def test_split_by_ratio_three_way(self, sample_dataframe):
        """Test 60/20/20 split."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        train, val, test = slicer.split_by_ratio([0.6, 0.2, 0.2])
        assert len(train) == 60
        assert len(val) == 20
        assert len(test) == 20

    def test_split_by_ratio_with_shuffle(self, sample_dataframe):
        """Test split with shuffling."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        train1, test1 = slicer.split_by_ratio([0.7, 0.3], shuffle=True, random_state=42)
        train2, test2 = slicer.split_by_ratio([0.7, 0.3], shuffle=True, random_state=42)
        # Same random state should give same results
        assert train1.equals(train2)
        assert test1.equals(test2)

    def test_split_by_ratio_invalid_ratios(self, sample_dataframe):
        """Test that invalid ratios raise error."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        with pytest.raises(ValueError, match="Ratios must sum to 1.0"):
            slicer.split_by_ratio([0.5, 0.3])  # Doesn't sum to 1.0


class TestSliceByValue:
    """Test value-based filtering functionality."""

    def test_slice_by_value_with_both_bounds(self, sample_dataframe):
        """Test filtering with min and max values."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        result = slicer.slice_by_value(column='value', min_value=20, max_value=30)
        assert len(result) == 11
        assert result['value'].min() == 20
        assert result['value'].max() == 30

    def test_slice_by_value_min_only(self, sample_dataframe):
        """Test filtering with only minimum value."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        result = slicer.slice_by_value(column='value', min_value=90)
        assert len(result) == 10
        assert result['value'].min() >= 90

    def test_slice_by_value_max_only(self, sample_dataframe):
        """Test filtering with only maximum value."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        result = slicer.slice_by_value(column='value', max_value=10)
        assert len(result) == 11
        assert result['value'].max() <= 10

    def test_slice_by_value_invalid_column(self, sample_dataframe):
        """Test that invalid column name raises error."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        with pytest.raises(ValueError, match="not found in DataFrame"):
            slicer.slice_by_value(column='nonexistent', min_value=0)

    def test_slice_by_value_with_series(self, sample_series):
        """Test filtering with Series data."""
        slicer = TimeSeriesSlicer(sample_series)
        # For Series, column parameter is ignored
        result = slicer.slice_by_value(column='value', min_value=20, max_value=30)
        assert len(result) == 11


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_result(self, sample_dataframe):
        """Test operations that result in empty data."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        result = slicer.slice_by_time('2025-01-01', '2025-12-31')
        assert len(result) == 0

    def test_single_row_data(self):
        """Test with single row DataFrame."""
        data = pd.DataFrame({
            'value': [1]
        }, index=pd.DatetimeIndex(['2024-01-01']))
        slicer = TimeSeriesSlicer(data)
        result = slicer.slice_by_index(0, 1)
        assert len(result) == 1

    def test_large_window_size(self, sample_dataframe):
        """Test with window size larger than data."""
        slicer = TimeSeriesSlicer(sample_dataframe)
        windows = list(slicer.slice_by_window(window_size=200))
        assert len(windows) == 0  # No complete windows can be formed


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
