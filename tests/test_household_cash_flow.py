"""
Projets du foyer et courbe de capital : comparaison à la traduction fidèle du R
(``tests/reference_r/exp_finance.py``), calcul à la main, et écarts assumés.
"""

from __future__ import annotations

import logging

import numpy as np
import pytest

from investment_calculator.modules.household_cash_flow import (
    Project,
    capital_curve,
    project_flows,
)
from tests.reference_r.exp_finance import r_cumulative_capital, r_exp_proj_hist

HORIZON = 20

# Projets entièrement compris dans l'horizon : le portage et le R doivent coïncider.
INSIDE = [
    Project("voiture", 3, 5_000.0, 2_000.0, 4, -3_000.0),
    Project("études", 0, 1_000.0, 6_000.0, 5, 0.0),
    Project("travaux", 7, 15_000.0, 0.0, 0, 0.0),
    Project("résidence secondaire", 2, 40_000.0, 9_000.0, 15, -120_000.0),
    Project("dernière année", 19, 1_000.0, 500.0, 1, -200.0),
    Project("à l'horizon", 20, 2_500.0, 0.0, 0, 0.0),
]


def _r_flows(p: Project) -> np.ndarray:
    return r_exp_proj_hist(
        HORIZON, p.start_year, p.initial_payment, p.annual_payment, p.duration_years,
        p.exit_amount,
    )


@pytest.mark.parametrize("project", INSIDE, ids=lambda p: p.name)
def test_project_flows_match_r(project: Project) -> None:
    np.testing.assert_allclose(project_flows(project, HORIZON), _r_flows(project))


def test_capital_curve_matches_r() -> None:
    rows = np.vstack([_r_flows(p) for p in INSIDE])
    expected = r_cumulative_capital(rows, HORIZON, sal_net=18_000.0, epar=25_000.0)
    np.testing.assert_allclose(capital_curve(INSIDE, HORIZON, 25_000.0, 18_000.0), expected)


def test_capital_curve_by_hand() -> None:
    car = Project("voiture", 2, 5_000.0, 2_000.0, 2, -3_000.0)
    # Flux : année 2 → 5 000 ; année 3 → 2 000 ; année 4 → 2 000 − 3 000.
    curve = capital_curve([car], 5, initial_savings=10_000.0, annual_savings=6_000.0)
    np.testing.assert_allclose(curve, [10_000, 16_000, 17_000, 21_000, 28_000, 34_000])


def test_capital_curve_without_projects_is_savings() -> None:
    curve = capital_curve([], 3, initial_savings=1_000.0, annual_savings=[100.0, 200.0, 300.0])
    np.testing.assert_allclose(curve, [1_000, 1_100, 1_300, 1_600])


# --- Écarts assumés avec le R --------------------------------------------------


def test_exit_after_horizon_is_not_capital() -> None:
    """Écart 1 : le R compte à l'horizon une revente qui a lieu après."""
    house = Project("maison", 15, 50_000.0, 10_000.0, 10, -300_000.0)
    ours = project_flows(house, HORIZON)
    theirs = _r_flows(house)
    assert ours[HORIZON] == pytest.approx(10_000.0)
    assert theirs[HORIZON] == pytest.approx(10_000.0 - 300_000.0)
    np.testing.assert_allclose(ours[:HORIZON], theirs[:HORIZON])


def test_started_project_counts_only_future_flows() -> None:
    """Écart 2 : le R recompte le versement initial et garde la durée entière."""
    loan = Project("crédit auto", -2, 8_000.0, 3_000.0, 5, 0.0)
    ours = project_flows(loan, HORIZON)
    theirs = _r_flows(loan)
    # Versements restants aux années 0, 1, 2 et 3 (années −1 et passées exclues).
    np.testing.assert_allclose(ours[:5], [3_000, 3_000, 3_000, 3_000, 0])
    assert ours.sum() == pytest.approx(12_000.0)
    np.testing.assert_allclose(theirs[:7], [8_000, 3_000, 3_000, 3_000, 3_000, 3_000, 0])


def test_exit_without_duration_is_refused() -> None:
    """Écart 3 : le R ignore la sortie ; ici elle est refusée."""
    assert r_exp_proj_hist(HORIZON, 4, 1_000.0, 0.0, 0, -500.0).sum() == pytest.approx(1_000.0)
    with pytest.raises(ValueError, match="sortie sans durée"):
        Project("revente seule", 4, 1_000.0, 0.0, 0, -500.0)


# --- Saisies invalides et signalements -----------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"duration_years": -1}, "durée"),
        ({"duration_years": 2.5}, "entiers"),
        ({"start_year": 1.5}, "entiers"),
        ({"annual_payment": float("nan")}, "montant"),
    ],
)
def test_invalid_project_is_refused(kwargs: dict[str, object], message: str) -> None:
    fields: dict[str, object] = {
        "name": "p", "start_year": 1, "initial_payment": 0.0, "annual_payment": 0.0,
        "duration_years": 1,
    }
    fields.update(kwargs)
    with pytest.raises(ValueError, match=message):
        Project(**fields)  # type: ignore[arg-type]


def test_annual_savings_length_is_checked() -> None:
    with pytest.raises(ValueError, match="exactement 3 montants"):
        capital_curve([], 3, 0.0, [1.0, 2.0])


def test_unfunded_projects_are_reported(caplog: pytest.LogCaptureFixture) -> None:
    trip = Project("tour du monde", 1, 30_000.0, 0.0, 0)
    with caplog.at_level(logging.WARNING):
        curve = capital_curve([trip], 3, initial_savings=5_000.0, annual_savings=10_000.0)
    np.testing.assert_allclose(curve, [5_000, -15_000, -5_000, 5_000])
    assert "années [1, 2]" in caplog.text
