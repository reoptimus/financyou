"""
Crédits en cours du foyer et taux d'endettement, année par année.

Un crédit en cours est décrit par son annuité, son taux et le nombre d'années
qui restent. On en tire, chaque année, la part d'intérêts, la part de capital
remboursé et le capital restant dû. Le taux d'endettement rapporte les charges
(loyer versé, annuités de crédit) aux revenus, les loyers perçus n'étant
comptés qu'en partie.

Aucune règle bancaire n'est écrite ici. Le taux d'endettement maximal et la
part des loyers perçus retenue par la banque sont saisis par l'utilisateur.

Équivalent R : ``fct_crd_flux.R`` (``Flux_crd``) et le bloc « taux_endt » de
``fct_chrono_flux.R``. La traduction fidèle est dans
``tests/reference_r/crd_flux.py``. Le portage donne les mêmes flux que le R, à
l'arrondi près. Il s'en écarte sur trois points :

1. **Pas d'arrondi.** Le R arrondit intérêts et capital à l'euro. Le capital
   remboursé cumulé s'écarte alors de quelques euros du capital restant dû, et
   une annuité non entière n'est plus payée exactement. Ici, les montants sont
   exacts.
2. **Crédit à taux zéro.** Le R rend des flux nuls pour un taux nul : le prêt
   disparaît des charges. Ici, l'annuité est remboursée en capital.
3. **Seuils saisis.** Le R code en dur le taux d'endettement maximal et la part
   des loyers perçus. Ici, ce sont des paramètres sans valeur par défaut.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

__all__ = ["Loan", "borrowing_capacity", "debt_ratio", "loan_schedule", "loans_total"]


@dataclass(frozen=True)
class Loan:
    """
    Crédit amortissable en cours.

    Attributes:
        name: libellé du crédit.
        annual_payment: annuité, en euros.
        rate: taux annuel du crédit (0,015 pour 1,5 %).
        years_left: nombre d'annuités restant à payer, la première l'année 0.
    """

    name: str
    annual_payment: float
    rate: float
    years_left: int

    def __post_init__(self) -> None:
        if not isinstance(self.years_left, int) or self.years_left < 0:
            raise ValueError(
                f"Crédit « {self.name} » : {self.years_left} années restantes. Donnez un "
                "nombre entier d'annuités, positif."
            )
        if not math.isfinite(self.annual_payment) or self.annual_payment < 0:
            raise ValueError(
                f"Crédit « {self.name} » : annuité invalide ({self.annual_payment}). "
                "Saisissez un montant positif."
            )
        if not math.isfinite(self.rate) or self.rate < 0:
            raise ValueError(
                f"Crédit « {self.name} » : taux invalide ({self.rate}). Saisissez un taux "
                "annuel positif, 0,015 pour 1,5 %."
            )


def loan_schedule(loan: Loan, horizon: int) -> pd.DataFrame:
    """
    Tableau d'amortissement du crédit, années 0 à ``horizon``.

    Returns:
        Colonnes ``outstanding`` (capital restant dû en début d'année),
        ``interest`` et ``principal`` (part de l'annuité de l'année).
    """
    if horizon < 1:
        raise ValueError(f"Horizon de {horizon} an(s) : il faut au moins un an.")
    years = np.arange(horizon + 1)
    remaining = np.clip(loan.years_left - years, 0, None).astype(float)
    if loan.rate == 0:
        outstanding = loan.annual_payment * remaining
    else:
        outstanding = loan.annual_payment * (1 - (1 + loan.rate) ** -remaining) / loan.rate
    paying = remaining > 0
    interest = np.where(paying, loan.rate * outstanding, 0.0)
    principal = np.where(paying, loan.annual_payment - interest, 0.0)
    if loan.years_left > horizon:
        logger.info(
            "Crédit « %s » : %d annuité(s) après l'horizon de %d ans, hors du tableau.",
            loan.name, loan.years_left - horizon - 1, horizon,
        )
    return pd.DataFrame(
        {"outstanding": outstanding, "interest": interest, "principal": principal},
        index=pd.RangeIndex(horizon + 1, name="year"),
    )


def loans_total(loans: Sequence[Loan], horizon: int) -> pd.DataFrame:
    """Somme des tableaux d'amortissement de plusieurs crédits (zéro sans crédit)."""
    total = pd.DataFrame(
        0.0, index=pd.RangeIndex(horizon + 1, name="year"),
        columns=["outstanding", "interest", "principal"],
    )
    for loan in loans:
        total += loan_schedule(loan, horizon)
    return total


def _check_share(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} = {value} : saisissez une part entre 0 et 1.")


def debt_ratio(
    income: Sequence[float] | np.ndarray,
    *,
    rental_income: Sequence[float] | np.ndarray,
    rental_income_weight: float,
    rent_paid: Sequence[float] | np.ndarray,
    loan_payments: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """
    Taux d'endettement de chaque année : charges / revenus retenus.

    Args:
        income: revenus d'activité et pensions, par année.
        rental_income: loyers perçus, par année.
        rental_income_weight: part des loyers perçus que la banque retient,
            saisie par l'utilisateur.
        rent_paid: loyer versé, par année.
        loan_payments: annuités de crédit (intérêts et capital), par année.

    Raises:
        ValueError: longueurs différentes, part hors de [0, 1], ou année sans
            revenu retenu : le taux n'y est pas défini.
    """
    _check_share("rental_income_weight", rental_income_weight)
    arrays = [np.asarray(x, dtype=float) for x in (income, rental_income, rent_paid, loan_payments)]
    if len({a.shape for a in arrays}) != 1:
        raise ValueError(
            "Revenus, loyers et annuités doivent couvrir les mêmes années : "
            f"longueurs {[a.size for a in arrays]}."
        )
    earned, rents, rent, payments = arrays
    retained = earned + rental_income_weight * rents
    empty = np.flatnonzero(retained <= 0).tolist()
    if empty:
        raise ValueError(
            f"Aucun revenu retenu aux années {empty} : le taux d'endettement n'y est pas "
            "défini. Vérifiez les revenus saisis."
        )
    return (rent + payments) / retained


def borrowing_capacity(
    income: Sequence[float] | np.ndarray,
    *,
    rental_income: Sequence[float] | np.ndarray,
    rental_income_weight: float,
    rent_paid: Sequence[float] | np.ndarray,
    loan_payments: Sequence[float] | np.ndarray,
    max_ratio: float,
) -> np.ndarray:
    """
    Annuité supplémentaire possible chaque année sous ``max_ratio``, saisi par
    l'utilisateur. Une valeur négative signale un taux déjà dépassé.
    """
    _check_share("max_ratio", max_ratio)
    ratio = debt_ratio(
        income, rental_income=rental_income, rental_income_weight=rental_income_weight,
        rent_paid=rent_paid, loan_payments=loan_payments,
    )
    retained = np.asarray(income, dtype=float) + rental_income_weight * np.asarray(
        rental_income, dtype=float
    )
    return (max_ratio - ratio) * retained
