"""
Parts fiscales et impôt sur le revenu du foyer : comparaison à la traduction
fidèle du R (``tests/reference_r/imp_ir.py``) sur le barème du régime, et
écarts assumés.
"""

from __future__ import annotations

import numpy as np
import pytest

from investment_calculator.modules.household_tax import (
    HouseholdShares,
    child_tax_advantages,
    household_shares,
    income_tax_by_year,
    marginal_rate,
    real_regime_rental_income,
    shares_by_year,
)
from investment_calculator.tax_regime import load_regime
from tests.reference_r.imp_ir import r_household_ir, r_part_imp

FR = load_regime("FR", 2026)
TAB_IR = [(float(b["lower"]), float(b["rate"])) for b in FR.document["income_tax"]["brackets"]]
HORIZ = 20


def _dependent_years(ages: list[int]) -> list[int]:
    # Le R compte un enfant les années 0 à 20 − âge incluses.
    return [21 - age for age in ages]


def test_shares_follow_the_regime() -> None:
    q = FR.document["income_tax"]["household_quotient"]
    assert household_shares(FR, adults=1, dependents=0) == HouseholdShares(
        q["shares_first_adult"], 0.0
    )
    three = household_shares(FR, adults=2, dependents=3)
    assert three.dependents == sum(q["shares_per_dependent"][:3])
    assert three.total == q["shares_first_adult"] + q["shares_second_adult"] + three.dependents
    # Au-delà de la liste, la dernière part vaut pour les suivants.
    four = household_shares(FR, adults=2, dependents=4)
    assert four.dependents == three.dependents + q["shares_per_dependent"][-1]


def test_shares_and_tax_match_r_without_cap() -> None:
    """Couple, deux enfants de 12 et 16 ans, revenu modeste : le plafonnement ne joue pas."""
    ages = [12, 16]
    shares = shares_by_year(FR, adults=2, dependent_years=_dependent_years(ages), horizon=HORIZ - 1)
    r_parts = r_part_imp(2.0, ages, HORIZ)
    np.testing.assert_allclose([s.total for s in shares], r_parts)
    income = np.linspace(30_000.0, 70_000.0, HORIZ)
    r_tax, r_marg = r_household_ir(income, r_parts, TAB_IR)
    np.testing.assert_allclose(income_tax_by_year(FR, income, shares), r_tax)
    np.testing.assert_allclose(
        [marginal_rate(FR, float(x), s) for x, s in zip(income, shares, strict=True)], r_marg
    )


def test_cap_on_quotient_is_applied() -> None:
    """Écart 2 : le R n'applique pas le plafonnement du quotient familial."""
    shares = household_shares(FR, adults=2, dependents=2)
    income = 200_000.0
    ours = income_tax_by_year(FR, [income], [shares])[0]
    r_tax, r_marg = r_household_ir(np.array([income]), np.array([shares.total]), TAB_IR)
    assert ours > r_tax[0]
    assert ours == pytest.approx(
        FR.income_tax_due(income, shares=shares.total, dependent_shares=shares.dependents)
    )
    # Le plafonnement joue : la tranche marginale est celle du revenu sur les parts de base.
    base = FR.income_tax_due(income + 100.0, shares=2.0) - FR.income_tax_due(income, shares=2.0)
    assert marginal_rate(FR, income, shares) == pytest.approx(base / 100.0)
    assert marginal_rate(FR, income, shares) > r_marg[0]


def test_dependent_rank_is_counted_each_year() -> None:
    """Écart 3 : quand l'aîné part, le cadet passe au rang 2 ; le R lui garde sa part de rang 3."""
    ages = [19, 10, 8]  # l'aîné quitte le foyer après l'année 2
    shares = shares_by_year(FR, adults=2, dependent_years=_dependent_years(ages), horizon=5)
    ranks = FR.document["income_tax"]["household_quotient"]["shares_per_dependent"]
    assert shares[0].dependents == sum(ranks[:3])
    assert shares[3].dependents == sum(ranks[:2])
    r_parts = r_part_imp(2.0, ages, 6)
    assert r_parts[3] - 2.0 == ranks[1] + ranks[2]
    assert shares[3].total < r_parts[3]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [({"adults": 3, "dependents": 0}, "1 ou 2"), ({"adults": 1, "dependents": -1}, "positif")],
)
def test_invalid_household_is_refused(kwargs: dict[str, int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        household_shares(FR, **kwargs)


def test_lengths_are_checked() -> None:
    with pytest.raises(ValueError, match="un revenu imposable par année"):
        income_tax_by_year(FR, [1.0, 2.0], [household_shares(FR, adults=1, dependents=0)])
    with pytest.raises(ValueError, match="positif"):
        shares_by_year(FR, adults=1, dependent_years=[-1], horizon=3)


def test_a_dependent_can_arrive_later() -> None:
    shares = shares_by_year(FR, adults=2, dependent_years=[2], dependent_from=[3], horizon=6)
    assert [s.dependents for s in shares] == [0, 0, 0, 0.5, 0.5, 0, 0]
    with pytest.raises(ValueError, match="une année d'arrivée par personne"):
        shares_by_year(FR, adults=2, dependent_years=[2], dependent_from=[], horizon=3)


def test_real_regime_by_hand() -> None:
    # Année 0 : bénéfice. Année 1 : déficit de 4 000 € hors intérêts, imputé sur le
    # revenu global. Année 2 : 2 000 € d'intérêts non couverts par les loyers
    # (reportés) et 15 000 € de travaux, dont 10 700 € sur le revenu global et
    # 4 300 € reportés : 6 300 € de report. Année 3 : bénéfice de 5 000 €, effacé
    # par le report. Année 4 : le reste du report (1 300 €) est imputé, 3 700 €
    # imposés.
    rents = [10_000.0, 10_000.0, 3_000.0, 10_000.0, 10_000.0]
    charges = [2_000.0, 12_000.0, 15_000.0, 2_000.0, 2_000.0]
    interest = [3_000.0, 2_000.0, 5_000.0, 3_000.0, 3_000.0]
    base, social = real_regime_rental_income(FR, rents, charges, interest)
    np.testing.assert_allclose(base, [5_000.0, -4_000.0, -10_700.0, 0.0, 3_700.0])
    np.testing.assert_allclose(social, [5_000.0, 0.0, 0.0, 0.0, 3_700.0])


def test_a_carried_deficit_expires() -> None:
    keep = int(FR.document["rental_income_regimes"]["real_regime"]["deficit_carry_forward_years"])
    # Déficit dû aux seuls intérêts à l'année 0, puis bénéfice après expiration.
    rents = [0.0] + [0.0] * keep + [1_000.0]
    interest = [500.0] + [0.0] * (keep + 1)
    base, _ = real_regime_rental_income(FR, rents, [0.0] * len(rents), interest)
    assert base[-1] == pytest.approx(1_000.0)
    base, _ = real_regime_rental_income(FR, rents[:-2] + [1_000.0], [0.0] * keep + [0.0],
                                        interest[:-1])
    assert base[-1] == pytest.approx(500.0)


def test_child_tax_advantages_by_age() -> None:
    care = FR.document["income_tax"]["child_tax_advantages"]["childcare_credit"]
    stages = FR.document["income_tax"]["child_tax_advantages"]["schooling_reduction"]["stages"]
    amount = {s["label"]: s["amount"] for s in stages}
    # Un enfant de 4 ans, à charge jusqu'à 20 ans, 5 000 € de garde par an.
    reduction, credit = child_tax_advantages(FR, [4], end_age=20, horizon=16,
                                             childcare_cost=5_000.0)
    capped = min(5_000.0, care["expense_cap_per_child"]) * care["rate"]
    np.testing.assert_allclose(credit, [capped, capped] + [0.0] * 15)
    assert reduction[0] == 0.0 and reduction[6] == 0.0          # 4 et 10 ans
    assert reduction[7] == pytest.approx(amount["collège"])     # 11 ans
    assert reduction[11] == pytest.approx(amount["lycée"])      # 15 ans
    assert reduction[14] == pytest.approx(amount["enseignement supérieur"])  # 18 ans
    assert reduction[16] == 0.0                                 # 20 ans : sorti
    # Un enfant à venir n'ouvre rien avant sa naissance.
    _, credit = child_tax_advantages(FR, [-2], end_age=20, horizon=3, childcare_cost=1_000.0)
    np.testing.assert_allclose(credit, [0.0, 0.0, 500.0, 500.0])
