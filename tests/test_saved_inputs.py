"""Sauvegarde de la saisie dans un fichier et rechargement à l'identique."""

from __future__ import annotations

import json

import pytest

from web_ui.saved_inputs import FORMAT, dump_inputs, load_inputs

STATE = {
    'form': {'age': 40, 'retirement_age': 55, 'couple': True, 'annual_income': 60_000.0,
             'annual_expenses': None, 'monthly_amount': 500.0, 'annual_increase': 0.0,
             'max_equity': None, 'min_bond': None},
    'holdings': [{'placement': 'livret_a', 'value': 10_000.0, 'contributions': 9_000.0,
                  'years_held': 3.0}],
    'projects': [{'name': 'études', 'start_year': 6, 'initial_payment': 2_000.0,
                  'annual_payment': 4_000.0, 'duration_years': 3, 'resale': 0.0}],
    'available_savings': 20_000.0, 'budget': None, 'loans': [], 'properties': [],
    'results': {'non': 'sauvegardé'}, 'page': 'Projection',
}


def test_aller_retour_a_l_identique_sans_les_resultats() -> None:
    text = dump_inputs(STATE)
    assert 'results' not in json.loads(text)
    assert load_inputs(text) == {k: v for k, v in STATE.items() if k not in ('results', 'page')}
    assert load_inputs(text.encode()) == load_inputs(text)


@pytest.mark.parametrize('text, message', [
    ("pas du json", "illisible"),
    (json.dumps({'format': 'autre'}), "Format de saisie"),
    (json.dumps([1, 2]), "Format de saisie"),
    (json.dumps({'format': FORMAT, 'projects': 'voiture'}), "« projects »"),
    (json.dumps({'format': FORMAT, 'available_savings': True}), "« available_savings »"),
])
def test_fichier_refuse_avec_la_raison(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_inputs(text)


def test_les_listes_absentes_sont_vides() -> None:
    inputs = load_inputs(json.dumps({'format': FORMAT}))
    assert inputs['projects'] == [] and inputs['form'] is None
