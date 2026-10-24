"""
Flux de trésorerie du foyer : portage de ``Exp_fin`` (legacy/R_scripts/Exp_finance_hist.R).
"""

from __future__ import annotations

import numpy as np
import pytest

from investment_calculator.modules.household_flows import (
    Project,
    check_available_capital,
    project_flows,
    projects_from_config,
)
from investment_calculator.modules.user_profile import UserProfileManager


def _exp_fin_r(m_projets: list[list[float]], horiz: int, sal_net: float, epar: float):
    """Transcription ligne à ligne de ``Exp_fin`` (indices R décalés de 1)."""
    hist = np.zeros((len(m_projets) + 1, horiz + 1))
    for i, (an_debut, m_debut, m_vers, duree, m_sortie) in enumerate(m_projets):
        an_debut, duree = int(an_debut), int(duree)
        if an_debut != 0:
            hist[i, an_debut] = m_debut
            if duree > 0:
                hist[i, an_debut + 1:an_debut + 1 + duree] = m_vers
                hist[i, an_debut + duree] = m_sortie
    hist[-1, 0] = -epar
    hist[-1, 1:] = -sal_net
    return -np.cumsum(hist.sum(axis=0))


VOITURE = Project("voiture", start_year=2, initial_payment=10_000.0, annual_payment=1_000.0,
                  duration=3, resale_value=4_000.0)


def test_courbe_de_capital_conforme_au_code_r() -> None:
    savings = np.array([0.0] + [5_000.0] * 6)
    capital = check_available_capital(savings - project_flows([VOITURE], 6).sum(axis=0))
    reference = _exp_fin_r([[2, 10_000, 1_000, 3, -4_000]], 6, 5_000.0, 0.0)
    # Seul écart voulu : la revente s'ajoute au dernier versement (1 000 €),
    # que le R écrasait.
    np.testing.assert_allclose(capital[:5], reference[:5])
    np.testing.assert_allclose(capital[5:] - reference[5:], -1_000.0)
    np.testing.assert_allclose(capital, [0, 5_000, 0, 4_000, 8_000, 16_000, 21_000])


def test_projet_sans_duree_et_hors_horizon() -> None:
    flows = project_flows([Project("études", 4, 3_000.0, 2_000.0, 5, 0.0),
                           Project("vacances", 0, 1_500.0, 0.0, 0, 9_999.0)], 6)
    np.testing.assert_allclose(flows[0], [0, 0, 0, 0, 3_000, 2_000, 2_000])
    # Sans durée, ni versement annuel ni revente, comme dans le R.
    np.testing.assert_allclose(flows[1], [1_500, 0, 0, 0, 0, 0, 0])


def test_foyer_a_decouvert_refuse() -> None:
    with pytest.raises(ValueError, match="il manque 5,000 € l'année 2"):
        check_available_capital(np.array([0.0, 5_000.0, -10_000.0, 5_000.0]))


def test_saisie_incomplete_ou_negative_refusee() -> None:
    with pytest.raises(ValueError, match="resale_value"):
        projects_from_config([{"name": "x", "start_year": 1, "initial_payment": 1.0,
                               "annual_payment": 0.0, "duration": 0}])
    with pytest.raises(ValueError, match="en positif"):
        Project("x", 1, -1.0, 0.0, 0, 0.0)


def test_les_projets_deviennent_des_retraits_du_profil() -> None:
    config = {
        "user_profile": {
            "personal_info": {"age": 40, "retirement_age": 50, "life_expectancy": 60},
            "financial_situation": {"current_savings": 0, "annual_income": 50_000},
            "investment_preferences": {"time_horizon": 10},
        },
        "contribution_schedule": [{"start_year": 0, "end_year": 10, "monthly_amount": 500,
                                   "annual_increase": 0.0}],
        "projects": [{"name": "voiture", "start_year": 2, "initial_payment": 10_000,
                      "annual_payment": 1_000, "duration": 3, "resale_value": 4_000}],
    }
    series = UserProfileManager().process(config)["investment_time_series"]
    np.testing.assert_allclose(series["withdrawal"][:7], [0, 0, 10_000, 1_000, 1_000, -3_000, 0])
    assert series["purpose"][2] == "voiture"
    config["projects"][0]["initial_payment"] = 20_000
    with pytest.raises(ValueError, match="dépassent l'épargne disponible"):
        UserProfileManager().process(config)
