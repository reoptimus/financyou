"""
GSE (Global Scenario Engine)

Generates economic scenarios for investment analysis including:
- Inflation rates
- Interest rates
- Market returns
- GDP growth
- Economic cycles

Supports both historical scenarios and Monte Carlo simulation.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class ScenarioType(Enum):
    """Types of economic scenarios"""
    HISTORICAL = "historical"
    MONTE_CARLO = "monte_carlo"
    PESSIMISTIC = "pessimistic"
    BASELINE = "baseline"
    OPTIMISTIC = "optimistic"
    CUSTOM = "custom"


@dataclass
class EconomicScenario:
    """
    Represents a single economic scenario with various economic indicators.

    Attributes:
        scenario_id (str): Unique identifier for the scenario
        scenario_type (ScenarioType): Type of scenario
        years (int): Number of years in the scenario
        inflation_rates (np.ndarray): Annual inflation rates
        interest_rates (np.ndarray): Risk-free interest rates
        stock_returns (np.ndarray): Stock market returns
        bond_returns (np.ndarray): Bond market returns
        real_estate_returns (np.ndarray): Real estate returns
        gdp_growth (np.ndarray): GDP growth rates
        probability (float): Probability of this scenario occurring
        metadata (Dict): Additional scenario metadata
    """

    scenario_id: str
    scenario_type: ScenarioType
    years: int
    inflation_rates: np.ndarray
    interest_rates: np.ndarray
    stock_returns: np.ndarray
    bond_returns: np.ndarray
    real_estate_returns: np.ndarray
    gdp_growth: np.ndarray
    probability: float = 1.0
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate scenario data"""
        arrays = [
            self.inflation_rates,
            self.interest_rates,
            self.stock_returns,
            self.bond_returns,
            self.real_estate_returns,
            self.gdp_growth,
        ]

        # Check all arrays have the same length
        if not all(len(arr) == self.years for arr in arrays):
            raise ValueError("All economic indicator arrays must have length equal to years")

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert scenario to a pandas DataFrame.

        Returns:
            pd.DataFrame: Scenario data with years as index
        """
        return pd.DataFrame(
            {
                "inflation_rate": self.inflation_rates,
                "interest_rate": self.interest_rates,
                "stock_return": self.stock_returns,
                "bond_return": self.bond_returns,
                "real_estate_return": self.real_estate_returns,
                "gdp_growth": self.gdp_growth,
            },
            index=pd.Index(range(1, self.years + 1), name="year"),
        )

    def get_summary_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate summary statistics for all economic indicators.

        Returns:
            Dict[str, Dict[str, float]]: Statistics for each indicator
        """
        indicators = {
            "inflation": self.inflation_rates,
            "interest_rates": self.interest_rates,
            "stock_returns": self.stock_returns,
            "bond_returns": self.bond_returns,
            "real_estate_returns": self.real_estate_returns,
            "gdp_growth": self.gdp_growth,
        }

        stats = {}
        for name, values in indicators.items():
            stats[name] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "median": float(np.median(values)),
            }

        return stats


class GlobalScenarioEngine:
    """
    Global Scenario Engine (GSE) for generating economic scenarios.

    This engine creates multiple economic scenarios that can be used for
    investment analysis and portfolio optimization.
    """

    def __init__(self, random_seed: Optional[int] = None):
        """
        Initialize the Global Scenario Engine.

        Args:
            random_seed (Optional[int]): Random seed for reproducibility
        """
        self.random_seed = random_seed
        if random_seed is not None:
            np.random.seed(random_seed)

        # Historical average values (US-based, can be configured)
        self.default_params = {
            "inflation_mean": 0.025,
            "inflation_std": 0.015,
            "interest_mean": 0.03,
            "interest_std": 0.02,
            "stock_return_mean": 0.10,
            "stock_return_std": 0.18,
            "bond_return_mean": 0.05,
            "bond_return_std": 0.07,
            "real_estate_mean": 0.08,
            "real_estate_std": 0.12,
            "gdp_growth_mean": 0.025,
            "gdp_growth_std": 0.02,
        }

    def generate_baseline_scenario(self, years: int) -> EconomicScenario:
        """
        Generate a baseline (expected) economic scenario using mean values.

        Args:
            years (int): Number of years to simulate

        Returns:
            EconomicScenario: Baseline scenario
        """
        scenario_id = "baseline"

        # Use mean values with small random variations
        inflation = np.random.normal(
            self.default_params["inflation_mean"],
            self.default_params["inflation_std"] * 0.3,
            years,
        )
        interest = np.random.normal(
            self.default_params["interest_mean"],
            self.default_params["interest_std"] * 0.3,
            years,
        )
        stocks = np.random.normal(
            self.default_params["stock_return_mean"],
            self.default_params["stock_return_std"] * 0.5,
            years,
        )
        bonds = np.random.normal(
            self.default_params["bond_return_mean"],
            self.default_params["bond_return_std"] * 0.5,
            years,
        )
        real_estate = np.random.normal(
            self.default_params["real_estate_mean"],
            self.default_params["real_estate_std"] * 0.5,
            years,
        )
        gdp = np.random.normal(
            self.default_params["gdp_growth_mean"],
            self.default_params["gdp_growth_std"] * 0.3,
            years,
        )

        return EconomicScenario(
            scenario_id=scenario_id,
            scenario_type=ScenarioType.BASELINE,
            years=years,
            inflation_rates=inflation,
            interest_rates=interest,
            stock_returns=stocks,
            bond_returns=bonds,
            real_estate_returns=real_estate,
            gdp_growth=gdp,
            probability=1.0,
            metadata={"description": "Baseline scenario with expected mean values"},
        )

    def generate_optimistic_scenario(self, years: int) -> EconomicScenario:
        """
        Generate an optimistic economic scenario (above-average returns).

        Args:
            years (int): Number of years to simulate

        Returns:
            EconomicScenario: Optimistic scenario
        """
        scenario_id = "optimistic"

        # Use higher means, lower volatility
        inflation = np.random.normal(0.02, 0.01, years)
        interest = np.random.normal(0.035, 0.015, years)
        stocks = np.random.normal(0.12, 0.15, years)
        bonds = np.random.normal(0.06, 0.05, years)
        real_estate = np.random.normal(0.10, 0.10, years)
        gdp = np.random.normal(0.035, 0.015, years)

        return EconomicScenario(
            scenario_id=scenario_id,
            scenario_type=ScenarioType.OPTIMISTIC,
            years=years,
            inflation_rates=inflation,
            interest_rates=interest,
            stock_returns=stocks,
            bond_returns=bonds,
            real_estate_returns=real_estate,
            gdp_growth=gdp,
            probability=0.25,
            metadata={"description": "Optimistic scenario with above-average growth"},
        )

    def generate_pessimistic_scenario(self, years: int) -> EconomicScenario:
        """
        Generate a pessimistic economic scenario (below-average returns, higher volatility).

        Args:
            years (int): Number of years to simulate

        Returns:
            EconomicScenario: Pessimistic scenario
        """
        scenario_id = "pessimistic"

        # Use lower means, higher volatility
        inflation = np.random.normal(0.03, 0.025, years)
        interest = np.random.normal(0.025, 0.025, years)
        stocks = np.random.normal(0.06, 0.25, years)
        bonds = np.random.normal(0.03, 0.10, years)
        real_estate = np.random.normal(0.04, 0.18, years)
        gdp = np.random.normal(0.015, 0.03, years)

        return EconomicScenario(
            scenario_id=scenario_id,
            scenario_type=ScenarioType.PESSIMISTIC,
            years=years,
            inflation_rates=inflation,
            interest_rates=interest,
            stock_returns=stocks,
            bond_returns=bonds,
            real_estate_returns=real_estate,
            gdp_growth=gdp,
            probability=0.25,
            metadata={"description": "Pessimistic scenario with below-average growth and high volatility"},
        )

    def generate_monte_carlo_scenarios(
        self,
        years: int,
        n_scenarios: int = 1000,
        custom_params: Optional[Dict[str, float]] = None,
    ) -> List[EconomicScenario]:
        """
        Generate multiple scenarios using Monte Carlo simulation.

        Args:
            years (int): Number of years to simulate
            n_scenarios (int): Number of scenarios to generate
            custom_params (Optional[Dict]): Custom parameters to override defaults

        Returns:
            List[EconomicScenario]: List of Monte Carlo scenarios
        """
        params = self.default_params.copy()
        if custom_params:
            params.update(custom_params)

        scenarios = []
        probability = 1.0 / n_scenarios

        for i in range(n_scenarios):
            scenario_id = f"mc_{i+1:04d}"

            # Generate correlated returns
            # Stocks and GDP are positively correlated
            # Bonds and stocks are negatively correlated
            # Inflation and interest rates are positively correlated

            base_shock = np.random.randn(years)
            inflation_shock = np.random.randn(years)
            market_shock = np.random.randn(years)

            inflation = (
                params["inflation_mean"]
                + params["inflation_std"] * (0.7 * base_shock + 0.3 * inflation_shock)
            )

            interest = (
                params["interest_mean"]
                + params["interest_std"] * (0.5 * base_shock + 0.5 * inflation_shock)
            )

            stocks = (
                params["stock_return_mean"]
                + params["stock_return_std"] * (0.8 * market_shock + 0.2 * base_shock)
            )

            bonds = (
                params["bond_return_mean"]
                + params["bond_return_std"] * (-0.3 * market_shock + 0.7 * base_shock)
            )

            real_estate = (
                params["real_estate_mean"]
                + params["real_estate_std"] * (0.5 * market_shock + 0.5 * base_shock)
            )

            gdp = (
                params["gdp_growth_mean"]
                + params["gdp_growth_std"] * (0.6 * market_shock + 0.4 * base_shock)
            )

            scenario = EconomicScenario(
                scenario_id=scenario_id,
                scenario_type=ScenarioType.MONTE_CARLO,
                years=years,
                inflation_rates=inflation,
                interest_rates=interest,
                stock_returns=stocks,
                bond_returns=bonds,
                real_estate_returns=real_estate,
                gdp_growth=gdp,
                probability=probability,
                metadata={"simulation_index": i + 1},
            )

            scenarios.append(scenario)

        return scenarios

    def generate_standard_scenarios(self, years: int) -> List[EconomicScenario]:
        """
        Generate a standard set of scenarios (pessimistic, baseline, optimistic).

        Args:
            years (int): Number of years to simulate

        Returns:
            List[EconomicScenario]: List of standard scenarios
        """
        return [
            self.generate_pessimistic_scenario(years),
            self.generate_baseline_scenario(years),
            self.generate_optimistic_scenario(years),
        ]

    def create_custom_scenario(
        self,
        scenario_id: str,
        years: int,
        inflation: Optional[np.ndarray] = None,
        interest: Optional[np.ndarray] = None,
        stocks: Optional[np.ndarray] = None,
        bonds: Optional[np.ndarray] = None,
        real_estate: Optional[np.ndarray] = None,
        gdp: Optional[np.ndarray] = None,
        probability: float = 1.0,
    ) -> EconomicScenario:
        """
        Create a custom scenario with user-defined values.

        Args:
            scenario_id (str): Unique identifier
            years (int): Number of years
            inflation (Optional[np.ndarray]): Custom inflation rates
            interest (Optional[np.ndarray]): Custom interest rates
            stocks (Optional[np.ndarray]): Custom stock returns
            bonds (Optional[np.ndarray]): Custom bond returns
            real_estate (Optional[np.ndarray]): Custom real estate returns
            gdp (Optional[np.ndarray]): Custom GDP growth rates
            probability (float): Scenario probability

        Returns:
            EconomicScenario: Custom scenario
        """
        # Use baseline values if not provided
        baseline = self.generate_baseline_scenario(years)

        return EconomicScenario(
            scenario_id=scenario_id,
            scenario_type=ScenarioType.CUSTOM,
            years=years,
            inflation_rates=inflation if inflation is not None else baseline.inflation_rates,
            interest_rates=interest if interest is not None else baseline.interest_rates,
            stock_returns=stocks if stocks is not None else baseline.stock_returns,
            bond_returns=bonds if bonds is not None else baseline.bond_returns,
            real_estate_returns=real_estate if real_estate is not None else baseline.real_estate_returns,
            gdp_growth=gdp if gdp is not None else baseline.gdp_growth,
            probability=probability,
            metadata={"description": "Custom user-defined scenario"},
        )

    def analyze_scenarios(self, scenarios: List[EconomicScenario]) -> pd.DataFrame:
        """
        Analyze and compare multiple scenarios.

        Args:
            scenarios (List[EconomicScenario]): List of scenarios to analyze

        Returns:
            pd.DataFrame: Comparison of scenario statistics
        """
        results = []

        for scenario in scenarios:
            stats = scenario.get_summary_statistics()

            row = {
                "scenario_id": scenario.scenario_id,
                "type": scenario.scenario_type.value,
                "probability": scenario.probability,
            }

            # Flatten statistics
            for indicator, indicator_stats in stats.items():
                for stat_name, value in indicator_stats.items():
                    row[f"{indicator}_{stat_name}"] = value

            results.append(row)

        return pd.DataFrame(results)
