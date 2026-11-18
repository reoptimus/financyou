"""
Sauvegarde de la saisie dans un fichier, puis rechargement.

Les prototypes R gardaient la saisie sous un pseudo, sur un serveur. Ici rien
n'est gardé côté serveur : l'utilisateur télécharge sa saisie (JSON) et la
recharge plus tard. Seule la saisie est sauvegardée, jamais un résultat :
une simulation se relance à partir de la saisie.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

__all__ = ["FORMAT", "SAVED_KEYS", "dump_inputs", "load_inputs"]

FORMAT = "financyou-saisie/1"

# Clés de l'état de session qui portent la saisie, et le type attendu de chacune.
SAVED_KEYS: dict[str, tuple[type, ...]] = {
    'form': (dict, type(None)),
    'holdings': (list,),
    'projects': (list,),
    'available_savings': (int, float, type(None)),
    'budget': (dict, type(None)),
    'loans': (list,),
    'properties': (list,),
    'work_changes': (list,),
}


def dump_inputs(state: Mapping[str, Any]) -> str:
    """Saisie de la session, en JSON lisible, avec son format."""
    payload = {'format': FORMAT, **{key: state.get(key) for key in SAVED_KEYS}}
    return json.dumps(payload, ensure_ascii=False, indent=2)


def load_inputs(text: str | bytes) -> dict[str, Any]:
    """
    Saisie relue depuis un fichier produit par :func:`dump_inputs`.

    Raises:
        ValueError: fichier illisible, d'un autre format, ou dont une rubrique
            n'a pas le type attendu ; le message dit laquelle.
    """
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(
            f"Fichier de saisie illisible ({error}) : rechargez un fichier "
            "téléchargé depuis FinancYou."
        ) from error
    if not isinstance(payload, dict) or payload.get('format') != FORMAT:
        found = payload.get('format') if isinstance(payload, dict) else None
        raise ValueError(
            f"Format de saisie {found!r} au lieu de {FORMAT!r} : ce fichier ne vient "
            "pas de cette version de FinancYou."
        )
    inputs = {}
    for key, types in SAVED_KEYS.items():
        value = payload.get(key)
        if value is None and key in ('holdings', 'projects', 'loans', 'properties', 'work_changes'):
            value = []
        if not isinstance(value, types) or isinstance(value, bool):
            raise ValueError(
                f"Rubrique « {key} » invalide dans le fichier de saisie : "
                f"{type(value).__name__} au lieu de {' ou '.join(t.__name__ for t in types)}."
            )
        inputs[key] = value
    return inputs
