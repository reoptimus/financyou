"""
Crédits en cours et taux d'endettement : comparaison à la traduction fidèle du
R (``tests/reference_r/crd_flux.py``), identique au vrai R d'après
``tests/test_reference_r.py``, et écarts assumés.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from investment_calculator.modules.household_loans import (
    Loan,
    borrowing_capacity,
    debt_ratio,
    loan_schedule,
    loans_total,
)
from tests.reference_r.crd_flux import r_debt_ratio, r_flux_crd

R_CASES: list[dict[str, Any]] = json.loads(
    (Path(__file__).parent / "reference_r" / "r_outputs.json").read_text(encoding="utf-8")
)["crd_flux"]


@pytest.mark.parametrize("case", [c for c in R_CASES if c["taux"] > 0], ids=str)
def test_same_flows_as_r_up_to_rounding(case: dict[str, Any]) -> None:
    loan = Loan("immo", case["annuite"], case["taux"], case["an_rest"])
    # Le R couvre horiz années (0 à horiz − 1).
    schedule = loan_schedule(loan, case["horiz"] - 1)
    np.testing.assert_allclose(schedule["interest"], case["interest"], atol=0.5)
    np.testing.assert_allclose(schedule["principal"], case["principal"], atol=1.0)


def test_payments_sum_to_the_annuity() -> None:
    """Écart 1 : sans arrondi, le capital remboursé éteint exactement le crédit."""
    loan = Loan("immo", 12_000.0, 0.015, 15)
    schedule = loan_schedule(loan, 19)
    paid = schedule["interest"] + schedule["principal"]
    np.testing.assert_allclose(paid[:15], 12_000.0)
    assert (paid[15:] == 0).all()
    # Le capital remboursé éteint exactement le capital restant dû de départ.
    assert schedule["principal"].sum() == pytest.approx(schedule["outstanding"].iloc[0])
    # Le R, qui arrondit à l'euro, rembourse quelques euros de trop ou de moins.
    odd = Loan("immo", 7_777.77, 0.0215, 20)
    r_principal, r_interest = r_flux_crd(21, odd.annual_payment, odd.rate, odd.years_left)
    exact = loan_schedule(odd, 20)
    assert exact["principal"].sum() == pytest.approx(exact["outstanding"].iloc[0])
    assert abs(r_principal.sum() - exact["outstanding"].iloc[0]) > 1.0
    assert (r_principal + r_interest)[0] != pytest.approx(odd.annual_payment)


def test_zero_rate_loan_is_repaid() -> None:
    """Écart 2 : le R fait disparaître un prêt à taux zéro."""
    case = next(c for c in R_CASES if c["taux"] == 0)
    assert case["principal"] == [0] * case["horiz"]
    schedule = loan_schedule(Loan("ptz", case["annuite"], 0.0, case["an_rest"]), case["horiz"] - 1)
    assert schedule["principal"].tolist()[:6] == [6_000.0] * 5 + [0.0]
    assert schedule["interest"].sum() == 0.0
    assert schedule["outstanding"].iloc[0] == 30_000.0


def test_debt_ratio_matches_r_with_the_same_thresholds() -> None:
    """Écart 3 : mêmes formules, seuils passés en paramètres."""
    loan = Loan("immo", 12_000.0, 0.015, 15)
    schedule = loan_schedule(loan, 19)
    income = np.linspace(50_000.0, 60_000.0, 20)
    rents = np.full(20, 6_000.0)
    rent_paid = np.zeros(20)
    payments = (schedule["interest"] + schedule["principal"]).to_numpy()
    ours = debt_ratio(income, rental_income=rents, rental_income_weight=0.7,
                      rent_paid=rent_paid, loan_payments=payments)
    capacity = borrowing_capacity(income, rental_income=rents, rental_income_weight=0.7,
                                  rent_paid=rent_paid, loan_payments=payments, max_ratio=0.35)
    r_ratio, r_extra = r_debt_ratio(
        income, rents, -rent_paid, -schedule["principal"].to_numpy(),
        -schedule["interest"].to_numpy(), 0.35, 0.7,
    )
    np.testing.assert_allclose(ours, r_ratio)
    np.testing.assert_allclose(capacity, r_extra)


def test_loans_add_up() -> None:
    loans = [Loan("immo", 12_000.0, 0.015, 15), Loan("auto", 3_000.0, 0.04, 3)]
    total = loans_total(loans, 10)
    expected = loan_schedule(loans[0], 10) + loan_schedule(loans[1], 10)
    np.testing.assert_allclose(total.to_numpy(), expected.to_numpy())
    assert (loans_total([], 3).to_numpy() == 0).all()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"years_left": -1}, "années restantes"), ({"years_left": 2.5}, "entier"),
     ({"rate": -0.01}, "taux"), ({"annual_payment": float("nan")}, "annuité")],
)
def test_invalid_loan_is_refused(kwargs: dict[str, object], message: str) -> None:
    fields: dict[str, object] = {"name": "c", "annual_payment": 1.0, "rate": 0.01, "years_left": 1}
    fields.update(kwargs)
    with pytest.raises(ValueError, match=message):
        Loan(**fields)  # type: ignore[arg-type]


def test_debt_ratio_inputs_are_checked() -> None:
    common = {"rental_income": [0.0], "rent_paid": [0.0], "loan_payments": [1.0]}
    with pytest.raises(ValueError, match="entre 0 et 1"):
        debt_ratio([1.0], rental_income_weight=1.5, **common)
    with pytest.raises(ValueError, match="années \\[0\\]"):
        debt_ratio([0.0], rental_income_weight=0.5, **common)
    with pytest.raises(ValueError, match="mêmes années"):
        debt_ratio([1.0, 2.0], rental_income_weight=0.5, **common)
