"""
Projection du patrimoine sur GSE+ : cohérence avec GSE++, assemblage des
versements, impôt de sortie par enveloppe.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from investment_calculator.modules.net_returns import TaxProfile, build_net_returns
from investment_calculator.modules.wealth_simulation import contribution_flows, simulate_wealth
from investment_calculator.placement_catalog import load_placement_catalog
from investment_calculator.wrapper_tax import liquidation_tax

FR_2026 = load_placement_catalog("fr-2026")
PROFILE = TaxProfile(invested_amount=1.0)


def _gross(n_scenarios: int = 50, n_periods: int = 10, seed: int = 3) -> pd.DataFrame:
    """GSE+ synthétique pour les six placements du catalogue."""
    rng = np.random.default_rng(seed)
    index = pd.MultiIndex.from_product(
        [[f"s{i:02d}" for i in range(n_scenarios)], [float(t + 1) for t in range(n_periods)]],
        names=["scenario_id", "time_period"],
    )
    columns = {
        pid: 0.04 + 0.12 * rng.standard_normal(len(index)) for pid in FR_2026.placement_ids
    }
    columns["livret_a"] = np.full(len(index), 0.02)
    return pd.DataFrame(columns, index=index)


def _weights(**w: float) -> pd.Series:
    return pd.Series(w, dtype=float)


@pytest.mark.parametrize("placement", ["pea_actions", "av_uc_actions", "cto_actions", "livret_a"])
def test_un_versement_unique_reproduit_gse_plus_plus(placement: str) -> None:
    gross = _gross()
    amount, horizon = 40_000.0, 8
    flows = np.zeros(11)
    flows[0] = amount
    sim = simulate_wealth(gross, FR_2026, PROFILE, _weights(**{placement: 1.0}), flows, horizon)
    net = build_net_returns(
        gross[[placement]], FR_2026, TaxProfile(invested_amount=amount), [horizon]
    )
    np.testing.assert_allclose(sim.net_terminal, amount * net.multiples[:, 0, 0], rtol=1e-12)


def test_les_versements_s_additionnent_avant_impot() -> None:
    gross = _gross()
    weights = _weights(pea_actions=0.6, livret_a=0.4)
    first = np.array([10_000.0] + [0.0] * 10)
    later = np.array([0.0, 0.0, 5_000.0] + [0.0] * 8)
    both = simulate_wealth(gross, FR_2026, PROFILE, weights, first + later, 6)
    alone = [simulate_wealth(gross, FR_2026, PROFILE, weights, f, 6) for f in (first, later)]
    np.testing.assert_allclose(both.value_paths, alone[0].value_paths + alone[1].value_paths)
    assert both.contributions == {"pea": 9_000.0, "livret_a": 6_000.0}


def test_l_assurance_vie_est_liquidee_une_fois_par_contrat() -> None:
    # Deux placements dans le même contrat : un seul abattement, sur la somme.
    gross = _gross()
    flows = np.array([100_000.0] + [0.0] * 10)
    weights = _weights(av_fonds_euros=0.5, av_uc_actions=0.5)
    sim = simulate_wealth(gross, FR_2026, TaxProfile(1.0, couple=True), weights, flows, 9)
    expected = liquidation_tax(
        FR_2026.regime, "assurance_vie", contributions=100_000.0,
        final_value=sim.value_paths[:, -1], holding_years=9, couple=True,
    )
    np.testing.assert_allclose(sim.net_terminal, expected.net_value)
    np.testing.assert_allclose(sim.exit_tax["assurance_vie"],
                               sim.value_paths[:, -1] - expected.net_value)


def test_anciennete_de_l_enveloppe() -> None:
    gross = _gross()
    flows = np.array([20_000.0] + [0.0] * 10)
    weights = _weights(pea_actions=1.0)
    young = simulate_wealth(gross, FR_2026, PROFILE, weights, flows, 3)
    old = simulate_wealth(gross, FR_2026, TaxProfile(1.0, wrapper_seniority={"pea": 5}),
                          weights, flows, 3)
    gained = young.value_paths[:, -1] > 20_000.0
    assert (old.net_terminal[gained] > young.net_terminal[gained]).all()


def test_statistiques() -> None:
    sim = simulate_wealth(_gross(), FR_2026, PROFILE, _weights(livret_a=1.0),
                          np.array([1_000.0] * 11), 10)
    stats = sim.statistics()
    assert stats["total_contributions"] == pytest.approx(11_000.0)
    assert stats["median_terminal_wealth"] == pytest.approx(sim.net_terminal[0])
    assert set(stats["mean_tax_by_wrapper"]) == {"livret_a"}


def test_entrees_invalides_refusees() -> None:
    gross = _gross()
    flows = np.array([1_000.0] + [0.0] * 10)
    with pytest.raises(ValueError, match="sommer à 1"):
        simulate_wealth(gross, FR_2026, PROFILE, _weights(pea_actions=0.5), flows, 5)
    with pytest.raises(ValueError, match="entre 1 et 10"):
        simulate_wealth(gross, FR_2026, PROFILE, _weights(pea_actions=1.0), flows, 11)
    with pytest.raises(ValueError, match="Aucun versement"):
        simulate_wealth(gross, FR_2026, PROFILE, _weights(pea_actions=1.0), flows * 0, 5)


def test_retraits_refuses() -> None:
    series = pd.DataFrame({"net_flow": [10_000.0, 1_000.0, -3_000.0]})
    with pytest.raises(NotImplementedError, match="années \\[2\\]"):
        contribution_flows(series, 5)
    flows = contribution_flows(pd.DataFrame({"contribution": [5.0, 1.0]}), 3)
    np.testing.assert_array_equal(flows, [5.0, 1.0, 0.0, 0.0])


def test_retrait_a_l_horizon_ignore() -> None:
    # Le départ à la retraite tombe à l'horizon : le patrimoine y est liquidé.
    series = pd.DataFrame({"net_flow": [10_000.0, 1_000.0, -3_000.0, -3_000.0]})
    np.testing.assert_array_equal(contribution_flows(series, 2), [10_000.0, 1_000.0, 0.0])
    with pytest.raises(NotImplementedError, match="années \\[2\\]"):
        contribution_flows(series, 3)
