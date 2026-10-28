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


# --- Surface réelle à cotations éparses (eur-bloomberg-2018) -----------------

REAL_SURFACE_ID = "eur-bloomberg-2018"


def _write_variant(tmp_path, monkeypatch, surface_id, mutate):
    """Écrire une variante modifiée de la surface réelle dans un répertoire de test."""
    document = json.loads(
        (PACKAGE_SURFACE_DIR / f"{REAL_SURFACE_ID}.json").read_text(encoding="utf-8")
    )
    document.pop("$schema", None)
    document["id"] = surface_id
    mutate(document)
    (tmp_path / f"{surface_id}.json").write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr("investment_calculator.swaption_surface.PACKAGE_SURFACE_DIR", tmp_path)


class TestSurfaceBloomberg2018:
    def test_se_charge_sans_opt_in_car_elle_n_est_pas_synthetique(self):
        surface = load_swaption_surface(REAL_SURFACE_ID)
        assert surface.synthetic is False
        assert surface.status == "draft"
        assert surface.vol_grid is None

    def test_les_neuf_cotations_du_csv_r_sont_reprises(self):
        """legacy/csv_files/Swaptions_V2.csv donne la vol en % : 0,6789 = 67,89 bp."""
        surface = load_swaption_surface(REAL_SURFACE_ID)
        assert len(surface.quotes) == 9
        assert surface.get_vol("9Y", "2Y") == pytest.approx(67.89)
        assert surface.get_vol("3Y", "7Y") == pytest.approx(56.96)
        assert surface.get_vol("15Y", "10Y") == pytest.approx(62.13)

    def test_echeances_et_tenors_distincts_et_croissants(self):
        surface = load_swaption_surface(REAL_SURFACE_ID)
        assert surface.expiries == ["3Y", "9Y", "10Y", "12Y", "15Y"]
        assert surface.tenors == ["2Y", "5Y", "7Y", "10Y"]

    def test_la_date_inconnue_est_une_lacune_declaree(self):
        surface = load_swaption_surface(REAL_SURFACE_ID)
        assert surface.observation_date is None
        assert any("Date d'observation inconnue" in gap for gap in surface.document["known_gaps"])

    def test_une_cotation_absente_leve_key_error(self):
        surface = load_swaption_surface(REAL_SURFACE_ID)
        with pytest.raises(KeyError, match="Aucune cotation"):
            surface.get_vol("1Y", "1Y")


class TestStatutValidated:
    def test_validated_sans_date_est_refuse(self, tmp_path, monkeypatch):
        def mutate(doc):
            doc["status"] = "validated"
            doc["validation"] = {"validated_by": "test", "validated_on": "2026-10-25"}

        _write_variant(tmp_path, monkeypatch, "sans-date", mutate)
        with pytest.raises(SwaptionSurfaceValidationError, match="observation_date"):
            load_swaption_surface("sans-date")

    def test_validated_sans_relecteur_est_refuse(self, tmp_path, monkeypatch):
        def mutate(doc):
            doc["status"] = "validated"
            doc["observation_date"] = "2018-08-01"

        _write_variant(tmp_path, monkeypatch, "sans-relecteur", mutate)
        with pytest.raises(SwaptionSurfaceValidationError, match="validated_by"):
            load_swaption_surface("sans-relecteur")

    def test_validated_synthetique_est_refuse(self, tmp_path, monkeypatch):
        def mutate(doc):
            doc["status"] = "validated"
            doc["synthetic"] = True

        _write_variant(tmp_path, monkeypatch, "synthetique-validee", mutate)
        with pytest.raises(SwaptionSurfaceValidationError, match="synthétique"):
            load_swaption_surface("synthetique-validee", allow_synthetic=True)

    def test_validated_complete_est_acceptee(self, tmp_path, monkeypatch):
        def mutate(doc):
            doc["status"] = "validated"
            doc["observation_date"] = "2018-08-01"
            doc["validation"] = {"validated_by": "test", "validated_on": "2026-10-25"}

        _write_variant(tmp_path, monkeypatch, "complete", mutate)
        assert load_swaption_surface("complete").status == "validated"


class TestFormeDuDocument:
    def test_grille_et_cotations_a_la_fois_est_refuse(self, tmp_path, monkeypatch):
        def mutate(doc):
            doc["grid"] = {"expiries": ["1Y"], "tenors": ["1Y"], "vol_normal_bp": [[50.0]]}

        _write_variant(tmp_path, monkeypatch, "les-deux", mutate)
        with pytest.raises(SwaptionSurfaceValidationError, match="schéma"):
            load_swaption_surface("les-deux")

    def test_une_cotation_en_double_est_refusee(self, tmp_path, monkeypatch):
        def mutate(doc):
            doc["quotes"].append(dict(doc["quotes"][0]))

        _write_variant(tmp_path, monkeypatch, "doublon", mutate)
        with pytest.raises(SwaptionSurfaceValidationError, match="deux fois"):
            load_swaption_surface("doublon")
