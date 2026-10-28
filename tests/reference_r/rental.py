"""
Traduction fidèle d'un bien loué acheté à crédit dans le R.

Sources :

- ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/fct_recalcul_revenu.R``
  (``fct_recalcul_revenu(nom_apport, montant, tab_chrono)``) : le loyer d'un
  bien selon son type ;
- ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/fct_discret_optim.R``
  (« calcul des caracteristiques de l'emprunt ») : l'emprunt tiré d'une annuité ;
- ``legacy/R_Financyou/ShinyR/BetaV1/Financyou/Data_Log/FCT_Global/modif_chrono_flux_plc.R``
  (branche autre que ``RimmoPropre``) : les lignes revenu, principal et
  intérêts ajoutées à ``tab_chrono`` à partir de ``debut_optim``.

Les constantes du R (rendement, part retenue) sont gardées telles quelles.
"""

from __future__ import annotations

import numpy as np

from tests.reference_r.crd_flux import r_flux_crd


def r_recalcul_revenu(nom_apport: str, montant: float, loyer_verse: np.ndarray) -> float:
    """``fct_recalcul_revenu`` ; ``loyer_verse`` est la ligne « loyer » (négative)."""
    if nom_apport == "RimmoPropre":
        return float(np.max(-loyer_verse))
    if nom_apport == "RimmoPinel":
        return 0.85 * 0.025 * montant
    if nom_apport == "RimmoLoc":
        return 0.85 * 0.04 * montant
    return 0.0


def r_emprunt(annuite: float, tau: float, n: int) -> float:
    """``emprunt <- annuite * (1 - (1 + tau)^-n) / tau``."""
    return annuite * (1 - (1 + tau) ** -n) / tau


def r_chrono_location(
    horiz: int, debut_optim: int, revenu: float, annuite: float, tau: float, n: int
) -> dict[str, np.ndarray]:
    """
    Lignes ajoutées à ``tab_chrono`` pour un bien loué, colonnes 1 à ``horiz``.

    ``debut_optim`` est l'indice R (à partir de 1) de l'année d'achat. Le
    principal et les intérêts sont négatifs, comme dans ``tab_chrono``.
    """
    before = np.zeros(debut_optim - 1)
    principal, interest = r_flux_crd(horiz, annuite, tau, n)
    kept = horiz - debut_optim + 1
    return {
        "revenu": np.concatenate([before, np.full(kept, revenu)]),
        "principal": -np.concatenate([before, principal[:kept]]),
        "interet": -np.concatenate([before, interest[:kept]]),
    }
