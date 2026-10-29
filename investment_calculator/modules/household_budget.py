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

Limites déclarées (``KNOWN_GAPS``) : les dépenses ne suivent pas la
composition du foyer, car les unités de consommation du R ne sont pas
sourcées. Les pensions alimentaires ne sont pas portées.
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
    rental_social_tax,
    rental_taxable_income,
    shares_by_year,
)
from investment_calculator.modules.rental_property import RentalProperty, property_flows
from investment_calculator.tax_regime import TaxRegime

logger = logging.getLogger(__name__)

__all__ = ["KNOWN_GAPS", "Earner", "earner_income", "household_budget"]

KNOWN_GAPS = [
    "Les dépenses courantes ne suivent pas la composition du foyer : les unités de "
    "consommation (naissance, départ d'un enfant) ne sont pas encore sourcées.",
    "Les pensions alimentaires versées ou reçues ne sont pas portées.",
]


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
    """

    taxable_income: float
    annual_growth: float
    retirement_year: int | None = None
    replacement_rate: float | None = None

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


def earner_income(earner: Earner, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Revenus d'activité et pensions d'un adulte, années 0 à ``horizon``.

    La pension est fixée à la retraite : taux de remplacement × revenu
    d'activité qu'aurait eu l'adulte cette année-là, puis constante.
    """
    years = np.arange(horizon + 1)
    salary = earner.taxable_income * (1 + earner.annual_growth) ** years
    pension = np.zeros(horizon + 1)
    retire = earner.retirement_year
    if retire is not None and retire <= horizon:
        assert earner.replacement_rate is not None
        pension[retire:] = salary[retire] * earner.replacement_rate
        salary[retire:] = 0.0
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
    expenses_follow_income: bool,
    properties: Sequence[RentalProperty] = (),
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
        expenses_follow_income: les dépenses suivent les revenus d'activité et
            de pension (sinon elles restent constantes).
        properties: biens achetés à crédit pour être loués nus.

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
    shares = shares_by_year(
        regime, adults=len(earners), dependent_years=dependent_years, horizon=horizon
    )
    tax = income_tax_by_year(regime, taxable.tolist(), shares)
    schedule = loans_total(loans, horizon)
    payments = (schedule["interest"] + schedule["principal"]).to_numpy()
    rent_paid = np.full(horizon + 1, float(rent))

    # Les dépenses viennent de la situation déclarée, sans les biens à acheter.
    expenses_0 = taxable[0] - tax[0] - rent_paid[0] - payments[0] - current_savings
    if expenses_0 < 0:
        raise ValueError(
            f"Épargne de {current_savings:,.0f} € par an pour {taxable[0] - tax[0]:,.0f} € de "
            f"revenus après impôt, {rent_paid[0] + payments[0]:,.0f} € de loyer et "
            "d'annuités : les dépenses seraient négatives. Vérifiez l'épargne et les revenus."
        )
    if expenses_follow_income:
        if taxable[0] <= 0:
            raise ValueError(
                "Aucun revenu à l'année 0 : les dépenses ne peuvent pas suivre les revenus. "
                "Choisissez des dépenses constantes."
            )
        expenses = expenses_0 * taxable / taxable[0]
    else:
        expenses = np.full(horizon + 1, expenses_0)
    flows = [property_flows(p, horizon) for p in properties]
    zero = np.zeros(horizon + 1)
    rental = sum((f["collected_rent"].to_numpy() for f in flows), zero)
    charges = sum((f["charges"].to_numpy() for f in flows), zero)
    down = sum((f["down_payment"].to_numpy() for f in flows), zero)
    social = zero
    if flows:
        rental_taxable = rental_taxable_income(
            regime, [f["collected_rent"].tolist() for f in flows]
        )
        tax = income_tax_by_year(regime, (taxable + rental_taxable).tolist(), shares)
        social = rental_social_tax(regime, rental_taxable.tolist())
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
