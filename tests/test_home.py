"""
Logement du foyer, repris des prototypes R (écran Vous, bloc Logement) :
locataire ou propriétaire, crédit de la résidence principale, valeur du bien.
"""

from __future__ import annotations

import numpy as np
import pytest

from investment_calculator.market_assumptions import load_market_assumptions
from web_ui.pipeline import build_home, build_profile_config, home_loan, run_projection

OWNER = {'status': 'owner', 'value': 300_000.0, 'paid': False,
         'monthly_payment': 1_000.0, 'rate': 2.0, 'years_left': 15}


def test_locataire_loyer_mensuel_annualise() -> None:
    rent, home = build_home({'status': 'tenant', 'monthly_rent': 950.0})
    assert rent == 11_400.0
    assert home == {'owner': False, 'value': None, 'loan': None}
    assert home_loan(home) is None


def test_proprietaire_avec_credit() -> None:
    rent, home = build_home(OWNER)
    assert rent == 0.0
    loan = home_loan(home)
    assert loan is not None
    assert (loan.annual_payment, loan.rate, loan.years_left) == (12_000.0, 0.02, 15)
    _, paid = build_home({**OWNER, 'paid': True})
    assert paid['loan'] is None


@pytest.mark.parametrize('answers, missing', [
    ({}, "locataire ou propriétaire"),
    ({'status': 'tenant'}, "loyer mensuel"),
    ({'status': 'owner', 'paid': True}, "valeur estimée"),
    ({'status': 'owner', 'value': 1.0}, "fini de payer"),
    ({**OWNER, 'rate': None}, "taux du crédit"),
])
def test_une_reponse_manquante_est_nommee(answers: dict, missing: str) -> None:
    with pytest.raises(ValueError, match=missing):
        build_home(answers)


def _budget(home_answers: dict) -> dict:
    rent, home = build_home(home_answers)
    return {
        'earners': [{'taxable_income': 60_000.0, 'annual_growth': 0.0,
                     'retirement_year': None, 'replacement_rate': None}],
        'rent': rent, 'home': home, 'dependent_years': [], 'loans': [],
        'expenses_follow_income': False,
    }


def _run(budget: dict) -> dict:
    form = {'age': 40, 'retirement_age': 55, 'couple': False, 'annual_income': 60_000.0,
            'annual_expenses': None, 'monthly_amount': 1_500.0, 'annual_increase': 0.0,
            'max_equity': None, 'min_bond': None, 'holdings': []}
    results = run_projection(build_profile_config(form), num_scenarios=20,
                             catalog_id='fr-2026', risk_aversion=5.0,
                             risk_free_placement=None, budget=budget)
    return results


def test_le_credit_de_la_residence_entre_dans_le_budget() -> None:
    results = _run(_budget(OWNER))
    table = results['budget']['table']
    assert table['loan_payments'][:15].tolist() == [12_000.0] * 15
    assert table['loan_payments'][15] == 0.0
    # Valeur nette l'année 0 : valeur saisie moins le capital restant dû,
    # 12 000 × (1 − 1,02^−15) / 0,02 = 154 191,1 €.
    bands = results['budget']['home_equity']
    np.testing.assert_allclose(bands.loc[0], 300_000.0 - 154_191.10, atol=0.1)
    # Ensuite, la valeur suit l'indice immobilier du GSE, net du rendement locatif.
    scenarios = results['scenarios']['scenarios']
    returns = scenarios.pivot(index='scenario_id', columns='time_period',
                              values='real_estate_return').to_numpy()
    rental_yield = load_market_assumptions().real_estate_rental_yield
    final = 300_000.0 * np.prod(1 + returns[:, :15] - rental_yield, axis=1)
    assert bands.loc[15, 'median'] == pytest.approx(np.median(final))
    assert bands.loc[15, 'p5'] < bands.loc[15, 'median'] < bands.loc[15, 'p95']


def test_un_locataire_n_a_pas_de_valeur_de_logement() -> None:
    results = _run(_budget({'status': 'tenant', 'monthly_rent': 900.0}))
    assert 'home_equity' not in results['budget']
    assert results['budget']['table']['rent'][0] == 10_800.0


def test_logement_saisi_dans_l_application() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file('../web_ui/app_enhanced.py', default_timeout=60).run()
    app.session_state['form'] = {'age': 40, 'retirement_age': 55, 'couple': False,
                                 'annual_income': 60_000.0, 'annual_expenses': None,
                                 'monthly_amount': 1_500.0, 'annual_increase': 0.0,
                                 'max_equity': None, 'min_bond': None}
    app.session_state['page'] = 'Budget'
    app.run()
    app.radio(key='home_status').set_value('owner').run()
    app.number_input(key='home_value').set_value(300_000.0)
    app.radio(key='home_paid').set_value(False).run()
    for key, value in (('home_payment', 1_000.0), ('home_rate', 2.0), ('home_years', 15)):
        app.number_input(key=key).set_value(value)
    app.number_input(key='inc0').set_value(60_000.0)
    app.number_input(key='gro0').set_value(0.0)
    next(b for b in app.button if 'Enregistrer le budget' in b.label).click().run()
    assert not app.exception and not app.error
    assert app.session_state['budget']['home'] == _budget(OWNER)['home']
