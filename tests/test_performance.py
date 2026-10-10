"""
Étape 1.C.5 : 1 000 scénarios × 30 ans en moins de 5 secondes.

Mesure la chaîne GSE+ → GSE++ → Markowitz par placement, frontière et
projection du patrimoine comprises, sur des scénarios stochastiques de taille
réelle. Avant vectorisation de l'ancien moteur : environ 14 s.
"""

import time

import pandas as pd

from investment_calculator.modules import scenario_generator
from investment_calculator.modules.placement_plan import plan_placements
from investment_calculator.placement_catalog import load_placement_catalog

BUDGET_SECONDS = 5.0


def test_tax_and_optimization_of_1000_scenarios_over_30_years_under_budget():
    scenarios = scenario_generator.ScenarioGenerator(random_seed=42).generate({
        'num_scenarios': 1000,
        'time_horizon': 30,
        'timestep': 1.0,
        'use_stochastic': True,
        'currency': 'EUR',
        'yield_curve_id': 'eiopa-fr-2018-04',
    })['scenarios']

    start = time.perf_counter()
    results = plan_placements(
        scenarios,
        load_placement_catalog('fr-2026'),
        pd.DataFrame({'period': range(31), 'net_flow': [1000.0] * 31}),
        horizon=30,
        objective='mean_variance',
        risk_aversion=5.0,
        risk_free_placement='livret_a',
    )
    elapsed = time.perf_counter() - start

    assert len(results['simulation_results']['terminal_wealth']) == 1000
    assert elapsed < BUDGET_SECONDS, f"{elapsed:.2f} s pour 1 000 scénarios × 30 ans"
