"""
Calcul lancé par l'interface : GSE → GSE+ → GSE++ → Markowitz par placement.

Séparé de ``app_enhanced.py`` pour être testé sans Streamlit. L'interface ne
fait que rassembler les choix de l'utilisateur et afficher le résultat.

Quand le foyer saisit des projets, le calcul y ajoute un plan par tranches
(portage du R, étapes 1 à 4) : courbe de capital, découpage en tranches,
allocation optimale à l'horizon de chaque tranche, puis assemblage en euros.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from investment_calculator.market_assumptions import load_market_assumptions
from investment_calculator.modules import scenario_generator, user_profile
from investment_calculator.modules.capital_tranches import split_into_tranches
from investment_calculator.modules.household_budget import KNOWN_GAPS as BUDGET_GAPS
from investment_calculator.modules.household_budget import Earner, household_budget
from investment_calculator.modules.household_cash_flow import Project, capital_curve
from investment_calculator.modules.household_loans import Loan
from investment_calculator.modules.net_returns import TaxProfile, build_net_returns
from investment_calculator.modules.placement_optimizer import (
    optimize_by_horizon,
    placement_constraints,
)
from investment_calculator.modules.placement_plan import plan_placements, profile_holdings
from investment_calculator.modules.placements import build_gross_placements
from investment_calculator.modules.rental_property import KNOWN_GAPS as RENTAL_GAPS
from investment_calculator.modules.rental_property import (
    RentalProperty,
    property_flows,
    property_values,
)
from investment_calculator.modules.tranche_allocation import (
    assemble_allocation,
    required_horizons,
)
from investment_calculator.modules.wealth_simulation import Holding, contribution_flows
from investment_calculator.placement_catalog import PlacementCatalog, load_placement_catalog

# Limites du plan par tranches, affichées avec lui.
TRANCHE_PLAN_GAPS = [
    "Les plafonds de versement des enveloppes sont appliqués à chaque horizon "
    "séparément, sur le capital maximal de la courbe : une enveloppe peut "
    "dépasser son plafond une fois les tranches additionnées.",
    "Le patrimoine projeté ci-dessus suit l'allocation à horizon unique ; la "
    "projection scénario par scénario du plan par tranches n'est pas encore portée.",
]


def build_projects(rows: Sequence[Mapping[str, Any]]) -> list[Project]:
    """
    Projets du foyer à partir des lignes saisies.

    Chaque ligne porte ``name``, ``start_year`` (années à partir d'aujourd'hui),
    ``initial_payment``, ``annual_payment``, ``duration_years`` et ``resale``,
    le montant récupéré en fin de projet (revente), positif. La revente
    s'ajoute au dernier versement.

    Raises:
        ValueError: une ligne est refusée par :class:`Project` ; le message
            nomme le projet.
    """
    projects = []
    for row in rows:
        try:
            projects.append(Project(
                str(row['name']), int(row['start_year']), float(row['initial_payment']),
                float(row['annual_payment']), int(row['duration_years']),
                -float(row['resale']),
            ))
        except ValueError as error:
            raise ValueError(f"Projet « {row['name']} » : {error}") from error
    return projects


def build_budget(
    budget: Mapping[str, Any], *, catalog: PlacementCatalog, horizon: int,
    annual_savings_now: float,
) -> pd.DataFrame:
    """
    Budget du foyer à partir de la saisie de la page Budget.

    ``budget`` porte ``earners`` (``taxable_income``, ``annual_growth``,
    ``retirement_year``, ``replacement_rate``), ``rent``, ``loans`` (``name``,
    ``annual_payment``, ``rate``, ``years_left``), ``dependent_years``,
    ``expenses_follow_income`` et ``properties`` (champs de
    :class:`RentalProperty`). ``annual_savings_now`` est l'épargne actuelle
    du profil, sur un an : elle fixe les dépenses courantes.

    Raises:
        ValueError: saisie refusée par :mod:`household_budget` ; le message dit
            quoi corriger.
    """
    earners = [
        Earner(float(e['taxable_income']), float(e['annual_growth']),
               None if e.get('retirement_year') is None else int(e['retirement_year']),
               None if e.get('replacement_rate') is None else float(e['replacement_rate']))
        for e in budget['earners']
    ]
    loans = [
        Loan(str(c['name']), float(c['annual_payment']), float(c['rate']), int(c['years_left']))
        for c in budget.get('loans', [])
    ]
    properties = [build_property(p) for p in budget.get('properties', [])]
    table = household_budget(
        catalog.regime, earners, horizon=horizon, current_savings=annual_savings_now,
        rent=float(budget['rent']), loans=loans,
        dependent_years=[int(n) for n in budget.get('dependent_years', [])],
        expenses_follow_income=bool(budget['expenses_follow_income']),
        properties=properties,
    )
    return table


def property_equity_bands(
    budget: Mapping[str, Any], scenarios: pd.DataFrame, horizon: int
) -> pd.DataFrame:
    """
    Valeur nette des biens loués en début d'année : 5e centile, médiane et 95e
    centile sur les scénarios du GSE.

    La valeur de chaque bien suit l'indice immobilier de chaque scénario
    (:func:`property_values`) ; on en retranche le capital restant dû. C'est
    une valeur avant frais et impôt de revente.
    """
    returns = scenarios.pivot(
        index='scenario_id', columns='time_period', values='real_estate_return'
    ).to_numpy()[:, :horizon]
    rental_yield = load_market_assumptions().real_estate_rental_yield
    equity = np.zeros((returns.shape[0], horizon + 1))
    for row in budget.get('properties', []):
        prop = build_property(row)
        outstanding = property_flows(prop, horizon)['outstanding'].to_numpy()
        equity += property_values(prop, returns, rental_yield) - outstanding
    return pd.DataFrame(
        {'p5': np.percentile(equity, 5, axis=0), 'median': np.median(equity, axis=0),
         'p95': np.percentile(equity, 95, axis=0)},
        index=pd.RangeIndex(horizon + 1, name='year'),
    )


def build_property(row: Mapping[str, Any]) -> RentalProperty:
    """Bien loué saisi dans l'application (taux en fractions, 0,04 pour 4 %)."""
    return RentalProperty(
        name=str(row['name']), price=float(row['price']),
        down_payment=float(row['down_payment']), loan_rate=float(row['loan_rate']),
        loan_years=int(row['loan_years']), gross_yield=float(row['gross_yield']),
        collected_share=float(row['collected_share']),
        annual_charges=float(row['annual_charges']), rent_growth=float(row['rent_growth']),
        purchase_year=int(row['purchase_year']), market_value=float(row['market_value']),
    )


def plan_tranches(
    scenarios: pd.DataFrame,
    catalog: PlacementCatalog,
    time_series: pd.DataFrame,
    *,
    horizon: int,
    projects: Sequence[Project],
    available_savings: float,
    risk_aversion: float,
    couple: bool = False,
    max_equity: float | None = None,
    min_bond: float | None = None,
    holdings: tuple[Holding, ...] = (),
    n_batches: int | None = None,
    annual_savings: Sequence[float] | None = None,
) -> dict[str, Any]:
    """
    Plan de placement par tranches : chaque euro est placé jusqu'à son projet.

    Le capital de l'année 0 est ``available_savings`` plus le premier versement ;
    s'y ajoutent ensuite les versements du profil, et s'en retranchent les
    projets. L'épargne existante saisie à part reste dans ses placements : elle
    ne compte ici que pour l'ancienneté des enveloppes et les plafonds.

    Avec ``annual_savings`` (années 0 à ``horizon``, l'épargne libre du budget
    du foyer), l'épargne de chaque année remplace les versements du profil.

    Raises:
        ValueError: projets non financés (capital négatif), ou entrées refusées
            par les modules appelés.
    """
    if annual_savings is None:
        flows = contribution_flows(time_series, horizon)
    else:
        flows = np.asarray(annual_savings, dtype=float)
        if flows.shape != (horizon + 1,):
            raise ValueError(
                f"{flows.size} montants d'épargne pour un horizon de {horizon} ans : il en "
                f"faut un par année, de 0 à {horizon}."
            )
    curve = capital_curve(
        projects, horizon, float(available_savings) + float(flows[0]), flows[1:].tolist()
    )
    tranches = split_into_tranches(curve)
    horizons = required_horizons(tranches)
    if not horizons:
        raise ValueError(
            "Aucun capital à placer pour au moins un an : augmentez l'épargne ou "
            "décalez les projets."
        )
    seniority: dict[str, float] = {}
    existing: dict[str, float] = {}
    for holding in holdings:
        wrapper = str(catalog.placement(holding.placement_id)["wrapper"])
        seniority[wrapper] = max(seniority.get(wrapper, 0.0), holding.years_held)
        existing[wrapper] = existing.get(wrapper, 0.0) + holding.contributions
    largest = float(curve.max())
    gross = build_gross_placements(scenarios, catalog)
    profile = TaxProfile(invested_amount=largest, couple=couple, wrapper_seniority=seniority)
    net = build_net_returns(gross, catalog, profile, horizons)
    constraints = placement_constraints(
        catalog, list(gross.columns), total_contributions=largest, n_periods=horizon,
        max_equity=max_equity, min_bond=min_bond, existing_contributions=existing,
    )
    weights = optimize_by_horizon(
        net, constraints, horizons, risk_aversion=risk_aversion, n_batches=n_batches
    )
    allocation = assemble_allocation(tranches, weights)
    return {
        'capital': curve.tolist(),
        'tranches': [
            {'amount': t.amount, 'start_year': t.start_year,
             'withdrawal_year': t.withdrawal_year, 'duration': t.duration}
            for t in tranches
        ],
        'weights_by_horizon': weights,
        'amounts': allocation.amounts,
        'unplaced': allocation.unplaced,
        'known_gaps': TRANCHE_PLAN_GAPS,
    }


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
    projects: Sequence[Project] = (),
    available_savings: float | None = None,
    budget: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Projeter le profil sur les placements du catalogue choisi.

    L'horizon est celui du profil (``investment_preferences.time_horizon``) ;
    les scénarios sont générés sur cette durée, graine 42. ``couple`` vaut pour
    l'imposition à la sortie (abattement de l'assurance-vie).

    Avec des ``projects``, ``available_savings`` est requis : c'est l'épargne
    déjà disponible pour les financer, saisie par l'utilisateur.

    Avec un ``budget`` (voir :func:`build_budget`), le budget du foyer est
    calculé, et son épargne libre remplace les versements du profil dans le
    plan par tranches.

    Returns:
        ``scenarios``, ``profile``, ``catalog`` (identifiant) et ``optimization``
        (sortie de :func:`plan_placements`) ; avec des projets, ``tranche_plan``
        (sortie de :func:`plan_tranches`).
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
    results = {
        'scenarios': scenario_results,
        'profile': profile_results,
        'catalog': catalog.id,
        'optimization': optimization,
    }
    savings: list[float] | None = None
    if budget is not None:
        flows = contribution_flows(profile_results['investment_time_series'], horizon)
        table = build_budget(budget, catalog=catalog, horizon=horizon,
                             annual_savings_now=float(flows[0]))
        gaps = BUDGET_GAPS + (RENTAL_GAPS if budget.get('properties') else [])
        budget_results: dict[str, Any] = {'table': table, 'known_gaps': gaps}
        if budget.get('properties'):
            budget_results['property_equity'] = property_equity_bands(
                budget, scenario_results['scenarios'], horizon
            )
        results['budget'] = budget_results
        savings = table['free_savings'].tolist()
    if projects:
        if available_savings is None:
            raise ValueError(
                "Projets saisis sans épargne disponible : indiquez l'épargne déjà "
                "disponible pour les financer (0 si aucune)."
            )
        constraints = profile_results['validated_profile']['constraints']
        results['tranche_plan'] = plan_tranches(
            scenario_results['scenarios'], catalog,
            profile_results['investment_time_series'], horizon=horizon,
            projects=projects, available_savings=available_savings,
            risk_aversion=risk_aversion, couple=couple,
            max_equity=constraints['max_equity_allocation'],
            min_bond=constraints['min_bond_allocation'],
            holdings=profile_holdings(profile_results['validated_profile']),
            annual_savings=savings,
        )
    return results
