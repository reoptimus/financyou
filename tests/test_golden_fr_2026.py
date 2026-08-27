"""
Cas d'or — régime fiscal France, millésime 2026.

Chaque cas de ``tests/golden/fr-2026.json`` décrit une situation fiscale
concrète et le résultat qu'elle doit produire au centime près. Ce fichier les
exécute contre le régime chargé par
``investment_calculator.tax_regime.load_regime`` et compare le résultat à la
valeur attendue.

Voir ``tests/golden/README.md`` pour le format des cas, et
``docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md`` pour le principe
général : la fiscalité est une donnée d'entrée du modèle, pas une règle codée.

À la création de ce banc, le régime ``fr-2026`` est un brouillon et aucune
valeur attendue n'a été établie : TOUS les cas échouent. C'est le comportement
voulu (voir étape 1.A du plan de travail) — un banc de cas d'or entièrement
vert avant d'avoir vérifié une seule valeur serait plus inquiétant qu'un banc
rouge.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from investment_calculator.tax_regime import TaxRegime, load_regime
from tests.golden.loader import CENT_TOLERANCE, compute, load_golden_file

CASES_PATH = Path(__file__).parent / "golden" / "fr-2026.json"
REGIME_ID, CASES = load_golden_file(CASES_PATH)

REQUIRED_FIELDS = ("income_tax", "social_contributions", "total", "net")


def _regime() -> TaxRegime:
    country, year = REGIME_ID.split("-")
    return load_regime(country, int(year), allow_draft=True)


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_cas_d_or(case):
    if case.kind == "known_gap":
        pytest.fail(
            f"lacune connue non comblée : {case.blocked_reason}\n"
            f"Voir docs/validation/1a-cas-d-or.md."
        )

    missing = [f for f in REQUIRED_FIELDS if case.expected.get(f) is None]
    if missing:
        pytest.fail(
            f"valeur(s) attendue(s) non encore établie(s) pour {', '.join(missing)} "
            f"— cas : {case.description}"
        )

    regime = _regime()
    result = compute(regime, case)
    for field in REQUIRED_FIELDS:
        calcule = round(result[field], 2)
        attendu = round(float(case.expected[field]), 2)
        assert abs(calcule - attendu) < CENT_TOLERANCE, (
            f"{case.id} — {field} : calculé {calcule:.2f} €, attendu {attendu:.2f} € "
            f"({case.description})"
        )
