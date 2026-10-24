"""
Assemblage multi-horizons : comparaison au R (``tests/reference_r/assembl_invest.py``,
identique au vrai R d'après ``tests/test_reference_r.py``), conservation du
capital et des contraintes, et branchement sur l'optimiseur.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from investment_calculator.modules.capital_tranches import split_into_tranches
from investment_calculator.modules.household_cash_flow import Project, capital_curve
from investment_calculator.modules.net_returns import NetReturns
from investment_calculator.modules.placement_optimizer import (
    optimize_by_horizon,
    placement_constraints,
)
from investment_calculator.modules.tranche_allocation import (
    assemble_allocation,
    required_horizons,
)
from investment_calculator.placement_catalog import load_placement_catalog
from tests.reference_r.assembl_invest import r_assembl_invest

R_CASE: dict[str, Any] = json.loads(
    (Path(__file__).parent / "reference_r" / "r_outputs.json").read_text(encoding="utf-8")
)["assembl_invest"]
PLACEMENTS = ["p1", "p2", "p3"]


def _weights(table: dict[int, list[float]]) -> pd.DataFrame:
    return pd.DataFrame({h: w for h, w in table.items()}, index=PLACEMENTS)


def test_same_allocation_as_r_on_equal_tranches() -> None:
    capital = np.asarray(R_CASE["capital"], dtype=float)
    weights = _weights({int(h): w for h, w in R_CASE["weights"].items()})
    allocation = assemble_allocation(split_into_tranches(capital), weights)
    r_output = np.asarray(R_CASE["output"], dtype=float)  # placements × dates R
    # Dernière année : capital nul, le R rend NaN (0 / 0), le portage 0.
    np.testing.assert_allclose(allocation.amounts.to_numpy().T[:, :-1], r_output[:, :-1])
    assert np.isnan(r_output[:, -1]).all()
    assert (allocation.amounts.iloc[-1] == 0).all()


def test_r_does_not_weight_tranches_by_amount() -> None:
    """Écart 1 : avec des tranches de montants différents, le R se trompe de répartition."""
    capital = np.array([10_000.0, 40_000.0, 10_000.0])
    tranches = split_into_tranches(capital)
    assert [(t.amount, t.duration) for t in tranches] == [(10_000.0, 2), (30_000.0, 1)]
    weights = _weights({1: [1.0, 0.0, 0.0], 2: [0.0, 0.0, 1.0]})
    ours = assemble_allocation(tranches, weights).amounts
    assert ours.loc[1].tolist() == pytest.approx([30_000.0, 0.0, 10_000.0])
    # Les mêmes tranches en dates R : chacune pèse autant, quel que soit son montant.
    soltot = np.zeros((3, 3, 3))
    soltot[:, 0, :] = np.array([1.0, 0.0, 0.0])[:, None]
    soltot[:, 1, :] = np.array([0.0, 0.0, 1.0])[:, None]
    tr1 = np.array([[1.0, 2.0, 1.0], [2.0, 2.0, 2.0]])
    theirs = r_assembl_invest(soltot, tr1, capital, horiz=3)
    assert theirs[:, 1].tolist() == pytest.approx([20_000.0, 0.0, 20_000.0])


def test_r_drops_weights_under_one_percent() -> None:
    """Écart 2 : le R met à zéro un placement à 0,5 % ; le portage le garde."""
    capital = np.array([10_000.0, 10_000.0, 0.0])
    weights = _weights({2: [0.995, 0.005, 0.0]})
    ours = assemble_allocation(split_into_tranches(capital), weights).amounts
    assert ours.loc[0, "p2"] == pytest.approx(50.0)
    soltot = np.zeros((3, 3, 3))
    soltot[:, 1, :] = np.array([0.995, 0.005, 0.0])[:, None]
    theirs = r_assembl_invest(soltot, np.array([[1.0, 2.0, 1.0]]), capital, horiz=3)
    assert theirs[1, 0] == 0.0 and theirs[0, 0] == pytest.approx(10_000.0)


def test_one_year_tranche_is_assembled() -> None:
    """Écart 3 : le R échoue sur une tranche présente une seule année."""
    assert R_CASE["one_year_error"] == "incorrect number of dimensions"
    tranches = split_into_tranches([0.0, 5_000.0, 0.0])
    allocation = assemble_allocation(tranches, _weights({1: [0.2, 0.8, 0.0]}))
    assert allocation.amounts.loc[1].tolist() == pytest.approx([1_000.0, 4_000.0, 0.0])


@pytest.mark.parametrize("seed", range(10))
def test_capital_and_linear_constraints_are_preserved(seed: int) -> None:
    rng = np.random.default_rng(seed)
    horizon = int(rng.integers(3, 25))
    curve = np.maximum(
        np.concatenate([[rng.uniform(0, 30_000)], rng.normal(3_000, 9_000, horizon)]).cumsum(), 0
    )
    tranches = split_into_tranches(curve)
    needed = required_horizons(tranches)
    # Poids aléatoires respectant tous « p1 ≤ 40 % ».
    table = {}
    for h in needed:
        w = rng.dirichlet(np.ones(3))
        if w[0] > 0.4:
            w = np.array([0.4, *(w[1:] * 0.6 / w[1:].sum())])
        table[h] = list(w)
    allocation = assemble_allocation(tranches, _weights(table))
    placed = allocation.amounts.sum(axis=1) + allocation.unplaced
    np.testing.assert_allclose(placed.to_numpy(), curve, atol=1e-6)
    assert (allocation.weights["p1"].dropna() <= 0.4 + 1e-9).all()


def test_amount_arriving_at_horizon_is_unplaced() -> None:
    allocation = assemble_allocation(
        split_into_tranches([1_000.0, 1_000.0, 3_000.0]), _weights({2: [1.0, 0.0, 0.0]})
    )
    assert allocation.unplaced.tolist() == [0.0, 0.0, 2_000.0]
    assert allocation.amounts["p1"].tolist() == [1_000.0, 1_000.0, 1_000.0]


def test_missing_horizon_is_reported() -> None:
    tranches = split_into_tranches([5_000.0, 0.0, 5_000.0, 5_000.0, 0.0])
    with pytest.raises(ValueError, match=r"horizons \[2\]"):
        assemble_allocation(tranches, _weights({1: [1.0, 0.0, 0.0]}))


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sommer à 1"):
        assemble_allocation(split_into_tranches([5_000.0, 0.0]), _weights({1: [0.5, 0.2, 0.0]}))


def test_with_the_optimizer_short_money_goes_to_the_safe_placement() -> None:
    """Bout en bout : projet à 2 ans, épargne longue ; le court terme va au moins risqué."""
    catalog = load_placement_catalog("fr-2026")
    placements = ["cto_actions", "av_fonds_euros"]
    horizons = list(range(1, 11))
    rng = np.random.default_rng(1)
    n = 2000
    equity = 0.06 + 0.18 * rng.standard_normal((n, 1))
    safe = 0.02 + 0.01 * rng.standard_normal((n, 1))
    h = np.asarray(horizons, dtype=float)[None, :]
    # Rendement annualisé : la volatilité des actions décroît en √H.
    eq_ann = 0.06 + (equity - 0.06) / np.sqrt(h)
    multiples = np.stack([(1 + eq_ann) ** h, (1 + safe) ** h], axis=-1)
    net = NetReturns(
        multiples=multiples,
        scenario_ids=[f"s{i}" for i in range(n)],
        horizons=horizons,
        placement_ids=placements,
    )
    trip = Project("voyage", 2, 20_000.0, 0.0, 0)
    curve = capital_curve([trip], 10, initial_savings=20_000.0, annual_savings=5_000.0)
    tranches = split_into_tranches(curve)
    constraints = placement_constraints(
        catalog, placements, total_contributions=float(curve.max()), n_periods=10
    )
    weights = optimize_by_horizon(
        net, constraints, required_horizons(tranches), risk_aversion=4.0
    )
    allocation = assemble_allocation(tranches, weights)
    short = next(t for t in tranches if t.withdrawal_year == 2)
    long = next(t for t in tranches if t.start_year == 0 and t.withdrawal_year is None)
    assert weights[short.duration]["cto_actions"] < weights[long.duration]["cto_actions"]
    np.testing.assert_allclose(
        allocation.amounts.sum(axis=1) + allocation.unplaced, curve, atol=1e-6
    )
