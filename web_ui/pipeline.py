"""
Calcul lancé par l'interface : GSE → GSE+ → GSE++ → Markowitz par placement.

Séparé de ``app_enhanced.py`` pour être testé sans Streamlit. L'interface ne
fait que rassembler les choix de l'utilisateur et afficher le résultat.

Quand le foyer saisit des projets, le calcul y ajoute un plan par tranches
(portage du R, étapes 1 à 4) : courbe de capital, découpage en tranches,
allocation optimale à l'horizon de chaque tranche, puis assemblage en euros.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from investment_calculator.market_assumptions import load_market_assumptions
from investment_calculator.modules import scenario_generator, user_profile
from investment_calculator.modules.capital_tranches import Tranche, split_into_tranches
from investment_calculator.modules.consumption_units import (
    household_units,
    load_consumption_scale,
)
from investment_calculator.modules.household_budget import KNOWN_GAPS as BUDGET_GAPS
from investment_calculator.modules.household_budget import (
    Earner,
    FutureChild,
    WorkChange,
    household_budget,
)
from investment_calculator.modules.household_cash_flow import Project, capital_curve
from investment_calculator.modules.household_loans import Loan, debt_ratio, loan_schedule
from investment_calculator.modules.household_tax import household_shares, marginal_rate
from investment_calculator.modules.net_returns import (
    TaxProfile,
    build_net_returns,
    without_unpriced_placements,
)
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


def work_changes_by_earner(
    rows: Sequence[Mapping[str, Any]], adults: int
) -> list[tuple[WorkChange, ...]]:
    """
    Temps partiels et congés de chaque adulte, à partir des lignes de la page
    Projets : ``earner`` (0 ou 1), ``start_year``, ``years``, ``worked_share``.

    Raises:
        ValueError: adulte absent du foyer, ou période invalide.
    """
    changes: list[list[WorkChange]] = [[] for _ in range(adults)]
    for row in rows:
        k = int(row['earner'])
        if not 0 <= k < adults:
            raise ValueError(
                f"Temps partiel « {row.get('name', '')} » de l'adulte {k + 1} : le foyer "
                f"compte {adults} adulte(s). Retirez ce projet ou corrigez le foyer."
            )
        changes[k].append(WorkChange(int(row['start_year']), int(row['years']),
                                     float(row['worked_share'])))
    return [tuple(c) for c in changes]


def build_budget(
    budget: Mapping[str, Any], *, catalog: PlacementCatalog, horizon: int,
    annual_savings_now: float,
) -> pd.DataFrame:
    """
    Budget du foyer à partir de la saisie de la page Budget.

    ``budget`` porte ``earners`` (``taxable_income``, ``annual_growth``,
    ``retirement_year``, ``replacement_rate``), ``rent``, ``loans`` (``name``,
    ``annual_payment``, ``rate``, ``years_left``), ``dependent_years``,
    ``children_ages``, ``children_end_age`` et ``future_children`` (voir
    :func:`future_children` et :func:`budget_units`),
    ``expenses_follow_income``, ``work_changes`` (voir
    :func:`work_changes_by_earner`), ``properties`` (champs de
    :class:`RentalProperty`) et, facultatif, ``home`` (voir :func:`home_loan`) :
    le crédit de la résidence principale s'ajoute aux crédits.
    ``annual_savings_now`` est l'épargne actuelle du profil, sur un an : elle
    fixe les dépenses courantes.

    Raises:
        ValueError: saisie refusée par :mod:`household_budget` ; le message dit
            quoi corriger.
    """
    changes = work_changes_by_earner(budget.get('work_changes', []), len(budget['earners']))
    earners = [
        Earner(float(e['taxable_income']), float(e['annual_growth']),
               None if e.get('retirement_year') is None else int(e['retirement_year']),
               None if e.get('replacement_rate') is None else float(e['replacement_rate']),
               changes[k])
        for k, e in enumerate(budget['earners'])
    ]
    loans = [
        Loan(str(c['name']), float(c['annual_payment']), float(c['rate']), int(c['years_left']))
        for c in budget.get('loans', [])
    ]
    residence = home_loan(budget.get('home'))
    if residence is not None:
        loans.append(residence)
    properties = [build_property(p) for p in budget.get('properties', [])]
    table = household_budget(
        catalog.regime, earners, horizon=horizon, current_savings=annual_savings_now,
        rent=float(budget['rent']), loans=loans,
        dependent_years=[int(n) for n in budget.get('dependent_years', [])],
        future_children=[
            FutureChild(int(c['arrival_year']), int(c['dependent_years']))
            for c in budget.get('future_children', [])
        ],
        consumption_units=budget_units(budget, horizon),
        expenses_follow_income=bool(budget['expenses_follow_income']),
        properties=properties,
    )
    return table


def _bands(equity: np.ndarray) -> pd.DataFrame:
    """5e centile, médiane et 95e centile, année par année, sur les scénarios."""
    return pd.DataFrame(
        {'p5': np.percentile(equity, 5, axis=0), 'median': np.median(equity, axis=0),
         'p95': np.percentile(equity, 95, axis=0)},
        index=pd.RangeIndex(equity.shape[1], name='year'),
    )


def _real_estate_returns(scenarios: pd.DataFrame, horizon: int) -> np.ndarray:
    returns: np.ndarray = scenarios.pivot(
        index='scenario_id', columns='time_period', values='real_estate_return'
    ).to_numpy()[:, :horizon]
    return returns


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
    returns = _real_estate_returns(scenarios, horizon)
    rental_yield = load_market_assumptions().real_estate_rental_yield
    equity = np.zeros((returns.shape[0], horizon + 1))
    for row in budget.get('properties', []):
        prop = build_property(row)
        outstanding = property_flows(prop, horizon)['outstanding'].to_numpy()
        equity += property_values(prop, returns, rental_yield) - outstanding
    return _bands(equity)


def dependent_years_from_ages(ages: Sequence[int], end_age: int | None) -> list[int]:
    """
    Années à charge de chaque enfant, à partir de son âge et de l'âge auquel il
    cessera d'être à charge, saisi par l'utilisateur (prototypes R : écran Vous,
    bloc Foyer fiscal, âge de chaque enfant).

    L'âge de fin de charge n'est pas supposé : il dépend de la situation de
    chaque foyer (études, rattachement au foyer fiscal).

    Raises:
        ValueError: âge négatif, ou âges saisis sans âge de fin de charge.
    """
    if not ages:
        return []
    if end_age is None:
        raise ValueError(
            "Âges des enfants saisis sans âge de fin de charge : indiquez à quel âge "
            "ils cesseront d'être à votre charge."
        )
    if any(age < 0 for age in ages) or end_age < 0:
        raise ValueError(f"Âges {list(ages)} et fin de charge à {end_age} ans : saisissez "
                         "des âges positifs.")
    return [max(int(end_age) - int(age), 0) for age in ages]


def future_children(arrivals: Sequence[int], end_age: int | None) -> list[dict[str, int]]:
    """
    Enfants à venir (prototypes R : projet « agrandir la famille »), à partir
    de l'année d'arrivée de chacun et de l'âge de fin de charge saisi par
    l'utilisateur. Leur coût vient des unités de consommation (:func:`budget_units`).

    Raises:
        ValueError: arrivées saisies sans âge de fin de charge, ou arrivée qui
            n'est pas à venir.
    """
    if not arrivals:
        return []
    if end_age is None:
        raise ValueError(
            "Enfants à venir saisis sans âge de fin de charge : indiquez à quel âge "
            "ils cesseront d'être à votre charge."
        )
    if any(a < 1 for a in arrivals) or end_age < 1:
        raise ValueError(f"Arrivées {list(arrivals)} et fin de charge à {end_age} ans : "
                         "saisissez des arrivées dans un an au moins (un enfant déjà né "
                         "se saisit par son âge) et une fin de charge d'au moins 1 an.")
    return [{'arrival_year': int(a), 'dependent_years': int(end_age)} for a in arrivals]


def budget_units(budget: Mapping[str, Any], horizon: int) -> list[float]:
    """
    Unités de consommation du foyer, années 0 à ``horizon``, selon l'échelle de
    l'OCDE modifiée (:mod:`consumption_units`) : adultes, enfants à charge
    selon leur âge, enfants à venir dès leur arrivée.
    """
    ages = [int(a) for a in budget.get('children_ages', [])]
    ages += [-int(c['arrival_year']) for c in budget.get('future_children', [])]
    end_age = budget.get('children_end_age')
    units = household_units(
        load_consumption_scale(), adults=len(budget['earners']), child_ages=ages,
        end_age=None if end_age is None else int(end_age), horizon=horizon,
    )
    return [float(u) for u in units]


def wealth_bands(wealth_paths: pd.DataFrame) -> pd.DataFrame:
    """
    Patrimoine par niveau de probabilité, année par année (prototypes R :
    « Capital par niveau de probabilité »).

    La ligne 10 % se lit : une chance sur dix d'être en dessous. Les
    trajectoires sont celles de la simulation, avant impôt de sortie.

    Args:
        wealth_paths: une ligne par scénario, ``scenario_id`` puis une colonne
            par année (``simulation_results['wealth_paths']``).
    """
    values = wealth_paths.drop(columns='scenario_id').to_numpy(dtype=float)
    levels = (5, 10, 50, 90, 95)
    return pd.DataFrame(
        {f'p{q}': np.percentile(values, q, axis=0) for q in levels},
        index=pd.RangeIndex(values.shape[1], name='year'),
    )


def budget_indicators(table: pd.DataFrame) -> dict[str, Any]:
    """
    Indicateurs du budget sur l'horizon, repris des prototypes R (écran Vos
    projections) : impôts, taux d'endettement maximal, épargne libre minimale.

    Le taux d'endettement n'est calculé que sans loyers perçus : avec des biens
    loués, il dépend de la part des loyers que la banque retient, qui n'est pas
    saisie. Il vaut alors ``None`` et ``debt_ratio_reason`` dit pourquoi.
    """
    income = (table['salaries'] + table['pensions']).to_numpy()
    rents = table['rental_income'].to_numpy()
    worst = int(table['free_savings'].idxmin())
    indicators: dict[str, Any] = {
        'total_income': float(income.sum() + rents.sum()),
        'total_income_tax': float(table['income_tax'].sum() + table['rental_social_tax'].sum()),
        'min_free_savings': float(table['free_savings'].min()),
        'min_free_savings_year': worst,
        'max_debt_ratio': None,
        'debt_ratio_reason': None,
    }
    if rents.any():
        indicators['debt_ratio_reason'] = (
            "loyers perçus : la part retenue par la banque n'est pas saisie"
        )
        return indicators
    try:
        ratio = debt_ratio(income, rental_income=rents, rental_income_weight=0.0,
                           rent_paid=table['rent'].to_numpy(),
                           loan_payments=table['loan_payments'].to_numpy())
    except ValueError as error:
        indicators['debt_ratio_reason'] = str(error)
        return indicators
    indicators['max_debt_ratio'] = float(ratio.max())
    return indicators


def home_loan(home: Mapping[str, Any] | None) -> Loan | None:
    """
    Crédit de la résidence principale saisi sur la page Budget, ou ``None``.

    ``home`` porte ``owner`` (propriétaire ou non), ``value`` (prix net vendeur
    estimé) et ``loan`` (``annual_payment``, ``rate`` en fraction,
    ``years_left``), ``None`` si le bien est payé.
    """
    if not home or not home.get('owner') or home.get('loan') is None:
        return None
    loan = home['loan']
    return Loan("Résidence principale", float(loan['annual_payment']), float(loan['rate']),
                int(loan['years_left']))


def build_home(answers: Mapping[str, Any]) -> tuple[float, dict[str, Any]]:
    """
    Loyer annuel et résidence principale à partir des questions « Votre logement »,
    reprises des prototypes R (écran Vous, bloc Logement).

    ``answers`` porte ``status`` (``'tenant'`` ou ``'owner'``), puis pour un
    locataire ``monthly_rent`` (charges comprises), pour un propriétaire
    ``value`` (prix net vendeur estimé) et ``paid`` ; s'il n'a pas fini de
    payer, ``monthly_payment``, ``rate`` (en %) et ``years_left``.

    Returns:
        Le loyer annuel versé et le logement au format de :func:`home_loan`.

    Raises:
        ValueError: une réponse manque ; le message la nomme.
    """
    def need(key: str, label: str) -> float:
        value = answers.get(key)
        if value is None:
            raise ValueError(f"Logement : renseignez {label}.")
        return float(value)

    status = answers.get('status')
    if status == 'tenant':
        rent = 12 * need('monthly_rent', "le loyer mensuel, charges comprises")
        return rent, {'owner': False, 'value': None, 'loan': None}
    if status != 'owner':
        raise ValueError("Logement : dites si vous êtes locataire ou propriétaire.")
    value = need('value', "la valeur estimée du bien")
    if answers.get('paid') is None:
        raise ValueError("Logement : dites si vous avez fini de payer le bien.")
    loan = None
    if not answers['paid']:
        loan = {
            'annual_payment': 12 * need('monthly_payment', "la mensualité du crédit"),
            'rate': need('rate', "le taux du crédit") / 100,
            'years_left': int(need('years_left', "le nombre d'années restantes")),
        }
    return 0.0, {'owner': True, 'value': value, 'loan': loan}


def home_equity_bands(
    home: Mapping[str, Any], scenarios: pd.DataFrame, horizon: int
) -> pd.DataFrame:
    """
    Valeur nette de la résidence principale en début d'année : 5e centile,
    médiane et 95e centile sur les scénarios du GSE.

    Comme pour un bien loué (:func:`property_values`), le prix suit le
    rendement immobilier total du GSE diminué du rendement locatif du modèle :
    le loyer que l'on ne paie pas n'est pas une plus-value. On retranche le
    capital restant dû du crédit (prochaines annuités actualisées à son taux).
    C'est une valeur avant frais de revente.

    Raises:
        ValueError: valeur du bien absente ou négative.
    """
    value = home.get('value')
    if value is None or not math.isfinite(float(value)) or float(value) < 0:
        raise ValueError(
            f"Valeur de la résidence principale invalide ({value!r}) : saisissez "
            "son prix net vendeur estimé, en euros."
        )
    returns = _real_estate_returns(scenarios, horizon)
    rental_yield = load_market_assumptions().real_estate_rental_yield
    growth = np.cumprod(1.0 + returns - rental_yield, axis=1)
    values = np.empty((returns.shape[0], horizon + 1))
    values[:, 0] = float(value)
    values[:, 1:] = float(value) * growth
    loan = home_loan(home)
    if loan is not None:
        values -= loan_schedule(loan, horizon)['outstanding'].to_numpy()
    return _bands(values)


def capital_timeline(
    flows: Sequence[float], *, projects: Sequence[Project], available_savings: float | None,
) -> dict[str, Any]:
    """
    Chronologie du capital constitué, en euros, années 0 à ``horizon``.

    C'est la courbe certaine des flux (épargne versée, projets payés), sans
    rendement ni scénario économique : celle que le plan par tranches découpe
    horizontalement (:func:`split_into_tranches`). Le capital de l'année 0 est
    l'épargne déjà disponible plus l'épargne de l'année 0, comme dans
    :func:`plan_tranches`.

    Args:
        flows: épargne de chaque année 0 à ``horizon`` (versements du profil, ou
            épargne libre du budget).
        projects: projets du foyer, éventuellement aucun.
        available_savings: épargne déjà disponible ; ``None`` si elle n'est pas
            saisie, la courbe part alors de la seule épargne de l'année 0.

    Returns:
        ``capital`` (série par année), ``tranches`` (liste de :class:`Tranche`,
        vide si la courbe ne se découpe pas), ``layers`` (montant de chaque
        tranche présente, une colonne par tranche) et ``reason`` (pourquoi la
        courbe ne se découpe pas, sinon ``None``).
    """
    values = np.asarray(flows, dtype=float)
    horizon = values.size - 1
    start = (available_savings or 0.0) + float(values[0])
    curve = capital_curve(projects, horizon, start, values[1:].tolist())
    capital = pd.Series(curve, index=pd.RangeIndex(horizon + 1, name='year'), name='capital')
    try:
        tranches = split_into_tranches(curve)
    except ValueError as error:
        return {'capital': capital, 'tranches': [], 'layers': None, 'reason': str(error)}
    layers = pd.DataFrame(
        {k: [t.amount if t.is_present(year) else 0.0 for year in capital.index]
         for k, t in enumerate(tranches)},
        index=capital.index,
    )
    return {'capital': capital, 'tranches': tranches, 'layers': layers, 'reason': None}


def tranche_label(tranche: Tranche) -> str:
    """Libellé d'une tranche : dates de placement et de retrait, durée."""
    end = "l'horizon" if tranche.withdrawal_year is None else f"l'année {tranche.withdrawal_year}"
    return f"Placée de l'année {tranche.start_year} à {end} ({tranche.duration} ans)"


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


def budget_marginal_rate(budget: Mapping[str, Any], *, catalog: PlacementCatalog) -> float:
    """
    Tranche marginale du foyer aujourd'hui, à partir de la saisie de la page Budget :
    revenus imposables des adultes et personnes à charge de l'année 0.

    Elle impose les revenus fonciers des SCPI détenues en direct, pour toute la
    durée de la projection.
    """
    earners = budget['earners']
    dependents = sum(1 for n in budget.get('dependent_years', []) if int(n) > 0)
    shares = household_shares(catalog.regime, adults=len(earners), dependents=dependents)
    income = sum(float(e['taxable_income']) for e in earners)
    return marginal_rate(catalog.regime, income, shares)


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
    marginal_income_tax_rate: float | None = None,
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
    gross, excluded = without_unpriced_placements(
        build_gross_placements(scenarios, catalog), catalog, marginal_income_tax_rate
    )
    profile = TaxProfile(
        invested_amount=largest, couple=couple, wrapper_seniority=seniority,
        marginal_income_tax_rate=marginal_income_tax_rate,
    )
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
        'excluded_placements': excluded,
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
        ``scenarios``, ``profile``, ``catalog`` (identifiant), ``optimization``
        (sortie de :func:`plan_placements`) et ``wealth_bands`` (voir
        :func:`wealth_bands`) ; avec des projets, ``tranche_plan``
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
    marginal = None if budget is None else budget_marginal_rate(budget, catalog=catalog)
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
        marginal_income_tax_rate=marginal,
        reference_wrapper='cto',
    )
    results = {
        'wealth_bands': wealth_bands(optimization['simulation_results']['wealth_paths']),
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
        gaps = (BUDGET_GAPS + list(load_consumption_scale().known_gaps)
                + (RENTAL_GAPS if budget.get('properties') else []))
        budget_results: dict[str, Any] = {'table': table, 'known_gaps': gaps,
                                          'indicators': budget_indicators(table)}
        if budget.get('properties'):
            budget_results['property_equity'] = property_equity_bands(
                budget, scenario_results['scenarios'], horizon
            )
        home = budget.get('home')
        if home and home.get('owner'):
            budget_results['home_equity'] = home_equity_bands(
                home, scenario_results['scenarios'], horizon
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
            annual_savings=savings, marginal_income_tax_rate=marginal,
        )
    flows_now: list[float] = (
        contribution_flows(profile_results['investment_time_series'], horizon).tolist()
        if savings is None else savings
    )
    results['capital_timeline'] = capital_timeline(
        flows_now, projects=projects, available_savings=available_savings,
    )
    return results
