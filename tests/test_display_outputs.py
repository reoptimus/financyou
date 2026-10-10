"""
Étape 1.C.2 : aucune sortie destinée à l'affichage n'est vide ou constante.

Le dépôt a contenu une cascade fiscale faite de nombres inventés, des soldes de
comptes à 0, un calendrier de rééquilibrage vide et des analyses de
sensibilité vides. Ce test parcourt toutes les sorties de la chaîne
GSE+ → GSE++ → Markowitz par placement et du rapport sur un petit pipeline
complet, et échoue dès
qu'une valeur affichable est vide ou ne varie pas d'un scénario à l'autre.
"""

import numpy as np
import pandas as pd
import pytest

from investment_calculator.modules import reporting, scenario_generator
from investment_calculator.modules.placement_plan import plan_placements
from investment_calculator.placement_catalog import load_placement_catalog

# Colonnes légitimement constantes : identifiants, et patrimoine initial
# (identique dans tous les scénarios par construction).
EXEMPT_COLUMNS = {'scenario_id', 'time_period', 'period', '0'}


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
    opt_results = plan_placements(
        scenarios,
        load_placement_catalog('fr-2026'),
        pd.DataFrame({'period': range(11), 'net_flow': [1000.0] * 11}),
        horizon=10,
        objective='mean_variance',
        risk_aversion=5.0,
        risk_free_placement='livret_a',
        goal_amount=12000,
        frontier_points=5,
    )
    report = reporting.ReportGenerator().generate({
        'optimization_results': opt_results,
        'report_config': {'format': 'json'},
    })
    return {'optimizer': opt_results, 'report': report}


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
            'report_config': {'format': 'json', 'charts': ['tax_impact_waterfall']},
        })
