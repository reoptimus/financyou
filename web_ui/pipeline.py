"""
Calcul lancé par l'interface : GSE → GSE+ → GSE++ → Markowitz par placement.

Séparé de ``app_enhanced.py`` pour être testé sans Streamlit. L'interface ne
fait que rassembler les choix de l'utilisateur et afficher le résultat.
"""

from __future__ import annotations

from typing import Any

from investment_calculator.modules import scenario_generator, user_profile
from investment_calculator.modules.placement_plan import plan_placements, profile_holdings
from investment_calculator.placement_catalog import load_placement_catalog


def build_profile_config(form: dict[str, Any]) -> dict[str, Any]:
    """
    Configuration du profil à partir de la saisie du formulaire.

    Seules les valeurs saisies sont transmises : rien n'est complété à la place
    de l'utilisateur. Les clés attendues sont ``age``, ``retirement_age``,
    ``annual_income``, ``monthly_amount``, ``annual_increase`` et ``holdings``
    (liste de dictionnaires ``placement``, ``value``, ``contributions``,
    ``years_held``) ; ``annual_expenses``, ``max_equity`` et ``min_bond`` sont
    facultatives (``None`` si non renseignées).

    Raises:
        KeyError: une saisie obligatoire manque.
    """
    horizon = int(form['retirement_age']) - int(form['age'])
    holdings = [dict(h) for h in form['holdings']]
    financial: dict[str, Any] = {
        'current_savings': sum(float(h['value']) for h in holdings),
        'annual_income': float(form['annual_income']),
        'existing_holdings': holdings,
    }
    if form.get('annual_expenses') is not None:
        financial['annual_expenses'] = float(form['annual_expenses'])
    constraints: dict[str, float] = {}
    if form.get('max_equity') is not None:
        constraints['max_equity_allocation'] = float(form['max_equity'])
    if form.get('min_bond') is not None:
        constraints['min_bond_allocation'] = float(form['min_bond'])
    return {
        'user_profile': {
            'personal_info': {
                'age': int(form['age']),
                'retirement_age': int(form['retirement_age']),
            },
            'financial_situation': financial,
            'investment_preferences': {'time_horizon': horizon},
            'constraints': constraints,
        },
        'contribution_schedule': [{
            'start_year': 0,
            'end_year': horizon,
            'monthly_amount': float(form['monthly_amount']),
            'annual_increase': float(form['annual_increase']),
        }],
        'withdrawal_schedule': [],
    }


def run_projection(
    profile_config: dict[str, Any],
    *,
    num_scenarios: int,
    catalog_id: str,
    risk_aversion: float,
    risk_free_placement: str | None,
    couple: bool = False,
) -> dict[str, Any]:
    """
    Projeter le profil sur les placements du catalogue choisi.

    L'horizon est celui du profil (``investment_preferences.time_horizon``) ;
    les scénarios sont générés sur cette durée, graine 42. ``couple`` vaut pour
    l'imposition à la sortie (abattement de l'assurance-vie).

    Returns:
        ``scenarios``, ``profile``, ``catalog`` (identifiant) et ``optimization``
        (sortie de :func:`plan_placements`).
    """
    horizon = int(profile_config['user_profile']['investment_preferences']['time_horizon'])
    if horizon < 1:
        raise ValueError(
            f"Horizon de {horizon} an(s) : l'âge de départ à la retraite doit être "
            "postérieur à l'âge actuel."
        )
    scenario_results = scenario_generator.ScenarioGenerator(random_seed=42).generate({
        'num_scenarios': num_scenarios,
        'time_horizon': horizon,
        'timestep': 1.0,
        'use_stochastic': False,
    })
    profile_results = user_profile.UserProfileManager().process(profile_config)
    catalog = load_placement_catalog(catalog_id)
    optimization = plan_placements(
        scenario_results['scenarios'],
        catalog,
        profile_results['investment_time_series'],
        horizon=horizon,
        objective='mean_variance',
        risk_aversion=risk_aversion,
        risk_free_placement=risk_free_placement,
        max_equity=profile_results['validated_profile']['constraints']['max_equity_allocation'],
        min_bond=profile_results['validated_profile']['constraints']['min_bond_allocation'],
        holdings=profile_holdings(profile_results['validated_profile']),
        couple=couple,
    )
    return {
        'scenarios': scenario_results,
        'profile': profile_results,
        'catalog': catalog.id,
        'optimization': optimization,
    }
