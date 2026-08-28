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

    @property
    def equity_risk_premium(self) -> float:
        """
        Prime de risque actions (monde réel), à ajouter au taux sans risque.

        À utiliser uniquement pour projeter un patrimoine — jamais pour un
        pricing ou un test de martingalité, qui restent risque-neutres. Voir
        docs/validation/1b-hypotheses-monde-reel.md pour la fourchette et la
        source.
        """
        return float(self.document["risk_premia"]["equity"]["value"])

    @property
    def real_estate_risk_premium(self) -> float:
        """Prime de risque immobilière (monde réel) ; mêmes réserves que equity_risk_premium."""
        return float(self.document["risk_premia"]["real_estate"]["value"])

    @property
    def equity_volatility(self) -> float:
        """Volatilité annualisée du rendement total actions (σ de Black-Scholes)."""
        return float(self.document["equity"]["volatility"])

    @property
    def real_estate_volatility(self) -> float:
        """Volatilité annualisée du prix immobilier."""
        return float(self.document["real_estate"]["dynamics"]["volatility"])

    @property
    def real_estate_mean_reversion(self) -> float:
        """Vitesse de retour à la moyenne du processus immobilier ('a' de RealEstateModel)."""
        return float(self.document["real_estate"]["dynamics"]["mean_reversion"])

    @property
    def real_estate_rental_yield(self) -> float:
        """Rendement locatif annuel supposé (paramètre du modèle stochastique immobilier)."""
        return float(self.document["real_estate"]["dynamics"]["rental_yield"])

    @property
    def real_estate_inflation_adjustment(self) -> float:
        """Ajustement du loyer à l'inflation (paramètre du modèle stochastique immobilier)."""
        return float(self.document["real_estate"]["dynamics"]["inflation_adjustment"])

    @property
    def risk_free_rate_mean(self) -> float:
        """
        Taux sans risque constant, utilisé uniquement par le chemin de génération
        simple (ScenarioGenerator._generate_simple), qui n'a ni courbe EIOPA ni
        modèle Hull-White. Sert aussi de base au drift monde réel de ce chemin :
        voir equity_expected_return et real_estate_expected_return.
        """
        return float(self.document["rates"]["risk_free_proxy"]["mean"])

    @property
    def risk_free_rate_volatility(self) -> float:
        """Volatilité du taux sans risque constant du chemin de génération simple."""
        return float(self.document["rates"]["risk_free_proxy"]["volatility"])

    @property
    def hull_white_mean_reversion_speed(self) -> float:
        """
        Paramètre 'a' de Hull-White pour le chemin stochastique. PLACEHOLDER non
        calibré tant que l'étape 1.B.5 (calibration sur swaptions réels) n'a pas
        été menée — voir le champ 'status' du document et
        docs/journal-1b-calibration.md.
        """
        return float(self.document["rates"]["hull_white"]["mean_reversion_speed"])

    @property
    def hull_white_volatility(self) -> float:
        """Paramètre 'sigma' de Hull-White ; mêmes réserves que hull_white_mean_reversion_speed."""
        return float(self.document["rates"]["hull_white"]["volatility"])

    @property
    def bond_return_mean(self) -> float:
        """Rendement obligataire moyen, chemin de génération simple."""
        return float(self.document["bond"]["mean"])

    @property
    def bond_return_volatility(self) -> float:
        """Volatilité du rendement obligataire, chemin de génération simple."""
        return float(self.document["bond"]["volatility"])

    @property
    def inflation_mean(self) -> float:
        """Inflation moyenne supposée."""
        return float(self.document["inflation"]["mean"])

    @property
    def inflation_volatility(self) -> float:
        """Volatilité de l'inflation supposée."""
        return float(self.document["inflation"]["volatility"])

    @property
    def gdp_growth_mean(self) -> float:
        """Croissance du PIB moyenne supposée."""
        return float(self.document["gdp_growth"]["mean"])

    @property
    def gdp_growth_volatility(self) -> float:
        """Volatilité de la croissance du PIB supposée."""
        return float(self.document["gdp_growth"]["volatility"])

    @property
    def correlations(self) -> dict[tuple[str, str], float]:
        """
        Matrice de corrélation entre classes d'actifs, sous la forme utilisée par
        ScenarioGenerator.default_correlations (clé = tuple des deux noms
        d'actifs). Voir known_gaps : à l'écriture, aucun des deux chemins de
        génération ne consomme cette donnée.
        """
        return {
            (entry["pair"][0], entry["pair"][1]): float(entry["value"])
            for entry in self.document["correlations"]
        }

    @property
    def equity_expected_return(self) -> float:
        """
        Rendement actions attendu, monde réel, chemin de génération simple :
        taux sans risque constant + prime de risque actions. Centralise la
        formule utilisée à la fois par ScenarioGenerator et GlobalScenarioEngine
        (étape 1.B.4) pour éviter de la dupliquer dans les deux modules.
        """
        return self.risk_free_rate_mean + self.equity_risk_premium

    @property
    def real_estate_expected_return(self) -> float:
        """Rendement immobilier attendu, chemin simple ; réserves : voir equity_expected_return."""
        return self.risk_free_rate_mean + self.real_estate_risk_premium


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
