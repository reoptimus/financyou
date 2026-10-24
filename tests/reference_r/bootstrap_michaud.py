"""
Traduction fidèle du rééchantillonnage de Michaud du R.

Source : ``legacy/R_Financyou/MOCA/FCT/Script_Bootstrap_V5_quick.R`` (fonction
``Boot_Michaud(GSE_plac_taxes, pas_t, Nbboots, Aversion, tabl_cont_t)``).

Le R découpe les scénarios en ``Nbboots`` paquets consécutifs. Sur chaque
paquet, il résout Markowitz par le lagrangien en forme fermée (``ginv``). Une
contrainte non nulle de ``tabl_cont_t`` fixe le poids du placement. Un poids
négatif est ensuite forcé à zéro, puis le système est résolu à nouveau. Le R
fait enfin la moyenne des solutions des paquets et la renormalise. Seule la
date 1 du GSE est lue (« pour accélérer », dit le commentaire du R).

``numpy.linalg.pinv`` remplace ``MASS::ginv`` : les deux calculent la
pseudo-inverse de Moore-Penrose, avec le même seuil relatif.
"""

from __future__ import annotations

import numpy as np

_TOL = float(np.sqrt(np.finfo(float).eps))


def _bordered(mat: np.ndarray, vec_e: np.ndarray, vcont: np.ndarray, i: int, value: float):
    """Ajoute la contrainte « poids i = value » au système bordé."""
    n = mat.shape[0]
    mat2 = np.zeros((n + 1, n + 1))
    mat2[:n, :n] = mat
    mat2[n, i] = 1.0
    mat2[i, n] = 1.0
    e2 = np.zeros(n + 1)
    e2[:n] = vec_e
    v2 = np.zeros(n + 1)
    v2[:n] = vcont
    v2[n] = value
    return mat2, e2, v2


def _solve(mat: np.ndarray, vec_e: np.ndarray, vcont: np.ndarray, aversion: float) -> np.ndarray:
    inv = np.linalg.pinv(mat, rcond=_TOL)
    return (1.0 / aversion) * (inv @ vec_e) + inv @ vcont


def r_boot_michaud(
    returns: np.ndarray, nbboots: int, aversion: float, constraints: np.ndarray
) -> np.ndarray:
    """
    ``Boot_Michaud`` sur ``returns[scénario, durée, placement]`` (la date 1 du GSE).

    Returns:
        ``soltot``, de forme ``(placements, durées)``.
    """
    ns, n_d, nb_actifs = returns.shape
    nbligboot = ns // nbboots
    soltot = np.zeros((nb_actifs, n_d))
    for tp_d in range(n_d):
        solboot = np.zeros((nbboots, nb_actifs))
        for b in range(nbboots):
            mat_e = returns[nbligboot * b : nbligboot * (b + 1), tp_d, :]
            esp = mat_e.mean(axis=0)
            cov = np.cov(mat_e, rowvar=False)
            mat = np.ones((nb_actifs + 1, nb_actifs + 1))
            mat[nb_actifs, nb_actifs] = 0.0
            mat[:nb_actifs, :nb_actifs] = cov
            vec_e = np.zeros(nb_actifs + 1)
            vec_e[:nb_actifs] = esp
            vcont = np.zeros(nb_actifs + 1)
            vcont[nb_actifs] = 1.0
            for i in range(nb_actifs):
                if constraints[i] != 0:
                    mat, vec_e, vcont = _bordered(mat, vec_e, vcont, i, float(constraints[i]))
            sol = _solve(mat, vec_e, vcont, aversion)
            satur = (np.asarray(constraints) != 0).astype(int)
            for _ in range(nb_actifs):
                for i in range(nb_actifs):
                    if satur[i] == 0 and sol[i] < 0:
                        satur[i] = 1
                        mat, vec_e, vcont = _bordered(mat, vec_e, vcont, i, 0.0)
                        sol = _solve(mat, vec_e, vcont, aversion)
            solboot[b, :] = sol[:nb_actifs]
        sol_mean = solboot.mean(axis=0)
        soltot[:, tp_d] = sol_mean / sol_mean.sum()
    return soltot
