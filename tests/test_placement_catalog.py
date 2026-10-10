"""
Catalogue des placements (GSE+) : chargement, refus des brouillons et
cohérence avec le régime fiscal. Voir
docs/adr/0002-le-placement-est-l-unite-d-optimisation.md.
"""

from __future__ import annotations

import copy
import json

import pytest

from investment_calculator import placement_catalog as pc
from investment_calculator.placement_catalog import (
    CatalogNotFoundError,
    CatalogValidationError,
    DraftCatalogError,
    load_placement_catalog,
)
from investment_calculator.tax_regime import load_regime

FR_2026 = json.loads((pc.PACKAGE_CATALOG_DIR / "fr-2026.json").read_text(encoding="utf-8"))
FR_2026.pop("$schema")


def _validate(document: dict) -> None:
    pc._validate(document, pc.PACKAGE_CATALOG_DIR / "test.json", load_regime("fr-2026"))


def _draft_dir(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Un répertoire de catalogues qui ne contient qu'un brouillon zz-2026."""
    document = copy.deepcopy(FR_2026)
    document.update(id="zz-2026", status="draft",
                    validation={"validated_by": None, "validated_on": None})
    (tmp_path / "zz-2026.json").write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(pc, "PACKAGE_CATALOG_DIR", tmp_path)


def test_brouillon_refuse_par_defaut(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _draft_dir(tmp_path, monkeypatch)
    with pytest.raises(DraftCatalogError, match="allow_draft=True"):
        load_placement_catalog("zz-2026")


def test_brouillon_charge_sur_demande(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    _draft_dir(tmp_path, monkeypatch)
    assert load_placement_catalog("zz-2026", allow_draft=True).status == "draft"


def test_fr_2026_valide_et_charge_par_defaut() -> None:
    catalog = load_placement_catalog("fr-2026")
    assert catalog.status == "validated"
    assert catalog.document["validation"]["validated_by"]
    assert catalog.regime.id == "fr-2026"
    assert catalog.placement_ids == [
        "cto_actions", "cto_obligations", "pea_actions",
        "av_fonds_euros", "av_uc_actions", "livret_a",
    ]
    assert catalog.placement("pea_actions")["wrapper"] == "pea"


def test_catalogue_inconnu() -> None:
    with pytest.raises(CatalogNotFoundError, match="Disponibles"):
        load_placement_catalog("zz-2026")


def test_placement_inconnu() -> None:
    catalog = load_placement_catalog("fr-2026")
    with pytest.raises(KeyError, match="Placements disponibles"):
        catalog.placement("pinel")


def test_chaque_placement_est_eligible_a_son_enveloppe() -> None:
    regime = load_regime("fr-2026")
    for placement in FR_2026["placements"]:
        eligible = regime.wrapper(placement["wrapper"])["eligible_assets"]
        assert placement["asset_class"] in eligible, placement["id"]


def test_enveloppe_absente_du_regime_refusee() -> None:
    document = copy.deepcopy(FR_2026)
    document["placements"][0]["wrapper"] = "pinel"
    with pytest.raises(CatalogValidationError, match="n'existe pas dans le régime"):
        _validate(document)


def test_classe_non_eligible_refusee() -> None:
    document = copy.deepcopy(FR_2026)
    pea = next(p for p in document["placements"] if p["id"] == "pea_actions")
    pea["asset_class"] = "bond"
    with pytest.raises(CatalogValidationError, match="n'est pas éligible"):
        _validate(document)


def test_identifiant_en_double_refuse() -> None:
    document = copy.deepcopy(FR_2026)
    document["placements"].append(copy.deepcopy(document["placements"][0]))
    with pytest.raises(CatalogValidationError, match="en double"):
        _validate(document)


def test_schema_refuse_une_serie_inconnue() -> None:
    document = copy.deepcopy(FR_2026)
    document["placements"][0]["support"]["series"] = "gold_return"
    with pytest.raises(CatalogValidationError, match="schéma"):
        _validate(document)


def test_valide_avec_valeur_inconnue_refuse() -> None:
    document = copy.deepcopy(FR_2026)
    document["status"] = "validated"
    document["validation"] = {"validated_by": "Une Personne", "validated_on": "2026-10-09"}
    document["placements"][0]["fees"]["entry_rate"] = None
    with pytest.raises(CatalogValidationError, match="valeur inconnue") as excinfo:
        _validate(document)
    assert "placements[0].fees.entry_rate" in str(excinfo.value)


def test_valide_sans_personne_refuse() -> None:
    document = copy.deepcopy(FR_2026)
    document["status"] = "validated"
    document["validation"] = {"validated_by": None, "validated_on": None}
    for placement in document["placements"]:
        placement["fees"] = {"entry_rate": 0.0, "annual_rate": 0.0}
        if placement["support"]["model"] == "euro_fund":
            placement["support"].update(pass_through=1.0, floor_rate=0.0)
    with pytest.raises(CatalogValidationError, match="validated_by"):
        _validate(document)


def test_liste_des_catalogues_sans_brouillon(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert "fr-2026" in pc.list_placement_catalogs()
    _draft_dir(tmp_path, monkeypatch)
    (tmp_path / "valide-2026.json").write_text(json.dumps(FR_2026), encoding="utf-8")
    (tmp_path / "illisible.json").write_text("{", encoding="utf-8")
    assert pc.list_placement_catalogs() == ["valide-2026"]
    assert pc.list_placement_catalogs(include_draft=True) == ["valide-2026", "zz-2026"]
