"""
Projets du foyer et courbe de capital disponible.

Un projet est une dépense datée : un versement initial l'année de début, des
versements annuels pendant une durée, puis un montant de sortie (une revente
s'écrit en négatif). Avec l'épargne de départ et l'épargne de chaque année, les
projets donnent le capital disponible année par année : c'est la courbe que
l'étape suivante découpe en tranches, chacune placée à son propre horizon.

Convention de temps : l'année 0 est aujourd'hui, l'année ``t`` la fin de la
``t``-ième année. Les flux de projets sont des sorties d'argent, comptées en
positif.

Équivalent R :

- ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/Exp_proj_hist.R``
  pour les flux d'un projet ;
- ``legacy/R_Financyou/MOCA/FCT/Exp_finance_hist.R`` pour la somme cumulée.

La traduction fidèle est dans ``tests/reference_r/exp_finance.py``. Le portage
s'en écarte sur trois points, où le R donne un chiffre faux :

1. **Projet qui dépasse l'horizon.** Le R tronque la durée à l'horizon et
   place la sortie à l'horizon. Une revente qui a lieu après l'horizon y est
   donc comptée comme du capital disponible. Ici, les flux postérieurs à
   l'horizon sont hors de la courbe, sortie comprise.
2. **Projet déjà commencé.** Le R ramène le début à l'année 0, recompte le
   versement initial, déjà payé, et garde la durée entière. Ici, seuls les
   flux encore à venir sont comptés, aux années où ils tombent.
3. **Sortie sans durée.** Le R ignore la sortie d'un projet de durée nulle.
   Ici, c'est une erreur : la date de la sortie est indéterminée.

Le R de MOCA (``Exp_finance_hist.R``) avait deux autres défauts, que
l'application avait déjà corrigés : un projet commençant à l'année 0 était
ignoré, et la sortie remplaçait le dernier versement au lieu de s'y ajouter.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["Project", "capital_curve", "project_flows"]


@dataclass(frozen=True)
class Project:
    """
    Un projet du foyer, au format de l'origine (``Debut, Versement, Mensualite,
    Duree, Revente``).

    Attributes:
        name: libellé du projet.
        start_year: année du versement initial, comptée depuis aujourd'hui.
            Négative pour un projet déjà commencé.
        initial_payment: versement de l'année de début, en euros.
        annual_payment: versement de chacune des ``duration_years`` années
            suivantes, en euros.
        duration_years: nombre de versements annuels, entier positif ou nul.
        exit_amount: montant de la dernière année, ajouté au dernier versement.
            Négatif pour une revente.
    """

    name: str
    start_year: int
    initial_payment: float
    annual_payment: float
    duration_years: int
    exit_amount: float = 0.0

    def __post_init__(self) -> None:
        years = (("start_year", self.start_year), ("duration_years", self.duration_years))
        for label, count in years:
            if not isinstance(count, int | np.integer):
                raise ValueError(
                    f"Projet « {self.name} » : {label} = {count!r}. Les années se comptent "
                    "en nombres entiers : arrondissez à l'année."
                )
        for label, value in (
            ("initial_payment", self.initial_payment),
            ("annual_payment", self.annual_payment),
            ("exit_amount", self.exit_amount),
        ):
            if not math.isfinite(value):
                raise ValueError(
                    f"Projet « {self.name} » : {label} = {value} n'est pas un montant. "
                    "Saisissez un nombre d'euros."
                )
        if self.duration_years < 0:
            raise ValueError(
                f"Projet « {self.name} » : durée de {self.duration_years} ans. "
                "La durée compte les versements annuels : saisissez 0 ou plus."
            )
        if self.duration_years == 0 and self.exit_amount != 0:
            raise ValueError(
                f"Projet « {self.name} » : montant de sortie sans durée. La sortie a lieu "
                "à la fin de la durée : donnez une durée d'au moins un an, ou ajoutez "
                "la sortie au versement initial."
            )


def project_flows(project: Project, horizon: int) -> np.ndarray:
    """
    Sorties d'argent d'un projet, années 0 à ``horizon`` incluses.

    Le versement initial tombe à ``start_year``, les versements annuels aux
    années ``start_year + 1`` à ``start_year + duration_years``, et la sortie
    s'ajoute au dernier versement. Les flux passés (année négative) ou
    postérieurs à l'horizon ne figurent pas dans le tableau.
    """
    if horizon < 1:
        raise ValueError(f"Horizon de {horizon} an(s) : il faut au moins un an.")
    flows = np.zeros(horizon + 1)
    start = project.start_year
    payments = {start: project.initial_payment}
    for year in range(start + 1, start + project.duration_years + 1):
        payments[year] = payments.get(year, 0.0) + project.annual_payment
    if project.duration_years > 0:
        end = start + project.duration_years
        payments[end] = payments[end] + project.exit_amount
    for year, amount in payments.items():
        if 0 <= year <= horizon:
            flows[year] += amount
    past = [y for y in payments if y < 0]
    beyond = [y for y in payments if y > horizon]
    if past:
        logger.info(
            "Projet « %s » : %d flux antérieurs à aujourd'hui, déjà payés, non comptés.",
            project.name, len(past),
        )
    if beyond:
        logger.info(
            "Projet « %s » : %d flux au-delà de l'horizon de %d ans, hors de la courbe.",
            project.name, len(beyond), horizon,
        )
    return flows


def capital_curve(
    projects: Sequence[Project],
    horizon: int,
    initial_savings: float,
    annual_savings: float | Sequence[float],
) -> np.ndarray:
    """
    Capital disponible à chaque année, de 0 à ``horizon`` inclus.

    ``capital[t] = initial_savings + somme des épargnes des années 1 à t
    − somme des flux de projets des années 0 à t``.

    Args:
        projects: projets du foyer, éventuellement aucun.
        horizon: dernière année de la courbe.
        initial_savings: épargne disponible aujourd'hui, en euros.
        annual_savings: épargne de chaque année 1 à ``horizon``, en euros : un
            montant unique, ou une suite de ``horizon`` montants.

    Returns:
        Tableau de ``horizon + 1`` montants. Une valeur négative signale que les
        projets dépassent l'épargne à cette date : ils ne sont pas financés.
    """
    if horizon < 1:
        raise ValueError(f"Horizon de {horizon} an(s) : il faut au moins un an.")
    if not math.isfinite(initial_savings):
        raise ValueError(f"Épargne de départ invalide ({initial_savings}) : saisissez un montant.")
    savings = np.zeros(horizon + 1)
    savings[0] = initial_savings
    if isinstance(annual_savings, int | float):
        savings[1:] = float(annual_savings)
    else:
        values = np.asarray(annual_savings, dtype=float)
        if values.shape != (horizon,):
            raise ValueError(
                f"{values.size} montants d'épargne annuelle pour un horizon de {horizon} ans. "
                f"Donnez un montant unique, ou exactement {horizon} montants (années 1 à "
                f"{horizon})."
            )
        savings[1:] = values
    if not np.isfinite(savings).all():
        raise ValueError("Épargne annuelle invalide : chaque année doit avoir un montant.")
    outflows = np.zeros(horizon + 1)
    for project in projects:
        outflows += project_flows(project, horizon)
    capital = np.cumsum(savings - outflows)
    short = np.flatnonzero(capital < 0)
    if short.size:
        logger.warning(
            "Capital négatif aux années %s : les projets ne sont pas financés par l'épargne.",
            short.tolist(),
        )
    return np.asarray(capital, dtype=float)
