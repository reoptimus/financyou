"""
Traduction fidèle des revenus, dépenses et de l'épargne libre du R.

Source : ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/fct_chrono_flux.R``
(blocs « REVENU », « depenses courantes hors projets » et « Epargne libre hors
projets »).

Le R lit le taux de remplacement dans ``tab_retraite`` et ``tab_coef_retraite`` :
on passe ici le taux final, produit de ces tables. Les unités de consommation
(``compte_pers``) sont passées par année. L'impôt « hors projets » est passé
tel que le R le calcule (``fct_flux_IR``, voir ``imp_ir.py``), positif.
Le R couvre ``horiz`` années, de 0 à ``horiz − 1``.
"""

from __future__ import annotations

import numpy as np


def r_salary(net_imposable: float, evol: float, horiz: int, res_retraite: int,
             taux_rempla: float) -> np.ndarray:
    """Ligne ``sal1`` (ou ``sal2``) : salaire, puis pension à partir de ``Res_retraite``."""
    sal = net_imposable * (1 + evol) ** np.arange(horiz)
    if res_retraite < horiz:
        sal[res_retraite:] = sal[res_retraite] * taux_rempla
    return sal


def r_expenses(salaries: np.ndarray, tax: np.ndarray, loyer: float, annuites: np.ndarray,
               taux_eparg: float, compte_pers: np.ndarray, box_evol_sal: int) -> np.ndarray:
    """
    Dépenses courantes hors projets, positives.

    ``taux_depense`` du R : revenus de l'année 0 − épargne − loyer − annuités −
    impôt ; ramené à une unité de consommation puis multiplié par
    ``compte_pers``. Si ``box_evol_sal`` vaut 1, les dépenses sont stables ;
    sinon elles suivent les salaires.
    """
    depense = salaries[0] - taux_eparg - loyer - annuites[0] - tax[0]
    depense_pers = depense / compte_pers[0]
    chrono = compte_pers * depense_pers
    if box_evol_sal == 1:
        return chrono
    return chrono * salaries / salaries[0]


def r_free_savings(salaries: np.ndarray, tax: np.ndarray, loyer: float,
                   annuites: np.ndarray, expenses: np.ndarray) -> np.ndarray:
    """« Epargne libre hors projets » : −(life + plc + impot), signes remis positifs."""
    return salaries - loyer - expenses - annuites - tax
