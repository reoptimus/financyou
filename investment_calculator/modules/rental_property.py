"""
Bien acheté à crédit pour être loué nu : apport, annuités, loyers et charges,
année par année.

L'utilisateur saisit tout : le prix, l'apport, le taux et la durée du crédit,
le rendement locatif brut, la part du loyer réellement encaissée, les charges
du propriétaire, l'évolution du loyer et l'année d'achat. Aucune hypothèse de
marché n'a de valeur par défaut.

L'année d'achat, l'apport sort de l'épargne et le crédit commence : sa
première annuité est payée cette année-là. Les loyers sont encaissés dès
cette année et suivent l'évolution saisie, comme les charges. Ce module ne
calcule que les flux du bien : leur imposition et leur entrée dans le budget du
foyer viennent à l'étape suivante.

Équivalent R : ``fct_recalcul_revenu.R`` (loyer d'un bien loué), le calcul de
l'emprunt de ``fct_discret_optim.R`` et la branche « location » de
``modif_chrono_flux_plc.R``. La traduction fidèle est dans
``tests/reference_r/rental.py``. Avec un rendement et une part encaissée
égaux à ceux du R, sans charges ni évolution du loyer, le portage donne les
mêmes loyers et le même crédit. Il s'en écarte sur trois points :

1. **Hypothèses saisies.** Le R code en dur le rendement (4 % pour une
   location, 2,5 % pour un Pinel) et la part retenue du loyer (85 %). Ici,
   ce sont des paramètres sans valeur par défaut.
2. **Achat saisi.** Le R choisit l'année d'achat, l'apport et l'annuité à
   partir de l'optimum de Markowitz (``optim_tang``), avec un apport minimal
   de 10 % et un prix minimal de 200 000 € codés en dur. Ici, l'utilisateur
   décrit l'achat qu'il envisage.
3. **Charges du propriétaire.** Le R n'en compte aucune. Ici, elles sont
   saisies.

Limites déclarées (``KNOWN_GAPS``).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from investment_calculator.modules.household_loans import Loan, loan_schedule

logger = logging.getLogger(__name__)

__all__ = ["KNOWN_GAPS", "RentalProperty", "loan_annuity", "property_flows"]

KNOWN_GAPS = [
    "Les loyers ne sont pas encore imposés ni ajoutés au budget du foyer : ce module "
    "ne donne que les flux du bien.",
    "La valeur du bien n'entre pas dans le patrimoine : l'apport et le capital "
    "remboursé sortent de l'épargne sans contrepartie. La revente et la plus-value "
    "immobilière ne sont pas encore portées.",
    "Les réductions d'impôt (Pinel, Malraux, Denormandie) ne sont pas portées : "
    "aucun millésime validé ne les décrit.",
    "La location meublée (LMNP) n'est pas portée : seule la location nue l'est.",
    "L'achat de la résidence principale (fin du loyer versé) n'est pas encore porté.",
]


@dataclass(frozen=True)
class RentalProperty:
    """
    Bien loué nu, acheté à crédit.

    Attributes:
        name: libellé du bien.
        price: coût total de l'achat (prix, frais de notaire et d'agence), en euros.
        down_payment: apport, en euros ; le reste est emprunté.
        loan_rate: taux annuel du crédit (0,035 pour 3,5 %).
        loan_years: durée du crédit, en années.
        gross_yield: loyer annuel hors charges / ``price`` (0,04 pour 4 %).
        collected_share: part du loyer réellement encaissée, après vacance et
            impayés (0,9 pour 90 %). C'est l'assiette de l'impôt.
        annual_charges: charges du propriétaire de l'année d'achat (taxe
            foncière, copropriété non récupérable, assurance), en euros.
        rent_growth: évolution annuelle du loyer et des charges (0,015 pour 1,5 %).
        purchase_year: année de l'achat (0 = cette année).
    """

    name: str
    price: float
    down_payment: float
    loan_rate: float
    loan_years: int
    gross_yield: float
    collected_share: float
    annual_charges: float
    rent_growth: float
    purchase_year: int

    def __post_init__(self) -> None:
        def fail(what: str, fix: str) -> None:
            raise ValueError(f"Bien « {self.name} » : {what}. {fix}")

        for field, value in (("prix", self.price), ("apport", self.down_payment),
                             ("charges", self.annual_charges)):
            if not math.isfinite(value) or value < 0:
                fail(f"{field} invalide ({value})", "Saisissez un montant positif.")
        if self.price <= 0:
            fail("prix nul", "Saisissez le coût total de l'achat.")
        if self.down_payment > self.price:
            fail(f"apport de {self.down_payment:,.0f} € pour un prix de {self.price:,.0f} €",
                 "L'apport ne peut pas dépasser le prix.")
        if not isinstance(self.loan_years, int) or self.loan_years < 0:
            fail(f"durée de crédit de {self.loan_years} an(s)",
                 "Donnez un nombre entier d'années, positif.")
        if self.down_payment < self.price and self.loan_years == 0:
            fail("emprunt sans durée", "Saisissez la durée du crédit, ou un apport égal au prix.")
        if not math.isfinite(self.loan_rate) or self.loan_rate < 0:
            fail(f"taux de crédit invalide ({self.loan_rate})",
                 "Saisissez un taux annuel positif, 0,035 pour 3,5 %.")
        if not math.isfinite(self.gross_yield) or self.gross_yield < 0:
            fail(f"rendement locatif invalide ({self.gross_yield})",
                 "Saisissez un rendement positif, 0,04 pour 4 %.")
        if not 0.0 <= self.collected_share <= 1.0:
            fail(f"part encaissée de {self.collected_share}", "Saisissez une part entre 0 et 1.")
        if not math.isfinite(self.rent_growth) or self.rent_growth <= -1:
            fail(f"évolution du loyer invalide ({self.rent_growth})",
                 "Saisissez un taux supérieur à −100 %, 0,015 pour 1,5 %.")
        if not isinstance(self.purchase_year, int) or self.purchase_year < 0:
            fail(f"achat à l'année {self.purchase_year}",
                 "Donnez une année à venir (0 = cette année).")

    @property
    def borrowed(self) -> float:
        """Montant emprunté, en euros."""
        return self.price - self.down_payment


def loan_annuity(amount: float, rate: float, years: int) -> float:
    """
    Annuité constante qui rembourse ``amount`` en ``years`` ans au taux ``rate``.

    C'est l'inverse du calcul de l'emprunt de ``fct_discret_optim.R`` :
    emprunt = annuité × (1 − (1 + taux)^−n) / taux.
    """
    if amount == 0:
        return 0.0
    if years <= 0:
        raise ValueError(f"Emprunt de {amount:,.0f} € sur {years} an(s) : donnez une durée.")
    if rate == 0:
        return amount / years
    return amount * rate / (1 - (1 + rate) ** -years)


def property_flows(prop: RentalProperty, horizon: int) -> pd.DataFrame:
    """
    Flux du bien, années 0 à ``horizon``.

    Returns:
        Colonnes ``down_payment`` (apport, l'année d'achat), ``collected_rent``
        (loyers encaissés), ``charges``, ``interest``, ``principal`` et
        ``outstanding`` (capital restant dû en début d'année). Tous positifs.
    """
    if horizon < 1:
        raise ValueError(f"Horizon de {horizon} an(s) : il faut au moins un an.")
    index = pd.RangeIndex(horizon + 1, name="year")
    flows = pd.DataFrame(0.0, index=index, columns=[
        "down_payment", "collected_rent", "charges", "interest", "principal", "outstanding",
    ])
    start = prop.purchase_year
    if start > horizon:
        logger.info(
            "Bien « %s » acheté après l'horizon de %d ans : aucun flux.", prop.name, horizon
        )
        return flows
    owned = np.arange(horizon + 1 - start, dtype=float)
    growth = (1 + prop.rent_growth) ** owned
    flows.loc[start, "down_payment"] = prop.down_payment
    flows.loc[start:, "collected_rent"] = (
        prop.price * prop.gross_yield * prop.collected_share * growth
    )
    flows.loc[start:, "charges"] = prop.annual_charges * growth
    if prop.borrowed > 0:
        annuity = loan_annuity(prop.borrowed, prop.loan_rate, prop.loan_years)
        loan = Loan(prop.name, annuity, prop.loan_rate, prop.loan_years)
        schedule = loan_schedule(loan, max(horizon - start, 1)).iloc[: horizon + 1 - start]
        for column in ("interest", "principal", "outstanding"):
            flows.loc[start:, column] = schedule[column].to_numpy()
    return flows
