"""
Catalogue des placements (GSE+) — chargement et validation.

Un placement associe un support, construit à partir des scénarios du GSE, à une
enveloppe du régime fiscal, avec ses frais. C'est l'unité de l'optimisation :
voir ``docs/adr/0002-le-placement-est-l-unite-d-optimisation.md``.

Comme un régime fiscal (ADR 0001), un catalogue est une donnée versionnée par
pays et millésime, validée par ``placement_catalogs/schema.json``. Un catalogue
``draft`` est refusé par défaut ; un catalogue ``validated`` ne peut contenir
aucune valeur inconnue (``null``) et nomme la personne qui l'a validé.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from investment_calculator.tax_regime import TaxRegime, load_regime

logger = logging.getLogger(__name__)

__all__ = [
    "PACKAGE_CATALOG_DIR",
    "SCHEMA_PATH",
    "CatalogError",
    "CatalogNotFoundError",
    "CatalogValidationError",
    "DraftCatalogError",
    "PlacementCatalog",
    "list_placement_catalogs",
    "load_placement_catalog",
]

PACKAGE_CATALOG_DIR = Path(__file__).parent / "placement_catalogs"
SCHEMA_PATH = PACKAGE_CATALOG_DIR / "schema.json"


class CatalogError(Exception):
    """Erreur générique liée au catalogue des placements."""


class CatalogNotFoundError(CatalogError):
    """Aucun catalogue ne correspond à l'identifiant demandé."""


class CatalogValidationError(CatalogError):
    """Le catalogue ne respecte pas le schéma ou contredit le régime fiscal."""


class DraftCatalogError(CatalogError):
    """Le catalogue est au statut ``draft`` et n'a pas été explicitement autorisé."""


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any]:
    schema: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return schema


def _null_paths(value: Any, prefix: str) -> list[str]:
    """Chemins des valeurs ``null`` d'un document, pour les nommer dans une erreur."""
    if value is None:
        return [prefix]
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in _null_paths(v, f"{prefix}.{k}")]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in _null_paths(v, f"{prefix}[{i}]")]
    return []


def _validate(document: dict[str, Any], origin: Path, regime: TaxRegime) -> None:
    import jsonschema

    validator = jsonschema.Draft202012Validator(_load_schema())
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        details = "\n".join(
            f"  - {'/'.join(str(p) for p in err.path) or '<racine>'} : {err.message}"
            for err in errors[:10]
        )
        raise CatalogValidationError(
            f"Le catalogue {origin} ne respecte pas le schéma {SCHEMA_PATH.name} :\n{details}"
        )

    problems: list[str] = []
    ids = [p["id"] for p in document["placements"]]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        problems.append(f"identifiants de placement en double : {duplicates}")
    for placement in document["placements"]:
        wrapper_id = placement["wrapper"]
        if wrapper_id not in regime.wrapper_ids:
            problems.append(
                f"{placement['id']} : l'enveloppe {wrapper_id!r} n'existe pas dans le "
                f"régime {regime.id} (enveloppes : {regime.wrapper_ids})"
            )
            continue
        eligible = regime.wrapper(wrapper_id).get("eligible_assets") or []
        if placement["asset_class"] not in eligible:
            problems.append(
                f"{placement['id']} : la classe {placement['asset_class']!r} n'est pas "
                f"éligible à l'enveloppe {wrapper_id!r} (éligibles : {eligible})"
            )
    if document["status"] == "validated":
        nulls = _null_paths(document["placements"], "placements")
        if nulls:
            problems.append(
                f"un catalogue validé ne peut contenir de valeur inconnue : {nulls}"
            )
        if not (document.get("validation") or {}).get("validated_by"):
            problems.append("un catalogue validé doit nommer une personne dans validated_by")
    if problems:
        raise CatalogValidationError(
            f"Le catalogue {origin} est incohérent :\n"
            + "\n".join(f"  - {p}" for p in problems)
            + "\nCorrigez le fichier, ou repassez-le au statut 'draft'."
        )


@dataclass(frozen=True)
class PlacementCatalog:
    """Un catalogue de placements chargé, validé et cohérent avec son régime fiscal."""

    document: dict[str, Any] = field(repr=False)
    source: Path
    regime: TaxRegime = field(repr=False)

    @property
    def id(self) -> str:
        return str(self.document["id"])

    @property
    def status(self) -> str:
        return str(self.document["status"])

    @property
    def known_gaps(self) -> list[str]:
        return list(self.document["known_gaps"])

    @property
    def placement_ids(self) -> list[str]:
        return [str(p["id"]) for p in self.document["placements"]]

    def placement(self, placement_id: str) -> dict[str, Any]:
        """La description d'un placement, telle qu'écrite dans le catalogue."""
        for entry in self.document["placements"]:
            if entry["id"] == placement_id:
                return dict(entry)
        raise KeyError(
            f"Aucun placement {placement_id!r} dans le catalogue {self.id}. "
            f"Placements disponibles : {self.placement_ids}."
        )


def list_placement_catalogs(*, include_draft: bool = False) -> list[str]:
    """
    Identifiants des catalogues livrés, triés.

    C'est la source de vérité pour l'interface : les catalogues proposés se
    déduisent des fichiers présents. Les brouillons sont exclus par défaut.
    """
    ids = []
    for path in sorted(PACKAGE_CATALOG_DIR.glob("*.json")):
        if path.name == SCHEMA_PATH.name:
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Catalogue illisible, ignoré : %s (%s)", path, exc)
            continue
        if include_draft or document.get("status") != "draft":
            ids.append(path.stem)
    return ids


def load_placement_catalog(
    catalog_id: str = "fr-2026", *, allow_draft: bool = False
) -> PlacementCatalog:
    """
    Charger un catalogue de placements et le confronter à son régime fiscal.

    Args:
        catalog_id: identifiant du fichier, par exemple ``"fr-2026"``.
        allow_draft: autorise un catalogue ``draft``. Réservé aux tests et à la
            mise au point : un chiffre non validé ne doit pas atteindre un
            utilisateur.

    Raises:
        CatalogNotFoundError: aucun fichier ne correspond.
        DraftCatalogError: le catalogue est un brouillon et ``allow_draft`` est faux.
        CatalogValidationError: le document est invalide ou contredit le régime.
    """
    path = PACKAGE_CATALOG_DIR / f"{catalog_id}.json"
    if not path.exists():
        available = sorted(
            p.stem for p in PACKAGE_CATALOG_DIR.glob("*.json") if p.name != SCHEMA_PATH.name
        )
        raise CatalogNotFoundError(
            f"Aucun catalogue de placements {catalog_id!r}. Disponibles : {available}. "
            f"Pour en ajouter un, déposez un fichier conforme à {SCHEMA_PATH.name} "
            f"dans {PACKAGE_CATALOG_DIR}."
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    document.pop("$schema", None)
    if document.get("status") == "draft" and not allow_draft:
        raise DraftCatalogError(
            f"Le catalogue {catalog_id} est au statut 'draft' : ses frais et paramètres "
            f"n'ont pas été validés par une personne. Passez allow_draft=True pour "
            f"l'utiliser en développement, ou faites-le valider (voir "
            f"docs/adr/0002-le-placement-est-l-unite-d-optimisation.md)."
        )
    regime = load_regime(str(document.get("tax_regime", "")))
    _validate(document, path, regime)
    logger.info(
        "Catalogue de placements chargé : %s (statut %s, %d placement(s), régime %s)",
        catalog_id,
        document["status"],
        len(document["placements"]),
        regime.id,
    )
    return PlacementCatalog(document=document, source=path, regime=regime)
