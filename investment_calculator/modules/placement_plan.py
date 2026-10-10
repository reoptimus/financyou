"""
Chaîne complète GSE → GSE+ → GSE++ → Markowitz → projection du patrimoine.

Ce module enchaîne, pour un utilisateur et un horizon, les briques de la
refonte (ADR 0002) et rend un dictionnaire au format attendu par
:class:`investment_calculator.modules.reporting.ReportGenerator` :

1. GSE+ : rendement de chaque placement du catalogue, net de frais annuels ;
2. GSE++ : rendement net de frais et d'impôts à l'horizon H, pour un versement
   égal aux versements totaux de l'utilisateur (abattement et seuils de
   l'assurance-vie) ;
3. Markowitz sur les moments de GSE++, sous les plafonds de versement ;
4. projection des versements réels selon les poids retenus.

Définitions des indicateurs restitués :

- ``expected_return`` et ``expected_volatility`` : moyenne et écart-type, sur
  les scénarios, du rendement net annualisé du portefeuille à l'horizon H ;
- ``sharpe_ratio`` : ``(expected_return − r) / expected_volatility``, où ``r``
  est le rendement net annualisé moyen à H du placement de référence
  ``risk_free_placement`` (le Livret A dans l'exemple). Sans placement de
  référence, le ratio n'est pas calculé et vaut ``None`` ;
- ``max_drawdown`` : médiane, sur les scénarios, de la perte maximale depuis un
  plus haut d'un euro placé selon les poids et conservé sans rééquilibrage, sur
  GSE+ (avant impôt).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from investment_calculator.modules.net_returns import TaxProfile, build_net_returns
from investment_calculator.modules.placement_optimizer import (
    efficient_frontier,
    optimize_horizon,
    placement_constraints,
)
from investment_calculator.modules.placements import build_gross_placements
from investment_calculator.modules.wealth_simulation import contribution_flows, simulate_wealth
from investment_calculator.placement_catalog import PlacementCatalog

logger = logging.getLogger(__name__)

__all__ = ["max_drawdown", "plan_placements"]


def max_drawdown(gross: pd.DataFrame, weights: pd.Series, horizon: int) -> float:
    """
    Médiane, sur les scénarios, de la perte maximale depuis un plus haut d'un
    euro investi selon ``weights`` sans rééquilibrage, sur GSE+ jusqu'à ``horizon``.
    """
    ordered = gross.sort_index()[list(weights.index)]
    n_scenarios = ordered.index.get_level_values(0).nunique()
    returns = ordered.to_numpy(dtype=float).reshape(n_scenarios, -1, len(weights))[:, :horizon]
    growth = np.cumprod(1.0 + returns, axis=1)
    value = np.concatenate([np.ones((n_scenarios, 1)), growth @ weights.to_numpy()], axis=1)
    peak = np.maximum.accumulate(value, axis=1)
    return float(np.median((1.0 - value / peak).max(axis=1)))


def plan_placements(
    scenarios: pd.DataFrame,
    catalog: PlacementCatalog,
    time_series: pd.DataFrame,
    *,
    horizon: int,
    objective: str,
    risk_aversion: float | None = None,
    target_return: float | None = None,
    risk_free_placement: str | None = None,
    goal_amount: float | None = None,
    couple: bool = False,
    wrapper_seniority: dict[str, float] | None = None,
    frontier_points: int = 20,
    max_equity: float | None = None,
    min_bond: float | None = None,
) -> dict[str, Any]:
    """
    Allocation optimale entre les placements du catalogue et patrimoine projeté.

    Args:
        scenarios: sortie ``scenarios`` du GSE.
        catalog: catalogue des placements (et régime fiscal).
        time_series: ``investment_time_series`` du profil utilisateur.
        horizon: durée de détention H, en années, au plus la durée des scénarios.
        objective, risk_aversion, target_return: voir
            :func:`~investment_calculator.modules.placement_optimizer.optimize_horizon`.
        risk_free_placement: placement de référence du ratio de Sharpe ; requis
            pour l'objectif ``max_sharpe``.
        goal_amount: patrimoine net visé, pour la probabilité de l'atteindre.
        couple, wrapper_seniority: situation fiscale (:class:`TaxProfile`).
        frontier_points: nombre de points de la frontière efficiente.
        max_equity, min_bond: contraintes du profil (``max_equity_allocation``,
            ``min_bond_allocation``) ; voir
            :func:`~investment_calculator.modules.placement_optimizer.placement_constraints`.

    Raises:
        ValueError: placement de référence inconnu, ou entrées refusées par
            les modules appelés.
    """
    gross = build_gross_placements(scenarios, catalog)
    placement_ids = list(gross.columns)
    if risk_free_placement is not None and risk_free_placement not in placement_ids:
        raise ValueError(
            f"Placement de référence {risk_free_placement!r} absent du catalogue "
            f"{catalog.id}. Placements disponibles : {placement_ids}."
        )
    if objective == "max_sharpe" and risk_free_placement is None:
        raise ValueError(
            "L'objectif 'max_sharpe' demande risk_free_placement, le placement dont le "
            "rendement net moyen sert de taux sans risque (par exemple 'livret_a')."
        )
    flows = contribution_flows(time_series, horizon)
    total = float(flows.sum())
    profile = TaxProfile(
        invested_amount=total, couple=couple, wrapper_seniority=wrapper_seniority or {}
    )
    net = build_net_returns(gross, catalog, profile, [horizon])
    constraints = placement_constraints(
        catalog, placement_ids, total_contributions=total, n_periods=horizon,
        max_equity=max_equity, min_bond=min_bond,
    )
    risk_free_rate = (
        float(net.annualized(horizon)[risk_free_placement].mean())
        if risk_free_placement is not None
        else None
    )
    allocation = optimize_horizon(
        net, horizon, constraints, objective=objective, risk_aversion=risk_aversion,
        target_return=target_return, risk_free_rate=risk_free_rate,
    )
    weights = allocation.weights.clip(lower=0.0)
    weights = weights / weights.sum()

    simulation = simulate_wealth(gross, catalog, profile, weights, flows, horizon)
    sharpe = (
        (allocation.expected_return - risk_free_rate) / allocation.volatility
        if risk_free_rate is not None and allocation.volatility > 0
        else None
    )
    years = [str(t) for t in range(horizon + 1)]
    wealth_paths = pd.DataFrame(simulation.value_paths, columns=years)
    wealth_paths.insert(0, "scenario_id", simulation.scenario_ids)

    results: dict[str, Any] = {
        "optimal_portfolio": {
            "weights": {str(p): float(w) for p, w in weights.items()},
            "expected_return": allocation.expected_return,
            "expected_volatility": allocation.volatility,
            "sharpe_ratio": sharpe,
            "risk_free_rate": risk_free_rate,
            "risk_free_placement": risk_free_placement,
            "max_drawdown": max_drawdown(gross, weights, horizon),
            "horizon": horizon,
            "objective": objective,
            "placement_catalog": catalog.id,
        },
        "efficient_frontier": efficient_frontier(
            net, horizon, constraints, n_points=frontier_points
        ),
        "simulation_results": {
            "wealth_paths": wealth_paths,
            "wealth_paths_label": "avant impôt de sortie",
            "terminal_wealth": pd.DataFrame(
                {"scenario_id": simulation.scenario_ids, "wealth": simulation.net_terminal}
            ),
            "statistics": simulation.statistics(),
        },
        "constraints_explanation": constraints.explanation,
        "known_gaps": catalog.known_gaps,
    }
    if goal_amount is not None:
        terminal = simulation.net_terminal
        results["goal_analysis"] = {
            "goal_amount": float(goal_amount),
            "probability_of_achieving": float((terminal >= goal_amount).mean()),
            "expected_surplus": float((terminal - goal_amount).mean()),
        }
    return results
