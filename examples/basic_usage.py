"""
Basic usage examples for time_series_slicer library.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from time_series_slicer import TimeSeriesSlicer, slice_by_time, slice_by_window


def create_sample_data():
    """Create sample time series data for demonstration."""
    dates = pd.date_range('2024-01-01', periods=1000, freq='H')
    data = pd.DataFrame({
        'value': np.random.randn(1000).cumsum(),
        'temperature': 20 + np.random.randn(1000) * 5,
        'humidity': 50 + np.random.randn(1000) * 10
    }, index=dates)
    return data


def example_time_slicing():
    """Demonstrate time-based slicing."""
    print("\n" + "="*60)
    print("Example 1: Time-based Slicing")
    print("="*60)

    data = create_sample_data()
    slicer = TimeSeriesSlicer(data)

    # Slice by date range
    january_data = slicer.slice_by_time('2024-01-01', '2024-01-31')
    print(f"\nJanuary data shape: {january_data.shape}")
    print(f"Date range: {january_data.index[0]} to {january_data.index[-1]}")

    # Slice from specific date to end
    recent_data = slicer.slice_by_time(start='2024-02-01')
    print(f"\nData from Feb onwards shape: {recent_data.shape}")


def example_index_slicing():
    """Demonstrate index-based slicing."""
    print("\n" + "="*60)
    print("Example 2: Index-based Slicing")
    print("="*60)

    data = create_sample_data()
    slicer = TimeSeriesSlicer(data)

    # Get first 100 rows
    first_100 = slicer.slice_by_index(0, 100)
    print(f"\nFirst 100 rows shape: {first_100.shape}")

    # Get last 50 rows
    last_50 = slicer.slice_by_index(-50, None)
    print(f"Last 50 rows shape: {last_50.shape}")


def example_window_slicing():
    """Demonstrate window-based slicing."""
    print("\n" + "="*60)
    print("Example 3: Window-based Slicing")
    print("="*60)

    data = create_sample_data()
    slicer = TimeSeriesSlicer(data)

    # Fixed-size windows (24 hours each)
    print("\nCreating 24-hour windows:")
    window_count = 0
    for window in slicer.slice_by_window(window_size=24, step_size=24):
        window_count += 1
        mean_temp = window['temperature'].mean()
        print(f"Window {window_count}: Mean temperature = {mean_temp:.2f}°C")
        if window_count >= 5:  # Show only first 5 windows
            break

    # Overlapping time-based windows
    print("\nCreating overlapping 7-day windows (3-day step):")
    window_count = 0
    for window in slicer.slice_by_window(
        window_size=timedelta(days=7),
        step_size=timedelta(days=3),
        overlap=True
    ):
        window_count += 1
        print(f"Window {window_count}: {window.index[0]} to {window.index[-1]}")
        if window_count >= 3:  # Show only first 3 windows
            break


def example_train_test_split():
    """Demonstrate train/test splitting."""
    print("\n" + "="*60)
    print("Example 4: Train/Test Splitting")
    print("="*60)

    data = create_sample_data()
    slicer = TimeSeriesSlicer(data)

    # 70/30 split
    train, test = slicer.split_by_ratio([0.7, 0.3])
    print(f"\nTrain set shape: {train.shape}")
    print(f"Test set shape: {test.shape}")

    # 60/20/20 split
    train, val, test = slicer.split_by_ratio([0.6, 0.2, 0.2])
    print(f"\nTrain set shape: {train.shape}")
    print(f"Validation set shape: {val.shape}")
    print(f"Test set shape: {test.shape}")


def example_value_filtering():
    """Demonstrate value-based filtering."""
    print("\n" + "="*60)
    print("Example 5: Value-based Filtering")
    print("="*60)

    data = create_sample_data()
    slicer = TimeSeriesSlicer(data)

    # Filter by temperature range
    comfortable_temp = slicer.slice_by_value(
        column='temperature',
        min_value=18,
        max_value=22
    )
    print(f"\nOriginal data shape: {data.shape}")
    print(f"Data with comfortable temperature (18-22°C): {comfortable_temp.shape}")

    # Filter high humidity
    high_humidity = slicer.slice_by_value(column='humidity', min_value=60)
    print(f"High humidity data (>60%): {high_humidity.shape}")


def example_convenience_functions():
    """Demonstrate convenience functions."""
    print("\n" + "="*60)
    print("Example 6: Convenience Functions")
    print("="*60)

    data = create_sample_data()

    # Direct time slicing without creating slicer object
    week_data = slice_by_time(data, '2024-01-01', '2024-01-07')
    print(f"\nOne week of data shape: {week_data.shape}")

    # Direct window creation
    print("\nCreating windows directly:")
    for i, window in enumerate(slice_by_window(data, window_size=100, step_size=50)):
        print(f"Window {i+1} shape: {window.shape}")
        if i >= 2:  # Show only first 3 windows
            break


def example_ml_pipeline():
    """Demonstrate a machine learning pipeline scenario."""
    print("\n" + "="*60)
    print("Example 7: Machine Learning Pipeline")
    print("="*60)

    data = create_sample_data()
    slicer = TimeSeriesSlicer(data)

    # Split data
    train_data, test_data = slicer.split_by_ratio([0.8, 0.2])
    print(f"\nDataset split - Train: {train_data.shape}, Test: {test_data.shape}")

    # Create training windows
    train_slicer = TimeSeriesSlicer(train_data)
    print("\nCreating training windows (sequence length: 24):")

    window_count = 0
    for window in train_slicer.slice_by_window(window_size=24, step_size=6):
        # In a real scenario, you would prepare features and train your model here
        window_count += 1

    print(f"Created {window_count} training windows")

    # Prepare test data
    test_slicer = TimeSeriesSlicer(test_data)
    test_windows = list(test_slicer.slice_by_window(window_size=24, step_size=24))
    print(f"Created {len(test_windows)} test windows")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("TIME SERIES SLICER - USAGE EXAMPLES")
    print("="*60)

    example_time_slicing()
    example_index_slicing()
    example_window_slicing()
    example_train_test_split()
    example_value_filtering()
    example_convenience_functions()
    example_ml_pipeline()

    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
