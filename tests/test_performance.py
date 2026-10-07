"""
Étape 1.C.5 : 1 000 scénarios × 30 ans en moins de 5 secondes.

Mesure la fiscalité et l'optimisation (simulation comprise) sur des scénarios
stochastiques de taille réelle. Avant vectorisation : environ 14 s.
"""

import time

import pandas as pd

from investment_calculator.modules import optimizer, scenario_generator, tax_engine

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
    taxed = tax_engine.apply_taxes_simple(scenarios, jurisdiction='FR')
    results = optimizer.PortfolioOptimizer().optimize({
        'scenarios': taxed['after_tax_scenarios'],
        'investment_time_series': pd.DataFrame({'period': range(31), 'net_flow': [1000.0] * 31}),
        'optimization_objective': 'max_sharpe',
    })
    elapsed = time.perf_counter() - start

    assert len(results['simulation_results']['terminal_wealth']) == 1000
    assert elapsed < BUDGET_SECONDS, f"{elapsed:.2f} s pour 1 000 scénarios × 30 ans"
