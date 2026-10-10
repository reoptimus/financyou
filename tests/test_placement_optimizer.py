"""
Markowitz sur GSE++ : une allocation entre placements par horizon, sous les
plafonds de versement des enveloppes.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest

from investment_calculator.modules.net_returns import NetReturns, TaxProfile, build_net_returns
from investment_calculator.modules.placement_optimizer import (
    OptimizationError,
    optimize_by_horizon,
    optimize_horizon,
    placement_constraints,
)
from investment_calculator.modules.placements import asset_exposures
from investment_calculator.placement_catalog import PlacementCatalog, load_placement_catalog
from investment_calculator.wrapper_allocation import InfeasibleConstraintsError

FR_2026 = load_placement_catalog("fr-2026")
PEA_CAP = FR_2026.regime.wrapper("pea")["contribution_limit"]
LIVRET_CAP = FR_2026.regime.wrapper("livret_a")["contribution_limit"]


def _net(placements: list[str], annualized: np.ndarray, horizon: int = 1) -> NetReturns:
    """GSE++ synthétique : rendements annualisés donnés, un horizon."""
    multiples = (1.0 + annualized) ** horizon
    return NetReturns(
        multiples=multiples[:, None, :],
        scenario_ids=[f"s{i}" for i in range(len(annualized))],
        horizons=[horizon],
        placement_ids=placements,
    )


def _two_assets(seed: int = 0) -> NetReturns:
    rng = np.random.default_rng(seed)
    returns = np.column_stack([
        0.06 + 0.15 * rng.standard_normal(2000),
        0.02 + 0.04 * rng.standard_normal(2000),
    ])
    return _net(["cto_actions", "av_fonds_euros"], returns)


def _free(net: NetReturns, total: float = 10_000.0):
    return placement_constraints(FR_2026, net.placement_ids, total_contributions=total, n_periods=1)


def test_moyenne_variance_solution_analytique_a_deux_placements() -> None:
    net = _two_assets()
    annualized = net.annualized(1)
    mu, cov = annualized.mean().to_numpy(), annualized.cov().to_numpy()
    lam = 5.0
    # max w·μ − λ/2 w'Σw avec w1 + w2 = 1 : solution intérieure fermée.
    d = cov[0, 0] + cov[1, 1] - 2 * cov[0, 1]
    w1 = (mu[0] - mu[1]) / (lam * d) + (cov[1, 1] - cov[0, 1]) / d
    allocation = optimize_horizon(net, 1, _free(net), risk_aversion=lam)
    assert 0 < w1 < 1
    assert allocation.weights["cto_actions"] == pytest.approx(w1, abs=1e-4)
    assert allocation.expected_return == pytest.approx(
        float(allocation.weights.to_numpy() @ mu)
    )


def test_aversion_croissante_moins_d_actions() -> None:
    net = _two_assets()
    weights = [
        optimize_horizon(net, 1, _free(net), risk_aversion=lam).weights["cto_actions"]
        for lam in (0.5, 5.0, 50.0)
    ]
    assert weights[0] > weights[1] > weights[2]


def test_volatilite_minimale_et_rendement_cible() -> None:
    net = _two_assets()
    low = optimize_horizon(net, 1, _free(net), objective="min_volatility")
    target = optimize_horizon(net, 1, _free(net), objective="target_return", target_return=0.04)
    assert target.expected_return == pytest.approx(0.04, abs=1e-6)
    assert target.volatility > low.volatility


def test_plafond_du_livret_a_respecte() -> None:
    # Le Livret A domine : sans plafond, tout irait dessus.
    rng = np.random.default_rng(1)
    returns = np.column_stack([
        0.05 + 0.001 * rng.standard_normal(500),
        0.01 + 0.10 * rng.standard_normal(500),
    ])
    net = _net(["livret_a", "cto_actions"], returns)
    total = 100_000.0
    constraints = placement_constraints(
        FR_2026, net.placement_ids, total_contributions=total, n_periods=1
    )
    allocation = optimize_horizon(net, 1, constraints, risk_aversion=5.0)
    assert allocation.weights["livret_a"] == pytest.approx(LIVRET_CAP / total, abs=1e-6)
    assert allocation.weights["livret_a"] <= LIVRET_CAP / total


def test_placements_d_une_meme_enveloppe_partagent_son_plafond() -> None:
    net = _net(["av_fonds_euros", "pea_actions"], np.zeros((3, 2)))
    constraints = placement_constraints(
        FR_2026, ["pea_actions", "av_fonds_euros"], total_contributions=300_000.0, n_periods=10
    )
    assert constraints.a_ub.tolist() == [[1.0, 0.0]]
    assert constraints.b_ub[0] == pytest.approx(PEA_CAP / 300_000.0, abs=1e-6)
    assert "pea" in constraints.explanation
    with pytest.raises(ValueError, match="placement_constraints"):
        optimize_horizon(net, 1, constraints, risk_aversion=5.0)


def test_plafonds_qui_ne_couvrent_pas_les_versements() -> None:
    net = _net(["livret_a"], np.full((10, 1), 0.02))
    constraints = placement_constraints(
        FR_2026, ["livret_a"], total_contributions=100_000.0, n_periods=1
    )
    with pytest.raises(ValueError, match="livret_a"):
        optimize_horizon(net, 1, constraints, risk_aversion=5.0)


def test_parametres_d_objectif_obligatoires() -> None:
    net = _two_assets()
    with pytest.raises(ValueError, match="risk_aversion"):
        optimize_horizon(net, 1, _free(net))
    with pytest.raises(ValueError, match="risk_free_rate"):
        optimize_horizon(net, 1, _free(net), objective="max_sharpe")
    with pytest.raises(ValueError, match="Objectifs disponibles"):
        optimize_horizon(net, 1, _free(net), objective="max_return", risk_aversion=1.0)


def test_rendement_cible_inatteignable_refuse() -> None:
    net = _two_assets()
    with pytest.raises(OptimizationError, match="n'a pas abouti"):
        optimize_horizon(net, 1, _free(net), objective="target_return", target_return=0.50)


def test_versements_nuls_refuses() -> None:
    with pytest.raises(ValueError, match="strictement positifs"):
        placement_constraints(FR_2026, ["livret_a"], total_contributions=0.0, n_periods=1)


def test_poids_par_horizon_sur_les_vrais_scenarios() -> None:
    from investment_calculator.modules.placements import build_gross_placements
    from investment_calculator.modules.scenario_generator import ScenarioGenerator

    document = copy.deepcopy(FR_2026.document)
    for placement in document["placements"]:
        placement["fees"] = {"entry_rate": 0.0, "annual_rate": 0.0}  # valeurs de test
    catalog = PlacementCatalog(document=document, source=FR_2026.source, regime=FR_2026.regime)
    ids = ["pea_actions", "cto_obligations", "livret_a"]
    scenarios = ScenarioGenerator(random_seed=42).generate(
        {"num_scenarios": 300, "time_horizon": 10, "timestep": 1.0, "use_stochastic": False}
    )["scenarios"]
    gross = build_gross_placements(scenarios, catalog, ids)
    net = build_net_returns(gross, catalog, TaxProfile(invested_amount=50_000.0), [3, 8])
    constraints = placement_constraints(
        catalog, net.placement_ids, total_contributions=50_000.0, n_periods=10
    )
    weights = optimize_by_horizon(net, constraints, risk_aversion=5.0)
    assert list(weights.columns) == [3, 8]
    assert list(weights.index) == ids
    np.testing.assert_allclose(weights.sum().to_numpy(), 1.0, atol=1e-6)
    assert (weights.loc["livret_a"] <= LIVRET_CAP / 50_000.0 + 1e-9).all()


def test_frontiere_efficiente_croissante_et_contrainte() -> None:
    from investment_calculator.modules.placement_optimizer import efficient_frontier

    net = _two_assets()
    frontier = efficient_frontier(net, 1, _free(net), n_points=8)
    low = optimize_horizon(net, 1, _free(net), objective="min_volatility")
    high = net.annualized(1).mean().max()
    assert list(frontier.columns) == ["return", "volatility"]
    assert frontier["return"].iloc[0] == pytest.approx(low.expected_return)
    assert frontier["return"].iloc[-1] == pytest.approx(high, abs=1e-6)
    assert (np.diff(frontier["volatility"]) > -1e-9).all()
    with pytest.raises(ValueError, match="au moins 2 points"):
        efficient_frontier(net, 1, _free(net), n_points=1)


def test_exposition_des_placements_de_fr_2026() -> None:
    exposures = asset_exposures(FR_2026, FR_2026.placement_ids)
    assert exposures.loc["cto_actions"].tolist() == [1.0, 0.0]
    assert exposures.loc["cto_obligations"].tolist() == [0.0, 1.0]
    assert exposures.loc["livret_a"].tolist() == [0.0, 0.0]
    # Fonds en euros au prorata de son actif général (choix de seb, 2026-10-10).
    assets = FR_2026.placement("av_fonds_euros")["support"]["assets"]
    equity = sum(a["weight"] for a in assets if a.get("series") == "stock_return")
    bond = sum(a["weight"] for a in assets if a["kind"] == "book_bonds")
    assert exposures.loc["av_fonds_euros"].tolist() == pytest.approx([equity, bond])


def _three_placements() -> NetReturns:
    rng = np.random.default_rng(1)
    returns = np.column_stack([
        0.08 + 0.15 * rng.standard_normal(2000),   # actions
        0.03 + 0.05 * rng.standard_normal(2000),   # obligations
        0.025 + 0.01 * rng.standard_normal(2000),  # fonds euros
    ])
    return _net(["cto_actions", "cto_obligations", "av_fonds_euros"], returns)


def test_plafond_d_actions_du_profil_respecte() -> None:
    net = _three_placements()
    free = optimize_horizon(net, 1, _free(net), risk_aversion=1.0)
    assert free.weights["cto_actions"] > 0.9  # sans contrainte, presque tout en actions
    constraints = placement_constraints(
        FR_2026, net.placement_ids, total_contributions=10_000.0, n_periods=1, max_equity=0.5
    )
    weights = optimize_horizon(net, 1, constraints, risk_aversion=1.0).weights
    exposure = asset_exposures(FR_2026, net.placement_ids)["equity"]
    assert float(weights @ exposure) <= 0.5 + 1e-6
    assert "50%" in constraints.explanation


def test_minimum_d_obligations_du_profil_respecte() -> None:
    net = _three_placements()
    constraints = placement_constraints(
        FR_2026, net.placement_ids, total_contributions=10_000.0, n_periods=1, min_bond=0.6
    )
    weights = optimize_horizon(net, 1, constraints, risk_aversion=1.0).weights
    exposure = asset_exposures(FR_2026, net.placement_ids)["bond"]
    assert float(weights @ exposure) >= 0.6 - 1e-6


def test_contraintes_du_profil_impossibles() -> None:
    # Ni actions ni obligations possibles avec le seul Livret A : 50 % d'obligations
    # au moins est hors d'atteinte, l'erreur le dit.
    net = _net(["livret_a"], np.full((10, 1), 0.02))
    constraints = placement_constraints(
        FR_2026, ["livret_a"], total_contributions=1_000.0, n_periods=1, min_bond=0.5
    )
    with pytest.raises(InfeasibleConstraintsError, match="contraintes du profil"):
        optimize_horizon(net, 1, constraints, risk_aversion=5.0)
    with pytest.raises(ValueError, match="entre 0 et 1"):
        placement_constraints(
            FR_2026, ["livret_a"], total_contributions=1_000.0, n_periods=1, max_equity=1.5
        )
