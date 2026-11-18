"""
Modèles de projets repris des prototypes R (``table_projets.xlsx``, feuille ``tab2``).

Chaque modèle pose les questions de son type de projet, puis traduit les
réponses dans le format projet du moteur : début, versement initial, versement
annuel, durée, revente (voir :class:`Project`). Un modèle ne fait que de
l'arithmétique sur les montants saisis : il n'ajoute aucune hypothèse, aucun
taux, aucune valeur par défaut.

Les modèles du R qui demandent une donnée absente du moteur ne sont pas
repris ici (voir ``docs/portage-r/interface-prototypes-r.md``). Le temps
partiel et les congés touchent les revenus : ils se saisissent à part, dans la
page Projets, et agissent sur le budget. Restent hors de portée :
agrandissement de la famille (unités de
consommation), Pinel et crédits d'impôt travaux (régime fiscal),
investissement locatif (page dédiée).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

__all__ = ["FIELD_KINDS", "TEMPLATES", "Field", "ProjectTemplate", "loan_annuity", "project_row"]

# Genre de chaque champ : (minimum, maximum, pas) de la saisie, et entier ou non.
FIELD_KINDS: dict[str, tuple[float, float | None, float, bool]] = {
    'year': (0, 100, 1, True),
    'years': (0, 100, 1, True),
    'amount': (0.0, None, 500.0, False),
    'rate': (0.0, 30.0, 0.1, False),
}


@dataclass(frozen=True)
class Field:
    """Une question d'un modèle : clé de la réponse, libellé, genre (``FIELD_KINDS``)."""

    key: str
    label: str
    kind: str


@dataclass(frozen=True)
class ProjectTemplate:
    """Un type de projet : ses questions et la traduction des réponses en projet."""

    label: str
    description: str
    fields: tuple[Field, ...]
    build: Callable[[Mapping[str, float]], dict[str, float]]


def loan_annuity(principal: float, rate: float, years: int) -> float:
    """
    Annuité constante d'un prêt : ``C × t / (1 − (1 + t)^−n)``, ou ``C / n`` à taux nul.

    Le R (``table_projets.xlsx``, « depense via credit ») écrit
    ``(-b*d*0.01)/(1-(1+d)^c)``, où le taux est pris tantôt en pour cent, tantôt
    en fraction : le portage applique la formule de l'annuité constante.

    Raises:
        ValueError: durée nulle ou taux négatif.
    """
    if years < 1:
        raise ValueError(
            f"Crédit sur {years} an(s) : la durée doit être d'au moins un an."
        )
    if rate < 0:
        raise ValueError(f"Taux du crédit de {rate:.2%} : saisissez un taux positif ou nul.")
    if rate == 0:
        return principal / years
    return principal * rate / (1 - (1 + rate) ** -years)


def _row(start: float, initial: float, annual: float, duration: float,
         resale: float = 0.0) -> dict[str, float]:
    return {'start_year': int(start), 'initial_payment': float(initial),
            'annual_payment': float(annual), 'duration_years': int(duration),
            'resale': float(resale)}


def _studies(v: Mapping[str, float]) -> dict[str, float]:
    years = int(v['years'])
    if years < 1:
        raise ValueError("Études sur 0 an : saisissez au moins une année d'études.")
    # Première année au début, puis une par an : n années en tout.
    return _row(v['start'], v['annual_cost'], v['annual_cost'], years - 1)


def _loan(v: Mapping[str, float]) -> dict[str, float]:
    years = int(v['years'])
    annuity = loan_annuity(v['principal'], v['rate'] / 100, years)
    # L'achat est financé l'année de début ; les annuités suivent, une par an.
    return _row(v['start'], 0.0, annuity, years)


def _upkeep(v: Mapping[str, float]) -> dict[str, float]:
    if int(v['years']) == 0 and v['resale'] > 0:
        raise ValueError(
            "Revente sans durée de détention : la revente a lieu à la fin de la "
            "détention, saisissez au moins un an."
        )
    return _row(v['start'], v['cost'], v['upkeep'], v['years'], v['resale'])


TEMPLATES: dict[str, ProjectTemplate] = {
    'custom': ProjectTemplate(
        "Projet libre",
        "Vous décrivez vous-même le projet : un versement l'année de début, puis un "
        "versement chaque année pendant la durée, et une éventuelle revente en fin "
        "de projet, qui s'ajoute au dernier versement.",
        (Field('start', "Début, dans combien d'années", 'year'),
         Field('initial', "Versement initial (€)", 'amount'),
         Field('annual', "Versement annuel (€)", 'amount'),
         Field('years', "Durée des versements annuels (ans)", 'years'),
         Field('resale', "Revente en fin de projet (€)", 'amount')),
        lambda v: _row(v['start'], v['initial'], v['annual'], v['years'], v['resale']),
    ),
    'one_off': ProjectTemplate(
        "Dépense ponctuelle (voyage, achat)",
        "Une dépense payée en une fois, à une date donnée.",
        (Field('start', "Dans combien d'années", 'year'),
         Field('cost', "Montant de la dépense (€)", 'amount')),
        lambda v: _row(v['start'], v['cost'], 0.0, 0),
    ),
    'upkeep': ProjectTemplate(
        "Achat avec frais d'entretien (voiture, bateau)",
        "Un achat, puis des frais chaque année pendant la détention, et la revente "
        "éventuelle à la fin.",
        (Field('start', "Achat dans combien d'années", 'year'),
         Field('cost', "Prix d'achat (€)", 'amount'),
         Field('upkeep', "Frais d'entretien annuels (€)", 'amount'),
         Field('years', "Durée de détention (ans)", 'years'),
         Field('resale', "Prix de revente attendu (€, 0 si aucun)", 'amount')),
        _upkeep,
    ),
    'loan': ProjectTemplate(
        "Dépense financée à crédit",
        "Un achat payé par un crédit à annuités constantes : l'annuité est calculée "
        "à partir du montant, du taux et de la durée que vous saisissez.",
        (Field('start', "Achat dans combien d'années", 'year'),
         Field('principal', "Montant emprunté (€)", 'amount'),
         Field('rate', "Taux du crédit (%)", 'rate'),
         Field('years', "Durée du crédit (ans)", 'years')),
        _loan,
    ),
    'studies': ProjectTemplate(
        "Études supérieures",
        "Un coût annuel pendant chaque année d'études.",
        (Field('start', "Début des études, dans combien d'années", 'year'),
         Field('annual_cost', "Coût annuel (€)", 'amount'),
         Field('years', "Nombre d'années d'études", 'years')),
        _studies,
    ),
    'energy_works': ProjectTemplate(
        "Travaux d'économie d'énergie (chauffage, isolation, panneaux solaires)",
        "Le coût des travaux, puis l'économie annuelle sur la durée de vie de "
        "l'installation, qui revient dans votre épargne. Les aides et crédits "
        "d'impôt ne sont pas comptés.",
        (Field('start', "Travaux dans combien d'années", 'year'),
         Field('cost', "Coût des travaux (€)", 'amount'),
         Field('saving', "Économie annuelle attendue (€)", 'amount'),
         Field('years', "Durée de vie de l'installation (ans)", 'years')),
        lambda v: _row(v['start'], v['cost'], -v['saving'], v['years']),
    ),
    'income_investment': ProjectTemplate(
        "Investissement avec recette annuelle",
        "Une mise de départ, puis une recette chaque année pendant la période. "
        "La recette est saisie nette d'impôt : elle n'est pas imposée ici.",
        (Field('start', "Investissement dans combien d'années", 'year'),
         Field('cost', "Mise de départ (€)", 'amount'),
         Field('income', "Recette annuelle nette (€)", 'amount'),
         Field('years', "Durée de la période (ans)", 'years')),
        lambda v: _row(v['start'], v['cost'], -v['income'], v['years']),
    ),
}


def project_row(template_id: str, name: str, values: Mapping[str, float | None]) -> dict:
    """
    Ligne projet (format de la page Projets) à partir des réponses à un modèle.

    Raises:
        ValueError: modèle inconnu, nom vide, réponse manquante ou incohérente ;
            le message dit quoi saisir.
    """
    if template_id not in TEMPLATES:
        raise ValueError(
            f"Modèle de projet inconnu : {template_id!r}. Choisissez parmi "
            f"{', '.join(TEMPLATES)}."
        )
    template = TEMPLATES[template_id]
    if not name.strip():
        raise ValueError("Donnez un nom au projet.")
    missing = [f.label for f in template.fields if values.get(f.key) is None]
    if missing:
        raise ValueError(f"À renseigner (0 si sans objet) : {', '.join(missing)}.")
    answers = {f.key: float(v) for f in template.fields if (v := values.get(f.key)) is not None}
    return {'name': name.strip(), **template.build(answers)}
