"""
Calcul de l'interface web : il passe par GSE++ et le catalogue choisi, sans
allocation fiscale figée.
"""

from __future__ import annotations

import numpy as np
import pytest

from investment_calculator.modules.household_tax import household_shares, marginal_rate
from investment_calculator.placement_catalog import load_placement_catalog
from web_ui.pipeline import (
    budget_marginal_rate,
    build_profile_config,
    build_projects,
    run_projection,
)


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
        'av_uc_actions', 'livret_a', 'av_scpi',
    }
    # Sans budget du foyer, la tranche marginale est inconnue : la SCPI en direct est écartée.
    assert list(results['optimization']['excluded_placements']) == ['scpi_direct']
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
    for page in ('Profile', 'Holdings', 'Projects', 'Budget', 'Projection'):
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
    assert any('Du capital de départ' in m.value for m in app.markdown)


# --- Projets du foyer et plan par tranches ---------------------------------------

PROJECT_ROWS = [
    {'name': 'voiture', 'start_year': 3, 'initial_payment': 15_000.0,
     'annual_payment': 0.0, 'duration_years': 0, 'resale': 0.0},
    {'name': 'études', 'start_year': 6, 'initial_payment': 2_000.0,
     'annual_payment': 4_000.0, 'duration_years': 3, 'resale': 1_000.0},
]


def test_la_revente_saisie_s_ajoute_au_dernier_versement() -> None:
    voiture, etudes = build_projects(PROJECT_ROWS)
    assert voiture.exit_amount == 0.0
    # Saisie positive, flux sortant négatif : 4 000 − 1 000 l'année 9.
    assert etudes.exit_amount == -1_000.0
    with pytest.raises(ValueError, match="Projet « bateau »"):
        build_projects([{**PROJECT_ROWS[0], 'name': 'bateau', 'duration_years': -1}])


def _tranche_results(available_savings: float | None = 20_000.0, rows=PROJECT_ROWS) -> dict:
    config = build_profile_config({**FORM, 'retirement_age': 55, 'holdings': []})
    return run_projection(config, num_scenarios=30, catalog_id='fr-2026', risk_aversion=5.0,
                          risk_free_placement=None, projects=build_projects(rows),
                          available_savings=available_savings)


def test_le_plan_par_tranches_place_tout_le_capital() -> None:
    plan = _tranche_results()['tranche_plan']
    # 20 000 € disponibles, 3 600 € par an dès l'année 0 (premier versement du
    # profil), moins les projets : calcul à la main.
    outflows = {3: 15_000.0, 6: 2_000.0, 7: 4_000.0, 8: 4_000.0, 9: 3_000.0}
    expected, capital = [], 20_000.0
    for year in range(16):
        capital += 3_600.0 - outflows.get(year, 0.0)
        expected.append(capital)
    assert plan['capital'] == pytest.approx(expected)
    placed = plan['amounts'].sum(axis=1) + plan['unplaced']
    assert placed.tolist() == pytest.approx(expected)
    # La voiture est financée par une tranche retirée l'année 3.
    assert any(t['withdrawal_year'] == 3 and t['start_year'] == 0 for t in plan['tranches'])
    assert plan['known_gaps']


def test_un_projet_non_finance_est_refuse() -> None:
    with pytest.raises(ValueError, match="pas financés"):
        _tranche_results(available_savings=0.0)


def test_des_projets_sans_epargne_disponible_sont_refuses() -> None:
    with pytest.raises(ValueError, match="épargne déjà disponible"):
        _tranche_results(available_savings=None)


def test_projets_saisis_dans_l_application() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file('../web_ui/app_enhanced.py', default_timeout=60).run()
    app.session_state['form'] = {**{k: v for k, v in FORM.items() if k != 'holdings'},
                                 'retirement_age': 55}
    app.session_state['page'] = 'Projects'
    app.run()
    app.text_input[0].set_value('voiture')
    available, *fields = app.number_input
    available.set_value(20_000.0)
    for field, value in zip(fields, (3, 15_000.0, 0.0, 0, 0.0), strict=True):
        field.set_value(value)
    _click(app, 'Ajouter le projet')
    assert app.session_state['projects'] == [PROJECT_ROWS[0]]
    assert app.session_state['available_savings'] == 20_000.0
    app.session_state['page'] = 'Projection'
    app.run()
    _click(app, 'Lancer')
    assert not app.exception and not app.error
    assert 'tranche_plan' in app.session_state['results']
    assert any('Plan par tranches' in m.value for m in app.markdown)


# --- Budget du foyer ------------------------------------------------------------

BUDGET = {
    'earners': [
        {'taxable_income': 40_000.0, 'annual_growth': 0.01, 'retirement_year': 12,
         'replacement_rate': 0.6},
        {'taxable_income': 25_000.0, 'annual_growth': 0.0, 'retirement_year': None,
         'replacement_rate': None},
    ],
    'rent': 0.0, 'dependent_years': [5],
    'loans': [{'name': 'résidence', 'annual_payment': 9_000.0, 'rate': 0.015, 'years_left': 10}],
    'expenses_follow_income': False,
}


def _budget_results(projects=(), available_savings=None) -> dict:
    config = build_profile_config({**FORM, 'retirement_age': 55, 'holdings': []})
    return run_projection(config, num_scenarios=20, catalog_id='fr-2026', risk_aversion=5.0,
                          risk_free_placement=None, couple=True, budget=BUDGET,
                          projects=projects, available_savings=available_savings)


def test_le_budget_part_de_l_epargne_du_profil() -> None:
    table = _budget_results()['budget']['table']
    assert len(table) == 16
    # L'épargne de l'année 0 est celle du profil : 300 € par mois.
    assert table['free_savings'].iloc[0] == pytest.approx(3_600.0)
    # Fin du crédit à l'année 10 : l'épargne libre monte de l'annuité.
    assert table['loan_payments'].iloc[9] == pytest.approx(9_000.0)
    assert table['loan_payments'].iloc[10] == 0.0
    d = table.iloc[10] - table.iloc[9]
    jump = d['salaries'] + d['pensions'] - d['income_tax'] + 9_000.0
    assert d['free_savings'] == pytest.approx(jump)


def test_la_tranche_marginale_vient_du_budget() -> None:
    catalog = load_placement_catalog('fr-2026')
    expected = marginal_rate(
        catalog.regime, 65_000.0, household_shares(catalog.regime, adults=2, dependents=1)
    )
    assert budget_marginal_rate(BUDGET, catalog=catalog) == pytest.approx(expected)
    assert expected > 0


def test_avec_le_budget_la_scpi_en_direct_est_proposee() -> None:
    results = _budget_results()
    assert 'scpi_direct' in results['optimization']['optimal_portfolio']['weights']
    assert 'excluded_placements' not in results['optimization']


def test_l_epargne_libre_alimente_le_plan_par_tranches() -> None:
    results = _budget_results(build_projects(PROJECT_ROWS[:1]), available_savings=20_000.0)
    savings = results['budget']['table']['free_savings'].to_numpy()
    capital = np.asarray(results['tranche_plan']['capital'])
    expected = 20_000.0 + np.cumsum(savings)
    expected[3:] -= 15_000.0
    np.testing.assert_allclose(capital, expected)


def test_un_budget_incoherent_est_refuse() -> None:
    config = build_profile_config({**FORM, 'monthly_amount': 10_000.0, 'holdings': []})
    with pytest.raises(ValueError, match="dépenses seraient négatives"):
        run_projection(config, num_scenarios=10, catalog_id='fr-2026', risk_aversion=5.0,
                       risk_free_placement=None, couple=True, budget=BUDGET)


def test_budget_saisi_dans_l_application() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file('../web_ui/app_enhanced.py', default_timeout=60).run()
    app.session_state['form'] = {**{k: v for k, v in FORM.items() if k != 'holdings'},
                                 'retirement_age': 55}
    app.session_state['page'] = 'Budget'
    app.run()
    assert not app.exception
    app.text_input[0].set_value('résidence')
    loan_fields = app.number_input[:3]
    for field, value in zip(loan_fields, (9_000.0, 1.5, 10), strict=True):
        field.set_value(value)
    _click(app, 'Ajouter le crédit')
    assert app.session_state['loans'] == BUDGET['loans']
    budget_fields = app.number_input[3:]
    values = (40_000.0, 1.0, 12, 60.0, 25_000.0, 0.0, None, None, 0.0)
    for field, value in zip(budget_fields, values, strict=True):
        field.set_value(value)
    app.text_input[1].set_value('5')
    _click(app, 'Enregistrer le budget')
    assert not app.error
    assert app.session_state['budget']['earners'][0]['replacement_rate'] == pytest.approx(0.6)
    app.session_state['page'] = 'Projection'
    app.run()
    _click(app, 'Lancer')
    assert not app.exception and not app.error
    assert any('Budget du foyer' in m.value for m in app.markdown)
