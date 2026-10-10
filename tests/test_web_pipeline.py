"""
Calcul de l'interface web : il passe par GSE++ et le catalogue choisi, sans
allocation fiscale figée.
"""

from __future__ import annotations

import pytest

from web_ui.pipeline import run_projection


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
