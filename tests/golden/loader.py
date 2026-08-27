"""
Chargeur et exécuteur de cas d'or.

Un cas d'or décrit une situation fiscale concrète et le résultat qu'elle doit
produire au centime près (voir ``tests/golden/README.md``). Ce module sait
lire un fichier de cas et calculer ce que le régime fiscal produit pour
chacun ; il ne juge pas si ce résultat est correct — c'est le rôle des tests
qui comparent le résultat à la valeur attendue.

Ce module vit sous ``tests/`` et non sous ``investment_calculator/`` : c'est
un outil de vérification, pas une brique du produit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from investment_calculator.tax_regime import TaxRegime

GOLDEN_DIR = Path(__file__).parent
SCHEMA_PATH = GOLDEN_DIR / "schema.json"

KNOWN_KINDS = {"income_tax", "wealth_tax", "wrapper_withdrawal", "known_gap"}

#: Tolérance de comparaison "au centime" : deux montants arrondis à 0,01 €
#: doivent coïncider. Un peu de marge absorbe les imprécisions binaires du
#: flottant, pas une erreur de calcul.
CENT_TOLERANCE = 0.005


class GoldenCaseError(Exception):
    """Le cas ne peut pas être calculé dans son état actuel — un échec normal tant que la lacune qu'il documente n'est pas comblée."""


@dataclass(frozen=True)
class GoldenCase:
    """Un cas d'or tel que décrit dans le fichier JSON, sous forme typée."""

    id: str
    description: str
    kind: str
    status: str
    inputs: dict[str, Any]
    expected: dict[str, Any]
    blocked_reason: str | None
    sources: list[dict[str, Any]]
    confidence: str | None
    notes: str | None


def load_golden_file(path: Path) -> tuple[str, list[GoldenCase]]:
    """Charger et valider un fichier de cas d'or ; renvoie (regime_id, cas)."""
    document = json.loads(path.read_text(encoding="utf-8"))
    _validate(document, path)
    cases = [_parse_case(raw) for raw in document["cases"]]
    ids = [c.id for c in cases]
    doublons = {i for i in ids if ids.count(i) > 1}
    if doublons:
        raise GoldenCaseError(f"{path} : identifiants de cas dupliqués : {sorted(doublons)}")
    return document["regime_id"], cases


def _parse_case(raw: dict[str, Any]) -> GoldenCase:
    return GoldenCase(
        id=raw["id"],
        description=raw["description"],
        kind=raw["kind"],
        status=raw["status"],
        inputs=raw.get("inputs", {}),
        expected=raw.get("expected", {}),
        blocked_reason=raw.get("blocked_reason"),
        sources=raw.get("sources", []),
        confidence=raw.get("confidence"),
        notes=raw.get("notes"),
    )


def _validate(document: dict[str, Any], origin: Path) -> None:
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        details = "\n".join(
            f"  - {'/'.join(str(p) for p in err.path) or '<racine>'} : {err.message}"
            for err in errors[:10]
        )
        raise GoldenCaseError(f"{origin} ne respecte pas {SCHEMA_PATH.name} :\n{details}")


def compute(regime: TaxRegime, case: GoldenCase) -> dict[str, float]:
    """
    Calculer ce que le régime produit pour un cas : income_tax, social_contributions, total, net.

    Lève :class:`GoldenCaseError` si le cas ne peut pas être calculé (lacune
    connue, ou entrée insuffisante). C'est un échec attendu du test, pas un
    défaut de ce module.
    """
    if case.kind == "known_gap":
        raise GoldenCaseError(
            f"cas {case.id!r} bloqué par une lacune connue du régime : {case.blocked_reason}"
        )
    if case.kind == "income_tax":
        return _compute_income_tax(regime, case.inputs)
    if case.kind == "wealth_tax":
        return _compute_wealth_tax(regime, case.inputs)
    if case.kind == "wrapper_withdrawal":
        return _compute_wrapper_withdrawal(regime, case.inputs)
    raise GoldenCaseError(f"cas {case.id!r} : kind inconnu {case.kind!r}")


def _compute_income_tax(regime: TaxRegime, inputs: dict[str, Any]) -> dict[str, float]:
    taxable_income = float(inputs["taxable_income"])
    shares = float(inputs.get("shares", 1.0))
    dependent_shares = float(inputs.get("dependent_shares", 0.0))
    income_tax = regime.income_tax_due(taxable_income, shares=shares, dependent_shares=dependent_shares)
    if inputs.get("apply_surtax"):
        married = inputs.get("household_status") == "couple"
        surtax_base = float(inputs.get("surtax_base", taxable_income))
        income_tax += regime.surtax_due(surtax_base, married=married)
    return {
        "income_tax": income_tax,
        "social_contributions": 0.0,
        "total": income_tax,
        "net": taxable_income - income_tax,
    }


def _compute_wealth_tax(regime: TaxRegime, inputs: dict[str, Any]) -> dict[str, float]:
    net_taxable_wealth = float(inputs["net_taxable_wealth"])
    wealth_tax = regime.wealth_tax_due(net_taxable_wealth)
    return {
        "income_tax": 0.0,
        "social_contributions": 0.0,
        "total": wealth_tax,
        "net": net_taxable_wealth - wealth_tax,
    }


def _compute_wrapper_withdrawal(regime: TaxRegime, inputs: dict[str, Any]) -> dict[str, float]:
    wrapper_id = inputs["wrapper_id"]
    withdrawal_amount = float(inputs["withdrawal_amount"])
    shares = float(inputs.get("shares", 1.0))

    rule = regime.select_withdrawal_rule(
        wrapper_id,
        holding_years=inputs.get("holding_years"),
        age=inputs.get("age"),
        premiums_paid=inputs.get("premiums_paid"),
        account_value=inputs.get("account_value"),
        exit_form=inputs.get("exit_form"),
    )

    taxable_base = rule.get("taxable_base", "full_withdrawal")
    if taxable_base == "full_withdrawal":
        taxable_amount = withdrawal_amount
    elif taxable_base == "gain_only":
        taxable_amount = float(inputs["gain_amount"])
    elif taxable_base == "proportional_gain":
        account_value = float(inputs["account_value"])
        total_gain = float(inputs["total_gain"])
        if account_value <= 0:
            raise GoldenCaseError("account_value doit être strictement positif pour proportional_gain")
        taxable_amount = withdrawal_amount * (total_gain / account_value)
    else:
        raise GoldenCaseError(f"taxable_base inconnu : {taxable_base!r}")

    income_tax_base = taxable_amount
    social_base = taxable_amount
    allowance = rule.get("allowance")
    if allowance:
        household_status = inputs.get("household_status", "single")
        amount = (
            allowance["amount_couple"] if household_status == "couple" else allowance["amount_single"]
        )
        against = allowance.get("against", "income_tax")
        if against in ("income_tax", "both"):
            income_tax_base = max(0.0, income_tax_base - amount)
        if against in ("social_contributions", "both"):
            social_base = max(0.0, social_base - amount)

    income_tax_rate = regime.resolve_income_tax_rate(rule, taxable_amount=income_tax_base, shares=shares)
    social_rate = regime.resolve_social_rate(rule)

    income_tax = income_tax_base * income_tax_rate
    social_contributions = social_base * social_rate
    total = income_tax + social_contributions
    return {
        "income_tax": income_tax,
        "social_contributions": social_contributions,
        "total": total,
        "net": withdrawal_amount - total,
    }
