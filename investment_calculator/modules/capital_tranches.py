"""
Découpage de la courbe de capital en tranches, chacune avec son horizon.

La courbe de capital disponible (:mod:`household_cash_flow`) monte avec
l'épargne et descend quand un projet est payé. On la découpe horizontalement.
Chaque couche de capital est présente sur une suite d'années consécutives : elle
y est placée, puis retirée l'année où la courbe passe sous elle. L'argent d'un
projet est ainsi placé à l'horizon du projet, et l'épargne de long terme à
l'horizon de la courbe.

Exemple : la courbe 10 000, 30 000, 12 000, 20 000 sur les années 0 à 3 donne
quatre tranches :

- 10 000 € présents toutes les années, encore placés à l'horizon ;
- 2 000 € (de 10 000 à 12 000) placés à l'année 1, encore placés à l'horizon ;
- 18 000 € (de 12 000 à 30 000) placés à l'année 1 et retirés à l'année 2 ;
- 8 000 € (de 12 000 à 20 000) placés à l'année 3.

Le découpage est exact : à chaque année, la somme des tranches présentes est
égale au capital.

Équivalent R : ``legacy/R_Financyou/MOCA/FCT/Reoptimus_striping.R`` (fonction
``stripping``). La traduction fidèle est dans ``tests/reference_r/striping.py``.
Le R découpe la courbe en tranches de taille fixe ``pas_E`` (5 000 €), après
interpolation, et en tire des dates fractionnaires. Le portage s'en écarte, car
ce découpage perd ou déplace du capital (tests à l'appui) :

1. **Le haut de la courbe n'est pas placé.** Le R ne garde que les tranches
   ``1`` à ``Tr_max − 1`` de chaque pic. Dans les tests, à l'année 9 d'une
   courbe à 64 000 €, il n'en place que 60 000.
2. **Les fortes baisses ne sont pas suivies.** Le pas d'interpolation se règle
   sur la plus forte hausse annuelle, pas sur la plus forte baisse. Ensuite,
   l'escalier ne descend que d'un niveau par point. Un projet qui fait chuter
   la courbe de plusieurs tranches en une année laisse donc ces tranches
   comptées comme placées pendant qu'elles financent le projet.
3. **Les dates sont des moyennes.** L'entrée d'une tranche est datée au temps
   moyen passé dans sa bande de 5 000 €, et non à l'année où le capital
   l'atteint.
4. **Une courbe plate fait échouer le R** (division par zéro dans le pas).

Ici, il n'y a pas de taille de tranche à choisir : les couches suivent les
valeurs de la courbe aux dates où l'argent est versé ou retiré, c'est-à-dire
aux années.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["Tranche", "split_into_tranches", "tranche_balance"]


@dataclass(frozen=True)
class Tranche:
    """
    Une couche de capital placée d'un seul tenant.

    Attributes:
        amount: montant de la tranche, en euros.
        start_year: année où la tranche est placée.
        withdrawal_year: année où elle est retirée (la courbe passe sous elle),
            ou ``None`` si elle est encore placée à l'horizon.
        horizon: dernière année de la courbe découpée.
    """

    amount: float
    start_year: int
    withdrawal_year: int | None
    horizon: int

    @property
    def duration(self) -> int:
        """Durée de placement en années : jusqu'au retrait, ou jusqu'à l'horizon."""
        end = self.horizon if self.withdrawal_year is None else self.withdrawal_year
        return end - self.start_year

    def is_present(self, year: int) -> bool:
        """La tranche est-elle placée à la fin de l'année ``year`` ?"""
        if year < self.start_year:
            return False
        return self.withdrawal_year is None or year < self.withdrawal_year


def split_into_tranches(capital: Sequence[float] | np.ndarray) -> list[Tranche]:
    """
    Découpe une courbe de capital (années 0 à ``horizon``) en tranches.

    Les couches qui partagent la même date de placement et la même date de
    retrait sont regroupées en une seule tranche. Les tranches sont triées par
    date de placement, puis par date de retrait (les tranches encore placées à
    l'horizon en dernier).

    Raises:
        ValueError: courbe de moins de deux années, valeur non finie, ou capital
            négatif. Un capital négatif veut dire que les projets ne sont pas
            financés : il n'y a rien à placer, et c'est à l'utilisateur de revoir
            ses projets ou son épargne.
    """
    curve = np.asarray(capital, dtype=float)
    if curve.ndim != 1 or curve.size < 2:
        raise ValueError(
            "La courbe de capital doit couvrir au moins les années 0 et 1 : "
            "construisez-la avec household_cash_flow.capital_curve."
        )
    if not np.isfinite(curve).all():
        raise ValueError("La courbe de capital contient une valeur non finie.")
    if (curve < 0).any():
        years = np.flatnonzero(curve < 0).tolist()
        raise ValueError(
            f"Capital négatif aux années {years} : les projets ne sont pas financés. "
            "Réduisez ou décalez les projets, ou augmentez l'épargne, avant de découper."
        )
    horizon = curve.size - 1
    amounts: dict[tuple[int, int | None], float] = {}
    previous = 0.0
    for level in np.unique(curve[curve > 0]):
        height = float(level - previous)
        present = curve >= level
        year = 0
        while year <= horizon:
            if not present[year]:
                year += 1
                continue
            start = year
            while year <= horizon and present[year]:
                year += 1
            withdrawal = year if year <= horizon else None
            amounts[(start, withdrawal)] = amounts.get((start, withdrawal), 0.0) + height
        previous = float(level)

    def order(key: tuple[int, int | None]) -> tuple[int, int]:
        start, withdrawal = key
        return start, horizon + 1 if withdrawal is None else withdrawal

    tranches = [
        Tranche(amount=amounts[key], start_year=key[0], withdrawal_year=key[1], horizon=horizon)
        for key in sorted(amounts, key=order)
    ]
    logger.debug("%d tranches sur un horizon de %d ans.", len(tranches), horizon)
    return tranches


def tranche_balance(tranches: Sequence[Tranche], horizon: int) -> np.ndarray:
    """Capital placé à chaque année, somme des tranches présentes : la courbe d'origine."""
    balance = np.zeros(horizon + 1)
    for tranche in tranches:
        for year in range(horizon + 1):
            if tranche.is_present(year):
                balance[year] += tranche.amount
    return balance
