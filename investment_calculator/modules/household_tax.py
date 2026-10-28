"""
Parts fiscales et impôt sur le revenu du foyer, année par année.

Le nombre de parts vient du régime (``income_tax.household_quotient`` :
parts du premier et du second adulte, parts de chaque personne à charge selon
son rang). L'impôt est celui de :meth:`TaxRegime.income_tax_due`, barème et
plafonnement du quotient compris. On en tire la tranche marginale du foyer,
qui ne sert qu'aux produits imposés au barème.

Aucune valeur fiscale n'est écrite ici : tout vient du régime. L'âge auquel
un enfant cesse d'être à charge n'est pas supposé : l'utilisateur donne, pour
chaque personne à charge, le nombre d'années pendant lesquelles elle le reste.

Équivalent R : ``fct_imp_IR.R`` (``fct_flux_IR``) et la partie « part
imposable » de ``fct_chrono_flux.R``. La traduction fidèle est dans
``tests/reference_r/imp_ir.py``. À barème égal, le portage donne le même impôt
et la même tranche marginale que le R. Il s'en écarte sur quatre points :

1. **Barème du régime.** Le R lit ``tab_IR``, le barème des revenus 2020. Ici,
   le barème est celui du régime choisi.
2. **Plafonnement du quotient familial.** Le R ne l'applique pas : un foyer
   aisé avec enfants paie trop peu. Ici, il est appliqué, et la tranche
   marginale suit le plafonnement quand il joue.
3. **Rang des personnes à charge.** Le R fixe la part d'un enfant par son rang
   de saisie, pour toute la durée. Quand l'aîné quitte le foyer, le troisième
   garde sa part entière. Ici, le rang est compté chaque année parmi les
   personnes encore à charge, comme le fait l'administration fiscale.
4. **Âge limite.** Le R arrête la part d'un enfant à 20 ans, valeur codée en
   dur. Ici, la durée est saisie par l'utilisateur.

Les loyers d'une location nue sont imposés au micro-foncier
(``rental_income_regimes.micro_foncier`` du régime) : abattement forfaitaire,
puis barème et prélèvements sociaux. Le R ajoutait les loyers bruts au revenu
imposable, sans abattement ni prélèvements sociaux.

Limites déclarées (``KNOWN_GAPS``) : la décote et la déduction forfaitaire
pour frais professionnels ne sont pas dans le régime. Le revenu attendu est
donc le revenu imposable, après déductions. Le régime réel des revenus
fonciers n'est pas porté.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from investment_calculator.tax_regime import TaxRegime

logger = logging.getLogger(__name__)

__all__ = [
    "KNOWN_GAPS",
    "HouseholdShares",
    "household_shares",
    "income_tax_by_year",
    "marginal_rate",
    "rental_social_tax",
    "rental_taxable_income",
    "shares_by_year",
]

KNOWN_GAPS = [
    "La décote de l'impôt sur le revenu n'est pas dans le régime : l'impôt des "
    "foyers modestes est surestimé.",
    "La déduction forfaitaire pour frais professionnels n'est pas dans le régime : "
    "le revenu saisi doit être le revenu imposable, après déductions.",
    "Les loyers ne sont imposés qu'au micro-foncier : le régime réel (charges et "
    "intérêts déductibles, déficit foncier) n'est pas porté, et des loyers au-dessus "
    "du seuil du micro-foncier sont refusés.",
    "La part déductible de la CSG sur les loyers n'est pas retranchée du revenu "
    "imposable de l'année suivante : l'impôt est légèrement surestimé.",
]


@dataclass(frozen=True)
class HouseholdShares:
    """
    Parts du foyer pour une année.

    Attributes:
        total: nombre total de parts.
        dependents: parts dues aux personnes à charge, qui servent au
            plafonnement du quotient familial.
    """

    total: float
    dependents: float


def _quotient(regime: TaxRegime) -> dict[str, Any]:
    quotient = regime.document["income_tax"].get("household_quotient", {})
    if not quotient.get("enabled"):
        raise NotImplementedError(
            f"Le régime {regime.id} ne pratique pas le quotient familial : les parts "
            "n'ont pas de sens. Calculez l'impôt avec income_tax_due(revenu)."
        )
    return dict(quotient)


def household_shares(regime: TaxRegime, *, adults: int, dependents: int) -> HouseholdShares:
    """
    Parts d'un foyer de ``adults`` adultes (1 ou 2) et ``dependents`` personnes à charge.

    La part d'une personne à charge dépend de son rang
    (``shares_per_dependent``) ; la dernière valeur vaut pour les suivantes.

    Raises:
        ValueError: nombre d'adultes autre que 1 ou 2, ou de personnes à charge négatif.
        NotImplementedError: le régime ne pratique pas le quotient familial.
    """
    if adults not in (1, 2):
        raise ValueError(f"{adults} adulte(s) : un foyer fiscal en compte 1 ou 2.")
    if dependents < 0:
        raise ValueError(f"{dependents} personne(s) à charge : le nombre doit être positif.")
    quotient = _quotient(regime)
    base = float(quotient["shares_first_adult"])
    if adults == 2:
        base += float(quotient["shares_second_adult"])
    ranks = [float(s) for s in quotient["shares_per_dependent"]]
    extra = sum(ranks[min(k, len(ranks) - 1)] for k in range(dependents))
    return HouseholdShares(total=base + extra, dependents=extra)


def shares_by_year(
    regime: TaxRegime, *, adults: int, dependent_years: Sequence[int], horizon: int
) -> list[HouseholdShares]:
    """
    Parts du foyer pour les années 0 à ``horizon``.

    Args:
        dependent_years: pour chaque personne à charge, le nombre d'années
            pendant lesquelles elle le reste : elle compte les années 0 à
            ``n − 1``.
    """
    if any(n < 0 for n in dependent_years):
        raise ValueError(
            f"Durées à charge {list(dependent_years)} : chaque durée est un nombre "
            "d'années positif."
        )
    return [
        household_shares(
            regime, adults=adults, dependents=sum(1 for n in dependent_years if year < n)
        )
        for year in range(horizon + 1)
    ]


def income_tax_by_year(
    regime: TaxRegime, taxable_income: Sequence[float], shares: Sequence[HouseholdShares]
) -> np.ndarray:
    """Impôt sur le revenu de chaque année, plafonnement du quotient compris."""
    if len(taxable_income) != len(shares):
        raise ValueError(
            f"{len(taxable_income)} revenus pour {len(shares)} années de parts : "
            "donnez un revenu imposable par année."
        )
    return np.array([
        regime.income_tax_due(float(income), shares=s.total, dependent_shares=s.dependents)
        for income, s in zip(taxable_income, shares, strict=True)
    ])


def marginal_rate(regime: TaxRegime, taxable_income: float, shares: HouseholdShares) -> float:
    """
    Tranche marginale d'imposition du foyer.

    C'est le taux de la tranche où tombe le revenu par part. Quand le
    plafonnement du quotient joue, le revenu par part est calculé sur les seules
    parts de base, puisque c'est alors l'impôt sans les enfants qui varie.
    """
    _quotient(regime)
    capped = regime.income_tax_due(
        taxable_income, shares=shares.total, dependent_shares=shares.dependents
    )
    uncapped = regime.income_tax_due(taxable_income, shares=shares.total)
    divisor = shares.total - shares.dependents if capped > uncapped else shares.total
    per_share = taxable_income / divisor
    rate = 0.0
    for bracket in regime.document["income_tax"]["brackets"]:
        if per_share > float(bracket.get("lower", 0.0)):
            rate = float(bracket["rate"])
    return rate


def rental_taxable_income(
    regime: TaxRegime, collected_rents: Sequence[Sequence[float]]
) -> np.ndarray:
    """
    Revenu foncier imposable de chaque année, au micro-foncier.

    Args:
        collected_rents: pour chaque bien loué nu, les loyers encaissés de
            chaque année (toutes les séries ont la même longueur).

    Returns:
        Loyers encaissés après l'abattement forfaitaire, tous biens confondus.

    Raises:
        NotImplementedError: le régime ne décrit pas le micro-foncier, ou les
            loyers d'une année dépassent son seuil. Le régime réel n'est pas
            porté : réduisez les loyers saisis ou attendez son portage.
    """
    micro = regime.document.get("rental_income_regimes", {}).get("micro_foncier")
    if not micro:
        raise NotImplementedError(
            f"Le régime {regime.id} ne décrit pas le micro-foncier : les loyers ne peuvent "
            "pas être imposés. Ajoutez rental_income_regimes.micro_foncier au régime."
        )
    rents = np.asarray(collected_rents, dtype=float)
    if rents.size == 0:
        return np.zeros(0)
    if rents.ndim != 2:
        raise ValueError("Donnez une série de loyers par bien, toutes de même longueur.")
    tested = rents if micro["threshold_basis"] == "per_property" else rents.sum(axis=0)[None, :]
    years = sorted(set(np.flatnonzero((tested > float(micro["revenue_threshold"])).any(axis=0))))
    if years:
        raise NotImplementedError(
            f"Loyers au-dessus du seuil du micro-foncier ({micro['revenue_threshold']:,.0f} €) "
            f"aux années {[int(y) for y in years]} : seul le micro-foncier est porté, pas le "
            "régime réel. Réduisez les loyers saisis."
        )
    taxable: np.ndarray = rents.sum(axis=0) * (1 - float(micro["allowance_rate"]))
    return taxable


def rental_social_tax(regime: TaxRegime, taxable_rent: Sequence[float]) -> np.ndarray:
    """
    Prélèvements sociaux sur le revenu foncier imposable de chaque année.

    Raises:
        NotImplementedError: le régime n'applique pas ses prélèvements sociaux
            aux revenus fonciers (``applies_to`` sans ``rental_income``).
    """
    social = regime.document["social_contributions"]["investment_income"]
    if "rental_income" not in social.get("applies_to", []):
        raise NotImplementedError(
            f"Le régime {regime.id} ne dit pas si ses prélèvements sociaux frappent les "
            "loyers. S'ils les frappent, ajoutez rental_income à "
            "social_contributions.investment_income.applies_to."
        )
    tax: np.ndarray = np.asarray(taxable_rent, dtype=float) * regime.social_rate
    return tax
