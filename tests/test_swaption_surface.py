"""
Surface de volatilité swaptions — chargement, validation, garde-fou
synthétique (étape 1.B.5, version de développement).
"""

from __future__ import annotations

import json

import pytest

from investment_calculator.swaption_surface import (
    PACKAGE_SURFACE_DIR,
    SCHEMA_PATH,
    SwaptionSurfaceNotFoundError,
    SwaptionSurfaceSyntheticNotAllowedError,
    SwaptionSurfaceValidationError,
    label_to_years,
    list_swaption_surfaces,
    load_swaption_surface,
)

SURFACE_ID = "eur-synthetic-2026-08"


def test_le_schema_est_un_json_schema_valide():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)


class TestLabelToYears:
    def test_mois(self):
        assert label_to_years("1M") == pytest.approx(1 / 12)
        assert label_to_years("3M") == pytest.approx(0.25)
        assert label_to_years("6M") == pytest.approx(0.5)

    def test_annees(self):
        assert label_to_years("1Y") == pytest.approx(1.0)
        assert label_to_years("30Y") == pytest.approx(30.0)

    def test_libelle_invalide_leve_une_erreur_explicite(self):
        with pytest.raises(ValueError, match="non reconnu"):
            label_to_years("10ans")


def test_la_surface_synthetique_est_listee():
    surfaces = list_swaption_surfaces()
    ids = [s["id"] for s in surfaces]
    assert SURFACE_ID in ids
    entry = next(s for s in surfaces if s["id"] == SURFACE_ID)
    assert entry["synthetic"] is True


def test_charger_une_surface_synthetique_sans_opt_in_est_refuse():
    with pytest.raises(SwaptionSurfaceSyntheticNotAllowedError, match="synthétique"):
        load_swaption_surface(SURFACE_ID)


def test_charger_une_surface_synthetique_avec_opt_in_fonctionne():
    surface = load_swaption_surface(SURFACE_ID, allow_synthetic=True)
    assert surface.synthetic is True
    assert surface.currency == "EUR"
    assert surface.vol_convention == "normal"
    assert surface.observation_date == "2026-08-28"


def test_un_identifiant_inconnu_leve_une_erreur_explicite():
    with pytest.raises(SwaptionSurfaceNotFoundError) as excinfo:
        load_swaption_surface("inexistante-2099", allow_synthetic=True)
    assert "Disponibles" in str(excinfo.value)


def test_la_grille_a_la_forme_attendue():
    surface = load_swaption_surface(SURFACE_ID, allow_synthetic=True)
    assert surface.vol_grid.shape == (len(surface.expiries), len(surface.tenors))
    assert (surface.vol_grid > 0).all()


def test_get_vol_renvoie_la_valeur_exacte_de_la_grille():
    surface = load_swaption_surface(SURFACE_ID, allow_synthetic=True)
    assert surface.get_vol("1M", "1Y") == pytest.approx(40.6)
    assert surface.get_vol("10Y", "10Y") == pytest.approx(68.0)


def test_get_vol_echeance_inconnue_leve_key_error():
    surface = load_swaption_surface(SURFACE_ID, allow_synthetic=True)
    with pytest.raises(KeyError):
        surface.get_vol("42Y", "1Y")


def test_reference_curve_et_verification_sont_exposees():
    surface = load_swaption_surface(SURFACE_ID, allow_synthetic=True)
    assert set(surface.reference_curve) == {"beta0", "beta1", "beta2", "tau"}
    assert surface.verification is not None
    assert len(surface.verification["fits"]) == 2


def test_une_grille_non_rectangulaire_est_rejetee(tmp_path, monkeypatch):
    """Contrôle de cohérence qu'un schéma JSON seul ne peut pas exprimer."""
    document = json.loads((PACKAGE_SURFACE_DIR / f"{SURFACE_ID}.json").read_text(encoding="utf-8"))
    document.pop("$schema", None)
    document["id"] = "cassee-test"
    document["grid"]["vol_normal_bp"][0] = document["grid"]["vol_normal_bp"][0][:-1]

    broken_path = tmp_path / "cassee-test.json"
    broken_path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        "investment_calculator.swaption_surface.PACKAGE_SURFACE_DIR", tmp_path
    )

    with pytest.raises(SwaptionSurfaceValidationError, match="non rectangulaire"):
        load_swaption_surface("cassee-test", allow_synthetic=True)
