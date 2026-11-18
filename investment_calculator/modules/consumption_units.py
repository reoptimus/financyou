"""
Unités de consommation du foyer, année par année.

Les dépenses courantes d'un foyer suivent sa composition : un enfant qui naît,
grandit ou quitte le foyer les fait varier. Comme dans le R
(``fct_chrono_flux.R``, ``compte_pers``), on ramène les dépenses de l'année 0 à
une unité de consommation, puis on les multiplie par le nombre d'unités de
chaque année.

L'échelle est une donnée d'entrée (``consumption_scales/*.json``), sourcée,
jamais une constante du code : par défaut, l'échelle de l'OCDE modifiée que
retient l'Insee. Le R utilisait l'échelle d'Oxford, sans source : elle n'est
pas reprise. Les lacunes de l'échelle sont déclarées dans son fichier.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

__all__ = ["ConsumptionScale", "household_units", "load_consumption_scale"]

SCALES_DIR = Path(__file__).resolve().parent.parent / "consumption_scales"


@dataclass(frozen=True)
class ConsumptionScale:
    """Une échelle d'équivalence : poids de chaque personne du foyer, en UC."""

    id: str
    label: str
    first_adult: float
    other_person_from_threshold: float
    child_below_threshold: float
    age_threshold: int
    sources: tuple[str, ...]
    known_gaps: tuple[str, ...]

    def child_weight(self, age: int) -> float:
        """Poids d'un enfant de cet âge (0 avant sa naissance)."""
        if age < 0:
            return 0.0
        if age < self.age_threshold:
            return self.child_below_threshold
        return self.other_person_from_threshold


def load_consumption_scale(scale_id: str = "oecd-modified") -> ConsumptionScale:
    """
    Charger une échelle d'équivalence par identifiant.

    Raises:
        FileNotFoundError: aucune échelle de ce nom ; le message liste celles
            qui existent.
    """
    path = SCALES_DIR / f"{scale_id}.json"
    if not path.exists():
        available = sorted(p.stem for p in SCALES_DIR.glob("*.json"))
        raise FileNotFoundError(
            f"Échelle de consommation « {scale_id} » introuvable : choisissez parmi "
            f"{', '.join(available)}."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return ConsumptionScale(
        id=str(data["id"]), label=str(data["label"]),
        first_adult=float(data["first_adult"]),
        other_person_from_threshold=float(data["other_person_from_threshold"]),
        child_below_threshold=float(data["child_below_threshold"]),
        age_threshold=int(data["age_threshold"]),
        sources=tuple(data["sources"]), known_gaps=tuple(data["known_gaps"]),
    )


def household_units(
    scale: ConsumptionScale, *, adults: int, child_ages: Sequence[int], end_age: int | None,
    horizon: int,
) -> np.ndarray:
    """
    Unités de consommation du foyer pour les années 0 à ``horizon``.

    Args:
        adults: 1 ou 2 adultes, présents sur tout l'horizon.
        child_ages: âge de chaque enfant aujourd'hui ; un âge négatif est une
            arrivée à venir (−3 : naissance dans 3 ans).
        end_age: âge auquel un enfant quitte la charge du foyer, saisi par
            l'utilisateur ; il ne compte plus à partir de cet âge.

    Raises:
        ValueError: nombre d'adultes autre que 1 ou 2, ou enfants sans âge de
            fin de charge.
    """
    if adults not in (1, 2):
        raise ValueError(f"{adults} adulte(s) : un foyer en compte 1 ou 2.")
    if child_ages and end_age is None:
        raise ValueError(
            "Enfants saisis sans âge de fin de charge : indiquez à quel âge ils "
            "cesseront d'être à votre charge."
        )
    base = scale.first_adult + (scale.other_person_from_threshold if adults == 2 else 0.0)
    units = np.full(horizon + 1, base)
    for age_now in child_ages:
        for year in range(horizon + 1):
            age = age_now + year
            if end_age is not None and age < end_age:
                units[year] += scale.child_weight(age)
    return units
