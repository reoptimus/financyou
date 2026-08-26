"""
Configuration centralisée de la journalisation pour FinancYou.

Ce module expose :

- ``LOGGER_NAME`` : le nom du logger racine de la bibliothèque (``financyou``) ;
- ``configure_logging()`` : configure ce logger racine (handler flux, format
  horodaté, format JSON optionnel pour la production) ;
- ``get_logger()`` : petit utilitaire pour obtenir un logger enfant.

La bibliothèque elle-même n'appelle jamais ``configure_logging()`` à l'import :
conformément aux bonnes pratiques, c'est l'application hôte (script, API web,
tâche planifiée) qui décide de la configuration. Chaque module se contente de
déclarer ``logger = logging.getLogger(__name__)`` et de journaliser ; un
``NullHandler`` est posé ici pour éviter le message
« No handlers could be found » lorsque rien n'est configuré.

Exemple :
    >>> from investment_calculator.logging_config import configure_logging
    >>> configure_logging(level="INFO")
    >>> # ou, en production, avec des journaux structurés :
    >>> configure_logging(level="WARNING", json_format=True)
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

__all__ = [
    "LOGGER_NAME",
    "DEFAULT_FORMAT",
    "DEFAULT_DATE_FORMAT",
    "JsonFormatter",
    "configure_logging",
    "get_logger",
]

#: Nom du logger racine de la bibliothèque. Tous les loggers de modules
#: (``investment_calculator.*``) sont rattachés à celui-ci via la hiérarchie
#: des noms uniquement si le paquet est nommé ainsi ; on configure donc
#: explicitement les deux espaces de noms dans :func:`configure_logging`.
LOGGER_NAME = "financyou"

#: Espaces de noms réellement utilisés par les modules de la bibliothèque.
_LIBRARY_NAMESPACES = ("financyou", "investment_calculator", "time_series_slicer")

DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

#: Attributs standards de ``LogRecord`` : tout le reste est considéré comme un
#: champ additionnel fourni via ``extra=`` et sérialisé dans la sortie JSON.
_RESERVED_RECORD_ATTRS = frozenset(
    {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "message", "module",
        "msecs", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "taskName", "thread", "threadName",
    }
)


class JsonFormatter(logging.Formatter):
    """
    Formateur produisant une ligne JSON par enregistrement.

    Destiné à la production, où les journaux sont collectés par un agrégateur
    (ELK, Loki, CloudWatch...) qui indexe les champs structurés. Les arguments
    passés via ``extra=`` sont ajoutés au document JSON, ce qui permet par
    exemple de tracer ``extra={"n_scenarios": 1000, "duration_s": 2.4}``.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, DEFAULT_DATE_FORMAT),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        # Champs additionnels fournis par l'appelant via extra=
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_ATTRS and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(
    level: int | str = logging.INFO,
    json_format: bool = False,
    stream: Any = None,
    propagate: bool = False,
) -> logging.Logger:
    """
    Configure la journalisation de la bibliothèque.

    Args:
        level: Niveau minimal des messages émis (``logging.INFO``, ``"DEBUG"``...).
        json_format: Si ``True``, chaque enregistrement est émis sous forme d'un
            objet JSON sur une ligne (recommandé en production). Sinon, un format
            texte horodaté lisible par un humain est utilisé.
        stream: Flux de sortie du handler. Par défaut ``sys.stderr``, afin de ne
            pas polluer ``stdout`` qui peut porter des données applicatives.
        propagate: Si ``True``, les enregistrements remontent aussi au logger
            racine de Python. Laissé à ``False`` pour éviter les doublons quand
            l'application hôte a sa propre configuration.

    Returns:
        Le logger racine ``financyou`` configuré.

    Note:
        La fonction est idempotente : appelée plusieurs fois, elle remplace les
        handlers qu'elle avait posés au lieu de les empiler (ce qui provoquerait
        des lignes de journal dupliquées).
    """
    if isinstance(level, str):
        resolved_level = logging.getLevelName(level.upper())
        if not isinstance(resolved_level, int):
            raise ValueError(f"Niveau de journalisation inconnu : {level!r}")
    else:
        resolved_level = level

    formatter: logging.Formatter
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(fmt=DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setLevel(resolved_level)
    handler.setFormatter(formatter)
    # Marqueur permettant de repérer nos propres handlers lors d'un réappel.
    handler.set_name("financyou-stream")

    root_logger = logging.getLogger(LOGGER_NAME)

    for namespace in _LIBRARY_NAMESPACES:
        logger = logging.getLogger(namespace)
        # Retire uniquement les handlers posés par cette fonction : on ne
        # touche pas à ceux que l'application hôte aurait ajoutés elle-même.
        for existing in list(logger.handlers):
            if getattr(existing, "name", None) == "financyou-stream":
                logger.removeHandler(existing)
                existing.close()
        logger.addHandler(handler)
        logger.setLevel(resolved_level)
        logger.propagate = propagate

    return root_logger


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """
    Renvoie un logger de la bibliothèque.

    Args:
        name: Nom complet du logger, typiquement ``__name__`` depuis un module.

    Returns:
        L'instance de logger correspondante.
    """
    return logging.getLogger(name)


# Un NullHandler sur chaque espace de noms de la bibliothèque évite le message
# « No handlers could be found for logger ... » quand l'application hôte n'a
# rien configuré. Il n'émet rien et n'interfère pas avec configure_logging().
for _namespace in _LIBRARY_NAMESPACES:
    logging.getLogger(_namespace).addHandler(logging.NullHandler())
