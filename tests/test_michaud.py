"""
Rééchantillonnage de Michaud : comparaison au R (``tests/reference_r/bootstrap_michaud.py``,
identique au vrai R d'après ``tests/test_reference_r.py``), contraintes du profil
conservées, et stabilité.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from investment_calculator.modules.net_returns import NetReturns
from investment_calculator.modules.placement_optimizer import (
    optimize_by_horizon,
    optimize_horizon,
    optimize_horizon_resampled,
    placement_constraints,
)
from investment_calculator.placement_catalog import load_placement_catalog
from tests.reference_r.bootstrap_michaud import r_boot_michaud

FR_2026 = load_placement_catalog("fr-2026")
R_CASE: dict[str, Any] = json.loads(
    (Path(__file__).parent / "reference_r" / "r_outputs.json").read_text(encoding="utf-8")
)["michaud"]
PLACEMENTS = ["cto_actions", "av_fonds_euros", "livret_a"]


def _net_from_annual(returns: np.ndarray) -> NetReturns:
    """GSE++ dont le rendement annualisé à l'horizon d (1, 2, …) vaut returns[:, d-1, :]."""
    horizons = list(range(1, returns.shape[1] + 1))
    h = np.asarray(horizons, dtype=float)[None, :, None]
    return NetReturns(
        multiples=(1.0 + returns) ** h,
        scenario_ids=[f"s{i}" for i in range(returns.shape[0])],
        horizons=horizons,
        placement_ids=PLACEMENTS,
    )


def _free(net: NetReturns):
    # Versements assez faibles pour qu'aucun plafond d'enveloppe ne morde.
    return placement_constraints(FR_2026, PLACEMENTS, total_contributions=1_000.0, n_periods=1)


R_RETURNS = np.asarray(R_CASE["returns"], dtype=float)


@pytest.mark.parametrize("case", R_CASE["cases"][:2], ids=["aversion 8", "aversion 1"])
def test_same_weights_as_r_without_profile_constraints(case: dict[str, Any]) -> None:
    net = _net_from_annual(R_RETURNS)
    expected = np.asarray(case["output"], dtype=float)
    ours = optimize_by_horizon(
        net, _free(net), risk_aversion=case["aversion"], n_batches=case["nbboots"]
    )
    np.testing.assert_allclose(ours.to_numpy(), expected, atol=2e-4)


def test_r_translation_agrees_on_the_same_case() -> None:
    case = R_CASE["cases"][0]
    ours = r_boot_michaud(R_RETURNS, case["nbboots"], case["aversion"], np.zeros(3))
    np.testing.assert_allclose(ours, case["output"], atol=1e-12)


def test_one_batch_is_plain_markowitz() -> None:
    net = _net_from_annual(R_RETURNS)
    plain = optimize_horizon(net, 1, _free(net), risk_aversion=8.0)
    resampled = optimize_horizon_resampled(net, 1, _free(net), n_batches=1, risk_aversion=8.0)
    np.testing.assert_allclose(resampled.weights, plain.weights, atol=1e-10)


def test_profile_constraints_hold_after_averaging() -> None:
    """Le R ignorait les plafonds : la moyenne des paquets les respecte ici."""
    net = _net_from_annual(R_RETURNS)
    constraints = placement_constraints(
        FR_2026, PLACEMENTS, total_contributions=1_000.0, n_periods=1, max_equity=0.10
    )
    allocation = optimize_horizon_resampled(
        net, 2, constraints, n_batches=4, risk_aversion=1.0
    )
    assert constraints.is_feasible(allocation.weights.to_numpy(), tol=1e-6)
    assert allocation.weights["cto_actions"] <= 0.10 + 1e-6


def test_resampling_diversifies_a_corner_solution() -> None:
    """Aversion faible : Markowitz met tout sur un placement, Michaud répartit."""
    net = _net_from_annual(R_RETURNS)
    plain = optimize_horizon(net, 2, _free(net), risk_aversion=1.0).weights
    resampled = optimize_horizon_resampled(net, 2, _free(net), n_batches=6, risk_aversion=1.0)
    assert plain.max() > 0.999
    assert resampled.weights.max() < plain.max()
    assert (resampled.weights > 1e-3).sum() >= (plain > 1e-3).sum()


@pytest.mark.parametrize("n_batches", [0, 31])
def test_invalid_batch_count_is_refused(n_batches: int) -> None:
    net = _net_from_annual(R_RETURNS)
    with pytest.raises(ValueError, match="paquet"):
        optimize_horizon_resampled(net, 1, _free(net), n_batches=n_batches, risk_aversion=8.0)
