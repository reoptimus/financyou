"""
Utility Functions

Helper functions for investment calculations, validation, and data processing.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union


def validate_inputs(
    age: int,
    investment_horizon: int,
    current_savings: float,
    monthly_contribution: float,
) -> tuple[bool, List[str]]:
    """
    Validate input parameters for investment calculations.

    Args:
        age (int): Investor age
        investment_horizon (int): Investment time horizon in years
        current_savings (float): Current savings amount
        monthly_contribution (float): Monthly contribution amount

    Returns:
        tuple[bool, List[str]]: (is_valid, list of error messages)
    """
    errors = []

    if age < 18 or age > 100:
        errors.append("Age must be between 18 and 100")

    if investment_horizon < 1 or investment_horizon > 60:
        errors.append("Investment horizon must be between 1 and 60 years")

    if current_savings < 0:
        errors.append("Current savings cannot be negative")

    if monthly_contribution < 0:
        errors.append("Monthly contribution cannot be negative")

    if current_savings == 0 and monthly_contribution == 0:
        errors.append("Either current savings or monthly contribution must be greater than zero")

    return len(errors) == 0, errors


def validate_allocation(allocation: Dict[str, float]) -> tuple[bool, List[str]]:
    """
    Validate asset allocation weights.

    Args:
        allocation (Dict[str, float]): Asset allocation dictionary

    Returns:
        tuple[bool, List[str]]: (is_valid, list of error messages)
    """
    errors = []

    if not allocation:
        errors.append("Allocation cannot be empty")
        return False, errors

    total_weight = sum(allocation.values())

    if not np.isclose(total_weight, 1.0, atol=0.01):
        errors.append(f"Allocation weights must sum to 1.0 (currently {total_weight:.3f})")

    for asset, weight in allocation.items():
        if weight < 0:
            errors.append(f"Asset '{asset}' has negative weight: {weight}")
        if weight > 1:
            errors.append(f"Asset '{asset}' has weight > 1: {weight}")

    return len(errors) == 0, errors


def calculate_returns(
    initial_value: float,
    final_value: float,
    years: int,
    contributions: float = 0.0,
) -> Dict[str, float]:
    """
    Calculate various return metrics.

    Args:
        initial_value (float): Initial investment value
        final_value (float): Final investment value
        years (int): Number of years
        contributions (float): Total contributions made during period

    Returns:
        Dict[str, float]: Dictionary containing return metrics
    """
    total_invested = initial_value + contributions
    gains = final_value - total_invested

    if total_invested == 0:
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "total_gain": 0.0,
            "gain_percentage": 0.0,
        }

    total_return = (final_value - total_invested) / total_invested

    if years > 0:
        annualized_return = (final_value / total_invested) ** (1 / years) - 1
    else:
        annualized_return = 0.0

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "total_gain": gains,
        "gain_percentage": (gains / total_invested) * 100,
    }


def calculate_future_value(
    present_value: float,
    annual_return: float,
    years: int,
    annual_contribution: float = 0.0,
    contribution_timing: str = "end",
) -> float:
    """
    Calculate future value of investment.

    Args:
        present_value (float): Present value (initial investment)
        annual_return (float): Expected annual return (as decimal, e.g., 0.08 for 8%)
        years (int): Number of years
        annual_contribution (float): Annual contribution amount
        contribution_timing (str): "end" for end of year, "beginning" for beginning

    Returns:
        float: Future value
    """
    # Future value of present value
    fv_pv = present_value * (1 + annual_return) ** years

    if annual_contribution == 0:
        return fv_pv

    # Future value of annuity
    if contribution_timing == "beginning":
        # Annuity due (beginning of period)
        fv_annuity = annual_contribution * (((1 + annual_return) ** years - 1) / annual_return) * (1 + annual_return)
    else:
        # Ordinary annuity (end of period)
        fv_annuity = annual_contribution * (((1 + annual_return) ** years - 1) / annual_return)

    return fv_pv + fv_annuity


def calculate_required_savings(
    target_amount: float,
    years: int,
    annual_return: float,
    initial_investment: float = 0.0,
) -> float:
    """
    Calculate required monthly savings to reach a target amount.

    Args:
        target_amount (float): Target amount to reach
        years (int): Number of years to reach target
        annual_return (float): Expected annual return
        initial_investment (float): Initial investment amount

    Returns:
        float: Required annual savings
    """
    if years <= 0:
        return target_amount - initial_investment

    # Future value of initial investment
    fv_initial = initial_investment * (1 + annual_return) ** years

    # Remaining amount needed from contributions
    remaining = target_amount - fv_initial

    if remaining <= 0:
        return 0.0

    # Calculate required annual contribution
    if annual_return == 0:
        return remaining / years
    else:
        # PMT = FV * r / ((1 + r)^n - 1)
        return remaining * annual_return / ((1 + annual_return) ** years - 1)


def inflation_adjust(
    nominal_amount: float,
    inflation_rate: float,
    years: int,
    reverse: bool = False,
) -> float:
    """
    Adjust amount for inflation.

    Args:
        nominal_amount (float): Nominal (current) amount
        inflation_rate (float): Annual inflation rate
        years (int): Number of years
        reverse (bool): If True, convert future to present; if False, present to future

    Returns:
        float: Inflation-adjusted amount
    """
    if reverse:
        # Convert future dollars to present dollars
        return nominal_amount / ((1 + inflation_rate) ** years)
    else:
        # Convert present dollars to future dollars
        return nominal_amount * ((1 + inflation_rate) ** years)


def calculate_compound_growth(
    initial_value: float,
    growth_rate: float,
    years: int,
) -> np.ndarray:
    """
    Calculate year-by-year compound growth.

    Args:
        initial_value (float): Initial value
        growth_rate (float): Annual growth rate
        years (int): Number of years

    Returns:
        np.ndarray: Array of values for each year
    """
    values = np.zeros(years)
    value = initial_value

    for i in range(years):
        value *= (1 + growth_rate)
        values[i] = value

    return values


def calculate_drawdown(balance_history: np.ndarray) -> Dict[str, float]:
    """
    Calculate drawdown statistics.

    Args:
        balance_history (np.ndarray): Array of balance values over time

    Returns:
        Dict[str, float]: Drawdown statistics
    """
    if len(balance_history) == 0:
        return {
            "max_drawdown": 0.0,
            "max_drawdown_duration": 0,
            "current_drawdown": 0.0,
        }

    peak = balance_history[0]
    max_dd = 0.0
    max_dd_duration = 0
    current_dd_duration = 0

    for balance in balance_history:
        if balance > peak:
            peak = balance
            current_dd_duration = 0
        else:
            dd = (peak - balance) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
            current_dd_duration += 1
            if current_dd_duration > max_dd_duration:
                max_dd_duration = current_dd_duration

    current_dd = (peak - balance_history[-1]) / peak if peak > 0 else 0.0

    return {
        "max_drawdown": max_dd,
        "max_drawdown_duration": max_dd_duration,
        "current_drawdown": current_dd,
    }


def calculate_sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
) -> float:
    """
    Calculate Sharpe ratio.

    Args:
        returns (np.ndarray): Array of period returns
        risk_free_rate (float): Risk-free rate

    Returns:
        float: Sharpe ratio
    """
    if len(returns) == 0:
        return 0.0

    excess_returns = returns - risk_free_rate
    mean_excess = np.mean(excess_returns)
    std_excess = np.std(excess_returns)

    if std_excess == 0:
        return 0.0

    return mean_excess / std_excess


def calculate_sortino_ratio(
    returns: np.ndarray,
    target_return: float = 0.0,
) -> float:
    """
    Calculate Sortino ratio (like Sharpe but only considers downside volatility).

    Args:
        returns (np.ndarray): Array of period returns
        target_return (float): Target/minimum acceptable return

    Returns:
        float: Sortino ratio
    """
    if len(returns) == 0:
        return 0.0

    excess_returns = returns - target_return
    mean_excess = np.mean(excess_returns)

    # Calculate downside deviation
    downside_returns = excess_returns[excess_returns < 0]
    if len(downside_returns) == 0:
        return float('inf') if mean_excess > 0 else 0.0

    downside_std = np.sqrt(np.mean(downside_returns ** 2))

    if downside_std == 0:
        return 0.0

    return mean_excess / downside_std


def rebalance_portfolio(
    current_values: Dict[str, float],
    target_allocation: Dict[str, float],
) -> Dict[str, float]:
    """
    Calculate trades needed to rebalance portfolio to target allocation.

    Args:
        current_values (Dict[str, float]): Current value of each asset
        target_allocation (Dict[str, float]): Target allocation weights

    Returns:
        Dict[str, float]: Amount to buy (positive) or sell (negative) for each asset
    """
    total_value = sum(current_values.values())

    if total_value == 0:
        return {asset: 0.0 for asset in current_values.keys()}

    trades = {}

    for asset in current_values.keys():
        current_value = current_values[asset]
        target_weight = target_allocation.get(asset, 0.0)
        target_value = total_value * target_weight

        trade = target_value - current_value
        trades[asset] = trade

    return trades


def format_currency(amount: float, decimals: int = 2) -> str:
    """
    Format amount as currency string.

    Args:
        amount (float): Amount to format
        decimals (int): Number of decimal places

    Returns:
        str: Formatted currency string
    """
    return f"${amount:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format value as percentage string.

    Args:
        value (float): Value to format (as decimal, e.g., 0.08 for 8%)
        decimals (int): Number of decimal places

    Returns:
        str: Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def normalize_allocation(allocation: Dict[str, float]) -> Dict[str, float]:
    """
    Normalize allocation weights to sum to 1.0.

    Args:
        allocation (Dict[str, float]): Asset allocation

    Returns:
        Dict[str, float]: Normalized allocation
    """
    total = sum(allocation.values())

    if total == 0:
        return allocation

    return {asset: weight / total for asset, weight in allocation.items()}
