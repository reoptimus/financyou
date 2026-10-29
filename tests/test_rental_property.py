"""
Bien loué nu acheté à crédit : comparaison à la traduction fidèle du R
(``tests/reference_r/rental.py``, vérifiée contre le R), calcul à la main et
saisies refusées.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pytest

from investment_calculator.modules.rental_property import (
    RentalProperty,
    loan_annuity,
    property_flows,
    property_values,
)
from tests.reference_r.rental import r_chrono_location, r_emprunt, r_recalcul_revenu

R_CASE = json.loads(
    (Path(__file__).parent / "reference_r" / "r_outputs.json").read_text(encoding="utf-8")
)["rental"]["chrono"]


def _flat(**changes: object) -> RentalProperty:
    base = RentalProperty(
        name="studio", price=150_000.0, down_payment=20_000.0, loan_rate=0.035, loan_years=15,
        gross_yield=0.04, collected_share=0.85, annual_charges=0.0, rent_growth=0.0,
        purchase_year=3, market_value=140_000.0,
    )
    return dataclasses.replace(base, **changes)  # type: ignore[arg-type]


def test_same_rent_and_loan_as_r() -> None:
    """Rendement 4 %, part retenue 85 % : les constantes du R, saisies ici."""
    price = R_CASE["montant"]
    borrowed = r_emprunt(R_CASE["annuite"], R_CASE["tau"], R_CASE["n"])
    prop = _flat(price=price, down_payment=price - borrowed, loan_rate=R_CASE["tau"],
                 loan_years=R_CASE["n"], purchase_year=R_CASE["debut_optim"] - 1)
    flows = property_flows(prop, 19)
    revenu = r_recalcul_revenu("RimmoLoc", price, np.zeros(1))
    r = r_chrono_location(20, R_CASE["debut_optim"], revenu, R_CASE["annuite"], R_CASE["tau"],
                          R_CASE["n"])
    assert loan_annuity(borrowed, R_CASE["tau"], R_CASE["n"]) == pytest.approx(R_CASE["annuite"])
    np.testing.assert_allclose(flows["collected_rent"], r["revenu"])
    # Le R arrondit intérêts et capital à l'euro (écart déjà décrit au 7a).
    np.testing.assert_allclose(flows["interest"], -r["interet"], atol=0.5)
    np.testing.assert_allclose(flows["principal"], -r["principal"], atol=0.5)
    paid = flows["interest"] + flows["principal"]
    np.testing.assert_allclose(paid, -(r["interet"] + r["principal"]), atol=1e-6)


def test_flows_by_hand() -> None:
    prop = _flat(annual_charges=1_000.0, rent_growth=0.02, purchase_year=1, loan_years=2,
                 loan_rate=0.0)
    flows = property_flows(prop, 4)
    np.testing.assert_allclose(flows["down_payment"], [0, 20_000, 0, 0, 0])
    rent = 150_000 * 0.04 * 0.85
    np.testing.assert_allclose(flows["collected_rent"],
                               [0, rent, rent * 1.02, rent * 1.02**2, rent * 1.02**3])
    np.testing.assert_allclose(flows["charges"], [0, 1_000, 1_020, 1_040.4, 1_061.208])
    np.testing.assert_allclose(flows["principal"], [0, 65_000, 65_000, 0, 0])
    np.testing.assert_allclose(flows["outstanding"], [0, 130_000, 65_000, 0, 0])


def test_cash_purchase_has_no_loan() -> None:
    flows = property_flows(_flat(down_payment=150_000.0, loan_years=0), 10)
    assert flows[["interest", "principal", "outstanding"]].to_numpy().sum() == 0
    assert flows["down_payment"].sum() == 150_000


def test_values_follow_the_gse_price_index() -> None:
    """Rendement total du GSE moins le rendement locatif du modèle, dès l'achat."""
    returns = np.array([[0.05, 0.06, 0.02, 0.04], [0.01, -0.03, 0.03, 0.05]])
    values = property_values(_flat(purchase_year=1), returns, rental_yield=0.03)
    np.testing.assert_allclose(values[0], [0, 140_000, 140_000 * 1.03, 140_000 * 1.03 * 0.99,
                                           140_000 * 1.03 * 0.99 * 1.01])
    np.testing.assert_allclose(values[1], [0, 140_000, 140_000 * 0.94, 140_000 * 0.94,
                                           140_000 * 0.94 * 1.02])
    assert not property_values(_flat(purchase_year=5), returns, 0.03).any()
    with pytest.raises(ValueError, match="scénarios, années"):
        property_values(_flat(), returns[0], 0.03)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"down_payment": 200_000.0}, "dépasser le prix"),
        ({"loan_years": 0}, "sans durée"),
        ({"collected_share": 1.2}, "entre 0 et 1"),
        ({"gross_yield": -0.01}, "rendement"),
        ({"purchase_year": -1}, "année à venir"),
        ({"price": 0.0}, "prix nul"),
        ({"market_value": -1.0}, "valeur du bien"),
    ],
)
def test_invalid_property_is_refused(changes: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _flat(**changes)
