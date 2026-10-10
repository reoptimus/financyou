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

FR_2026 = load_placement_catalog("fr-2026")


def _catalog(**overrides: dict) -> PlacementCatalog:
    """Le catalogue fr-2026, avec des valeurs de test pour les champs à null."""
    document = copy.deepcopy(FR_2026.document)
    for placement in document["placements"]:
        placement.update(copy.deepcopy(overrides.get(placement["id"], {})))
    return PlacementCatalog(document=document, source=FR_2026.source, regime=FR_2026.regime)


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
    catalog = _catalog(av_uc_actions={"fees": {"entry_rate": 0.0, "annual_rate": 0.0088}})
    gse_plus = build_gross_placements(scenarios, catalog, ["av_uc_actions"])
    expected = (1 + scenarios["stock_return"].to_numpy()) * (1 - 0.0088) - 1
    np.testing.assert_allclose(gse_plus["av_uc_actions"].to_numpy(), expected)


UNKNOWN_FEES = {"fees": {"entry_rate": None, "annual_rate": None}}


def test_valeur_non_sourcee_refusee() -> None:
    catalog = _catalog(
        cto_actions=UNKNOWN_FEES,
        pea_actions=UNKNOWN_FEES,
        av_fonds_euros={"support": {"model": "euro_fund", "reference_series": "bond_return",
                                    "pass_through": None, "floor_rate": 0.0}},
    )
    with pytest.raises(UnsourcedValueError, match="fees.annual_rate"):
        build_gross_placements(_scenarios(stock_return=[0.1, 0.1]), catalog, ["cto_actions"])
    with pytest.raises(UnsourcedValueError, match="pass_through"):
        build_gross_placements(_scenarios(stock_return=[0.1, 0.1]), catalog, ["av_fonds_euros"])
    with pytest.raises(UnsourcedValueError, match="fees.entry_rate"):
        entry_fee_rates(catalog, ["pea_actions"])


def test_fonds_euros_plancher_avant_frais() -> None:
    # Capital garanti hors frais (OPEF 2026, p. 27) : une année blanche coûte
    # les frais de gestion.
    catalog = _catalog(av_fonds_euros={
        "support": {"model": "euro_fund", "reference_series": "bond_return",
                    "pass_through": 0.9, "floor_rate": 0.0},
        "fees": {"entry_rate": 0.0, "annual_rate": 0.0066},
    })
    scenarios = _scenarios(bond_return=[0.04, -0.05])
    served = build_gross_placements(scenarios, catalog, ["av_fonds_euros"])["av_fonds_euros"]
    np.testing.assert_allclose(served.to_numpy(), [(1 + 0.036) * (1 - 0.0066) - 1, -0.0066])


# Le modèle annuel que fr-2026 utilisait avant l'actif général : point de comparaison.
ANNUAL_EURO_FUND = {
    "support": {"model": "euro_fund", "reference_series": "bond_return",
                "pass_through": 0.85, "floor_rate": 0.0},
    "fees": {"entry_rate": 0.0055, "annual_rate": 0.0067},
}


def _smoothed(renewal_years: float | None = 8.0, initial_yield: float | None = 0.02) -> dict:
    return {
        "support": {"model": "euro_fund_smoothed", "reference_series": "interest_rate",
                    "renewal_years": renewal_years, "initial_yield": initial_yield,
                    "pass_through": 0.85, "floor_rate": 0.0},
        "fees": {"entry_rate": 0.0, "annual_rate": 0.0067},
    }


def test_fonds_euros_lisse_suit_le_portefeuille_renouvele() -> None:
    # Un huitième du portefeuille est réinvesti chaque année au taux du GSE.
    catalog = _catalog(av_fonds_euros=_smoothed())
    scenarios = _scenarios(interest_rate=[0.06, 0.06, 0.00, 0.00])
    served = build_gross_placements(scenarios, catalog, ["av_fonds_euros"])["av_fonds_euros"]
    y1 = 0.02 + (0.06 - 0.02) / 8
    y2 = y1 + (0.06 - y1) / 8
    y1b = 0.02 + (0.00 - 0.02) / 8  # le second scénario repart du rendement initial
    y2b = y1b + (0.00 - y1b) / 8
    expected = [(1 + 0.85 * y) * (1 - 0.0067) - 1 for y in (y1, y2, y1b, y2b)]
    np.testing.assert_allclose(served.to_numpy(), expected)


def test_fonds_euros_lisse_independant_de_l_ordre_des_lignes() -> None:
    catalog = _catalog(av_fonds_euros=_smoothed())
    scenarios = _scenarios(interest_rate=[0.06, 0.01, 0.03, 0.00])
    ordered = build_gross_placements(scenarios, catalog, ["av_fonds_euros"])
    shuffled = build_gross_placements(scenarios.iloc[[3, 1, 0, 2]], catalog, ["av_fonds_euros"])
    pd.testing.assert_frame_equal(ordered.sort_index(), shuffled.sort_index())


def test_fonds_euros_sans_lissage_reproduit_le_modele_annuel() -> None:
    # renewal_years = 1 : tout est réinvesti chaque année, y(t) = r(t).
    catalog = _catalog(av_fonds_euros=_smoothed(renewal_years=1.0))
    scenarios = _scenarios(interest_rate=[0.04, -0.05])
    served = build_gross_placements(scenarios, catalog, ["av_fonds_euros"])["av_fonds_euros"]
    np.testing.assert_allclose(served.to_numpy(), [(1 + 0.034) * (1 - 0.0067) - 1, -0.0067])


def test_fonds_euros_lisse_valeurs_non_sourcees_refusees() -> None:
    scenarios = _scenarios(interest_rate=[0.02, 0.02])
    for name, kwargs in (("initial_yield", {"initial_yield": None}),
                         ("renewal_years", {"renewal_years": None})):
        catalog = _catalog(av_fonds_euros=_smoothed(**kwargs))
        with pytest.raises(UnsourcedValueError, match=name):
            build_gross_placements(scenarios, catalog, ["av_fonds_euros"])
    with pytest.raises(ValueError, match="au moins"):
        build_gross_placements(scenarios, _catalog(av_fonds_euros=_smoothed(0.5)),
                               ["av_fonds_euros"])


def test_fonds_euros_lisse_volatilite_realiste_sur_le_gse() -> None:
    """Preuve : sur les vrais scénarios, le lissage ramène la volatilité annuelle
    du taux servi sous celle du taux de référence, et loin du modèle annuel."""
    from investment_calculator.modules.scenario_generator import ScenarioGenerator

    scenarios = ScenarioGenerator(random_seed=42).generate(
        {"num_scenarios": 200, "time_horizon": 30, "timestep": 1.0, "use_stochastic": False}
    )["scenarios"]
    annual = build_gross_placements(
        scenarios, _catalog(av_fonds_euros=ANNUAL_EURO_FUND), ["av_fonds_euros"]
    )["av_fonds_euros"]
    smoothed = build_gross_placements(
        scenarios, _catalog(av_fonds_euros=_smoothed()), ["av_fonds_euros"]
    )["av_fonds_euros"]
    # Variation moyenne du taux servi d'une année sur l'autre, dans chaque scénario.
    year_to_year = smoothed.groupby(level="scenario_id").diff().abs().mean()
    assert smoothed.std() < 0.25 * annual.std()
    assert year_to_year < 0.005


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
    rate = build_gross_placements(scenarios, FR_2026, ["livret_a"])["livret_a"]
    np.testing.assert_allclose(rate.to_numpy(), [expected] * 2)


def test_serie_absente_refusee() -> None:
    scenarios = _scenarios(stock_return=[0.1, 0.1]).drop(columns=["inflation"])
    with pytest.raises(ValueError, match="inflation"):
        build_gross_placements(scenarios, FR_2026, ["livret_a"])


def test_sur_les_vrais_scenarios() -> None:
    from investment_calculator.modules.scenario_generator import ScenarioGenerator

    scenarios = ScenarioGenerator(random_seed=42).generate(
        {"num_scenarios": 20, "time_horizon": 5, "timestep": 1.0, "use_stochastic": False}
    )["scenarios"]
    gse_plus = build_gross_placements(scenarios, FR_2026, ["av_uc_actions", "livret_a"])
    assert gse_plus.shape == (100, 2)
    assert gse_plus.notna().all().all()
    assert (gse_plus["livret_a"] >= 0.005).all()


def _general_account(
    assets: list[dict] | None = None,
    initial_rate: float | None = 0.04,
    release_divisor: float | None = 2.0,
    floor_rate: float = 0.0,
    insurer_margin: float | None = 0.0,
    annual_fee: float = 0.0,
) -> dict:
    return {
        "support": {
            "model": "euro_fund_general_account",
            "assets": assets if assets is not None else [
                {"kind": "gse_series", "weight": 1.0, "series": "stock_return"},
            ],
            "pass_through": 0.85,
            "profit_sharing_reserve": {
                "initial_rate": initial_rate, "release_divisor": release_divisor,
            },
            "floor_rate": floor_rate,
            "insurer_margin": insurer_margin,
        },
        "fees": {"entry_rate": 0.0, "annual_rate": annual_fee},
    }


def _served(catalog: PlacementCatalog, scenarios: pd.DataFrame) -> np.ndarray:
    gross = build_gross_placements(scenarios, catalog, ["av_fonds_euros"])
    return gross["av_fonds_euros"].to_numpy()


def test_actif_general_provision_calcul_a_la_main() -> None:
    # Réserve disponible = provision + 85 % du rendement de l'actif ; on en sert la moitié.
    catalog = _catalog(av_fonds_euros=_general_account())
    scenarios = _scenarios(stock_return=[0.04, 0.10])
    b1 = 0.04 + 0.85 * 0.04
    b2 = b1 / 2 + 0.85 * 0.10
    np.testing.assert_allclose(_served(catalog, scenarios), [b1 / 2, b2 / 2])


def test_actif_general_provision_jamais_negative() -> None:
    # Une perte que la provision ne couvre pas est absorbée par l'assureur :
    # taux servi au plancher, provision vidée, et rien n'est reporté sur l'année suivante.
    catalog = _catalog(av_fonds_euros=_general_account())
    scenarios = _scenarios(stock_return=[-0.50, 0.02])
    np.testing.assert_allclose(_served(catalog, scenarios), [0.0, 0.85 * 0.02 / 2])


def test_actif_general_melange_pondere() -> None:
    assets = [
        {"kind": "gse_series", "weight": 0.25, "series": "stock_return"},
        {"kind": "gse_series", "weight": 0.75, "series": "bond_return"},
    ]
    catalog = _catalog(
        av_fonds_euros=_general_account(assets, initial_rate=0.0, release_divisor=1.0)
    )
    scenarios = _scenarios(stock_return=[0.08, 0.08], bond_return=[0.04, 0.04])
    np.testing.assert_allclose(_served(catalog, scenarios), [0.85 * 0.05] * 2)


def test_actif_general_sans_provision_reproduit_le_modele_lisse() -> None:
    # Sans provision ni lissage, un actif 100 % obligataire en valeur comptable
    # redonne exactement euro_fund_smoothed.
    bonds = {"kind": "book_bonds", "weight": 1.0, "reference_series": "interest_rate",
             "renewal_years": 8.0, "initial_yield": 0.02}
    general = _catalog(av_fonds_euros=_general_account(
        [bonds], initial_rate=0.0, release_divisor=1.0, annual_fee=0.0067,
    ))
    smoothed = _catalog(av_fonds_euros=_smoothed())
    scenarios = _scenarios(interest_rate=[0.06, 0.06, 0.00, 0.00])
    np.testing.assert_allclose(_served(general, scenarios), _served(smoothed, scenarios))


def test_actif_general_marge_prelevee_comme_des_frais() -> None:
    with_margin = _catalog(av_fonds_euros=_general_account(insurer_margin=0.004, annual_fee=0.0067))
    fees_only = _catalog(av_fonds_euros=_general_account(annual_fee=0.0107))
    scenarios = _scenarios(stock_return=[0.04, 0.10])
    np.testing.assert_allclose(_served(with_margin, scenarios), _served(fees_only, scenarios))


def test_actif_general_independant_de_l_ordre_des_lignes() -> None:
    catalog = _catalog(av_fonds_euros=_general_account())
    scenarios = _scenarios(stock_return=[0.04, 0.10, -0.20, 0.03])
    expected = build_gross_placements(scenarios, catalog, ["av_fonds_euros"])["av_fonds_euros"]
    shuffled = scenarios.iloc[[3, 1, 0, 2]]
    result = build_gross_placements(shuffled, catalog, ["av_fonds_euros"])["av_fonds_euros"]
    pd.testing.assert_series_equal(result.sort_index(), expected.sort_index())


def test_actif_general_poids_incoherents_refuses() -> None:
    assets = [{"kind": "gse_series", "weight": 0.9, "series": "stock_return"}]
    catalog = _catalog(av_fonds_euros=_general_account(assets))
    with pytest.raises(ValueError, match="font 0.9"):
        _served(catalog, _scenarios(stock_return=[0.04, 0.10]))


@pytest.mark.parametrize(
    "overrides",
    [
        {"initial_rate": None},
        {"release_divisor": None},
        {"insurer_margin": None},
        {"assets": [{"kind": "gse_series", "weight": None, "series": "stock_return"}]},
    ],
)
def test_actif_general_valeurs_non_sourcees_refusees(overrides: dict) -> None:
    catalog = _catalog(av_fonds_euros=_general_account(**overrides))
    with pytest.raises(UnsourcedValueError):
        _served(catalog, _scenarios(stock_return=[0.04, 0.10]))


def test_actif_general_volatilite_realiste_sur_le_gse() -> None:
    """Preuve : avec les obligations en valeur comptable et la provision, le taux
    servi varie de moins d'un point par an, loin du modèle annuel actuel."""
    from investment_calculator.modules.scenario_generator import ScenarioGenerator

    scenarios = ScenarioGenerator(random_seed=42).generate(
        {"num_scenarios": 200, "time_horizon": 30, "timestep": 1.0, "use_stochastic": False}
    )["scenarios"]
    # Poids et paramètres d'essai, pas des valeurs proposées.
    assets = [
        {"kind": "book_bonds", "weight": 0.80, "reference_series": "interest_rate",
         "renewal_years": 10.0, "initial_yield": 0.0391},
        {"kind": "gse_series", "weight": 0.10, "series": "stock_return"},
        {"kind": "gse_series", "weight": 0.05, "series": "real_estate_return"},
        {"kind": "gse_series", "weight": 0.05, "series": "interest_rate"},
    ]
    catalog = _catalog(av_fonds_euros=_general_account(
        assets, initial_rate=0.043, release_divisor=2.65, annual_fee=0.0067,
    ))
    general = build_gross_placements(scenarios, catalog, ["av_fonds_euros"])["av_fonds_euros"]
    annual = build_gross_placements(
        scenarios, _catalog(av_fonds_euros=ANNUAL_EURO_FUND), ["av_fonds_euros"]
    )["av_fonds_euros"]
    year_to_year = general.groupby(level="scenario_id").diff().abs().mean()
    assert general.std() < 0.3 * annual.std()
    assert year_to_year < 0.01
    assert (general > -0.0067 + 1e-12).mean() > 0.99  # presque jamais au plancher


def test_actif_general_accepte_par_le_schema() -> None:
    from investment_calculator import placement_catalog as pc
    from investment_calculator.tax_regime import load_regime

    document = copy.deepcopy(FR_2026.document)
    for placement in document["placements"]:
        if placement["id"] == "av_fonds_euros":
            placement["support"] = _general_account([
                {"kind": "book_bonds", "weight": 0.9, "reference_series": "interest_rate",
                 "renewal_years": 10, "initial_yield": 0.03},
                {"kind": "gse_series", "weight": 0.1, "series": "stock_return"},
            ])["support"]
    pc._validate(document, pc.PACKAGE_CATALOG_DIR / "test.json", load_regime("fr-2026"))


def test_fonds_euros_fr_2026_calage() -> None:
    """Preuve du calage de fr-2026 : sur 1 000 scénarios, le fonds euros sert en
    moyenne entre 2 % et 3,5 % net (2,63 % observé en 2024, ACPR n° 175) et varie
    de moins d'un point par an."""
    from investment_calculator.modules.scenario_generator import ScenarioGenerator

    scenarios = ScenarioGenerator(random_seed=42).generate(
        {"num_scenarios": 1000, "time_horizon": 30, "timestep": 1.0, "use_stochastic": False}
    )["scenarios"]
    served = build_gross_placements(scenarios, FR_2026, ["av_fonds_euros"])["av_fonds_euros"]
    year_to_year = served.groupby(level="scenario_id").diff().abs().mean()
    assert 0.02 < served.mean() < 0.035
    assert year_to_year < 0.01
