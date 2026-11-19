"""
Budget du foyer année par année : revenus, retraite, impôt, charges, dépenses
et épargne libre.

L'épargne libre d'une année est ce qui reste des revenus après l'impôt sur le
revenu, le loyer, les annuités de crédit et les dépenses courantes. C'est elle
qui alimente la courbe de capital (:mod:`household_cash_flow`).

Toutes les hypothèses sont saisies par l'utilisateur : évolution de chaque
salaire, année de départ à la retraite, taux de remplacement, épargne actuelle.
Les dépenses courantes ne sont pas demandées : comme dans le R, elles se
déduisent de l'épargne actuelle. Ce sont les revenus de l'année 0, moins
l'impôt, le loyer, les annuités et l'épargne déclarée. Elles restent ensuite
constantes, ou suivent les revenus d'activité et de pension si l'utilisateur
le choisit.

Équivalent R : les blocs revenus, dépenses et « Epargne libre hors projets »
de ``fct_chrono_flux.R``. La traduction fidèle est dans
``tests/reference_r/chrono_flux.py``. Pour un foyer sans enfant, le portage
donne les mêmes revenus, dépenses et épargne libre que le R. Il s'en écarte
sur deux points :

1. **Taux de remplacement saisi.** Le R le lit dans ``tab_retraite`` (par
   métier, avec une pente et un coefficient selon l'évolution du salaire). Ici,
   l'utilisateur saisit directement le taux de remplacement de chaque adulte.
2. **Impôt avec plafonnement.** L'impôt est celui de :mod:`household_tax`
   (plafonnement du quotient familial compris, absent du R).

Les biens loués nus (:mod:`rental_property`) ajoutent leurs loyers, leurs
charges, leurs annuités, leur apport et leur impôt (barème et prélèvements
sociaux sur le revenu foncier). Les dépenses courantes restent celles de la
situation actuelle, sans ces biens.

Les dépenses suivent la composition du foyer par les unités de consommation
(:mod:`consumption_units`), comme dans le R : un enfant qui naît, passe
14 ans ou quitte la charge du foyer les fait varier. Une naissance ou une
adoption à venir (:class:`FutureChild`) ajoute aussi une part fiscale pendant
ses années à charge.

Un temps partiel ou un congé (:class:`WorkChange`, projets « travail » des
prototypes R) réduit le salaire d'un adulte pendant une période, à la part
travaillée saisie par l'utilisateur. Les dépenses courantes restent déduites
de la situation déclarée, sans ces changements.

Limites déclarées (``KNOWN_GAPS``) : les prestations familiales ne sont pas
comptées. Les pensions alimentaires ne sont pas portées. Un temps partiel ou
un congé ne change ni la pension de retraite ni les allocations.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from investment_calculator.modules.household_loans import Loan, loans_total
from investment_calculator.modules.household_tax import (
    income_tax_by_year,
    real_regime_rental_income,
    rental_social_tax,
    rental_taxable_income,
    shares_by_year,
)
from investment_calculator.modules.rental_property import RentalProperty, property_flows
from investment_calculator.tax_regime import TaxRegime

logger = logging.getLogger(__name__)

__all__ = ["KNOWN_GAPS", "Earner", "FutureChild", "WorkChange", "earner_income",
           "household_budget"]

KNOWN_GAPS = [
    "Les prestations familiales (allocations, aides à la garde) ne sont pas comptées.",
    "Les pensions alimentaires versées ou reçues ne sont pas portées.",
    "Un temps partiel ou un congé réduit le salaire seulement : la pension de retraite "
    "reste calculée sur un salaire à temps plein, et les allocations (congé parental, "
    "chômage) ne sont pas comptées.",
]


@dataclass(frozen=True)
class WorkChange:
    """
    Temps partiel ou congé d'un adulte.

    Attributes:
        start_year: première année concernée (0 = cette année).
        years: nombre d'années concernées.
        worked_share: part du salaire perçue, saisie par l'utilisateur (0,8 pour
            un temps partiel à 80 %, 0 pour un congé sans solde).
    """

    start_year: int
    years: int
    worked_share: float

    def __post_init__(self) -> None:
        if self.start_year < 0 or self.years < 1:
            raise ValueError(
                f"Temps partiel ou congé à l'année {self.start_year} sur {self.years} an(s) : "
                "donnez une année à venir (0 = cette année) et au moins un an."
            )
        if not math.isfinite(self.worked_share) or not 0 <= self.worked_share <= 1:
            raise ValueError(
                f"Part travaillée de {self.worked_share} : saisissez une part entre 0 "
                "(congé sans solde) et 1 (temps plein), 0,8 pour 80 %."
            )


@dataclass(frozen=True)
class FutureChild:
    """
    Naissance ou adoption à venir (« agrandir la famille » des prototypes R).

    Son coût ne se saisit pas : il vient des unités de consommation du foyer
    (``consumption_units`` de :func:`household_budget`), qui suivent son âge.

    Attributes:
        arrival_year: année de l'arrivée, 1 au plus tôt ; un enfant déjà né se
            saisit par son âge.
        dependent_years: nombre d'années à charge, à partir de l'arrivée.
    """

    arrival_year: int
    dependent_years: int

    def __post_init__(self) -> None:
        if self.arrival_year < 1 or self.dependent_years < 1:
            raise ValueError(
                f"Enfant à venir à l'année {self.arrival_year}, à charge {self.dependent_years} "
                "an(s) : donnez une arrivée dans un an au moins (un enfant déjà né se saisit "
                "par son âge) et au moins un an à charge."
            )


@dataclass(frozen=True)
class Earner:
    """
    Un adulte du foyer et ses revenus.

    Attributes:
        taxable_income: revenu imposable annuel d'aujourd'hui, en euros.
        annual_growth: évolution annuelle de ce revenu (0,01 pour 1 %).
        retirement_year: année du départ à la retraite (0 = cette année), ou
            ``None`` s'il n'a pas lieu avant l'horizon.
        replacement_rate: pension / dernier revenu d'activité, saisi par
            l'utilisateur. Requis si ``retirement_year`` est donné.
        work_changes: temps partiels et congés à venir.
    """

    taxable_income: float
    annual_growth: float
    retirement_year: int | None = None
    replacement_rate: float | None = None
    work_changes: tuple[WorkChange, ...] = ()

    def __post_init__(self) -> None:
        if not math.isfinite(self.taxable_income) or self.taxable_income < 0:
            raise ValueError(
                f"Revenu imposable invalide ({self.taxable_income}) : saisissez un montant "
                "positif."
            )
        if not math.isfinite(self.annual_growth) or self.annual_growth <= -1:
            raise ValueError(
                f"Évolution annuelle invalide ({self.annual_growth}) : saisissez un taux "
                "supérieur à −100 %, 0,01 pour 1 %."
            )
        if self.retirement_year is not None:
            if self.retirement_year < 0:
                raise ValueError(
                    f"Retraite à l'année {self.retirement_year} : donnez une année à venir "
                    "(0 = cette année)."
                )
            if self.replacement_rate is None or not 0 <= self.replacement_rate:
                raise ValueError(
                    "Départ à la retraite sans taux de remplacement : saisissez la pension "
                    "attendue en part du dernier revenu (0,6 pour 60 %)."
                )


def earner_income(
    earner: Earner, horizon: int, *, with_changes: bool = True
) -> tuple[np.ndarray, np.ndarray]:
    """
    Revenus d'activité et pensions d'un adulte, années 0 à ``horizon``.

    La pension est fixée à la retraite : taux de remplacement × revenu
    d'activité qu'aurait eu l'adulte cette année-là à temps plein, puis
    constante. Avec ``with_changes``, le salaire de chaque année de temps
    partiel ou de congé est multiplié par la part travaillée.
    """
    years = np.arange(horizon + 1)
    salary = earner.taxable_income * (1 + earner.annual_growth) ** years
    pension = np.zeros(horizon + 1)
    retire = earner.retirement_year
    if retire is not None and retire <= horizon:
        assert earner.replacement_rate is not None
        pension[retire:] = salary[retire] * earner.replacement_rate
        salary[retire:] = 0.0
    if with_changes:
        for change in earner.work_changes:
            salary[change.start_year:change.start_year + change.years] *= change.worked_share
    return salary, pension


def household_budget(
    regime: TaxRegime,
    earners: Sequence[Earner],
    *,
    horizon: int,
    current_savings: float,
    rent: float,
    loans: Sequence[Loan] = (),
    dependent_years: Sequence[int] = (),
    future_children: Sequence[FutureChild] = (),
    consumption_units: Sequence[float] | None = None,
    expenses_follow_income: bool,
    properties: Sequence[RentalProperty] = (),
    rental_regime: str = "micro_foncier",
) -> pd.DataFrame:
    """
    Budget du foyer, une ligne par année de 0 à ``horizon``.

    Args:
        regime: régime fiscal (barème, parts).
        earners: un ou deux adultes.
        current_savings: épargne de l'année 0, en euros par an : c'est elle qui
            fixe les dépenses courantes.
        rent: loyer annuel versé, constant.
        loans: crédits en cours.
        dependent_years: pour chaque personne à charge, nombre d'années à charge.
        future_children: naissances ou adoptions à venir : une part fiscale de
            plus pendant leurs années à charge.
        consumption_units: unités de consommation du foyer, années 0 à
            ``horizon`` (:func:`consumption_units.household_units`) ; les
            dépenses de l'année 0 sont ramenées à une unité, puis multipliées
            par les unités de chaque année. Constantes si omises.
        expenses_follow_income: les dépenses suivent les revenus d'activité et
            de pension (sinon elles restent constantes).
        properties: biens achetés à crédit pour être loués nus.
        rental_regime: imposition de leurs loyers, ``"micro_foncier"``
            (:func:`household_tax.rental_taxable_income`) ou ``"real_regime"``
            (:func:`household_tax.real_regime_rental_income`, déficit foncier
            compris), au choix de l'utilisateur.

    Returns:
        Colonnes ``salaries``, ``pensions``, ``income_tax`` (loyers compris),
        ``rent``, ``loan_payments`` (biens loués compris), ``expenses``,
        ``rental_income`` (loyers encaissés), ``property_charges``,
        ``rental_social_tax``, ``down_payments`` et ``free_savings``.

    Raises:
        ValueError: nombre d'adultes autre que 1 ou 2, ou épargne actuelle
            supérieure à ce qui reste des revenus (dépenses négatives).
    """
    if len(earners) not in (1, 2):
        raise ValueError(f"{len(earners)} adulte(s) : un foyer fiscal en compte 1 ou 2.")
    if horizon < 1:
        raise ValueError(f"Horizon de {horizon} an(s) : il faut au moins un an.")
    incomes = [earner_income(e, horizon) for e in earners]
    salaries = sum(s for s, _ in incomes)
    pensions = sum(p for _, p in incomes)
    taxable = np.asarray(salaries + pensions, dtype=float)
    # Situation déclarée, sans temps partiel ni congé : elle fixe les dépenses.
    declared = [earner_income(e, horizon, with_changes=False) for e in earners]
    declared_taxable = np.asarray(sum(s + p for s, p in declared), dtype=float)
    shares = shares_by_year(
        regime, adults=len(earners),
        dependent_years=[*dependent_years, *(c.dependent_years for c in future_children)],
        dependent_from=[0] * len(dependent_years) + [c.arrival_year for c in future_children],
        horizon=horizon,
    )
    tax = income_tax_by_year(regime, taxable.tolist(), shares)
    schedule = loans_total(loans, horizon)
    payments = (schedule["interest"] + schedule["principal"]).to_numpy()
    rent_paid = np.full(horizon + 1, float(rent))

    # Les dépenses viennent de la situation déclarée, sans les biens à acheter,
    # les temps partiels et congés, ni les enfants à venir.
    declared_shares = shares_by_year(
        regime, adults=len(earners), dependent_years=dependent_years, horizon=0
    )
    declared_tax_0 = income_tax_by_year(regime, [float(declared_taxable[0])], declared_shares)[0]
    expenses_0 = (declared_taxable[0] - declared_tax_0 - rent_paid[0] - payments[0]
                  - current_savings)
    if expenses_0 < 0:
        raise ValueError(
            f"Épargne de {current_savings:,.0f} € par an pour "
            f"{declared_taxable[0] - declared_tax_0:,.0f} € de "
            f"revenus après impôt, {rent_paid[0] + payments[0]:,.0f} € de loyer et "
            "d'annuités : les dépenses seraient négatives. Vérifiez l'épargne et les revenus."
        )
    if expenses_follow_income:
        if declared_taxable[0] <= 0:
            raise ValueError(
                "Aucun revenu à l'année 0 : les dépenses ne peuvent pas suivre les revenus. "
                "Choisissez des dépenses constantes."
            )
        expenses = expenses_0 * taxable / declared_taxable[0]
    else:
        expenses = np.full(horizon + 1, expenses_0)
    if consumption_units is not None:
        units = np.asarray(consumption_units, dtype=float)
        if units.shape != (horizon + 1,) or not (units > 0).all():
            raise ValueError(
                f"{units.size} unités de consommation pour {horizon + 1} années : donnez "
                "une valeur positive par année, de 0 à l'horizon."
            )
        expenses = expenses * units / units[0]
    flows = [property_flows(p, horizon) for p in properties]
    zero = np.zeros(horizon + 1)
    rental = sum((f["collected_rent"].to_numpy() for f in flows), zero)
    charges = sum((f["charges"].to_numpy() for f in flows), zero)
    down = sum((f["down_payment"].to_numpy() for f in flows), zero)
    social = zero
    if flows:
        if rental_regime == "micro_foncier":
            rental_taxable = rental_taxable_income(
                regime, [f["collected_rent"].tolist() for f in flows]
            )
            rental_social_base = rental_taxable
        elif rental_regime == "real_regime":
            interest = sum((f["interest"].to_numpy() for f in flows), zero)
            rental_taxable, rental_social_base = real_regime_rental_income(
                regime, rental.tolist(), charges.tolist(), interest.tolist()
            )
        else:
            raise ValueError(
                f"Régime des loyers « {rental_regime} » inconnu : choisissez "
                "micro_foncier ou real_regime."
            )
        # Un déficit foncier ne rend pas le revenu imposable négatif.
        base = np.maximum(taxable + rental_taxable, 0.0)
        tax = income_tax_by_year(regime, base.tolist(), shares)
        social = rental_social_tax(regime, rental_social_base.tolist())
        payments = payments + sum(
            (f["interest"].to_numpy() + f["principal"].to_numpy() for f in flows), zero
        )
    free = taxable - tax - rent_paid - payments - expenses + rental - charges - social - down
    if (free < 0).any():
        logger.warning(
            "Épargne libre négative aux années %s : le foyer puise dans son capital.",
            np.flatnonzero(free < 0).tolist(),
        )
    return pd.DataFrame(
        {
            "salaries": salaries, "pensions": pensions, "income_tax": tax,
            "rent": rent_paid, "loan_payments": payments, "expenses": expenses,
            "rental_income": rental, "property_charges": charges,
            "rental_social_tax": social, "down_payments": down, "free_savings": free,
        },
        index=pd.RangeIndex(horizon + 1, name="year"),
    )
