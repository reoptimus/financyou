"""
Surfaces de volatilité swaptions — chargement, validation et garde-fou
synthétique.

Donnée d'entrée versionnée pour la calibration Hull-White (voir
:mod:`investment_calculator.stochastic_models.calibration`,
:class:`SwaptionCalibrator`), au même titre que le régime fiscal
(:mod:`investment_calculator.tax_regime`) et la courbe des taux
(:mod:`investment_calculator.yield_curve`) — voir
``docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md`` et
``investment_calculator/swaption_surfaces/README.md``.

Différence avec les deux autres : une surface peut être ``synthetic`` — des
valeurs produites par un modèle paramétrique, PAS des cotations de marché
(voir ``eur-synthetic-2026-08.json``, fourni en attendant une source de
marché payante). Ce module refuse de la charger sans un opt-in explicite de
l'appelant (``allow_synthetic=True``), pour qu'un usage en production ne
puisse pas glisser silencieusement dessus — voir
``docs/journal-1b-calibration.md``, point 8.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    "PACKAGE_SURFACE_DIR",
    "SCHEMA_PATH",
    "SwaptionSurface",
    "SwaptionSurfaceError",
    "SwaptionSurfaceNotFoundError",
    "SwaptionSurfaceSyntheticNotAllowedError",
    "SwaptionSurfaceValidationError",
    "label_to_years",
    "list_swaption_surfaces",
    "load_swaption_surface",
]

PACKAGE_SURFACE_DIR = Path(__file__).parent / "swaption_surfaces"
SCHEMA_PATH = PACKAGE_SURFACE_DIR / "schema.json"

_LABEL_RE = re.compile(r"^(\d+(?:\.\d+)?)([MY])$")
_MONTHS_PER_YEAR = 12.0


class SwaptionSurfaceError(Exception):
    """Erreur générique liée à une surface de volatilité swaptions."""


class SwaptionSurfaceNotFoundError(SwaptionSurfaceError):
    """Aucune surface ne correspond à l'identifiant demandé."""


class SwaptionSurfaceValidationError(SwaptionSurfaceError):
    """Le document ne respecte pas le schéma, ou la grille chargée est incohérente."""


class SwaptionSurfaceSyntheticNotAllowedError(SwaptionSurfaceError):
    """
    La surface demandée est synthétique et l'appelant n'a pas explicitement
    accepté ce statut via ``allow_synthetic=True``.

    Ce n'est pas juste une donnée `draft` (voir
    investment_calculator.yield_curve, qui autorise `draft` par défaut) : une
    surface synthétique n'est pas une cotation de marché imparfaite, c'est
    une valeur inventée pour faire tourner le code. Le laisser passer par
    défaut violerait la règle « aucune valeur inventée » de CLAUDE.md.
    """


def label_to_years(label: str) -> float:
    """
    Convertir un libellé d'échéance ('1M', '3M', '10Y'...) en années.

    Raises:
        ValueError: libellé non reconnu (format attendu : un entier ou
            décimal suivi de 'M' ou 'Y').
    """
    match = _LABEL_RE.match(label.strip())
    if not match:
        raise ValueError(f"Libellé d'échéance non reconnu : {label!r} (attendu ex. '3M', '10Y').")
    value, unit = match.groups()
    return float(value) / _MONTHS_PER_YEAR if unit == "M" else float(value)


def list_swaption_surfaces() -> list[dict[str, Any]]:
    """Inventorier les surfaces disponibles (id, millésime, statut, synthétique)."""
    surfaces = []
    for path in sorted(PACKAGE_SURFACE_DIR.glob("*.json")):
        if path.name == "schema.json":
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Surface illisible, ignorée : %s (%s)", path, exc)
            continue
        surfaces.append(
            {
                "id": doc.get("id"),
                "observation_date": doc.get("observation_date"),
                "status": doc.get("status"),
                "synthetic": doc.get("synthetic"),
                "path": path,
            }
        )
    return surfaces


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validate_document(document: dict[str, Any], origin: Path) -> None:
    import jsonschema

    validator = jsonschema.Draft202012Validator(_load_schema())
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        details = "\n".join(
            f"  - {'/'.join(str(p) for p in err.path) or '<racine>'} : {err.message}"
            for err in errors[:10]
        )
        raise SwaptionSurfaceValidationError(f"{origin} ne respecte pas le schéma :\n{details}")


def _check_coherence(document: dict[str, Any], origin: Path) -> np.ndarray:
    grid = document["grid"]
    expiries, tenors, rows = grid["expiries"], grid["tenors"], grid["vol_normal_bp"]

    if len(rows) != len(expiries):
        raise SwaptionSurfaceValidationError(
            f"{origin} : {len(rows)} lignes de volatilité pour {len(expiries)} échéances."
        )
    for i, row in enumerate(rows):
        if len(row) != len(tenors):
            raise SwaptionSurfaceValidationError(
                f"{origin} : ligne {expiries[i]!r} a {len(row)} valeurs pour "
                f"{len(tenors)} ténors — grille non rectangulaire."
            )

    vol_grid = np.array(rows, dtype=float)
    if not np.isfinite(vol_grid).all():
        raise SwaptionSurfaceValidationError(f"{origin} : valeurs non finies dans la grille.")
    if vol_grid.min() <= 0:
        raise SwaptionSurfaceValidationError(f"{origin} : volatilité non positive dans la grille.")

    try:
        expiry_years = [label_to_years(e) for e in expiries]
        tenor_years = [label_to_years(t) for t in tenors]
    except ValueError as exc:
        raise SwaptionSurfaceValidationError(f"{origin} : {exc}") from exc

    if sorted(expiry_years) != expiry_years:
        raise SwaptionSurfaceValidationError(f"{origin} : les échéances ne sont pas croissantes.")
    if sorted(tenor_years) != tenor_years:
        raise SwaptionSurfaceValidationError(f"{origin} : les ténors ne sont pas croissants.")

    return vol_grid


@dataclass(frozen=True)
class SwaptionSurface:
    """Une surface de volatilité swaptions chargée, validée, prête à calibrer."""

    document: dict[str, Any] = field(repr=False)
    vol_grid: np.ndarray = field(repr=False)
    source: Path

    @property
    def id(self) -> str:
        return str(self.document["id"])

    @property
    def status(self) -> str:
        return str(self.document["status"])

    @property
    def synthetic(self) -> bool:
        return bool(self.document["synthetic"])

    @property
    def currency(self) -> str:
        return str(self.document["currency"])

    @property
    def observation_date(self) -> str:
        """Millésime de la surface, à consigner dans les métadonnées de toute calibration."""
        return str(self.document["observation_date"])

    @property
    def vol_convention(self) -> str:
        return str(self.document["vol_convention"])

    @property
    def expiries(self) -> list[str]:
        return list(self.document["grid"]["expiries"])

    @property
    def tenors(self) -> list[str]:
        return list(self.document["grid"]["tenors"])

    @property
    def expiries_years(self) -> np.ndarray:
        return np.array([label_to_years(e) for e in self.expiries])

    @property
    def tenors_years(self) -> np.ndarray:
        return np.array([label_to_years(t) for t in self.tenors])

    @property
    def reference_curve(self) -> dict[str, float] | None:
        """
        Paramètres Nelson-Siegel associés à cette surface, UNIQUEMENT pour
        reproduire ses forwards ATM et ses résultats de vérification (voir
        known_gaps du document). Jamais pour une courbe de production : voir
        investment_calculator.yield_curve.
        """
        curve = self.document.get("reference_curve")
        return dict(curve) if curve is not None else None

    @property
    def verification(self) -> dict[str, Any] | None:
        """Calibrations de référence fournies avec la surface, pour non-régression."""
        verification = self.document.get("verification")
        return dict(verification) if verification is not None else None

    def get_vol(self, expiry: str, tenor: str) -> float:
        """
        Volatilité normale (bp/an) pour une échéance/ténor exacts de la grille.

        Raises:
            KeyError: l'échéance ou le ténor demandé n'est pas un point exact
                de la grille (pas d'interpolation ici : voir
                SwaptionCalibrator pour une sélection de points par distance).
        """
        try:
            i = self.expiries.index(expiry)
        except ValueError as exc:
            raise KeyError(f"Échéance {expiry!r} absente de la grille : {self.expiries}") from exc
        try:
            j = self.tenors.index(tenor)
        except ValueError as exc:
            raise KeyError(f"Ténor {tenor!r} absent de la grille : {self.tenors}") from exc
        return float(self.vol_grid[i, j])


def load_swaption_surface(surface_id: str, *, allow_synthetic: bool = False) -> SwaptionSurface:
    """
    Charger et valider une surface de volatilité swaptions par identifiant.

    Args:
        surface_id: identifiant du fichier, par exemple ``"eur-synthetic-2026-08"``.
        allow_synthetic: doit être explicitement mis à ``True`` pour charger
            une surface ``synthetic: true`` (voir SwaptionSurfaceSyntheticNotAllowedError).
            Faux par défaut, à la différence de
            :func:`investment_calculator.yield_curve.load_yield_curve` : une
            surface synthétique n'est pas une donnée de marché imparfaite,
            c'est une valeur inventée pour du développement — voir
            investment_calculator/swaption_surfaces/README.md.

    Raises:
        SwaptionSurfaceNotFoundError: aucun fichier ne correspond à ``surface_id``.
        SwaptionSurfaceValidationError: document invalide, ou grille incohérente.
        SwaptionSurfaceSyntheticNotAllowedError: surface synthétique sans opt-in.
    """
    path = PACKAGE_SURFACE_DIR / f"{surface_id}.json"
    if not path.exists():
        disponibles = ", ".join(s["id"] for s in list_swaption_surfaces()) or "aucune"
        raise SwaptionSurfaceNotFoundError(
            f"Aucune surface de volatilité swaptions {surface_id!r}. Disponibles : {disponibles}."
        )

    document = json.loads(path.read_text(encoding="utf-8"))
    document.pop("$schema", None)
    _validate_document(document, path)

    if document["synthetic"] and not allow_synthetic:
        raise SwaptionSurfaceSyntheticNotAllowedError(
            f"La surface {surface_id!r} est synthétique (synthetic=true) : ce ne sont pas des "
            f"cotations de marché. Interdiction d'en tirer une calibration publiée ou affichée à "
            f"un utilisateur. Passez allow_synthetic=True si c'est un usage de développement/test "
            f"assumé — voir investment_calculator/swaption_surfaces/README.md."
        )

    vol_grid = _check_coherence(document, path)

    logger.info(
        "Surface de volatilité swaptions chargée : %s (millésime %s, statut %s, synthétique=%s)",
        surface_id,
        document["observation_date"],
        document["status"],
        document["synthetic"],
    )
    return SwaptionSurface(document=document, vol_grid=vol_grid, source=path)
