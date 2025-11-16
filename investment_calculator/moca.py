"""
MOCA (Moteur de Calcul / Calculation Engine)

Portfolio optimization and statistical analysis engine that:
1. Compiles investment results for each scenario
2. Calculates statistical metrics (returns, volatility, VaR, Sharpe ratio, etc.)
3. Optimizes portfolios using classic techniques (mean-variance, efficient frontier, etc.)
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable
from enum import Enum
from scipy.optimize import minimize

from .gse import EconomicScenario
from .gse_plus import TaxIntegratedScenario, AccountType
from .personal_variables import PersonalVariables, InvestmentProfile


class OptimizationMethod(Enum):
    """Portfolio optimization methods"""
    MEAN_VARIANCE = "mean_variance"
    MIN_VOLATILITY = "min_volatility"
    MAX_SHARPE = "max_sharpe"
    MAX_RETURN = "max_return"
    RISK_PARITY = "risk_parity"
    EQUAL_WEIGHT = "equal_weight"


@dataclass
class InvestmentResult:
    """
    Results from simulating an investment strategy under a scenario.

    Attributes:
        scenario_id (str): Scenario identifier
        asset_allocation (Dict[str, float]): Asset allocation used
        initial_investment (float): Starting investment amount
        annual_contribution (float): Annual contribution amount
        years (int): Investment time horizon
        balances (np.ndarray): Account balance each year
        contributions (np.ndarray): Cumulative contributions each year
        returns (np.ndarray): Annual returns
        final_balance (float): Final account balance
        total_contributions (float): Total amount contributed
        total_gains (float): Total gains (final - contributions)
        total_return (float): Total return percentage
        annualized_return (float): Annualized return percentage
        volatility (float): Return volatility (standard deviation)
        sharpe_ratio (float): Sharpe ratio (assuming 0% risk-free rate)
        max_drawdown (float): Maximum drawdown experienced
        probability (float): Scenario probability
    """

    scenario_id: str
    asset_allocation: Dict[str, float]
    initial_investment: float
    annual_contribution: float
    years: int
    balances: np.ndarray
    contributions: np.ndarray
    returns: np.ndarray
    final_balance: float = field(init=False)
    total_contributions: float = field(init=False)
    total_gains: float = field(init=False)
    total_return: float = field(init=False)
    annualized_return: float = field(init=False)
    volatility: float = field(init=False)
    sharpe_ratio: float = field(init=False)
    max_drawdown: float = field(init=False)
    probability: float = 1.0

    def __post_init__(self):
        """Calculate derived metrics"""
        self.final_balance = self.balances[-1]
        self.total_contributions = self.contributions[-1]
        self.total_gains = self.final_balance - self.total_contributions

        if self.total_contributions > 0:
            self.total_return = self.total_gains / self.total_contributions
            self.annualized_return = (
                (self.final_balance / self.total_contributions) ** (1 / self.years) - 1
            )
        else:
            self.total_return = 0.0
            self.annualized_return = 0.0

        self.volatility = np.std(self.returns) if len(self.returns) > 0 else 0.0

        if self.volatility > 0:
            self.sharpe_ratio = self.annualized_return / self.volatility
        else:
            self.sharpe_ratio = 0.0

        self.max_drawdown = self._calculate_max_drawdown()

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from peak"""
        if len(self.balances) == 0:
            return 0.0

        peak = self.balances[0]
        max_dd = 0.0

        for balance in self.balances:
            if balance > peak:
                peak = balance
            dd = (peak - balance) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return {
            "scenario_id": self.scenario_id,
            "asset_allocation": self.asset_allocation,
            "initial_investment": self.initial_investment,
            "annual_contribution": self.annual_contribution,
            "final_balance": self.final_balance,
            "total_contributions": self.total_contributions,
            "total_gains": self.total_gains,
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "probability": self.probability,
        }


@dataclass
class PortfolioStatistics:
    """
    Statistical analysis across multiple scenarios.

    Attributes:
        mean_final_balance (float): Expected final balance
        median_final_balance (float): Median final balance
        std_final_balance (float): Standard deviation of final balance
        percentile_5 (float): 5th percentile (bad outcome)
        percentile_25 (float): 25th percentile
        percentile_75 (float): 75th percentile
        percentile_95 (float): 95th percentile (good outcome)
        probability_of_loss (float): Probability of losing money
        probability_of_target (float): Probability of reaching target (if specified)
        mean_return (float): Expected annualized return
        std_return (float): Return volatility
        mean_sharpe (float): Expected Sharpe ratio
        value_at_risk_95 (float): 95% VaR (5th percentile loss)
        conditional_var_95 (float): 95% CVaR (expected shortfall)
        target_balance (Optional[float]): Target balance for probability calculation
    """

    mean_final_balance: float
    median_final_balance: float
    std_final_balance: float
    percentile_5: float
    percentile_25: float
    percentile_75: float
    percentile_95: float
    probability_of_loss: float
    probability_of_target: float
    mean_return: float
    std_return: float
    mean_sharpe: float
    value_at_risk_95: float
    conditional_var_95: float
    target_balance: Optional[float] = None


class PortfolioOptimizer:
    """
    Optimizes portfolio allocation using various methods.
    """

    def __init__(
        self,
        asset_returns: pd.DataFrame,
        asset_names: List[str],
        constraints: Optional[Dict] = None,
    ):
        """
        Initialize portfolio optimizer.

        Args:
            asset_returns (pd.DataFrame): Historical or simulated returns for each asset
            asset_names (List[str]): Names of assets
            constraints (Optional[Dict]): Portfolio constraints (min/max weights, etc.)
        """
        self.asset_returns = asset_returns
        self.asset_names = asset_names
        self.n_assets = len(asset_names)

        # Default constraints: long-only, fully invested
        self.constraints = constraints or {
            "min_weight": 0.0,
            "max_weight": 1.0,
            "sum_weights": 1.0,
        }

        # Calculate mean returns and covariance matrix
        self.mean_returns = asset_returns.mean().values
        self.cov_matrix = asset_returns.cov().values

    def calculate_portfolio_stats(
        self,
        weights: np.ndarray,
    ) -> Tuple[float, float, float]:
        """
        Calculate portfolio statistics.

        Args:
            weights (np.ndarray): Asset weights

        Returns:
            Tuple[float, float, float]: (expected return, volatility, Sharpe ratio)
        """
        portfolio_return = np.dot(weights, self.mean_returns)
        portfolio_variance = np.dot(weights.T, np.dot(self.cov_matrix, weights))
        portfolio_std = np.sqrt(portfolio_variance)

        sharpe_ratio = portfolio_return / portfolio_std if portfolio_std > 0 else 0.0

        return portfolio_return, portfolio_std, sharpe_ratio

    def optimize_mean_variance(
        self,
        target_return: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Mean-variance optimization (Markowitz).

        Args:
            target_return (Optional[float]): Target return (if None, maximize Sharpe)

        Returns:
            Dict[str, float]: Optimal asset allocation
        """
        if target_return is None:
            return self.optimize_max_sharpe()

        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))

        # Constraints
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},  # Fully invested
            {"type": "eq", "fun": lambda w: np.dot(w, self.mean_returns) - target_return},  # Target return
        ]

        # Bounds
        bounds = tuple(
            (self.constraints["min_weight"], self.constraints["max_weight"])
            for _ in range(self.n_assets)
        )

        # Initial guess: equal weights
        x0 = np.array([1.0 / self.n_assets] * self.n_assets)

        # Optimize
        result = minimize(
            portfolio_volatility,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            return dict(zip(self.asset_names, result.x))
        else:
            # Return equal weights if optimization fails
            return dict(zip(self.asset_names, x0))

    def optimize_min_volatility(self) -> Dict[str, float]:
        """
        Minimize portfolio volatility.

        Returns:
            Dict[str, float]: Optimal asset allocation
        """
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = tuple(
            (self.constraints["min_weight"], self.constraints["max_weight"])
            for _ in range(self.n_assets)
        )

        x0 = np.array([1.0 / self.n_assets] * self.n_assets)

        result = minimize(
            portfolio_volatility,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            return dict(zip(self.asset_names, result.x))
        else:
            return dict(zip(self.asset_names, x0))

    def optimize_max_sharpe(self) -> Dict[str, float]:
        """
        Maximize Sharpe ratio.

        Returns:
            Dict[str, float]: Optimal asset allocation
        """
        def neg_sharpe(weights):
            ret, std, sharpe = self.calculate_portfolio_stats(weights)
            return -sharpe  # Negative because we're minimizing

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = tuple(
            (self.constraints["min_weight"], self.constraints["max_weight"])
            for _ in range(self.n_assets)
        )

        x0 = np.array([1.0 / self.n_assets] * self.n_assets)

        result = minimize(
            neg_sharpe,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            return dict(zip(self.asset_names, result.x))
        else:
            return dict(zip(self.asset_names, x0))

    def optimize_max_return(self) -> Dict[str, float]:
        """
        Maximize expected return (essentially all in highest-return asset).

        Returns:
            Dict[str, float]: Optimal asset allocation
        """
        weights = np.zeros(self.n_assets)
        max_return_idx = np.argmax(self.mean_returns)
        weights[max_return_idx] = 1.0

        return dict(zip(self.asset_names, weights))

    def optimize_risk_parity(self) -> Dict[str, float]:
        """
        Risk parity allocation (equal risk contribution).

        Returns:
            Dict[str, float]: Optimal asset allocation
        """
        def risk_parity_objective(weights):
            portfolio_var = np.dot(weights.T, np.dot(self.cov_matrix, weights))
            marginal_contrib = np.dot(self.cov_matrix, weights)
            risk_contrib = weights * marginal_contrib / np.sqrt(portfolio_var)
            target = np.ones(self.n_assets) / self.n_assets
            return np.sum((risk_contrib - target) ** 2)

        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = tuple(
            (self.constraints["min_weight"], self.constraints["max_weight"])
            for _ in range(self.n_assets)
        )

        x0 = np.array([1.0 / self.n_assets] * self.n_assets)

        result = minimize(
            risk_parity_objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            return dict(zip(self.asset_names, result.x))
        else:
            return dict(zip(self.asset_names, x0))

    def generate_efficient_frontier(
        self,
        n_points: int = 50,
    ) -> pd.DataFrame:
        """
        Generate the efficient frontier.

        Args:
            n_points (int): Number of points on the frontier

        Returns:
            pd.DataFrame: Efficient frontier data
        """
        min_return = np.min(self.mean_returns)
        max_return = np.max(self.mean_returns)

        target_returns = np.linspace(min_return, max_return, n_points)

        frontier_data = []

        for target in target_returns:
            try:
                weights_dict = self.optimize_mean_variance(target_return=target)
                weights = np.array([weights_dict[name] for name in self.asset_names])
                ret, vol, sharpe = self.calculate_portfolio_stats(weights)

                frontier_data.append({
                    "target_return": target,
                    "expected_return": ret,
                    "volatility": vol,
                    "sharpe_ratio": sharpe,
                    **weights_dict,
                })
            except:
                continue

        return pd.DataFrame(frontier_data)


class MOCA:
    """
    MOCA (Moteur de Calcul / Calculation Engine)

    Main calculation engine that orchestrates:
    1. Investment simulations across scenarios
    2. Statistical analysis
    3. Portfolio optimization
    """

    def __init__(
        self,
        investment_profile: InvestmentProfile,
    ):
        """
        Initialize MOCA with an investment profile.

        Args:
            investment_profile (InvestmentProfile): Investor's profile
        """
        self.profile = investment_profile
        self.results: List[InvestmentResult] = []

    def simulate_investment(
        self,
        scenario: TaxIntegratedScenario,
        asset_allocation: Dict[str, float],
    ) -> InvestmentResult:
        """
        Simulate investment under a specific scenario and allocation.

        Args:
            scenario (TaxIntegratedScenario): Economic scenario with taxes
            asset_allocation (Dict[str, float]): Asset allocation weights

        Returns:
            InvestmentResult: Simulation result
        """
        pv = self.profile.personal_vars
        years = pv.investment_horizon
        initial = pv.current_savings
        annual_contrib = pv.monthly_contribution * 12

        balance = initial
        balances = []
        contributions = []
        returns = []

        cumulative_contrib = initial

        for year in range(years):
            # Calculate weighted return
            stock_weight = asset_allocation.get("stocks", 0.0) + asset_allocation.get("domestic_stocks", 0.0) + asset_allocation.get("international_stocks", 0.0) + asset_allocation.get("emerging_markets", 0.0)
            bond_weight = asset_allocation.get("bonds", 0.0) + asset_allocation.get("government_bonds", 0.0) + asset_allocation.get("corporate_bonds", 0.0)
            re_weight = asset_allocation.get("real_estate", 0.0)

            weighted_return = (
                stock_weight * scenario.after_tax_stock_returns[year]
                + bond_weight * scenario.after_tax_bond_returns[year]
                + re_weight * scenario.after_tax_real_estate_returns[year]
            )

            # Apply return
            balance *= (1 + weighted_return)
            returns.append(weighted_return)

            # Add annual contribution
            balance += annual_contrib
            cumulative_contrib += annual_contrib

            balances.append(balance)
            contributions.append(cumulative_contrib)

        return InvestmentResult(
            scenario_id=scenario.base_scenario.scenario_id,
            asset_allocation=asset_allocation,
            initial_investment=initial,
            annual_contribution=annual_contrib,
            years=years,
            balances=np.array(balances),
            contributions=np.array(contributions),
            returns=np.array(returns),
            probability=scenario.base_scenario.probability,
        )

    def run_scenarios(
        self,
        scenarios: List[TaxIntegratedScenario],
        asset_allocation: Dict[str, float],
    ) -> List[InvestmentResult]:
        """
        Run investment simulation across multiple scenarios.

        Args:
            scenarios (List[TaxIntegratedScenario]): List of scenarios
            asset_allocation (Dict[str, float]): Asset allocation to test

        Returns:
            List[InvestmentResult]: Results for all scenarios
        """
        self.results = [
            self.simulate_investment(scenario, asset_allocation)
            for scenario in scenarios
        ]
        return self.results

    def calculate_statistics(
        self,
        results: Optional[List[InvestmentResult]] = None,
        target_balance: Optional[float] = None,
    ) -> PortfolioStatistics:
        """
        Calculate statistical metrics across scenarios.

        Args:
            results (Optional[List[InvestmentResult]]): Results to analyze (uses self.results if None)
            target_balance (Optional[float]): Target balance for probability calculation

        Returns:
            PortfolioStatistics: Statistical analysis
        """
        if results is None:
            results = self.results

        if not results:
            raise ValueError("No results to analyze")

        final_balances = np.array([r.final_balance for r in results])
        annualized_returns = np.array([r.annualized_return for r in results])
        sharpe_ratios = np.array([r.sharpe_ratio for r in results])
        probabilities = np.array([r.probability for r in results])

        # Weight by probability if available
        if np.sum(probabilities) > 0 and not np.all(probabilities == probabilities[0]):
            mean_balance = np.average(final_balances, weights=probabilities)
            mean_return = np.average(annualized_returns, weights=probabilities)
            mean_sharpe = np.average(sharpe_ratios, weights=probabilities)
        else:
            mean_balance = np.mean(final_balances)
            mean_return = np.mean(annualized_returns)
            mean_sharpe = np.mean(sharpe_ratios)

        # Calculate percentiles
        p5 = np.percentile(final_balances, 5)
        p25 = np.percentile(final_balances, 25)
        p75 = np.percentile(final_balances, 75)
        p95 = np.percentile(final_balances, 95)

        # Probability of loss
        initial_contributions = results[0].total_contributions
        prob_loss = np.sum(final_balances < initial_contributions) / len(final_balances)

        # Probability of reaching target
        if target_balance is not None:
            prob_target = np.sum(final_balances >= target_balance) / len(final_balances)
        else:
            prob_target = 0.0

        # Value at Risk (VaR) and Conditional VaR (CVaR)
        var_95 = initial_contributions - p5
        losses = initial_contributions - final_balances[final_balances < initial_contributions]
        cvar_95 = np.mean(losses) if len(losses) > 0 else 0.0

        return PortfolioStatistics(
            mean_final_balance=mean_balance,
            median_final_balance=np.median(final_balances),
            std_final_balance=np.std(final_balances),
            percentile_5=p5,
            percentile_25=p25,
            percentile_75=p75,
            percentile_95=p95,
            probability_of_loss=prob_loss,
            probability_of_target=prob_target,
            mean_return=mean_return,
            std_return=np.std(annualized_returns),
            mean_sharpe=mean_sharpe,
            value_at_risk_95=var_95,
            conditional_var_95=cvar_95,
            target_balance=target_balance,
        )

    def optimize_portfolio(
        self,
        scenarios: List[TaxIntegratedScenario],
        method: OptimizationMethod = OptimizationMethod.MAX_SHARPE,
        asset_classes: Optional[List[str]] = None,
        constraints: Optional[Dict] = None,
    ) -> Tuple[Dict[str, float], PortfolioStatistics]:
        """
        Optimize portfolio allocation across scenarios.

        Args:
            scenarios (List[TaxIntegratedScenario]): Scenarios to optimize over
            method (OptimizationMethod): Optimization method
            asset_classes (Optional[List[str]]): Asset classes to include
            constraints (Optional[Dict]): Portfolio constraints

        Returns:
            Tuple[Dict[str, float], PortfolioStatistics]: (optimal allocation, statistics)
        """
        if asset_classes is None:
            asset_classes = ["stocks", "bonds", "real_estate"]

        # Build return matrix from scenarios
        returns_data = []
        for scenario in scenarios:
            scenario_returns = {}
            if "stocks" in asset_classes:
                scenario_returns["stocks"] = scenario.after_tax_stock_returns.mean()
            if "bonds" in asset_classes:
                scenario_returns["bonds"] = scenario.after_tax_bond_returns.mean()
            if "real_estate" in asset_classes:
                scenario_returns["real_estate"] = scenario.after_tax_real_estate_returns.mean()

            returns_data.append(scenario_returns)

        returns_df = pd.DataFrame(returns_data)

        # Create optimizer
        optimizer = PortfolioOptimizer(
            asset_returns=returns_df,
            asset_names=asset_classes,
            constraints=constraints,
        )

        # Optimize based on method
        if method == OptimizationMethod.MAX_SHARPE:
            optimal_weights = optimizer.optimize_max_sharpe()
        elif method == OptimizationMethod.MIN_VOLATILITY:
            optimal_weights = optimizer.optimize_min_volatility()
        elif method == OptimizationMethod.MAX_RETURN:
            optimal_weights = optimizer.optimize_max_return()
        elif method == OptimizationMethod.RISK_PARITY:
            optimal_weights = optimizer.optimize_risk_parity()
        elif method == OptimizationMethod.EQUAL_WEIGHT:
            optimal_weights = {asset: 1.0 / len(asset_classes) for asset in asset_classes}
        else:
            optimal_weights = optimizer.optimize_max_sharpe()

        # Run scenarios with optimal allocation
        results = self.run_scenarios(scenarios, optimal_weights)
        statistics = self.calculate_statistics(results)

        return optimal_weights, statistics

    def generate_report(self) -> str:
        """
        Generate a comprehensive investment report.

        Returns:
            str: Investment report
        """
        if not self.results:
            return "No simulation results available."

        stats = self.calculate_statistics()

        report = f"""
{'=' * 70}
MOCA INVESTMENT ANALYSIS REPORT
{'=' * 70}

Investment Profile:
  Investor Age: {self.profile.personal_vars.age}
  Investment Horizon: {self.profile.personal_vars.investment_horizon} years
  Initial Investment: ${self.profile.personal_vars.current_savings:,.2f}
  Monthly Contribution: ${self.profile.personal_vars.monthly_contribution:,.2f}
  Annual Contribution: ${self.profile.personal_vars.monthly_contribution * 12:,.2f}

Portfolio Allocation:
"""
        if self.results:
            allocation = self.results[0].asset_allocation
            for asset, weight in allocation.items():
                report += f"  {asset}: {weight:.1%}\n"

        report += f"""
Expected Outcomes (across {len(self.results)} scenarios):
  Expected Final Balance: ${stats.mean_final_balance:,.2f}
  Median Final Balance: ${stats.median_final_balance:,.2f}
  Standard Deviation: ${stats.std_final_balance:,.2f}

  Percentile Analysis:
    5th Percentile (worst 5%): ${stats.percentile_5:,.2f}
    25th Percentile: ${stats.percentile_25:,.2f}
    75th Percentile: ${stats.percentile_75:,.2f}
    95th Percentile (best 5%): ${stats.percentile_95:,.2f}

Return Metrics:
  Expected Annualized Return: {stats.mean_return:.2%}
  Return Volatility: {stats.std_return:.2%}
  Expected Sharpe Ratio: {stats.mean_sharpe:.2f}

Risk Metrics:
  Probability of Loss: {stats.probability_of_loss:.1%}
  95% Value at Risk: ${stats.value_at_risk_95:,.2f}
  95% Conditional VaR: ${stats.conditional_var_95:,.2f}

{'=' * 70}
"""

        return report
