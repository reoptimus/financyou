"""
Flux de trésorerie du foyer : projets et dépenses prévues.

Portage de ``Exp_fin`` (``legacy/R_scripts/Exp_finance_hist.R``). Chaque projet
(achat, études, garde d'enfant, véhicule...) se décrit comme dans le code
d'origine (note ``Reoptimus_V4``, « Budget et dépenses prévisionnels ») :

- un premier versement l'année de début ;
- un versement annuel pendant ``duration`` années, les années suivant le début ;
- une revente éventuelle la dernière de ces années.

Écarts avec le code R, voulus :

- le montant de sortie s'ajoute au dernier versement annuel au lieu de
  l'écraser (le commentaire R parle d'« ajout du montant de sortie ») ;
- un projet peut commencer l'année 0 (le R ignorait les lignes dont l'année de
  début vaut 0, qui marquaient les lignes vides de sa matrice) ;
- la revente se saisit en positif (le R l'attendait en négatif) ;
- la courbe de capital disponible ne peut pas devenir négative : un foyer à
  découvert lève une erreur au lieu de se projeter.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["Project", "check_available_capital", "project_flows", "projects_from_config"]

_FIELDS = ("name", "start_year", "initial_payment", "annual_payment", "duration",
           "resale_value")


@dataclass(frozen=True)
class Project:
    """Un projet ou une dépense prévue, en euros d'aujourd'hui."""

    name: str
    start_year: int
    initial_payment: float
    annual_payment: float
    duration: int
    resale_value: float

    def __post_init__(self) -> None:
        if self.start_year < 0 or self.duration < 0:
            raise ValueError(
                f"Projet {self.name!r} : l'année de début et la durée doivent être "
                "positives ou nulles."
            )
        if min(self.initial_payment, self.annual_payment, self.resale_value) < 0:
            raise ValueError(
                f"Projet {self.name!r} : les montants se saisissent en positif "
                "(la revente est une recette, elle est déduite des dépenses)."
            )


def projects_from_config(entries: Sequence[Mapping[str, Any]]) -> tuple[Project, ...]:
    """
    Projets d'une configuration de profil (clé ``projects``).

    Raises:
        ValueError: un champ manque ; aucun n'a de valeur par défaut.
    """
    projects = []
    for k, entry in enumerate(entries):
        missing = [f for f in _FIELDS if f not in entry]
        if missing:
            raise ValueError(
                f"Le projet n° {k + 1} n'a pas {missing} : ces champs n'ont pas de "
                "valeur par défaut. Renseignez-les, 0 pour un montant ou une durée nuls."
            )
        projects.append(Project(
            name=str(entry["name"]),
            start_year=int(entry["start_year"]),
            initial_payment=float(entry["initial_payment"]),
            annual_payment=float(entry["annual_payment"]),
            duration=int(entry["duration"]),
            resale_value=float(entry["resale_value"]),
        ))
    return tuple(projects)


def project_flows(projects: Sequence[Project], n_years: int) -> np.ndarray:
    """
    Dépenses nettes de chaque projet, année par année.

    Returns:
        Tableau ``(len(projects), n_years + 1)`` : dépense de l'année ``t``,
        négative quand la revente dépasse le versement de l'année. Les flux
        postérieurs à ``n_years`` sont hors projection et ne sont pas retenus.
    """
    flows = np.zeros((len(projects), n_years + 1))
    for i, project in enumerate(projects):
        row = np.zeros(project.start_year + project.duration + 1)
        row[project.start_year] = project.initial_payment
        if project.duration > 0:
            row[project.start_year + 1:] = project.annual_payment
            row[-1] -= project.resale_value
        kept = min(len(row), n_years + 1)
        flows[i, :kept] = row[:kept]
        if len(row) > kept:
            logger.info(
                "Projet %r : flux des années %d à %d hors projection, non retenus.",
                project.name, n_years + 1, len(row) - 1,
            )
    return flows


def check_available_capital(net_flow: np.ndarray, tolerance: float = 1e-6) -> np.ndarray:
    """
    Capital disponible cumulé (``sum_cuml`` du R) ; refuse un foyer à découvert.

    Raises:
        ValueError: le cumul des versements moins les dépenses devient négatif.
    """
    capital = np.cumsum(net_flow)
    short = np.flatnonzero(capital < -tolerance)
    if short.size:
        year = int(short[0])
        raise ValueError(
            f"Les projets dépassent l'épargne disponible : il manque "
            f"{-capital[year]:,.0f} € l'année {year}. Réduisez ou décalez un projet, "
            "ou augmentez l'épargne. L'épargne existante, laissée dans ses "
            "placements, ne finance pas les projets."
        )
    return capital
