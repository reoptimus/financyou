# Time Series Slicer

A powerful and flexible Python library for slicing, segmenting, and manipulating time series data with ease.

## Features

- **Time-based Slicing**: Slice data by date/time ranges
- **Index-based Slicing**: Slice data by integer indices
- **Window-based Slicing**: Create fixed-size or time-based sliding windows
- **Value-based Filtering**: Filter data based on value thresholds
- **Train/Test Splitting**: Split data by ratios with optional shuffling
- **Flexible Input**: Works with pandas DataFrame and Series
- **Iterator Support**: Memory-efficient window iteration for large datasets

## Installation

### From Source

```bash
git clone https://github.com/yourusername/time_series_slicer.git
cd time_series_slicer
pip install -e .
```

### Requirements

- Python >= 3.7
- pandas >= 1.0.0
- numpy >= 1.18.0

## Quick Start

```python
import pandas as pd
from datetime import datetime, timedelta
from time_series_slicer import TimeSeriesSlicer

# Create sample time series data
dates = pd.date_range('2024-01-01', periods=100, freq='H')
data = pd.DataFrame({
    'timestamp': dates,
    'value': range(100),
    'temperature': [20 + i * 0.1 for i in range(100)]
})
data.set_index('timestamp', inplace=True)

# Initialize the slicer
slicer = TimeSeriesSlicer(data)

# Slice by time range
subset = slicer.slice_by_time('2024-01-01', '2024-01-02')

# Create sliding windows
for window in slicer.slice_by_window(window_size=10, step_size=5):
    print(f"Window shape: {window.shape}")

# Split into train/test sets
train, test = slicer.split_by_ratio([0.7, 0.3])
```

## Usage Examples

### 1. Time-based Slicing

Extract data within specific date/time ranges:

```python
from time_series_slicer import slice_by_time

# Slice between two dates
result = slice_by_time(
    data,
    start='2024-01-01 00:00:00',
    end='2024-01-01 23:59:59'
)

# Slice from start to specific date
result = slice_by_time(data, end='2024-01-02')

# Slice from specific date to end
result = slice_by_time(data, start='2024-01-03')
```

### 2. Index-based Slicing

Slice data using integer positions:

```python
from time_series_slicer import slice_by_index

# Get first 50 rows
first_half = slice_by_index(data, start_idx=0, end_idx=50)

# Get last 30 rows
last_rows = slice_by_index(data, start_idx=-30)

# Get rows 20 to 40
middle = slice_by_index(data, start_idx=20, end_idx=40)
```

### 3. Window-based Slicing

Create fixed-size sliding windows for time series analysis:

```python
from time_series_slicer import slice_by_window
from datetime import timedelta

# Fixed-size windows (row count)
# Non-overlapping windows of 10 rows each
for window in slice_by_window(data, window_size=10):
    print(window.mean())

# Overlapping windows with step size
for window in slice_by_window(data, window_size=20, step_size=5, overlap=True):
    # Process each window
    pass

# Time-based windows
# 1-hour windows with 30-minute step
for window in slice_by_window(
    data,
    window_size=timedelta(hours=1),
    step_size=timedelta(minutes=30),
    overlap=True
):
    print(f"Window from {window.index[0]} to {window.index[-1]}")
```

### 4. Value-based Filtering

Filter data based on column values:

```python
slicer = TimeSeriesSlicer(data)

# Get all rows where temperature is between 20 and 25
filtered = slicer.slice_by_value(
    column='temperature',
    min_value=20,
    max_value=25
)

# Get all rows where value is above 50
high_values = slicer.slice_by_value(column='value', min_value=50)
```

### 5. Train/Test Splitting

Split data into multiple sets:

```python
slicer = TimeSeriesSlicer(data)

# 70/30 train/test split
train, test = slicer.split_by_ratio([0.7, 0.3])

# 60/20/20 train/validation/test split
train, val, test = slicer.split_by_ratio([0.6, 0.2, 0.2])

# Shuffle before splitting (useful for non-time-dependent data)
train, test = slicer.split_by_ratio([0.8, 0.2], shuffle=True, random_state=42)
```

### 6. Working with DataFrame without DatetimeIndex

```python
# When DataFrame doesn't have DatetimeIndex
data = pd.DataFrame({
    'date': pd.date_range('2024-01-01', periods=100, freq='D'),
    'value': range(100)
})

# Specify the time column
slicer = TimeSeriesSlicer(data, time_column='date')

# Now you can use time-based operations
result = slicer.slice_by_time('2024-01-10', '2024-01-20')
```

## API Reference

### TimeSeriesSlicer Class

#### `__init__(data, time_column=None)`

Initialize the slicer with time series data.

**Parameters:**
- `data` (pd.DataFrame or pd.Series): Time series data
- `time_column` (str, optional): Name of the time column for DataFrames without DatetimeIndex

#### `slice_by_time(start=None, end=None)`

Slice by time range.

**Parameters:**
- `start` (str or datetime, optional): Start timestamp (inclusive)
- `end` (str or datetime, optional): End timestamp (inclusive)

**Returns:** Sliced data

#### `slice_by_index(start_idx=None, end_idx=None)`

Slice by integer indices.

**Parameters:**
- `start_idx` (int, optional): Start index (inclusive)
- `end_idx` (int, optional): End index (exclusive)

**Returns:** Sliced data

#### `slice_by_window(window_size, step_size=None, overlap=False)`

Create sliding windows.

**Parameters:**
- `window_size` (int or timedelta): Size of each window
- `step_size` (int or timedelta, optional): Step between windows
- `overlap` (bool): Whether to allow overlapping windows

**Yields:** Window iterator

#### `split_by_ratio(ratios, shuffle=False, random_state=None)`

Split data by ratio.

**Parameters:**
- `ratios` (list of float): List of ratios summing to 1.0
- `shuffle` (bool): Whether to shuffle before splitting
- `random_state` (int, optional): Random seed for reproducibility

**Returns:** List of data splits

#### `slice_by_value(column, min_value=None, max_value=None)`

Filter by value thresholds.

**Parameters:**
- `column` (str): Column name to filter
- `min_value` (float, optional): Minimum value
- `max_value` (float, optional): Maximum value

**Returns:** Filtered data

## Use Cases

### Machine Learning Pipeline

```python
from time_series_slicer import TimeSeriesSlicer

# Prepare data
slicer = TimeSeriesSlicer(timeseries_data)

# Split into train/test
train_data, test_data = slicer.split_by_ratio([0.8, 0.2])

# Create training windows for sequence modeling
train_slicer = TimeSeriesSlicer(train_data)
for window in train_slicer.slice_by_window(window_size=100, step_size=10):
    # Train model on each window
    X, y = prepare_features(window)
    model.fit(X, y)
```

### Anomaly Detection

```python
# Analyze data in hourly windows
for window in slicer.slice_by_window(window_size=timedelta(hours=1)):
    mean = window['value'].mean()
    std = window['value'].std()

    # Detect anomalies
    anomalies = slicer.slice_by_value(
        column='value',
        min_value=mean - 3*std,
        max_value=mean + 3*std
    )
```

### Backtesting Trading Strategies

```python
# Test strategy on different time periods
for year in range(2020, 2024):
    year_data = slicer.slice_by_time(
        start=f'{year}-01-01',
        end=f'{year}-12-31'
    )
    # Run backtest on this period
    results = backtest_strategy(year_data)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Authors

Time Series Slicer Contributors

## Acknowledgments

- Built with pandas and numpy
- Inspired by the need for flexible time series manipulation in data science workflows
