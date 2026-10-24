"""
Traduction fidèle des crédits en cours et du taux d'endettement du R.

Sources :

- ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/fct_crd_flux.R``
  (fonction ``Flux_crd(horiz, Annuite, Taux_crd_immo, An_rest)``) : un crédit
  amortissable en principal et intérêts, année par année ;
- ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/fct_chrono_flux.R``
  (bloc « cacul du taux_endt et credit sup max possible », hors projets) : le
  taux d'endettement et la mensualité supplémentaire possible.

Les deux constantes du R (``taux_endet_max``, ``taux_compt_div``) sont passées
ici en arguments.
"""

from __future__ import annotations

import numpy as np


def r_round(x: np.ndarray) -> np.ndarray:
    """``round`` du R : arrondi au pair le plus proche, comme ``numpy.round``."""
    return np.round(x)


def r_flux_crd(
    horiz: int, annuite: float, taux: float, an_rest: int
) -> tuple[np.ndarray, np.ndarray]:
    """``Flux_crd`` : (principal, intérêts), chacun de longueur ``horiz``."""
    if taux == 0:
        return np.zeros(horiz), np.zeros(horiz)
    k = np.arange(an_rest, -1, -1, dtype=float)
    crd = annuite * (1 - (1 + taux) ** (-k)) / taux
    if len(crd) <= horiz:
        crd = np.concatenate([crd, np.zeros(horiz - len(crd))])
        chrono = np.concatenate([np.full(an_rest, annuite), np.zeros(horiz - an_rest)])
    else:
        crd = crd[:horiz]
        chrono = np.full(horiz, annuite)
    interest = r_round(taux * crd)
    principal = r_round(chrono - interest)
    return principal, interest


def r_debt_ratio(
    salaries: np.ndarray,
    rental_income: np.ndarray,
    rent_paid: np.ndarray,
    principal: np.ndarray,
    interest: np.ndarray,
    taux_endet_max: float,
    taux_compt_div: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Taux d'endettement et « credit sup » hors projets.

    Les charges entrent avec le signe du R : loyer versé, principal et intérêts
    négatifs.
    """
    a = salaries
    b = taux_compt_div * rental_income
    d, e, f = rent_paid, principal, interest
    ratio = -(d + e + f) / (a + b)
    extra = taux_endet_max * (a + b) + (d + e + f)
    return ratio, extra
