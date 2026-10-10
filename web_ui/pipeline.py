"""
Calcul lancé par l'interface : GSE → GSE+ → GSE++ → Markowitz par placement.

Séparé de ``app_enhanced.py`` pour être testé sans Streamlit. L'interface ne
fait que rassembler les choix de l'utilisateur et afficher le résultat.
"""

from __future__ import annotations

from typing import Any

from investment_calculator.modules import scenario_generator, user_profile
from investment_calculator.modules.placement_plan import plan_placements
from investment_calculator.placement_catalog import load_placement_catalog


def run_projection(
    profile_config: dict[str, Any],
    *,
    num_scenarios: int,
    catalog_id: str,
    risk_aversion: float,
    risk_free_placement: str | None,
) -> dict[str, Any]:
    """
    Projeter le profil sur les placements du catalogue choisi.

    L'horizon est celui du profil (``investment_preferences.time_horizon``) ;
    les scénarios sont générés sur cette durée, graine 42.

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
    )
    return {
        'scenarios': scenario_results,
        'profile': profile_results,
        'catalog': catalog.id,
        'optimization': optimization,
    }
