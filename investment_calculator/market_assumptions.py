"""
Hypothèses de marché et de comportement — chargement et validation.

Distinctes d'un régime fiscal (voir :mod:`investment_calculator.tax_regime`) :
un régime décrit l'imposition ; ce module décrit des hypothèses de marché
(rendement, répartition, comportement de réalisation) que le moteur fiscal
utilise pour approximer des scénarios, mais qui ne sont pas de la fiscalité.
Voir ``docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md``, section
« ce qui n'est pas de la fiscalité ».

Avant l'étape 1.A.6, ces valeurs étaient des littéraux codés en dur dans
``investment_calculator/modules/tax_engine.py``, recensés explicitement dans
``tests/test_tax_regime_contract.py::LITTERAUX_TOLERES``. Elles vivent
désormais ici, comme donnée versionnée — sans pour autant être vérifiées :
voir le statut ``draft`` et les ``known_gaps`` de
``market_assumptions/default-2026.json``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "PACKAGE_ASSUMPTIONS_DIR",
    "SCHEMA_PATH",
    "MarketAssumptions",
    "MarketAssumptionsError",
    "MarketAssumptionsNotFoundError",
    "MarketAssumptionsValidationError",
    "load_market_assumptions",
]

PACKAGE_ASSUMPTIONS_DIR = Path(__file__).parent / "market_assumptions"
SCHEMA_PATH = PACKAGE_ASSUMPTIONS_DIR / "schema.json"


class MarketAssumptionsError(Exception):
    """Erreur générique liée aux hypothèses de marché."""


class MarketAssumptionsNotFoundError(MarketAssumptionsError):
    """Aucun jeu d'hypothèses ne correspond à l'identifiant demandé."""


class MarketAssumptionsValidationError(MarketAssumptionsError):
    """Le document ne respecte pas le schéma des hypothèses de marché."""


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validate(document: dict[str, Any], origin: Path) -> None:
    import jsonschema

    validator = jsonschema.Draft202012Validator(_load_schema())
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        details = "\n".join(
            f"  - {'/'.join(str(p) for p in err.path) or '<racine>'} : {err.message}"
            for err in errors[:10]
        )
        raise MarketAssumptionsValidationError(
            f"Le jeu d'hypothèses {origin} ne respecte pas le schéma :\n{details}"
        )

    shares = document["real_estate"]
    total = shares["rental_income_share"] + shares["appreciation_share"]
    if abs(total - 1.0) > 1e-9:
        raise MarketAssumptionsValidationError(
            f"{origin} : rental_income_share + appreciation_share doit valoir 1, vaut {total}."
        )


@dataclass(frozen=True)
class MarketAssumptions:
    """Un jeu d'hypothèses de marché chargé et validé."""

    document: dict[str, Any] = field(repr=False)
    source: Path

    @property
    def id(self) -> str:
        return str(self.document["id"])

    @property
    def status(self) -> str:
        return str(self.document["status"])

    @property
    def dividend_yield(self) -> float:
        """Rendement du dividende supposé, en fraction du cours."""
        return float(self.document["equity"]["dividend_yield"])

    @property
    def rental_income_share(self) -> float:
        """Part du rendement immobilier supposée provenir du loyer."""
        return float(self.document["real_estate"]["rental_income_share"])

    @property
    def appreciation_share(self) -> float:
        """Part du rendement immobilier supposée provenir de l'appréciation."""
        return float(self.document["real_estate"]["appreciation_share"])

    @property
    def annual_realized_fraction(self) -> float:
        """Fraction des plus-values latentes supposée réalisée chaque année."""
        return float(self.document["capital_gains_behavior"]["annual_realized_fraction"])

    @property
    def reference_household_income(self) -> float:
        """Revenu de foyer utilisé pour réduire un barème progressif à un taux moyen."""
        return float(
            self.document["household_income_approximation"]["reference_household_income"]
        )


def load_market_assumptions(assumptions_id: str = "default-2026") -> MarketAssumptions:
    """
    Charger un jeu d'hypothèses de marché par identifiant.

    Args:
        assumptions_id: identifiant du fichier, par exemple ``"default-2026"``.

    Raises:
        MarketAssumptionsNotFoundError: aucun fichier ne correspond.
        MarketAssumptionsValidationError: le document existe mais est invalide.
    """
    path = PACKAGE_ASSUMPTIONS_DIR / f"{assumptions_id}.json"
    if not path.exists():
        disponibles = sorted(
            p.stem for p in PACKAGE_ASSUMPTIONS_DIR.glob("*.json") if p.name != "schema.json"
        )
        raise MarketAssumptionsNotFoundError(
            f"Aucun jeu d'hypothèses de marché '{assumptions_id}'. "
            f"Disponibles : {', '.join(disponibles)}."
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    document.pop("$schema", None)
    _validate(document, path)
    logger.info(
        "Hypothèses de marché chargées : %s (statut %s)", assumptions_id, document["status"]
    )
    return MarketAssumptions(document=document, source=path)
