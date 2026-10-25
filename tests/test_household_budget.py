"""
Budget du foyer : comparaison à la traduction fidèle du R
(``tests/reference_r/chrono_flux.py``), calcul à la main, et limites.
"""

from __future__ import annotations

import logging

import numpy as np
import pytest

from investment_calculator.modules.household_budget import (
    Earner,
    earner_income,
    household_budget,
)
from investment_calculator.modules.household_loans import Loan
from investment_calculator.tax_regime import load_regime
from tests.reference_r.chrono_flux import r_expenses, r_free_savings, r_salary
from tests.reference_r.imp_ir import r_household_ir

FR = load_regime("FR", 2026)
TAB_IR = [(float(b["lower"]), float(b["rate"])) for b in FR.document["income_tax"]["brackets"]]
HORIZON = 19  # le R couvre 20 années


def _couple() -> list[Earner]:
    return [Earner(42_000.0, 0.015, 12, 0.55), Earner(30_000.0, 0.01, 15, 0.6)]


@pytest.mark.parametrize("follow", [False, True])
def test_same_budget_as_r_for_a_couple_without_children(follow: bool) -> None:
    loan = Loan("résidence", 11_000.0, 0.02, 14)
    ours = household_budget(FR, _couple(), horizon=HORIZON, current_savings=9_000.0, rent=0.0,
                            loans=[loan], expenses_follow_income=follow)
    sal = r_salary(42_000.0, 0.015, 20, 12, 0.55) + r_salary(30_000.0, 0.01, 20, 15, 0.6)
    tax, _ = r_household_ir(sal, np.full(20, 2.0), TAB_IR)
    annuites = (ours["loan_payments"]).to_numpy()  # crédit vérifié en 7a
    expenses = r_expenses(sal, tax, 0.0, annuites, 9_000.0, np.full(20, 1.5), 0 if follow else 1)
    np.testing.assert_allclose(ours["salaries"] + ours["pensions"], sal)
    np.testing.assert_allclose(ours["income_tax"], tax)
    np.testing.assert_allclose(ours["expenses"], expenses)
    np.testing.assert_allclose(
        ours["free_savings"], r_free_savings(sal, tax, 0.0, annuites, expenses)
    )
    # L'épargne de l'année 0 est celle déclarée.
    assert ours["free_savings"].iloc[0] == pytest.approx(9_000.0)


def test_retirement_by_hand() -> None:
    salary, pension = earner_income(Earner(40_000.0, 0.02, 2, 0.5), 3)
    np.testing.assert_allclose(salary, [40_000.0, 40_800.0, 0.0, 0.0])
    np.testing.assert_allclose(pension, [0.0, 0.0, 20_808.0, 20_808.0])


def test_renter_single_by_hand() -> None:
    single = Earner(30_000.0, 0.0)
    budget = household_budget(FR, [single], horizon=2, current_savings=2_000.0, rent=9_000.0,
                              expenses_follow_income=False)
    tax = FR.income_tax_due(30_000.0)
    np.testing.assert_allclose(budget["expenses"], 30_000.0 - tax - 9_000.0 - 2_000.0)
    np.testing.assert_allclose(budget["free_savings"], 2_000.0)


def test_children_lower_the_tax_and_raise_savings() -> None:
    with_children = household_budget(FR, _couple(), horizon=5, current_savings=5_000.0,
                                     rent=0.0, dependent_years=[3, 6],
                                     expenses_follow_income=False)
    tax_year_4 = FR.income_tax_due(
        with_children["salaries"].iloc[4], shares=2.5, dependent_shares=0.5
    )
    assert with_children["income_tax"].iloc[4] == pytest.approx(tax_year_4)
    # Quand un enfant part, l'impôt monte et l'épargne libre baisse (dépenses
    # inchangées, voir KNOWN_GAPS).
    assert with_children["free_savings"].iloc[3] < with_children["free_savings"].iloc[2]


def test_savings_above_income_is_refused() -> None:
    with pytest.raises(ValueError, match="dépenses seraient négatives"):
        household_budget(FR, [Earner(20_000.0, 0.0)], horizon=3, current_savings=25_000.0,
                         rent=0.0, expenses_follow_income=False)


def test_negative_free_savings_is_reported(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        budget = household_budget(FR, [Earner(40_000.0, 0.0, 1, 0.3)], horizon=3,
                                  current_savings=1_000.0, rent=0.0,
                                  expenses_follow_income=False)
    assert budget["free_savings"].iloc[1] < 0
    assert "Épargne libre négative" in caplog.text


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"taxable_income": -1.0}, "Revenu imposable"), ({"annual_growth": -1.0}, "Évolution"),
     ({"retirement_year": 5}, "taux de remplacement"), ({"retirement_year": -1,
                                                       "replacement_rate": 0.5}, "à venir")],
)
def test_invalid_earner_is_refused(kwargs: dict[str, object], message: str) -> None:
    fields: dict[str, object] = {"taxable_income": 1.0, "annual_growth": 0.0}
    fields.update(kwargs)
    with pytest.raises(ValueError, match=message):
        Earner(**fields)  # type: ignore[arg-type]


def test_household_size_is_checked() -> None:
    with pytest.raises(ValueError, match="1 ou 2"):
        household_budget(FR, [], horizon=3, current_savings=0.0, rent=0.0,
                         expenses_follow_income=False)
