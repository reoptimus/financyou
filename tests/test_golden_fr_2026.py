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

Un cas dont ``status`` n'est pas ``"ready"`` est marqué ``xfail`` : la CI
(``.github/workflows/ci.yml``) exige un ``pytest`` intégralement vert, donc un
échec documenté ne doit pas faire échouer la CI, mais il doit rester VISIBLE
dans le rapport (``xfailed``, pas ``skipped``) — sinon une lacune comblée par
erreur passerait inaperçue. Si un cas ``xfail`` se met à réussir sans que son
``status`` soit passé à ``"ready"``, ``strict=False`` évite un échec bruyant :
c'est un signal à traiter (mettre à jour le banc), pas une régression.
Un cas ``"ready"`` n'a, lui, aucune tolérance : s'il échoue, la CI échoue.
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


def _xfail_reason(case) -> str | None:
    """None si le cas doit réussir ; sinon la raison de l'échec attendu."""
    if case.status == "ready":
        return None
    if case.kind == "known_gap":
        return f"lacune connue : {case.blocked_reason}"
    missing = [f for f in REQUIRED_FIELDS if case.expected.get(f) is None]
    if missing:
        return f"valeur(s) attendue(s) non établie(s) pour {', '.join(missing)}"
    return f"statut {case.status!r} : pas encore prêt"


def _as_param(case) -> pytest.param:
    reason = _xfail_reason(case)
    marks = [pytest.mark.xfail(reason=reason, strict=False)] if reason else []
    return pytest.param(case, id=case.id, marks=marks)


@pytest.mark.parametrize("case", [_as_param(c) for c in CASES])
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
