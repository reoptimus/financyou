"""
Modèles de projets repris des prototypes R : chacun se traduit dans le format
projet du moteur, sans valeur ajoutée.
"""

from __future__ import annotations

import pytest

from investment_calculator.modules.household_cash_flow import project_flows
from web_ui.pipeline import build_projects
from web_ui.project_templates import TEMPLATES, loan_annuity, project_row


def _flows(template_id: str, values: dict, horizon: int = 15) -> list[float]:
    (project,) = build_projects([project_row(template_id, 'p', values)])
    return project_flows(project, horizon).tolist()


def test_annuite_constante_calculee_a_la_main() -> None:
    # 10 000 € à 3 % sur 5 ans : 10 000 × 0,03 / (1 − 1,03^−5) = 2 183,55 €.
    assert loan_annuity(10_000.0, 0.03, 5) == pytest.approx(2_183.5457, abs=1e-3)
    assert loan_annuity(10_000.0, 0.0, 4) == 2_500.0
    with pytest.raises(ValueError, match="au moins un an"):
        loan_annuity(10_000.0, 0.03, 0)


def test_depense_a_credit_rembourse_les_annees_suivantes() -> None:
    flows = _flows('loan', {'start': 2, 'principal': 10_000.0, 'rate': 3.0, 'years': 5})
    assert flows[2] == 0.0
    assert flows[3:8] == pytest.approx([2_183.5457] * 5, abs=1e-3)
    assert sum(flows[8:]) == 0.0


def test_etudes_un_cout_par_annee_d_etudes() -> None:
    flows = _flows('studies', {'start': 4, 'annual_cost': 6_000.0, 'years': 3})
    assert flows[4:7] == [6_000.0] * 3
    assert sum(flows) == 18_000.0
    with pytest.raises(ValueError, match="au moins une année"):
        project_row('studies', 'p', {'start': 4, 'annual_cost': 6_000.0, 'years': 0})


def test_travaux_l_economie_revient_dans_l_epargne() -> None:
    flows = _flows('energy_works', {'start': 1, 'cost': 12_000.0, 'saving': 800.0, 'years': 10})
    assert flows[1] == 12_000.0
    assert flows[2:12] == [-800.0] * 10


def test_achat_avec_entretien_et_revente() -> None:
    flows = _flows('upkeep', {'start': 0, 'cost': 30_000.0, 'upkeep': 1_500.0,
                              'years': 8, 'resale': 9_000.0})
    assert flows[0] == 30_000.0
    assert flows[1:8] == [1_500.0] * 7
    assert flows[8] == 1_500.0 - 9_000.0


def test_projet_libre_identique_a_la_saisie_d_avant() -> None:
    row = project_row('custom', ' voiture ', {'start': 3, 'initial': 15_000.0, 'annual': 0.0,
                                               'years': 0, 'resale': 0.0})
    assert row == {'name': 'voiture', 'start_year': 3, 'initial_payment': 15_000.0,
                   'annual_payment': 0.0, 'duration_years': 0, 'resale': 0.0}


@pytest.mark.parametrize('template_id', list(TEMPLATES))
def test_une_reponse_manquante_est_nommee(template_id: str) -> None:
    template = TEMPLATES[template_id]
    values = {f.key: 1.0 for f in template.fields}
    values[template.fields[-1].key] = None
    with pytest.raises(ValueError, match=template.fields[-1].label.split(' (')[0]):
        project_row(template_id, 'p', values)
    with pytest.raises(ValueError, match="nom"):
        project_row(template_id, '  ', {f.key: 1.0 for f in template.fields})


def test_modele_choisi_dans_l_application() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file('../web_ui/app_enhanced.py', default_timeout=60).run()
    app.session_state['page'] = 'Projects'
    app.run()
    app.selectbox(key='project_template').set_value('loan').run()
    app.text_input[0].set_value('cuisine')
    for key, value in (('start', 2), ('principal', 10_000.0), ('rate', 3.0), ('years', 5)):
        app.number_input(key=f'project_loan_{key}').set_value(value)
    next(b for b in app.button if 'Ajouter le projet' in b.label).click().run()
    assert not app.exception and not app.error
    (row,) = app.session_state['projects']
    assert row['annual_payment'] == pytest.approx(2_183.5457, abs=1e-3)
    assert row['duration_years'] == 5 and row['initial_payment'] == 0.0
