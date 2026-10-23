"""
Découpage de la courbe de capital en tranches : exactitude, cas calculés à la
main, et écarts mesurés avec le R (``tests/reference_r/striping.py``, identique
au vrai R d'après ``tests/test_reference_r.py``).
"""

from __future__ import annotations

import numpy as np
import pytest

from investment_calculator.modules.capital_tranches import (
    Tranche,
    split_into_tranches,
    tranche_balance,
)
from investment_calculator.modules.household_cash_flow import Project, capital_curve
from tests.reference_r.striping import r_stripping

PAS_E = 5_000.0
RISING = capital_curve([], 10, 10_000.0, 6_000.0)  # 10 000 à 70 000
DROP = np.array([20_000.0, 26_000.0, 32_000.0, 8_000.0, 14_000.0, 20_000.0, 26_000.0])


def _as_tuples(tranches: list[Tranche]) -> list[tuple[float, int, int | None]]:
    return [(t.amount, t.start_year, t.withdrawal_year) for t in tranches]


def _r_present_capital(curve: np.ndarray, year: int) -> float:
    """Capital que le R compte comme placé à ``year`` (date R = year + 1)."""
    tr1 = r_stripping(PAS_E, curve)
    date = year + 1
    return PAS_E * float(((tr1[:, 0] <= date) & (date <= tr1[:, 1])).sum())


def test_example_of_the_docstring() -> None:
    tranches = split_into_tranches([10_000.0, 30_000.0, 12_000.0, 20_000.0])
    assert _as_tuples(tranches) == [
        (10_000.0, 0, None),
        (18_000.0, 1, 2),
        (2_000.0, 1, None),
        (8_000.0, 3, None),
    ]
    assert [t.duration for t in tranches] == [3, 1, 2, 0]


def test_project_money_is_placed_until_the_project() -> None:
    car = Project("voiture", 4, 20_000.0, 0.0, 0)
    curve = capital_curve([car], 6, initial_savings=30_000.0, annual_savings=5_000.0)
    np.testing.assert_allclose(curve, [30_000, 35_000, 40_000, 45_000, 30_000, 35_000, 40_000])
    # La chute de 15 000 € à l'année 4 retire les trois couches placées aux années 1 à 3.
    assert _as_tuples(split_into_tranches(curve)) == [
        (30_000.0, 0, None),
        (5_000.0, 1, 4),
        (5_000.0, 2, 4),
        (5_000.0, 3, 4),
        (5_000.0, 5, None),
        (5_000.0, 6, None),
    ]


@pytest.mark.parametrize("seed", range(20))
def test_tranches_rebuild_the_curve(seed: int) -> None:
    rng = np.random.default_rng(seed)
    horizon = int(rng.integers(2, 40))
    steps = rng.normal(4_000.0, 12_000.0, size=horizon)
    curve = np.maximum(np.concatenate([[rng.uniform(0, 50_000)], steps]).cumsum(), 0.0)
    curve[rng.integers(0, horizon + 1, size=3)] = 0.0  # des années à capital nul
    tranches = split_into_tranches(curve)
    np.testing.assert_allclose(tranche_balance(tranches, horizon), curve, atol=1e-6)
    assert all(t.amount > 0 for t in tranches)
    assert all(t.duration >= 0 for t in tranches)
    keys = [(t.start_year, t.withdrawal_year) for t in tranches]
    assert len(keys) == len(set(keys))


def test_flat_curve_is_one_tranche() -> None:
    assert _as_tuples(split_into_tranches([5_000.0] * 4)) == [(5_000.0, 0, None)]
    # Le R échoue : le pas d'interpolation divise par la plus forte hausse, nulle.
    with pytest.raises(ZeroDivisionError):
        r_stripping(PAS_E, np.full(4, 5_000.0))


def test_negative_capital_is_refused() -> None:
    with pytest.raises(ValueError, match="années \\[2\\]"):
        split_into_tranches([1_000.0, 500.0, -200.0])


# --- Écarts mesurés avec le R ----------------------------------------------------


def test_r_loses_the_top_tranches() -> None:
    """Écart 1 : à l'année 9, sur 64 000 € de capital, le R n'en place que 60 000."""
    assert _r_present_capital(RISING, 9) == pytest.approx(60_000.0)
    assert RISING[9] == pytest.approx(64_000.0)
    assert tranche_balance(split_into_tranches(RISING), 10)[9] == pytest.approx(64_000.0)


def test_r_keeps_counting_money_spent_on_a_project() -> None:
    """Écart 2 : après une chute de 32 000 à 8 000 €, le R compte encore 20 000 € placés."""
    assert DROP[3] == pytest.approx(8_000.0)
    assert _r_present_capital(DROP, 3) == pytest.approx(20_000.0)
    assert tranche_balance(split_into_tranches(DROP), 6)[3] == pytest.approx(8_000.0)


def test_r_dates_tranches_after_the_money_arrives() -> None:
    """Écart 3 : le capital atteint 15 000 € à l'année 1, le R place la 3e tranche à 2,25."""
    tr1 = r_stripping(PAS_E, RISING)
    third = tr1[tr1[:, 2] == 3]
    assert third[0, 0] == pytest.approx(2.25)  # date R, soit l'année 1,25
    ours = split_into_tranches(RISING)
    assert ours[1].start_year == 1 and ours[1].amount == pytest.approx(6_000.0)
