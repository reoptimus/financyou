"""
Loyers d'un bien loué nu dans le budget du foyer : micro-foncier lu dans le
régime, prélèvements sociaux, et écart au R (loyer brut au barème).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from investment_calculator.modules.household_budget import Earner, household_budget
from investment_calculator.modules.household_tax import (
    rental_social_tax,
    rental_taxable_income,
)
from investment_calculator.modules.rental_property import RentalProperty, property_flows
from investment_calculator.tax_regime import load_regime
from tests.reference_r.rental import r_emprunt

FR = load_regime("FR", 2026)
MICRO = FR.document["rental_income_regimes"]["micro_foncier"]
R_CASE = json.loads(
    (Path(__file__).parent / "reference_r" / "r_outputs.json").read_text(encoding="utf-8")
)["rental"]["chrono"]


def _r_property() -> RentalProperty:
    """Le bien du cas R : rendement 4 %, part retenue 85 %, sans charges."""
    price = R_CASE["montant"]
    return RentalProperty(
        name="R", price=price,
        down_payment=price - r_emprunt(R_CASE["annuite"], R_CASE["tau"], R_CASE["n"]),
        loan_rate=R_CASE["tau"], loan_years=R_CASE["n"], gross_yield=0.04,
        collected_share=0.85, annual_charges=0.0, rent_growth=0.0,
        purchase_year=R_CASE["debut_optim"] - 1, market_value=price,
    )


def test_micro_foncier_from_the_regime() -> None:
    rents = [[0.0, 6_000.0], [0.0, 3_000.0]]
    taxable = rental_taxable_income(FR, rents)
    np.testing.assert_allclose(taxable, [0, 9_000 * (1 - MICRO["allowance_rate"])])
    np.testing.assert_allclose(rental_social_tax(FR, taxable.tolist()), taxable * FR.social_rate)


def test_rents_above_the_micro_foncier_threshold_are_refused() -> None:
    """Au-dessus du seuil, le micro-foncier est refusé : le message renvoie au réel."""
    half = MICRO["revenue_threshold"] / 2 + 1
    with pytest.raises(NotImplementedError, match="Choisissez le régime réel"):
        rental_taxable_income(FR, [[half], [half]])  # seuil apprécié pour le foyer


def test_budget_taxes_rent_after_allowance_unlike_r() -> None:
    """Le R impose le loyer brut au barème, sans abattement ni prélèvements sociaux."""
    out = R_CASE["output"]
    prop = _r_property()
    earners = [Earner(R_CASE["salaire"], 0.0), Earner(0.0, 0.0)]
    kwargs = dict(horizon=19, current_savings=5_000.0, rent=0.0, expenses_follow_income=False)
    without = household_budget(FR, earners, **kwargs)  # type: ignore[arg-type]
    ours = household_budget(FR, earners, properties=[prop], **kwargs)  # type: ignore[arg-type]
    rent = R_CASE["revenu"]
    r_extra = np.subtract(out["ir"], out["ir"][0])  # IR du R : négatif
    # Le R : 30 % (tranche marginale) du loyer brut.
    assert -r_extra[5] == pytest.approx(0.30 * rent)
    taxable = rent * (1 - MICRO["allowance_rate"])
    extra = ours["income_tax"] - without["income_tax"]
    assert extra[5] == pytest.approx(0.30 * taxable)
    assert ours["rental_social_tax"][5] == pytest.approx(FR.social_rate * taxable)
    # Les dépenses restent celles de la situation déclarée.
    np.testing.assert_allclose(ours["expenses"], without["expenses"])
    flows = property_flows(prop, 19)
    np.testing.assert_allclose(
        ours["free_savings"] - without["free_savings"],
        flows["collected_rent"] - flows["charges"] - flows["interest"] - flows["principal"]
        - flows["down_payment"] - extra - ours["rental_social_tax"],
    )
    assert ours["free_savings"][2] == pytest.approx(without["free_savings"][2])


def test_budget_without_property_is_unchanged() -> None:
    earners = [Earner(45_000.0, 0.01)]
    out = household_budget(FR, earners, horizon=10, current_savings=4_000.0, rent=9_000.0,
                           expenses_follow_income=True)
    for column in ("rental_income", "property_charges", "rental_social_tax", "down_payments"):
        assert not out[column].any()


def test_real_regime_in_the_budget() -> None:
    """Au réel, charges et intérêts se déduisent ; le déficit baisse l'impôt."""
    prop = RentalProperty(
        name="studio", price=160_000.0, down_payment=10_000.0, loan_rate=0.04,
        loan_years=20, gross_yield=0.04, collected_share=0.9, annual_charges=3_000.0,
        rent_growth=0.0, purchase_year=0, market_value=150_000.0,
    )
    earners = [Earner(50_000.0, 0.0)]
    kwargs = dict(horizon=3, current_savings=3_000.0, rent=0.0, expenses_follow_income=False,
                  properties=[prop])
    micro = household_budget(FR, earners, **kwargs)
    real = household_budget(FR, earners, rental_regime="real_regime", **kwargs)
    flows = property_flows(prop, 3)
    net = flows["collected_rent"] - flows["charges"] - flows["interest"]
    assert (net < 0).all()  # 5 760 € de loyers, 3 000 € de charges, ~6 000 € d'intérêts
    # La part du déficit due aux intérêts non couverts par les loyers est
    # reportée ; le reste (sous le plafond) s'impute sur le revenu global. Pas
    # de prélèvements sociaux sur un déficit.
    uncovered = (flows["interest"] - flows["collected_rent"]).clip(lower=0)
    to_global = -net - uncovered
    assert (real["rental_social_tax"] == 0).all()
    expected = [FR.income_tax_due(50_000.0 - d) for d in to_global]
    np.testing.assert_allclose(real["income_tax"], expected)
    assert (real["income_tax"] < micro["income_tax"]).all()
    with pytest.raises(ValueError, match="micro_foncier ou real_regime"):
        household_budget(FR, earners, rental_regime="lmnp", **kwargs)
