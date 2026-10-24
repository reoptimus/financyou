"""
Traduction fidèle des flux de projets et de la courbe de capital du R.

Sources :

- ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/Exp_proj_hist.R``
  (fonction ``Exp_fin`` de l'application, mai 2020) : les flux d'un projet ;
- ``legacy/R_Financyou/MOCA/FCT/Exp_finance_hist.R`` (fonction ``Exp_fin`` de
  MOCA, janvier 2020, identique à ``legacy/R_scripts/Exp_finance_hist.R``) :
  la somme cumulée qui donne le capital disponible.

Seule différence d'interface : ``Exp_proj_hist.R`` reçoit une date de début et
la convertit en années par ``floor(jours / 365)``. Ici, on lui passe
directement ce nombre d'années.
"""

from __future__ import annotations

import math

import numpy as np


def r_exp_proj_hist(
    horiz: int,
    an_debut: int,
    mdebut: float,
    mvers: float,
    duree: float,
    msortie: float,
) -> np.ndarray:
    """``Exp_fin(horiz, AnDebut, Mdebut, Mvers, duree, Msortie, pente)``.

    ``pente`` est un argument inutilisé du R : il est omis.
    """
    pas_t = 1
    duree = min(horiz - an_debut, math.ceil(duree / pas_t))
    m = [an_debut, mdebut, mvers, duree, msortie]
    hist = np.zeros(horiz + 1)
    if m[0] >= 0:
        # Hist_detail[1, M[1]+1] <- M[2]
        hist[int(m[0])] = m[1]
        if m[3] > 0:
            # Hist_detail[1, (M[1]+2):(M[1]+1+M[4])] <- rep(M[3], M[4])
            hist[int(m[0]) + 1 : int(m[0]) + 1 + int(m[3])] = m[2]
            # Hist_detail[1, M[1]+1+M[4]] <- ... + M[5]
            hist[int(m[0]) + int(m[3])] += m[4]
    else:
        m[0] = 0
        hist[0] = m[1]
        if m[3] > 0:
            hist[1 : 1 + int(m[3])] = m[2]
            hist[int(m[3])] += m[4]
    return hist


def r_cumulative_capital(
    project_rows: np.ndarray, horiz: int, sal_net: float, epar: float
) -> np.ndarray:
    """
    Fin de ``Exp_finance_hist.R`` : ajout de l'épargne et des salaires, puis somme
    cumulée. ``project_rows`` a une ligne par projet et ``horiz + 1`` colonnes.
    """
    nb_proj = project_rows.shape[0]
    hist = np.zeros((nb_proj + 1, horiz + 1))
    hist[:nb_proj, :] = project_rows
    # Hist_detail[nb_proj+1, 1] <- -epar
    hist[nb_proj, 0] = -epar
    # Hist_detail[nb_proj+1, 2:(horiz+1)] <- rep(-salNet, horiz)
    hist[nb_proj, 1:] = -sal_net
    sum_cuml = hist.sum(axis=0)
    for i in range(horiz):
        sum_cuml[i + 1] = sum_cuml[i] + sum_cuml[i + 1]
    return -sum_cuml
