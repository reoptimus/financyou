"""
Traduction fidèle de l'assemblage des tranches du R : la répartition en euros.

Source : ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_A/Assembl_investV3.R``
(fonction ``Assembl_invest(soltoti, Tr1, GSEpp, sum_cuml)``). Seule la
répartition ``Mat_result_final`` est traduite. Les rendements par scénario
(``Rdt_terme``, ``Rdt_liquide``) relèvent de la projection du patrimoine, qui
n'est pas portée à cette étape.

``horiz`` est une variable globale dans le R. Elle est passée ici en argument.
Les tableaux R sont indexés à partir de 1 : on garde cette convention avec une
ligne et une colonne 0 inutilisées.
"""

from __future__ import annotations

import math

import numpy as np


def r_assembl_invest(
    soltot: np.ndarray, tr1: np.ndarray, sum_cuml: np.ndarray, horiz: int
) -> np.ndarray:
    """
    ``Assembl_invest(soltoti, Tr1, GSEpp, sum_cuml)[[1]]``.

    Args:
        soltot: poids optimaux, de forme ``(Nb_plac, D, Tp)`` (``soltot[p, D-1, t-1]``).
        tr1: tranches du R, une ligne ``(début, fin, numéro)`` en dates R.
        sum_cuml: capital, une valeur par colonne R (dates 1 à ``Horizon_max``).
        horiz: la variable globale ``horiz`` du R.

    Returns:
        ``Mat_result_final``, de forme ``(Nb_plac, Horizon_max)`` : les euros par
        placement et par date.
    """
    nb_plac, horizon_max = soltot.shape[0], soltot.shape[1]
    # Indexation R : sol[p, D, t] avec p, D, t à partir de 1.
    sol = np.zeros((nb_plac + 1, soltot.shape[1] + 1, soltot.shape[2] + 1))
    sol[1:, 1:, 1:] = soltot
    mat = np.zeros((nb_plac + 1, horizon_max + 1))

    strips = [(math.floor(row[0]), math.ceil(row[1]) + 1) for row in tr1]
    strips = [(a, b - a) for a, b in strips]
    strips = [s for s in strips if s[0] != 0]
    strips = [s for s in strips if s[1] != 0]

    for tp_deb, d in strips:
        tp_deb = min(tp_deb, horiz - 1)
        d = min(d, horiz)
        fin = min(tp_deb + d - 1, horiz)
        if d != 0:
            ajout = sol[1:, d, tp_deb : fin + 1]
            mat[1:, tp_deb : fin + 1] = ajout + mat[1:, tp_deb : fin + 1]

    mat = mat[1:, 1:]
    with np.errstate(invalid="ignore", divide="ignore"):
        final = mat / mat.sum(axis=0)
    final[np.isnan(final)] = 0
    final[final < 0.01] = 0
    with np.errstate(invalid="ignore", divide="ignore"):
        final = final / final.sum(axis=0)
    # R ne remet pas les NaN à zéro après cette seconde normalisation.
    return final * np.asarray(sum_cuml[:horizon_max], dtype=float)
