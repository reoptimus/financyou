"""
Courbes des taux — chargement, validation et traçabilité du millésime.

La courbe des taux sans risque est une donnée d'entrée du modèle, au même
titre que le régime fiscal (voir :mod:`investment_calculator.tax_regime` et
``docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md``) : elle varie
par pays et par millésime, et une simulation archivée doit pouvoir être
rejouée à l'identique en référençant l'identifiant de la courbe utilisée —
c'est pourquoi cet identifiant doit figurer dans les métadonnées de chaque
simulation (voir ``ScenarioGenerator._generate_stochastic``).

Ce module ne recalcule pas la courbe lui-même : il délègue le bootstrap, la
calibration et l'interpolation à
:class:`investment_calculator.stochastic_models.calibration.EIOPACalibrator`.
Sa seule responsabilité est la traçabilité — quel fichier, quelle feuille,
quel millésime — et une vérification de cohérence minimale avant de servir
la courbe à un modèle de taux.

Le fichier source référencé par une courbe (typiquement dans ``legacy/``)
n'est jamais modifié par ce paquet : voir ``CLAUDE.md``, ``legacy/`` est une
référence de vérité en lecture seule.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from investment_calculator.stochastic_models.calibration import EIOPACalibrator

logger = logging.getLogger(__name__)

__all__ = [
    "PACKAGE_CURVE_DIR",
    "REPO_ROOT",
    "SCHEMA_PATH",
    "YieldCurve",
    "YieldCurveError",
    "YieldCurveNotFoundError",
    "YieldCurveValidationError",
    "list_yield_curves",
    "load_yield_curve",
]

PACKAGE_CURVE_DIR = Path(__file__).parent / "yield_curves"
SCHEMA_PATH = PACKAGE_CURVE_DIR / "schema.json"
REPO_ROOT = Path(__file__).resolve().parent.parent


class YieldCurveError(Exception):
    """Erreur générique liée à une courbe des taux."""


class YieldCurveNotFoundError(YieldCurveError):
    """Aucune courbe ne correspond à l'identifiant demandé."""


class YieldCurveValidationError(YieldCurveError):
    """Le document ne respecte pas le schéma, ou la courbe chargée est incohérente."""


def list_yield_curves() -> list[dict[str, Any]]:
    """Inventorier les courbes disponibles (id, millésime, statut)."""
    curves = []
    for path in sorted(PACKAGE_CURVE_DIR.glob("*.json")):
        if path.name == "schema.json":
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Courbe illisible, ignorée : %s (%s)", path, exc)
            continue
        curves.append(
            {
                "id": doc.get("id"),
                "vintage_date": doc.get("vintage_date"),
                "status": doc.get("status"),
                "path": path,
            }
        )
    return curves


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
        raise YieldCurveValidationError(f"{origin} ne respecte pas le schéma :\n{details}")


@dataclass(frozen=True)
class YieldCurve:
    """Une courbe des taux chargée, calibrée, prête à alimenter un modèle de taux."""

    document: dict[str, Any] = field(repr=False)
    calibrator: EIOPACalibrator
    source: Path

    @property
    def id(self) -> str:
        return str(self.document["id"])

    @property
    def vintage_date(self) -> str:
        """Millésime de la courbe, à consigner dans les métadonnées de toute simulation."""
        return str(self.document["vintage_date"])

    @property
    def status(self) -> str:
        return str(self.document["status"])

    @property
    def country_code(self) -> str:
        return str(self.document["country"]["code"])

    def get_forward_curve(self, n_steps: int | None = None) -> np.ndarray:
        return self.calibrator.get_forward_curve(n_steps=n_steps)

    def get_bond_prices(self, n_steps: int | None = None) -> np.ndarray:
        return self.calibrator.get_bond_prices(n_steps=n_steps)


def load_yield_curve(curve_id: str, *, dt: float = 0.5, allow_draft: bool = True) -> YieldCurve:
    """
    Charger et calibrer une courbe des taux par identifiant.

    Args:
        curve_id: identifiant du fichier, par exemple ``"eiopa-fr-2018-04"``.
        dt: pas de temps pour l'interpolation/calibration (voir ``EIOPACalibrator``).
        allow_draft: autorise le chargement d'une courbe au statut ``draft``.
            Vrai par défaut ici, à la différence de
            :func:`investment_calculator.tax_regime.load_regime` :
            ``eiopa-fr-2018-04`` est validée depuis le 2026-08-28 (voir son
            ``validation.validated_by``), mais le défaut reste permissif pour
            qu'une future courbe encore ``draft`` (nouveau pays, nouveau
            millésime) ne bloque pas le développement avant sa relecture. À
            resserrer à ``False`` si l'on veut qu'un ``yield_curve_id``
            draft soit refusé par défaut, comme pour un régime fiscal.

    Raises:
        YieldCurveNotFoundError: aucun fichier ne correspond à ``curve_id``.
        YieldCurveValidationError: document invalide, ou courbe chargée
            incohérente (P(0,t) hors bornes économiquement plausibles).
    """
    path = PACKAGE_CURVE_DIR / f"{curve_id}.json"
    if not path.exists():
        disponibles = ", ".join(c["id"] for c in list_yield_curves()) or "aucune"
        raise YieldCurveNotFoundError(
            f"Aucune courbe des taux {curve_id!r}. Disponibles : {disponibles}."
        )

    document = json.loads(path.read_text(encoding="utf-8"))
    document.pop("$schema", None)
    _validate_document(document, path)

    if document["status"] == "draft" and not allow_draft:
        raise YieldCurveValidationError(
            f"La courbe {curve_id!r} est au statut 'draft' et allow_draft=False."
        )

    source = document["source"]
    filepath = REPO_ROOT / source["path"]
    if source["kind"] == "excel":
        calibrator = EIOPACalibrator.from_excel(
            str(filepath),
            sheet_name=source.get("sheet_name", "RFR"),
            country_column=source.get("column", 1),
            start_row=source.get("start_row", 1),
            end_row=source.get("end_row"),
            dt=dt,
        )
    elif source["kind"] == "csv":
        calibrator = EIOPACalibrator.from_csv(
            str(filepath),
            country_column=source.get("column_name", document["country"]["name"]),
            dt=dt,
        )
    else:
        raise YieldCurveValidationError(f"Type de source inconnu : {source['kind']!r}")

    calibrator.calibrate()
    _check_coherence(calibrator, curve_id)

    logger.info(
        "Courbe des taux chargée : %s (millésime %s, statut %s)",
        curve_id,
        document["vintage_date"],
        document["status"],
    )
    return YieldCurve(document=document, calibrator=calibrator, source=path)


def _check_coherence(calibrator: EIOPACalibrator, curve_id: str) -> None:
    """
    Contrôles de cohérence qu'un schéma JSON ne peut pas exprimer.

    Une courbe des taux n'est pas juste une suite de nombres : P(0,t) doit
    rester dans des bornes économiquement plausibles, et la courbe forward
    doit être finie partout. Ces contrôles ne remplacent pas une relecture
    humaine (voir ``known_gaps``), mais ils attrapent une erreur de lecture
    grossière (mauvaise colonne, mauvaise feuille, décalage de ligne) — le
    genre d'erreur qui existait précisément dans les anciens défauts de
    ``EIOPACalibrator.from_excel`` avant l'étape 1.B.2.
    """
    p0t = calibrator.P0t_interp
    f0t = calibrator.f0t
    if p0t is None or f0t is None:
        raise YieldCurveValidationError(f"{curve_id} : calibrate() n'a pas produit P0t/f0t.")

    if not np.isfinite(p0t).all() or not np.isfinite(f0t).all():
        raise YieldCurveValidationError(f"{curve_id} : valeurs non finies dans P0t ou f0t.")

    # P(0,0) = 1 exactement ; des taux courts négatifs peuvent temporairement
    # pousser P(0,t) légèrement au-dessus de 1 (observé sur cette courbe même,
    # au voisinage de 2 ans), mais pas de façon déraisonnable.
    if abs(p0t[0] - 1.0) > 1e-6:
        raise YieldCurveValidationError(f"{curve_id} : P(0,0) devrait valoir 1, vaut {p0t[0]}.")
    if p0t.max() > 1.10:
        raise YieldCurveValidationError(
            f"{curve_id} : P(0,t) atteint {p0t.max():.4f}, largement au-dessus de 1 — "
            f"probablement une erreur de lecture (mauvaise colonne ou ligne)."
        )
    if p0t.min() <= 0:
        raise YieldCurveValidationError(f"{curve_id} : P(0,t) atteint une valeur non positive.")

    # Aux longues maturités, une fois la zone éventuelle de taux négatifs de
    # court terme dépassée, P(0,t) doit décroître : sinon la courbe n'a
    # probablement pas été lue dans le bon ordre ou la bonne colonne.
    tail = p0t[len(p0t) // 2:]
    if not (np.diff(tail) <= 1e-9).all():
        raise YieldCurveValidationError(
            f"{curve_id} : P(0,t) n'est pas décroissant sur la seconde moitié de "
            f"la courbe — vérifiez la colonne et l'ordre des lignes lues."
        )
