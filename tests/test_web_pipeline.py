"""
Calcul de l'interface web : il passe par GSE++ et le catalogue choisi, sans
allocation fiscale figée.
"""

from __future__ import annotations

import pytest

from web_ui.pipeline import build_profile_config, run_projection


def _profile(age: int = 40, retirement_age: int = 50) -> dict:
    return {
        'user_profile': {
            'personal_info': {'age': age, 'retirement_age': retirement_age,
                              'life_expectancy': 90},
            'financial_situation': {'current_savings': 0, 'annual_income': 60_000,
                                    'annual_expenses': 40_000},
            'investment_preferences': {'time_horizon': retirement_age - age},
        },
        'contribution_schedule': [{'start_year': 0, 'end_year': retirement_age - age,
                                   'monthly_amount': 500, 'annual_increase': 0.0}],
        'withdrawal_schedule': [],
    }


def test_projection_par_placement() -> None:
    results = run_projection(_profile(), num_scenarios=50, catalog_id='fr-2026',
                             risk_aversion=5.0, risk_free_placement='livret_a')
    portfolio = results['optimization']['optimal_portfolio']
    assert results['catalog'] == 'fr-2026'
    assert portfolio['horizon'] == 10
    assert set(portfolio['weights']) == {
        'cto_actions', 'cto_obligations', 'pea_actions', 'av_fonds_euros',
        'av_uc_actions', 'livret_a',
    }
    assert sum(portfolio['weights'].values()) == pytest.approx(1.0)
    assert portfolio['sharpe_ratio'] is not None
    assert {'return', 'volatility'} <= set(results['optimization']['efficient_frontier'])


def test_horizon_nul_refuse() -> None:
    with pytest.raises(ValueError, match="retraite"):
        run_projection(_profile(age=60, retirement_age=60), num_scenarios=10,
                       catalog_id='fr-2026', risk_aversion=5.0, risk_free_placement=None)


FORM = {
    'age': 40, 'retirement_age': 60, 'couple': True, 'annual_income': 50_000.0,
    'annual_expenses': None, 'monthly_amount': 300.0, 'annual_increase': 0.0,
    'max_equity': None, 'min_bond': None,
    'holdings': [{'placement': 'pea_actions', 'value': 30_000.0,
                  'contributions': 20_000.0, 'years_held': 6.0}],
}


def test_le_formulaire_ne_suppose_rien() -> None:
    # Le versement est celui saisi, sans hausse ni contrainte ajoutée ;
    # l'épargne existante est transmise telle quelle.
    config = build_profile_config(FORM)
    schedule = config['contribution_schedule']
    assert schedule == [{'start_year': 0, 'end_year': 20, 'monthly_amount': 300.0,
                         'annual_increase': 0.0}]
    financial = config['user_profile']['financial_situation']
    assert financial == {'current_savings': 30_000.0, 'annual_income': 50_000.0,
                         'existing_holdings': FORM['holdings']}
    assert config['user_profile']['constraints'] == {}
    constrained = build_profile_config({**FORM, 'max_equity': 0.6, 'min_bond': 0.2})
    assert constrained['user_profile']['constraints'] == {
        'max_equity_allocation': 0.6, 'min_bond_allocation': 0.2,
    }


def test_l_epargne_existante_saisie_est_projetee() -> None:
    config = build_profile_config({**FORM, 'retirement_age': 50})
    results = run_projection(config, num_scenarios=20, catalog_id='fr-2026',
                             risk_aversion=5.0, risk_free_placement=None, couple=True)
    held = results['optimization']['existing_holdings']
    assert held == [{'placement': 'pea_actions', 'value': 30_000.0,
                     'contributions': 20_000.0, 'years_held': 6.0}]
    statistics = results['optimization']['simulation_results']['statistics']
    assert statistics['total_contributions'] == pytest.approx(20_000.0 + 3_600.0 * 11)


def test_l_application_s_affiche_sans_saisie() -> None:
    # Chaque page s'ouvre sans valeur préremplie ni erreur.
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file('../web_ui/app_enhanced.py', default_timeout=30).run()
    assert not app.exception
    for page in ('Profile', 'Holdings', 'Projection'):
        app.session_state['page'] = page
        app.run()
        assert not app.exception
    app.session_state['page'] = 'Profile'
    app.run()
    assert all(field.value is None for field in app.number_input)


def _click(app, label: str) -> None:
    next(b for b in app.button if label in b.label).click().run()


def test_parcours_complet_dans_l_application() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file('../web_ui/app_enhanced.py', default_timeout=60).run()
    app.session_state['page'] = 'Profile'
    app.run()
    for field, value in zip(app.number_input, (40, 50, 50_000.0, None, 300.0, 0.0), strict=True):
        field.set_value(value)
    _click(app, 'Enregistrer')
    assert app.session_state['form']['monthly_amount'] == 300.0
    app.session_state['page'] = 'Holdings'
    app.run()
    next(s for s in app.selectbox if s.label == 'Placement').set_value('pea_actions')
    for field, value in zip(app.number_input, (30_000.0, 20_000.0, 6.0), strict=True):
        field.set_value(value)
    _click(app, 'Ajouter')
    assert app.session_state['holdings'] == [{'placement': 'pea_actions', 'value': 30_000.0,
                                              'contributions': 20_000.0, 'years_held': 6.0}]
    app.session_state['page'] = 'Projection'
    app.run()
    _click(app, 'Lancer')
    assert not app.exception and not app.error
    assert app.session_state['results']['optimization']['existing_holdings']
    assert any('Patrimoine net médian' in m.label for m in app.metric)
