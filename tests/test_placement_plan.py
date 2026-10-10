"""
Chaîne GSE → GSE+ → GSE++ → Markowitz → patrimoine, au format du rapport.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from investment_calculator.modules.placement_plan import max_drawdown, plan_placements
from investment_calculator.modules.scenario_generator import ScenarioGenerator
from investment_calculator.placement_catalog import load_placement_catalog

FR_2026 = load_placement_catalog("fr-2026")


@pytest.fixture(scope="module")
def scenarios() -> pd.DataFrame:
    return ScenarioGenerator(random_seed=42).generate(
        {"num_scenarios": 200, "time_horizon": 12, "timestep": 1.0, "use_stochastic": False}
    )["scenarios"]


def _flows(n: int = 12, amount: float = 12_000.0) -> pd.DataFrame:
    return pd.DataFrame({"net_flow": [amount] * (n + 1)})


def test_resultats_au_format_du_rapport(scenarios: pd.DataFrame) -> None:
    results = plan_placements(
        scenarios, FR_2026, _flows(), horizon=10, objective="mean_variance",
        risk_aversion=5.0, risk_free_placement="livret_a", goal_amount=150_000.0,
        frontier_points=6,
    )
    portfolio = results["optimal_portfolio"]
    weights = pd.Series(portfolio["weights"])
    assert list(weights.index) == FR_2026.placement_ids
    assert weights.sum() == pytest.approx(1.0) and (weights >= 0).all()
    assert portfolio["sharpe_ratio"] == pytest.approx(
        (portfolio["expected_return"] - portfolio["risk_free_rate"])
        / portfolio["expected_volatility"]
    )
    assert 0.0 <= portfolio["max_drawdown"] < 1.0

    simulation = results["simulation_results"]
    terminal = simulation["terminal_wealth"]["wealth"].to_numpy()
    assert simulation["wealth_paths"].shape == (200, 1 + 11)
    assert simulation["statistics"]["total_contributions"] == pytest.approx(11 * 12_000.0)
    goal = results["goal_analysis"]
    assert goal["probability_of_achieving"] == pytest.approx((terminal >= 150_000.0).mean())
    assert not results["efficient_frontier"].empty


def test_sans_placement_de_reference_le_sharpe_n_est_pas_calcule(
    scenarios: pd.DataFrame,
) -> None:
    results = plan_placements(
        scenarios, FR_2026, _flows(), horizon=5, objective="min_volatility", frontier_points=3
    )
    assert results["optimal_portfolio"]["sharpe_ratio"] is None
    assert "goal_analysis" not in results
    with pytest.raises(ValueError, match="risk_free_placement"):
        plan_placements(scenarios, FR_2026, _flows(), horizon=5, objective="max_sharpe")
    with pytest.raises(ValueError, match="absent du catalogue"):
        plan_placements(scenarios, FR_2026, _flows(), horizon=5, objective="min_volatility",
                        risk_free_placement="compte_courant")


def test_perte_maximale_d_un_portefeuille_fixe() -> None:
    index = pd.MultiIndex.from_product([["a", "b"], [1.0, 2.0, 3.0]])
    # a : +10 %, −50 %, +100 % ; b : toujours +10 %.
    gross = pd.DataFrame({"x": [0.1, -0.5, 1.0, 0.1, 0.1, 0.1]}, index=index)
    weights = pd.Series({"x": 1.0})
    assert max_drawdown(gross, weights, 3) == pytest.approx(np.median([0.5, 0.0]))
    assert max_drawdown(gross, weights, 1) == 0.0
