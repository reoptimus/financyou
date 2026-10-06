"""
Étape 1.C.2 : aucune sortie destinée à l'affichage n'est vide ou constante.

Le dépôt a contenu une cascade fiscale faite de nombres inventés, des soldes de
comptes à 0, un calendrier de rééquilibrage vide et des analyses de
sensibilité vides. Ce test parcourt toutes les sorties de l'optimiseur, du
moteur fiscal et du rapport sur un petit pipeline complet, et échoue dès
qu'une valeur affichable est vide ou ne varie pas d'un scénario à l'autre.
"""

import numpy as np
import pandas as pd
import pytest

from investment_calculator.modules import optimizer, reporting, scenario_generator, tax_engine

# Colonnes légitimement constantes : identifiants, et patrimoine initial
# (identique dans tous les scénarios par construction).
EXEMPT_COLUMNS = {'scenario_id', 'time_period', 'period', 'year_0'}


@pytest.fixture(scope='module')
def pipeline_outputs():
    scenarios = scenario_generator.ScenarioGenerator(random_seed=42).generate({
        'num_scenarios': 100,
        'time_horizon': 10,
        'timestep': 1.0,
        'use_stochastic': True,
        'currency': 'EUR',
        'yield_curve_id': 'eiopa-fr-2018-04',
    })['scenarios']
    tax_results = tax_engine.apply_taxes_simple(scenarios, jurisdiction='FR')
    opt_results = optimizer.PortfolioOptimizer().optimize({
        'scenarios': tax_results['after_tax_scenarios'],
        'investment_time_series': pd.DataFrame({
            'period': range(10), 'contribution': [1000.0] * 10, 'net_flow': [1000.0] * 10
        }),
        'optimization_objective': 'max_sharpe',
        'goal_amount': 20000,
    })
    report = reporting.ReportGenerator().generate({
        'optimization_results': opt_results,
        'tax_results': tax_results,
        'report_config': {'format': 'json'},
    })
    return {'tax': tax_results, 'optimizer': opt_results, 'report': report}


def _find_empty_or_constant(value, path):
    """Renvoie la liste des chemins dont la valeur est vide ou constante."""
    problems = []
    if isinstance(value, pd.DataFrame):
        if value.empty:
            problems.append(f"{path} : tableau vide")
        elif len(value) > 1:
            for col in value.select_dtypes(include='number').columns:
                if col not in EXEMPT_COLUMNS and value[col].nunique(dropna=False) <= 1:
                    problems.append(f"{path}[{col}] : colonne constante")
    elif isinstance(value, dict):
        if not value:
            problems.append(f"{path} : dictionnaire vide")
        for key, item in value.items():
            problems.extend(_find_empty_or_constant(item, f"{path}.{key}"))
    elif isinstance(value, list | tuple):
        if not value:
            problems.append(f"{path} : liste vide")
        for i, item in enumerate(value):
            problems.extend(_find_empty_or_constant(item, f"{path}[{i}]"))
    elif isinstance(value, float | np.floating) and not np.isfinite(value):
        problems.append(f"{path} : valeur non finie")
    return problems


def test_optimizer_outputs_are_neither_empty_nor_constant(pipeline_outputs):
    assert _find_empty_or_constant(pipeline_outputs['optimizer'], 'optimizer') == []


def test_tax_outputs_are_neither_empty_nor_constant(pipeline_outputs):
    assert _find_empty_or_constant(pipeline_outputs['tax'], 'tax') == []


def test_report_tables_and_summary_are_neither_empty_nor_constant(pipeline_outputs):
    report = pipeline_outputs['report']
    problems = _find_empty_or_constant(report['tables'], 'tables')
    problems += _find_empty_or_constant(report['executive_summary'], 'executive_summary')
    for name, figure in report['figures'].items():
        problems += _find_empty_or_constant(figure['data'], f'figures.{name}.data')
    assert problems == []


def test_key_findings_are_computed_from_results(pipeline_outputs):
    """Les constats affichés citent la probabilité réellement calculée."""
    goal = pipeline_outputs['optimizer']['goal_analysis']
    findings = pipeline_outputs['report']['executive_summary']['key_findings']
    assert any(f"{goal['probability_of_achieving']:.0%}" in f for f in findings)


def test_fake_tax_waterfall_is_refused(pipeline_outputs):
    with pytest.raises(ValueError, match='inventées'):
        reporting.ReportGenerator().generate({
            'optimization_results': pipeline_outputs['optimizer'],
            'tax_results': pipeline_outputs['tax'],
            'report_config': {'format': 'json', 'charts': ['tax_impact_waterfall']},
        })


def test_real_wealth_is_deflated_by_inflation(pipeline_outputs):
    terminal = pipeline_outputs['optimizer']['simulation_results']['terminal_wealth']
    assert (terminal['real_wealth'] < terminal['wealth']).mean() > 0.9
