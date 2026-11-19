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
    "child_tax_advantages",
    "household_shares",
    "income_tax_by_year",
    "marginal_rate",
    "real_regime_rental_income",
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
    regime: TaxRegime, *, adults: int, dependent_years: Sequence[int], horizon: int,
    dependent_from: Sequence[int] | None = None,
) -> list[HouseholdShares]:
    """
    Parts du foyer pour les années 0 à ``horizon``.

    Args:
        dependent_years: pour chaque personne à charge, le nombre d'années
            pendant lesquelles elle le reste : elle compte les années
            ``d`` à ``d + n − 1``.
        dependent_from: pour chaque personne à charge, l'année ``d`` où elle
            le devient (naissance ou adoption à venir) ; 0 pour toutes si omis.
    """
    starts = [0] * len(dependent_years) if dependent_from is None else list(dependent_from)
    if len(starts) != len(dependent_years):
        raise ValueError(
            f"{len(starts)} années d'arrivée pour {len(dependent_years)} personnes à charge : "
            "donnez une année d'arrivée par personne."
        )
    if any(n < 0 for n in dependent_years) or any(d < 0 for d in starts):
        raise ValueError(
            f"Durées à charge {list(dependent_years)}, arrivées {starts} : chaque durée et "
            "chaque année d'arrivée est un nombre d'années positif."
        )
    return [
        household_shares(
            regime, adults=adults,
            dependents=sum(1 for d, n in zip(starts, dependent_years, strict=True)
                           if d <= year < d + n),
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
            loyers d'une année dépassent son seuil : choisissez alors le régime
            réel (:func:`real_regime_rental_income`).
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
            f"aux années {[int(y) for y in years]} : le micro-foncier ne s'applique pas. "
            "Choisissez le régime réel."
        )
    taxable: np.ndarray = rents.sum(axis=0) * (1 - float(micro["allowance_rate"]))
    return taxable


def child_tax_advantages(
    regime: TaxRegime, child_ages: Sequence[int], *, end_age: int | None, horizon: int,
    childcare_cost: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Avantages fiscaux liés à l'âge des enfants à charge, années 0 à ``horizon``
    (``income_tax.child_tax_advantages`` du régime).

    Args:
        child_ages: âge de chaque enfant aujourd'hui ; un âge négatif est une
            arrivée à venir. Un enfant est à charge de 0 an à ``end_age``.
        end_age: âge de fin de charge, saisi par l'utilisateur.
        childcare_cost: frais de garde annuels de chaque enfant d'âge à
            ouvrir le crédit, saisis par l'utilisateur (0 si aucun).

    Returns:
        ``(reduction, credit)`` : réductions d'impôt, qui ne peuvent que
        l'annuler, et crédits d'impôt, restitués au-delà de l'impôt dû, selon
        le champ ``refundable`` du régime (en France : frais de scolarisation
        en réduction, frais de garde en crédit).

    Raises:
        NotImplementedError: le régime ne décrit pas ces avantages alors que
            des enfants sont saisis.
    """
    reduction = np.zeros(horizon + 1)
    credit = np.zeros(horizon + 1)
    if not child_ages:
        return reduction, credit
    if end_age is None:
        raise ValueError(
            "Enfants saisis sans âge de fin de charge : indiquez à quel âge ils "
            "cesseront d'être à votre charge."
        )
    advantages = regime.document["income_tax"].get("child_tax_advantages")
    if advantages is None:
        raise NotImplementedError(
            f"Le régime {regime.id} ne décrit pas les avantages fiscaux liés à l'âge des "
            "enfants. Ajoutez income_tax.child_tax_advantages au régime."
        )
    care = advantages.get("childcare_credit")
    stages = sorted(advantages.get("schooling_reduction", {}).get("stages", []),
                    key=lambda stage: int(stage["from_age"]))
    for age_now in child_ages:
        for year in range(horizon + 1):
            age = age_now + year
            if not 0 <= age < end_age:
                continue
            if care and age < int(care["age_below"]):
                cost = min(float(childcare_cost), float(care["expense_cap_per_child"]))
                target = credit if care["refundable"] else reduction
                target[year] += cost * float(care["rate"])
            reached = [stage for stage in stages if age >= int(stage["from_age"])]
            if reached:
                school = advantages["schooling_reduction"]
                target = credit if school["refundable"] else reduction
                target[year] += float(reached[-1]["amount"])
    return reduction, credit


def real_regime_rental_income(
    regime: TaxRegime, rents: Sequence[float], charges: Sequence[float],
    interest: Sequence[float],
) -> tuple[np.ndarray, np.ndarray]:
    """
    Revenu foncier au régime réel, tous biens loués nus confondus, année par
    année (CGI art. 28, 31 et 156-I-3°).

    Le revenu net est loyers − charges − intérêts d'emprunt. Négatif, c'est
    un déficit foncier :

    - la part due aux intérêts ne s'impute que sur les revenus fonciers des
      années suivantes ;
    - le reste s'impute sur le revenu global, dans la limite de
      ``real_regime.deficit_cap_against_global_income`` par an ; l'excédent
      se reporte sur les revenus fonciers ;
    - un déficit reporté s'impute sur les revenus fonciers des
      ``deficit_carry_forward_years`` années suivantes, le plus ancien
      d'abord, puis il est perdu.

    Args:
        rents: loyers encaissés de chaque année.
        charges: charges déductibles hors intérêts (taxe foncière, assurance,
            gestion, entretien), saisies par l'utilisateur.
        interest: intérêts d'emprunt de chaque année.

    Returns:
        ``(income_tax_base, social_base)`` : ce qui s'ajoute au revenu
        imposable au barème (négatif l'année d'un déficit imputé sur le revenu
        global), et l'assiette des prélèvements sociaux (revenu foncier net
        positif, après les déficits reportés).

    Raises:
        NotImplementedError: le régime ne décrit pas le régime réel.
    """
    real = regime.document.get("rental_income_regimes", {}).get("real_regime")
    if not real:
        raise NotImplementedError(
            f"Le régime {regime.id} ne décrit pas le régime réel des revenus fonciers. "
            "Ajoutez rental_income_regimes.real_regime au régime, ou choisissez le "
            "micro-foncier."
        )
    cap = float(real["deficit_cap_against_global_income"])
    keep = int(real["deficit_carry_forward_years"])
    r, c, i = (np.asarray(x, dtype=float) for x in (rents, charges, interest))
    if not r.shape == c.shape == i.shape:
        raise ValueError("Donnez loyers, charges et intérêts sur les mêmes années.")
    base = np.zeros(r.size)
    social = np.zeros(r.size)
    carried: list[list[float]] = []  # [montant restant, année de création]
    for year in range(r.size):
        carried = [d for d in carried if year - d[1] <= keep and d[0] > 0]
        net = r[year] - c[year] - i[year]
        if net >= 0:
            for deficit in carried:
                used = min(deficit[0], net)
                deficit[0] -= used
                net -= used
            base[year] = social[year] = net
            continue
        interest_part = max(i[year] - r[year], 0.0)
        other_part = -net - interest_part
        to_global = min(other_part, cap)
        base[year] = -to_global
        if interest_part + other_part - to_global > 0:
            carried.append([interest_part + other_part - to_global, float(year)])
    return base, social


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
