"""
GSE++ : rendements nets de frais et d'impôts, par scénario, horizon et placement.
Les cas sont recalculés à la main à partir du régime fr-2026.
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from investment_calculator.market_assumptions import load_market_assumptions
from investment_calculator.modules.net_returns import (
    TaxProfile,
    build_net_returns,
    net_return_moments,
)
from investment_calculator.modules.placements import UnsourcedValueError
from investment_calculator.placement_catalog import PlacementCatalog, load_placement_catalog

DRAFT = load_placement_catalog("fr-2026", allow_draft=True)
PS = DRAFT.regime.social_rate          # prélèvements sociaux du régime
PFU_IR = DRAFT.regime.flat_tax_income_rate


def _catalog(entry: float = 0.0, annual: float = 0.0) -> PlacementCatalog:
    """Le brouillon fr-2026 avec des frais connus partout (valeurs de test)."""
    document = copy.deepcopy(DRAFT.document)
    for placement in document["placements"]:
        placement["fees"] = {"entry_rate": entry, "annual_rate": annual}
    return PlacementCatalog(document=document, source=DRAFT.source, regime=DRAFT.regime)


def _gross(column: str, paths: list[list[float]]) -> pd.DataFrame:
    rows = [
        (f"s{s}", float(t + 1), r) for s, path in enumerate(paths) for t, r in enumerate(path)
    ]
    frame = pd.DataFrame(rows, columns=["scenario_id", "time_period", column])
    return frame.set_index(["scenario_id", "time_period"])


PROFILE = TaxProfile(invested_amount=10_000.0)


def test_pea_apres_cinq_ans_seuls_les_prelevements_sociaux() -> None:
    gross = _gross("pea_actions", [[0.10] * 6])
    net = build_net_returns(gross, _catalog(), PROFILE, [6])
    multiple = 1.10 ** 6
    # Formule Ra du R pour le PEA, frais nuls : 1 + (R - 1)(1 - CS).
    assert net.multiples[0, 0, 0] == pytest.approx(1 + (multiple - 1) * (1 - PS))


def test_pea_avant_cinq_ans_impot_et_prelevements() -> None:
    gross = _gross("pea_actions", [[0.10] * 6])
    net = build_net_returns(gross, _catalog(), PROFILE, [3])
    multiple = 1.10 ** 3
    assert net.multiples[0, 0, 0] == pytest.approx(1 + (multiple - 1) * (1 - 0.128 - PS))


def test_anciennete_d_un_pea_deja_ouvert() -> None:
    gross = _gross("pea_actions", [[0.10] * 6])
    profile = TaxProfile(invested_amount=10_000.0, wrapper_seniority={"pea": 4})
    net = build_net_returns(gross, _catalog(), profile, [3])
    assert net.multiples[0, 0, 0] == pytest.approx(1 + (1.10 ** 3 - 1) * (1 - PS))


def test_une_perte_ne_donne_aucun_credit_d_impot() -> None:
    gross = _gross("pea_actions", [[-0.20, 0.05, 0.0]])
    net = build_net_returns(gross, _catalog(), PROFILE, [3])
    assert net.multiples[0, 0, 0] == pytest.approx(0.80 * 1.05)


def test_assurance_vie_huit_ans_abattement() -> None:
    # 10 000 € à 3 % pendant 8 ans : plus-value 2 668 € < abattement 4 600 €.
    gross = _gross("av_uc_actions", [[0.03] * 8])
    net = build_net_returns(gross, _catalog(), PROFILE, [8])
    gain = 1.03 ** 8 - 1
    assert net.multiples[0, 0, 0] == pytest.approx(1 + gain * (1 - PS))


def test_cto_dividendes_imposes_chaque_annee() -> None:
    gross = _gross("cto_actions", [[0.06, 0.06]])
    net = build_net_returns(gross, _catalog(), PROFILE, [2])
    d = load_market_assumptions().dividend_yield
    rate = PFU_IR + PS
    value, basis = 1.0, 1.0
    for _ in range(2):
        tax = value * d * rate
        basis += value * d - tax
        value = value * 1.06 - tax
    expected = value - (value - basis) * rate
    assert net.multiples[0, 0, 0] == pytest.approx(expected)


def test_livret_a_sans_impot() -> None:
    gross = _gross("livret_a", [[0.015] * 4])
    net = build_net_returns(gross, DRAFT, PROFILE, [4])
    assert net.multiples[0, 0, 0] == pytest.approx(1.015 ** 4)


def test_frais_d_entree_preleves_sur_le_versement() -> None:
    gross = _gross("livret_a", [[0.0] * 2])
    net = build_net_returns(gross, _catalog(entry=0.02), PROFILE, [2])
    assert net.multiples[0, 0, 0] == pytest.approx(0.98)


def test_frais_d_entree_non_sources_refuses() -> None:
    gross = _gross("pea_actions", [[0.1, 0.1]])
    with pytest.raises(UnsourcedValueError, match="entry_rate"):
        build_net_returns(gross, DRAFT, PROFILE, [2])


def test_horizon_hors_des_scenarios_refuse() -> None:
    gross = _gross("livret_a", [[0.01] * 3])
    with pytest.raises(ValueError, match="entre 1 et 3"):
        build_net_returns(gross, DRAFT, PROFILE, [4])


def test_montant_nul_refuse() -> None:
    with pytest.raises(ValueError, match="strictement positif"):
        TaxProfile(invested_amount=0.0)


def test_moments_sur_les_scenarios() -> None:
    paths = [[0.10] * 6, [0.0] * 6, [-0.05] * 6]
    gross = _gross("pea_actions", paths).join(_gross("livret_a", [[0.015] * 6] * 3))
    net = build_net_returns(gross, _catalog(), PROFILE, [6])
    mean, cov = net_return_moments(net, 6)
    annual = net.annualized(6)
    assert list(mean.index) == ["pea_actions", "livret_a"]
    assert mean["livret_a"] == pytest.approx(0.015)
    assert cov.loc["livret_a", "livret_a"] == pytest.approx(0.0)
    np.testing.assert_allclose(cov.to_numpy(), annual.cov().to_numpy())
    assert annual.loc["s2", "pea_actions"] == pytest.approx(0.95 - 1)


def test_sur_les_vrais_scenarios_l_impot_reduit_moyenne_et_volatilite() -> None:
    from investment_calculator.modules.placements import build_gross_placements
    from investment_calculator.modules.scenario_generator import ScenarioGenerator

    scenarios = ScenarioGenerator(random_seed=42).generate(
        {"num_scenarios": 300, "time_horizon": 10, "timestep": 1.0, "use_stochastic": False}
    )["scenarios"]
    catalog = _catalog()
    gross = build_gross_placements(scenarios, catalog, ["av_uc_actions"])
    net = build_net_returns(gross, catalog, PROFILE, [10])
    after = net.annualized(10)["av_uc_actions"]
    before = gross["av_uc_actions"].groupby(level=0).apply(lambda r: (1 + r).prod() ** 0.1 - 1)
    assert after.mean() < before.mean()
    assert after.std() < before.std()
