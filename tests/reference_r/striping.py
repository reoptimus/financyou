"""
Traduction fidèle du découpage en tranches du R.

Source : ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_A/Reoptimus_striping.R``
(fonction ``stripping(pas_E, a)``, version de l'application de février 2020).
La version MOCA (``legacy/R_Financyou/MOCA/FCT/Reoptimus_striping.R``) n'en
diffère que par l'écriture sur disque et par la remise à 1 du premier temps.

Les tableaux R sont indexés à partir de 1 : on garde cette convention avec une
ligne 0 inutilisée, pour que chaque ligne se lise contre le R. ``_r_seq``
reproduit ``a:b`` de R, décroissant quand ``b < a`` (``1:0`` vaut ``c(1, 0)``).
"""

from __future__ import annotations

import math

import numpy as np


def _r_seq(a: int, b: int) -> list[int]:
    return list(range(a, b + 1)) if b >= a else list(range(a, b - 1, -1))


def _r_seq_by(start: float, end: float, by: float) -> np.ndarray:
    """``seq(start, end, by)`` de R."""
    n = math.floor((end - start) / by + 1e-10)
    return start + by * np.arange(n + 1)


def _subset_nonzero(m: np.ndarray, col: int) -> np.ndarray:
    """``subset(m, m[, col] != 0)``, en gardant la ligne 0 inutilisée."""
    body = m[1:]
    body = body[body[:, col] != 0]
    return np.vstack([np.zeros((1, m.shape[1])), body])


def r_stripping(pas_e: float, a: np.ndarray) -> np.ndarray:
    """
    ``stripping(pas_E, a)`` : tranches de ``pas_E`` euros d'une courbe de capital.

    Renvoie ``Tr1`` sans la ligne 0 : une ligne par tranche, colonnes date de
    début, date de fin et numéro de tranche. Les dates sont en unités R
    (1 = premier point de la courbe).
    """
    a = np.asarray(a, dtype=float)
    n = len(a)
    date = np.arange(1, n + 1, dtype=float)
    pas_t = math.ceil(np.max(a[1:] - a[:-1]) / pas_e)
    pas_t = 1 / pas_t
    date2 = _r_seq_by(1, n, pas_t)
    resultat = np.interp(date2, date, a)
    bf = np.zeros((len(date2) + 1, 3))
    bf[1:, 1] = date2
    bf[1:, 2] = resultat

    if bf[1, 2] > bf[2, 2]:
        tr_ref = math.ceil(bf[1, 2] / pas_e) - 1
    else:
        tr_ref = math.floor(bf[1, 2] / pas_e)

    indice = 1
    bf2 = np.zeros((1001, 4))  # colonnes 1..3 : niveau, temps, nombre de points
    bf2[1, 1] = tr_ref
    bf2[1, 2] = bf[1, 1]
    bf2[1, 3] = 1
    for i in range(2, len(date2) + 1):
        if tr_ref * pas_e <= bf[i, 2] <= (tr_ref + 1) * pas_e:
            bf2[indice, 1] = tr_ref
            bf2[indice, 2] += bf[i, 1]
            bf2[indice, 3] += 1
        else:
            indice += 1
            if bf[i, 2] < tr_ref * pas_e:
                tr_ref -= 1
            else:
                tr_ref += 1
            bf2[indice, 1] = tr_ref
            bf2[indice, 2] += bf[i, 1]
            bf2[indice, 3] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        bf2[:, 2] = bf2[:, 2] / bf2[:, 3]
    bf2[np.isnan(bf2)] = 0
    bf2 = _subset_nonzero(bf2, 1)
    bf2[1, 2] = 1  # on remet le premier point au temps 1
    n2 = bf2.shape[0] - 1
    first = int(bf2[1, 1])
    last = int(bf2[n2, 1])

    # Points fictifs pour partir de zéro et y revenir.
    bf3 = np.zeros((1001, 3))
    for i in _r_seq(1, first):
        bf3[i, 1] = i
        bf3[i, 2] = i * 1 / bf2[1, 1]
    bf3[first : n2 + first, 1:3] = bf2[1:, 1:3]
    j0 = first + n2 - 1
    for i in _r_seq(1, last - 1):
        bf3[j0 + i, 1] = bf2[n2, 1] - i
        bf3[j0 + i, 2] = bf2[n2, 2] + i * 1 / bf2[n2, 1]
    bf3[np.isnan(bf3)] = 0
    bf3 = _subset_nonzero(bf3, 1)
    n3 = bf3.shape[0] - 1

    min_t = first
    max_t = n2 + min_t + 1
    point_max = 0
    point_min = 0
    k = 0
    tr = np.zeros((1001, 4))
    tr_max = 0
    t_max = 0

    def cut(lo: int, hi: int) -> None:
        nonlocal k
        window = _r_seq(lo, hi)
        for j in _r_seq(1, int(tr_max) - 1):
            k += 1
            hits = [pos for pos, idx in enumerate(window, start=1) if bf3[idx, 1] == j]
            if len(hits) == 0:
                tr[k, 1:4] = (bf3[lo, 2], bf3[hi, 2], j)
            elif len(hits) == 1:
                if bf3[lo, 1] > bf3[hi, 1]:
                    tr[k, 1:4] = (bf3[lo, 2], bf3[hits[0] + lo - 1, 2], j)
                else:
                    tr[k, 1:4] = (bf3[hits[0] + lo - 1, 2], bf3[hi, 2], j)
            else:
                tr[k, 1:4] = (bf3[hits[0] + lo - 1, 2], bf3[hits[1] + lo - 1, 2], j)

    for i in range(2, n3):
        if bf3[i, 1] > bf3[i + 1, 1] and bf3[i - 1, 1] < bf3[i, 1]:
            tr_max = bf3[i, 1]
            point_max += 1
        if bf3[i, 1] < bf3[i + 1, 1] and bf3[i - 1, 1] > bf3[i, 1]:
            t_max = i
            point_min += 1
        if point_max == 1 and point_min == 1:
            point_max = 0
            point_min = 0
            cut(min_t, t_max)
            min_t = t_max

    # Dernière redescente, entre min_t et max_t.
    cut(min_t, max_t)

    tr = _subset_nonzero(tr, 1)
    tr1 = tr.copy()
    nb = tr1.shape[0] - 1
    for j in range(1, nb + 1):
        for i in range(2, nb + 1):
            if tr1[j, 2] == tr1[i, 1] and tr1[j, 3] == tr1[i, 3] and tr1[j, 1] != 0:
                tr1[j, 2] = tr1[i, 2]
                tr1[i, 1:4] = 0
    tr1 = _subset_nonzero(tr1, 1)
    tr1 = _subset_nonzero(tr1, 2)
    return tr1[1:, 1:4]
