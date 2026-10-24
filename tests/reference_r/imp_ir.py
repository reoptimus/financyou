"""
Traduction fidèle de l'impôt sur le revenu et des parts fiscales du R.

Sources :

- ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/fct_imp_IR.R``
  (fonction ``fct_flux_IR(QF)``) : l'impôt d'une part, année par année ;
- ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/fct_chrono_flux.R``
  (blocs « PART IMPOSABLE hors projets », « calcul de l'impot » et « taux
  marginal ») : les parts du foyer, l'impôt du foyer et la tranche marginale.

``tab_IR`` est une variable globale du R : il est passé ici en argument, sous
forme de lignes ``(seuil, taux)``. Le R applique au revenu un abattement
forfaitaire pour frais ; ici, on passe directement le revenu après abattement.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from tests.reference_r.exp_finance import r_exp_proj_hist


def r_fct_flux_ir(qf: np.ndarray, tab_ir: Sequence[tuple[float, float]]) -> np.ndarray:
    """``fct_flux_IR(QF)`` : impôt d'une part, de la tranche haute vers la basse."""
    qfi = np.asarray(qf, dtype=float).copy()
    imp = qfi * 0
    for lower, rate in reversed(tab_ir[1:]):
        above = np.maximum(0.0, qfi - lower)
        imp = imp + above * rate
        qfi = qfi - above
    return imp


def r_part_imp(nb_sal: float, child_ages: Sequence[float], horiz: int) -> np.ndarray:
    """
    Parts du foyer sur ``horiz`` années : ``nb_sal`` plus, pour chaque enfant,
    0,5 part (deux premiers saisis) ou 1 part (suivants) jusqu'à 20 ans.
    """
    parts = np.full(horiz, float(nb_sal))
    for i, age in enumerate(child_ages, start=1):
        enf = 0.5 if i <= 2 else 1.0
        parts = parts + r_exp_proj_hist(horiz - 1, 0, enf, enf, 20 - age, 0.0)
    return parts


def r_household_ir(
    revenue: np.ndarray, parts: np.ndarray, tab_ir: Sequence[tuple[float, float]]
) -> tuple[np.ndarray, np.ndarray]:
    """Impôt du foyer et tranche marginale : ``fct_flux_IR(QF / part) * part``."""
    qf = np.asarray(revenue, dtype=float) / parts
    imp = r_fct_flux_ir(qf, tab_ir) * parts
    taux_marg = np.zeros(len(qf))
    for lower, rate in tab_ir:
        taux_marg[qf > lower] = rate
    return imp, taux_marg
