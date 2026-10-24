"""
Assemblage multi-horizons : chaque tranche reçoit l'allocation de sa durée.

Une tranche (:mod:`capital_tranches`) est placée l'année ``start_year`` pour
``duration`` années. Elle reçoit les poids optimaux à cet horizon, tirés par
exemple de :func:`placement_optimizer.optimize_by_horizon`. À chaque année, le
montant placé dans chaque placement est la somme, sur les tranches présentes,
de ``montant × poids``. L'argent d'un projet proche est ainsi placé à court
terme, et l'épargne de long terme à long terme.

Les contraintes linéaires sur les poids (bornes, plafonds d'enveloppe en part
des versements, exposition aux actions et aux obligations) restent respectées
après assemblage. La répartition d'une année est en effet une moyenne des
poids des tranches, pondérée par leurs montants. Si chaque jeu de poids
respecte les contraintes, leur moyenne les respecte aussi.

Une tranche de durée nulle est de l'argent qui n'arrive qu'à l'horizon. Elle
n'est pas placée, et son montant est rendu à part (``unplaced``), jamais
réparti en silence.

Équivalent R : ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_A/Assembl_investV3.R``
(``Mat_result_final``). La traduction fidèle est dans
``tests/reference_r/assembl_invest.py``. Sur des tranches de même découpage,
le portage donne la même répartition que le R. Il s'en écarte sur trois points :

1. **Pondération par montant.** Le R additionne les poids des tranches sans
   les pondérer. C'est juste tant que toutes les tranches valent ``pas_E``,
   mais faux pour les tranches exactes de :mod:`capital_tranches`, de montants
   différents.
2. **Pas de filtre à 1 %.** Le R met à zéro tout placement sous 1 % de
   l'année, puis renormalise : la répartition affichée n'est plus celle de
   l'optimum. Ici, tous les poids sont gardés.
3. **Tranche d'un an.** Une tranche présente une seule année fait échouer le R
   (« incorrect number of dimensions »). Ici, elle est assemblée comme les
   autres.

Convention d'horizon : une tranche encore présente à l'horizon est placée
jusqu'à l'horizon, soit ``horizon − start_year`` années. Le R comptait une
année de plus.

La projection du patrimoine du plan assemblé, scénario par scénario (les
``Rdt_terme`` et ``Rdt_liquide`` du R), n'est pas encore portée.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from investment_calculator.modules.capital_tranches import Tranche

logger = logging.getLogger(__name__)

__all__ = ["TrancheAllocation", "assemble_allocation", "required_horizons"]


@dataclass(frozen=True)
class TrancheAllocation:
    """
    Plan de placement assemblé.

    Attributes:
        amounts: euros placés, une ligne par année (0 à l'horizon), une colonne
            par placement.
        unplaced: euros non placés par année : les tranches de durée nulle,
            qui n'arrivent qu'à l'horizon.
    """

    amounts: pd.DataFrame
    unplaced: pd.Series

    @property
    def weights(self) -> pd.DataFrame:
        """Part de chaque placement dans le capital placé, par année (vide si rien n'est placé)."""
        total = self.amounts.sum(axis=1)
        return self.amounts.div(total.where(total > 0), axis=0)


def required_horizons(tranches: Sequence[Tranche]) -> list[int]:
    """Durées, en années, pour lesquelles il faut une allocation optimale."""
    return sorted({t.duration for t in tranches if t.duration > 0})


def assemble_allocation(
    tranches: Sequence[Tranche], weights_by_horizon: pd.DataFrame
) -> TrancheAllocation:
    """
    Assemble les tranches selon les poids optimaux de leur durée.

    Args:
        tranches: tranches d'une même courbe de capital
            (:func:`capital_tranches.split_into_tranches`).
        weights_by_horizon: poids par placement (lignes) et par horizon en années
            (colonnes), comme le rend :func:`placement_optimizer.optimize_by_horizon`.

    Raises:
        ValueError: aucune tranche, horizons différents entre tranches, horizon
            manquant, ou poids qui ne somment pas à 1.
    """
    if not tranches:
        raise ValueError(
            "Aucune tranche à assembler : la courbe de capital est nulle. "
            "Vérifiez l'épargne et les projets du foyer."
        )
    horizons = {t.horizon for t in tranches}
    if len(horizons) != 1:
        raise ValueError(
            f"Tranches d'horizons différents ({sorted(horizons)}) : assemblez les tranches "
            "d'une seule courbe de capital."
        )
    horizon = horizons.pop()
    needed = required_horizons(tranches)
    missing = [h for h in needed if h not in weights_by_horizon.columns]
    if missing:
        raise ValueError(
            f"Pas d'allocation pour les horizons {missing} ans. Calculez-les avec "
            f"optimize_by_horizon(net, constraints, horizons={needed}, ...)."
        )
    weights = weights_by_horizon[needed].astype(float)
    sums = weights.sum(axis=0)
    if not np.allclose(sums.to_numpy(), 1.0, atol=1e-6):
        bad = sums[~np.isclose(sums.to_numpy(), 1.0, atol=1e-6)].round(6).to_dict()
        raise ValueError(f"Les poids doivent sommer à 1 pour chaque horizon ; reçu {bad}.")

    years = pd.RangeIndex(horizon + 1, name="year")
    amounts = pd.DataFrame(0.0, index=years, columns=weights.index)
    unplaced = pd.Series(0.0, index=years, name="unplaced")
    for tranche in tranches:
        present = [y for y in years if tranche.is_present(y)]
        if tranche.duration == 0:
            unplaced.loc[present] += tranche.amount
            continue
        amounts.loc[present] += tranche.amount * weights[tranche.duration].to_numpy()
    if unplaced.any():
        logger.info(
            "%.0f € n'arrivent qu'à l'horizon et ne sont pas placés.", float(unplaced.max())
        )
    return TrancheAllocation(amounts=amounts, unplaced=unplaced)
