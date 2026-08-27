"""
Courbe des taux — chargement, validation, traçabilité du millésime.

Étape 1.B.2 : la courbe des taux devient une donnée d'entrée versionnée,
sur le même principe que le régime fiscal (voir
docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md et
investment_calculator.tax_regime).
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from investment_calculator.yield_curve import (
    SCHEMA_PATH,
    YieldCurveNotFoundError,
    list_yield_curves,
    load_yield_curve,
)


def test_le_schema_est_un_json_schema_valide():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)


def test_une_courbe_est_livree():
    curves = list_yield_curves()
    assert curves, "Aucune courbe des taux livrée : le moteur n'a aucune donnée de marché."
    assert any(c["id"] == "eiopa-fr-2018-04" for c in curves)


def test_la_courbe_par_defaut_se_charge_et_est_coherente():
    curve = load_yield_curve("eiopa-fr-2018-04")

    assert curve.id == "eiopa-fr-2018-04"
    assert curve.vintage_date == "2018-04-30"
    assert curve.country_code == "FR"

    p0t = curve.get_bond_prices(n_steps=60)
    assert p0t[0] == pytest.approx(1.0, abs=1e-6)
    # Taux courts négatifs en avril 2018 : léger dépassement de 1 toléré,
    # mais borné — voir investment_calculator.yield_curve._check_coherence.
    assert p0t.max() < 1.10
    assert p0t.min() > 0


def test_un_identifiant_inconnu_leve_une_erreur_explicite():
    with pytest.raises(YieldCurveNotFoundError, match="Disponibles"):
        load_yield_curve("inexistante-2099")


def test_le_millesime_est_expose_pour_les_metadonnees():
    """
    Le millésime doit pouvoir être consigné dans les métadonnées de toute
    simulation qui utilise cette courbe — voir
    ScenarioGenerator._generate_stochastic, calibration_info.yield_curve_id.
    """
    curve = load_yield_curve("eiopa-fr-2018-04")
    assert curve.vintage_date is not None
    assert curve.status in ("draft", "validated")


def test_une_courbe_incoherente_est_rejetee():
    """
    _check_coherence doit attraper une courbe dont P(0,t) part largement hors
    des bornes économiquement plausibles — le genre d'erreur (mauvaise
    colonne/ligne) qui rendait EIOPACalibrator.from_excel silencieusement
    inutilisable avant l'étape 1.B.2, faute d'appelant pour la révéler.
    """
    from investment_calculator.stochastic_models import EIOPACalibrator
    from investment_calculator.yield_curve import (
        YieldCurveValidationError,
        _check_coherence,
    )

    # Taux constant négatif sur 60 ans : P(0,60) = 1/(1-0,02)^60 ≈ 3,36,
    # largement au-dessus de la borne de tolérance (1,10).
    maturities = np.arange(1, 61)
    spot_rates = np.full(60, -0.02)
    calibrator = EIOPACalibrator(spot_rates=spot_rates, maturities=maturities, dt=1.0)
    calibrator.calibrate()

    with pytest.raises(YieldCurveValidationError, match="au-dessus de 1"):
        _check_coherence(calibrator, "test-taux-constant-negatif")
