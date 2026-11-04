"""
Bien loué à loyer fixe, valorisé scénario par scénario (évolution E1).

Un bien loué n'est pas un indice de rendement total dont le loyer serait une
part fixe de la valeur : le bail fixe un loyer **en euros**. Le bien se
décompose donc en deux jambes (papier « risque neutre immobilier », doc
Article EAJ, v5) :

1. **La jambe de loyers** : les loyers du bail ``L_i``, payés aux dates
   ``t_i <= T_b``. C'est un portefeuille de zéro-coupons, valorisé avec les
   prix Hull-White ``P(t, t_i)`` du scénario. Elle ne porte que du risque de
   taux.
2. **La valeur libre** ``H`` : le bien sans flux, que le propriétaire reprend
   à la fin du bail ``T_b``. En risque neutre, sa dérive est ``r - y``, où
   ``y`` est le rendement locatif de marché (taux continu annuel). En monde
   réel, la prime de risque immobilière ne porte que sur ``H``.

Valeur du bien, loyer de ``t`` déjà encaissé :

    V(t) = Σ_{t < t_i <= T_b} L_i · P(t, t_i)  +  H(t) · exp(-y · (T_b - t))

Construction de ``H``. Le GSE produit déjà un indice immobilier de rendement
total ``I`` dont le drift (``RealEstateModel.risk_neutral_drift``) rend
``D(t) · I(t)`` martingale. ``H(t) = H(0) · I(t) · exp(-y·t)`` a donc
exactement la dérive ``r - y`` : ``E[D(t) · H(t) · exp(y·t)] = H(0)``.
``H(0)`` se déduit de la valeur du bien en ``t = 0`` :
``H(0) = (V(0) - Σ L_i · P(0, t_i)) · exp(y · T_b)``.

Après la fin du bail, le bien est reloué au rendement de marché : il vaut
``H`` et rapporte, en fin de période, ``H(t) · (exp(y·dt) - 1)``. Ce loyer
est celui qui laisse ``D · (V + loyers perçus)`` martingale ; il ne suppose
aucune vacance entre deux baux.

Propriété vérifiée (``tests/test_leased_property.py``) : en risque neutre,
``D(t) · V(t) + Σ_{s <= t} D(s) · loyer(s)`` a pour espérance ``V(0)`` à
toute date. L'approche « indice » (valeur = indice de prix, loyer en euros)
échoue à ce test.

Conventions de grille, celles de ``HullWhiteModel`` et ``RealEstateModel`` :
la colonne ``i`` est la date ``t_i = i · dt``, la colonne 0 est ``t = 0``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from .hull_white import HullWhiteModel

logger = logging.getLogger(__name__)

__all__ = ["KNOWN_GAPS", "FixedRentLease", "LeasedPropertyPaths", "leased_property_paths"]

KNOWN_GAPS = [
    "Le bail n'est pas encore branché sur les biens loués du foyer "
    "(modules/rental_property.py), qui gardent un rendement locatif en "
    "pourcentage : c'est l'évolution E2.",
    "Le rendement locatif de marché y est constant sur tout l'horizon et "
    "saisi par l'appelant : aucune valeur par défaut, aucune source encore "
    "retenue.",
    "Après la fin du bail, le bien est reloué sans vacance au rendement de "
    "marché y. Ni vacance, ni impayé, ni défaut du locataire ne sont modélisés "
    "sur la jambe de loyers.",
    "La dérive de H hérite du calibrage de l'indice immobilier du GSE ; le "
    "calibrage sourcé (EAJ, a = 0,51, σ = 5,7 %) est l'évolution E4.",
]


@dataclass(frozen=True)
class FixedRentLease:
    """
    Bail à loyer fixé en euros.

    Attributes:
        rents: loyer de chaque période du bail, en euros, payé en fin de
            période : ``rents[k]`` est versé en ``t_{k+1}``. Le bail se termine
            en ``T_b = len(rents) · dt``. Une indexation connue d'avance se
            saisit directement dans ces montants.
        market_yield: rendement locatif de marché ``y``, taux continu annuel
            (0,04 pour 4 %). C'est une hypothèse de marché, pas de la fiscalité.
    """

    rents: np.ndarray
    market_yield: float

    def __post_init__(self) -> None:
        rents = np.asarray(self.rents, dtype=float)
        if rents.ndim != 1 or rents.size == 0:
            raise ValueError(
                f"Le bail doit compter au moins un loyer, en tableau à une dimension "
                f"(reçu la forme {rents.shape}) : saisir un loyer par période du bail."
            )
        if not np.all(np.isfinite(rents)) or np.any(rents < 0):
            raise ValueError(
                "Les loyers du bail doivent être des montants finis et positifs ou "
                "nuls : corriger les loyers saisis."
            )
        if not np.isfinite(self.market_yield) or self.market_yield < 0:
            raise ValueError(
                f"Rendement locatif de marché invalide ({self.market_yield}) : saisir "
                "un taux continu annuel fini et positif ou nul (0,04 pour 4 %)."
            )
        object.__setattr__(self, "rents", rents)

    @property
    def n_periods(self) -> int:
        """Nombre de périodes du bail, ``b`` (``T_b = b · dt``)."""
        return int(self.rents.size)


@dataclass(frozen=True)
class LeasedPropertyPaths:
    """
    Trajectoires d'un bien loué, (n_scénarios × n_dates) chacune.

    Attributes:
        value: valeur du bien ``V(t_i)``, loyer de ``t_i`` déjà encaissé.
        rent: loyer encaissé en ``t_i`` (colonne 0 nulle).
        free_value: valeur libre ``H(t_i)``.
        initial_free_value: ``H(0)``, en euros.
    """

    value: np.ndarray
    rent: np.ndarray
    free_value: np.ndarray
    initial_free_value: float


def leased_property_paths(
    rates: HullWhiteModel,
    short_rates: np.ndarray,
    real_estate_log_returns: np.ndarray,
    lease: FixedRentLease,
    initial_value: float,
) -> LeasedPropertyPaths:
    """
    Valeur et loyers d'un bien loué à loyer fixe, dans chaque scénario du GSE.

    Args:
        rates: le modèle Hull-White qui a produit ``short_rates`` ; sa courbe
            initiale doit couvrir la fin du bail.
        short_rates: taux courts ``r(t_i)``, sortie ``'rt'`` de
            ``HullWhiteModel.generate_scenarios`` (n_scénarios × n_dates).
        real_estate_log_returns: log-rendements totaux de l'indice immobilier,
            sortie ``'total_returns'`` de ``RealEstateModel.generate_returns``,
            même grille. Prime de risque nulle pour la valorisation risque
            neutre, prime du monde réel pour une projection.
        lease: le bail.
        initial_value: valeur du bien en ``t = 0``, en euros.

    Returns:
        Les trajectoires du bien.

    Raises:
        ValueError: grilles incompatibles, valeur initiale non positive, ou
            loyers du bail qui valent plus que le bien.
    """
    short_rates = np.asarray(short_rates, dtype=float)
    log_returns = np.asarray(real_estate_log_returns, dtype=float)
    if short_rates.shape != log_returns.shape or short_rates.ndim != 2:
        raise ValueError(
            f"Taux courts {short_rates.shape} et rendements immobiliers "
            f"{log_returns.shape} doivent avoir la même grille (n_scénarios × n_dates) : "
            "les prendre dans le même tirage du GSE."
        )
    if not np.isfinite(initial_value) or initial_value <= 0:
        raise ValueError(
            f"Valeur initiale du bien invalide ({initial_value}) : saisir un montant "
            "en euros strictement positif."
        )

    dt = rates.dt
    y = lease.market_yield
    n_dates = short_rates.shape[1]
    b = lease.n_periods
    P0 = np.asarray(rates.P0t, dtype=float)
    if len(P0) <= b:
        raise ValueError(
            f"La courbe initiale compte {len(P0)} points, il en faut {b + 1} pour "
            f"valoriser un bail de {b} périodes : charger la courbe sur un horizon "
            "plus long ou raccourcir le bail."
        )

    # P(0, t_i) relatif à t = 0, pour ne pas dépendre de la valeur de P0t[0].
    rent_leg_0 = float(lease.rents @ (P0[1:b + 1] / P0[0]))
    lease_end = b * dt
    h0 = (initial_value - rent_leg_0) * np.exp(y * lease_end)
    if h0 <= 0:
        raise ValueError(
            f"Les loyers du bail valent {rent_leg_0:.0f} € en t = 0, au moins la valeur "
            f"du bien ({initial_value:.0f} €) : la valeur libre serait négative. "
            "Vérifier le loyer, la durée du bail et la valeur saisie."
        )

    times = dt * np.arange(n_dates)
    cumulative = np.cumsum(log_returns, axis=1)
    free_value = h0 * np.exp(cumulative - y * times[None, :])

    value = np.empty_like(free_value)
    rent = np.zeros_like(free_value)
    for i in range(n_dates):
        if i < b:
            zc = rates.zero_coupon_prices(short_rates[:, i], i, b - i)
            value[:, i] = zc @ lease.rents[i:] + free_value[:, i] * np.exp(
                -y * (lease_end - times[i])
            )
        else:
            value[:, i] = free_value[:, i]
        if 1 <= i <= b:
            rent[:, i] = lease.rents[i - 1]
        elif i > b:
            # Relocation au rendement de marché : loyer qui garde D·(V + loyers)
            # martingale, E[D(t_i)·H(t_i)] = H(0)·exp(-y·t_i).
            rent[:, i] = free_value[:, i] * np.expm1(y * dt)

    logger.debug(
        "Bien loué : V(0) = %.0f €, jambe de loyers %.0f €, H(0) = %.0f €, bail de %d pas",
        initial_value, rent_leg_0, h0, b,
    )
    return LeasedPropertyPaths(
        value=value, rent=rent, free_value=free_value, initial_free_value=float(h0)
    )
