"""
GSE+ : rendements avant impôt de chaque placement du catalogue.
Voir docs/adr/0002-le-placement-est-l-unite-d-optimisation.md.
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from investment_calculator.modules.placements import (
    UnsourcedValueError,
    build_gross_placements,
    entry_fee_rates,
)
from investment_calculator.placement_catalog import PlacementCatalog, load_placement_catalog

DRAFT = load_placement_catalog("fr-2026", allow_draft=True)


def _catalog(**overrides: dict) -> PlacementCatalog:
    """Le brouillon fr-2026, avec des valeurs de test pour les champs à null."""
    document = copy.deepcopy(DRAFT.document)
    for placement in document["placements"]:
        placement.update(copy.deepcopy(overrides.get(placement["id"], {})))
    return PlacementCatalog(document=document, source=DRAFT.source, regime=DRAFT.regime)


def _scenarios(**series: list[float]) -> pd.DataFrame:
    n = len(next(iter(series.values())))
    base = {
        "scenario_id": [i // 2 for i in range(n)],
        "time_period": [float(i % 2 + 1) for i in range(n)],
        "interest_rate": [0.02] * n,
        "stock_return": [0.10] * n,
        "bond_return": [0.03] * n,
        "real_estate_return": [0.05] * n,
        "inflation": [0.01] * n,
    }
    base.update(series)
    return pd.DataFrame(base)


NO_FEES = {"fees": {"entry_rate": 0.0, "annual_rate": 0.0}}


def test_sans_frais_un_placement_reproduit_sa_serie() -> None:
    scenarios = _scenarios(stock_return=[0.12, -0.20, 0.05, 0.31])
    gse_plus = build_gross_placements(scenarios, _catalog(cto_actions=NO_FEES), ["cto_actions"])
    np.testing.assert_array_equal(gse_plus["cto_actions"].to_numpy(), scenarios["stock_return"])
    assert gse_plus.index.names == ["scenario_id", "time_period"]


def test_frais_annuels_preleves_sur_l_encours() -> None:
    scenarios = _scenarios(stock_return=[0.10, -0.20])
    gse_plus = build_gross_placements(scenarios, DRAFT, ["av_uc_actions"])
    expected = (1 + scenarios["stock_return"].to_numpy()) * (1 - 0.0088) - 1
    np.testing.assert_allclose(gse_plus["av_uc_actions"].to_numpy(), expected)


def test_valeur_non_sourcee_refusee() -> None:
    with pytest.raises(UnsourcedValueError, match="fees.annual_rate"):
        build_gross_placements(_scenarios(stock_return=[0.1, 0.1]), DRAFT, ["cto_actions"])
    with pytest.raises(UnsourcedValueError, match="pass_through"):
        build_gross_placements(_scenarios(stock_return=[0.1, 0.1]), DRAFT, ["av_fonds_euros"])
    with pytest.raises(UnsourcedValueError, match="fees.entry_rate"):
        entry_fee_rates(DRAFT, ["pea_actions"])


def test_fonds_euros_plancher_net_de_frais() -> None:
    catalog = _catalog(av_fonds_euros={
        "support": {"model": "euro_fund", "reference_series": "bond_return",
                    "pass_through": 0.9, "floor_rate": 0.0},
    })
    scenarios = _scenarios(bond_return=[0.04, -0.05])
    served = build_gross_placements(scenarios, catalog, ["av_fonds_euros"])["av_fonds_euros"]
    np.testing.assert_allclose(served.to_numpy(), [(1 + 0.036) * (1 - 0.0066) - 1, 0.0])


@pytest.mark.parametrize(
    ("short_rate", "inflation", "expected"),
    [
        (0.02, 0.01, 0.015),     # moyenne exacte
        (0.0201, 0.0104, 0.015),  # 1,525 % arrondi au dixième le plus proche
        (0.01, 0.011, 0.011),    # 1,05 % : à égalité, dixième supérieur
        (-0.005, 0.0, 0.005),    # plancher de 0,5 %
    ],
)
def test_livret_a_formule_reglementaire(
    short_rate: float, inflation: float, expected: float
) -> None:
    scenarios = _scenarios(interest_rate=[short_rate] * 2, inflation=[inflation] * 2)
    rate = build_gross_placements(scenarios, DRAFT, ["livret_a"])["livret_a"]
    np.testing.assert_allclose(rate.to_numpy(), [expected] * 2)


def test_serie_absente_refusee() -> None:
    scenarios = _scenarios(stock_return=[0.1, 0.1]).drop(columns=["inflation"])
    with pytest.raises(ValueError, match="inflation"):
        build_gross_placements(scenarios, DRAFT, ["livret_a"])


def test_sur_les_vrais_scenarios() -> None:
    from investment_calculator.modules.scenario_generator import ScenarioGenerator

    scenarios = ScenarioGenerator(random_seed=42).generate(
        {"num_scenarios": 20, "time_horizon": 5, "timestep": 1.0, "use_stochastic": False}
    )["scenarios"]
    gse_plus = build_gross_placements(scenarios, DRAFT, ["av_uc_actions", "livret_a"])
    assert gse_plus.shape == (100, 2)
    assert gse_plus.notna().all().all()
    assert (gse_plus["livret_a"] >= 0.005).all()
