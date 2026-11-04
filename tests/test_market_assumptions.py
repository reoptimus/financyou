"""
Hypothèses de marché et de comportement — chargement et validation.

Étape 1.A.6 : ces valeurs (rendement du dividende, répartition
loyer/appréciation, part de plus-value réalisée annuellement, revenu de
référence pour approximer un barème progressif) vivaient auparavant en dur
dans investment_calculator/modules/tax_engine.py — voir
tests/test_tax_regime_contract.py::LITTERAUX_TOLERES pour l'historique.

Elles ne sont PAS de la fiscalité (voir
docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md) et ne sont pas
davantage vérifiées que ne l'étaient les littéraux dont elles proviennent :
le statut ``draft`` et les ``known_gaps`` du document le disent
explicitement.
"""

from __future__ import annotations

import json

import pytest

from investment_calculator.market_assumptions import (
    PACKAGE_ASSUMPTIONS_DIR,
    SCHEMA_PATH,
    MarketAssumptionsNotFoundError,
    MarketAssumptionsValidationError,
    load_market_assumptions,
)


def test_le_schema_est_un_json_schema_valide():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)


def test_le_jeu_par_defaut_se_charge():
    assumptions = load_market_assumptions()
    assert assumptions.id == "default-2026"
    assert assumptions.status == "validated"


def test_un_identifiant_inconnu_leve_une_erreur_explicite():
    with pytest.raises(MarketAssumptionsNotFoundError) as excinfo:
        load_market_assumptions("inexistant-2099")
    assert "Disponibles" in str(excinfo.value)


def test_les_parts_immobilieres_somment_a_un():
    """
    Contrôle sémantique que le schéma JSON seul ne peut pas exprimer :
    rental_income_share + appreciation_share doit valoir 1, sans quoi le
    moteur sous- ou sur-compte le rendement immobilier total.
    """
    path = PACKAGE_ASSUMPTIONS_DIR / "default-2026.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    # Ne somme plus à 1 avec rental_income_share=0.4.
    document["real_estate"]["appreciation_share"] = 0.9
    document.pop("$schema", None)

    from investment_calculator.market_assumptions import _validate

    with pytest.raises(MarketAssumptionsValidationError, match="doit valoir 1"):
        _validate(document, path)


def test_les_valeurs_exposees_correspondent_au_document():
    assumptions = load_market_assumptions()
    assert 0.0 <= assumptions.dividend_yield <= 1.0
    assert assumptions.rental_income_share + assumptions.appreciation_share == pytest.approx(1.0)
    assert 0.0 <= assumptions.annual_realized_fraction <= 1.0
    assert assumptions.reference_household_income > 0


def test_les_primes_de_risque_sont_exposees():
    """Étape 1.B.3 : primes de risque monde réel, jamais couvertes par un test dédié."""
    assumptions = load_market_assumptions()
    assert 0.0 < assumptions.equity_risk_premium < 0.5
    assert 0.0 < assumptions.real_estate_risk_premium < 0.5


def test_les_hypotheses_economiques_de_l_etape_1_b_4_sont_exposees():
    """
    Étape 1.B.4 : les constantes qui étaient en dur dans
    ScenarioGenerator.__init__ et GlobalScenarioEngine.__init__ (volatilités,
    taux sans risque du chemin simple, paramètres Hull-White, corrélations)
    sont désormais lues depuis ce document.
    """
    assumptions = load_market_assumptions()
    assert assumptions.equity_volatility > 0
    assert assumptions.real_estate_volatility > 0
    assert assumptions.real_estate_mean_reversion > 0
    assert 0.0 <= assumptions.real_estate_rental_yield <= 1.0
    assert assumptions.risk_free_rate_mean > 0
    assert assumptions.risk_free_rate_volatility > 0
    assert assumptions.hull_white_mean_reversion_speed > 0
    assert assumptions.hull_white_volatility > 0
    assert assumptions.bond_return_mean > 0
    assert assumptions.bond_return_volatility > 0
    assert assumptions.inflation_mean > 0
    assert assumptions.inflation_volatility > 0
    assert assumptions.gdp_growth_mean > 0
    assert assumptions.gdp_growth_volatility > 0


@pytest.fixture(scope="module")
def hull_white():
    path = PACKAGE_ASSUMPTIONS_DIR / "default-2026.json"
    return json.loads(path.read_text(encoding="utf-8"))["rates"]["hull_white"]


class TestHullWhiteCalibre:
    """
    rates.hull_white n'est plus un placeholder : il doit se recalculer à partir
    de la surface et de la courbe qu'il cite (étape 1.B.5). Un sigma modifié à
    la main dans le JSON, ou une surface non validée, fait échouer ces tests.
    """

    def test_statut_calibre_avec_provenance(self, hull_white):
        assert hull_white["status"] == "calibrated"
        assert hull_white["calibration"]["validated_by"]

    def test_la_surface_citee_est_reelle_et_validee(self, hull_white):
        from investment_calculator.swaption_surface import load_swaption_surface

        surface = load_swaption_surface(hull_white["calibration"]["swaption_surface_id"])
        assert surface.synthetic is False
        assert surface.status == "validated"

    def test_la_courbe_citee_est_celle_du_chemin_stochastique(self, hull_white):
        from investment_calculator.modules.scenario_generator import ScenarioGenerator

        assert (
            hull_white["calibration"]["yield_curve_id"]
            == ScenarioGenerator.DEFAULT_YIELD_CURVE_ID
        )

    def test_sigma_se_recalcule_depuis_la_surface_et_la_courbe(self, hull_white):
        from investment_calculator.stochastic_models.calibration import (
            SwaptionCalibrator,
            grid_curve_functions,
        )
        from investment_calculator.swaption_surface import load_swaption_surface
        from investment_calculator.yield_curve import load_yield_curve

        calibration = hull_white["calibration"]
        dt = 0.025
        curve = load_yield_curve(calibration["yield_curve_id"], dt=dt)
        curve_p0, curve_f0 = grid_curve_functions(
            curve.get_bond_prices(), curve.get_forward_curve(), dt
        )
        calibrator = SwaptionCalibrator(
            load_swaption_surface(calibration["swaption_surface_id"]), curve_p0, curve_f0
        )
        wanted = {tuple(label.split("×")) for label in calibration["instruments"]}
        band = [
            inst for inst in calibrator.instruments
            if (inst.expiry_label, inst.tenor_label) in wanted
        ]
        assert len(band) == len(wanted)

        result = calibrator.calibrate(band, fixed_a=hull_white["mean_reversion_speed"])
        assert hull_white["volatility"] == pytest.approx(result.sigma, abs=1e-6)
        assert calibration["rmse_bp"] == pytest.approx(result.rmse_bp, abs=0.01)


def test_un_hull_white_calibre_sans_provenance_est_refuse():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((PACKAGE_ASSUMPTIONS_DIR / "schema.json").read_text(encoding="utf-8"))
    document = json.loads(
        (PACKAGE_ASSUMPTIONS_DIR / "default-2026.json").read_text(encoding="utf-8")
    )
    del document["rates"]["hull_white"]["calibration"]
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(document))
    assert any("calibration" in error.message for error in errors)


def test_correlations_a_la_forme_consommee_par_scenario_generator():
    """
    ScenarioGenerator.default_correlations attend un dict clé = tuple de deux
    noms d'actifs, valeur = corrélation — la forme que produisait l'ancien
    littéral inline avant l'étape 1.B.4.
    """
    assumptions = load_market_assumptions()
    correlations = assumptions.correlations
    assert len(correlations) > 0
    for pair, value in correlations.items():
        assert isinstance(pair, tuple)
        assert len(pair) == 2
        assert -1.0 <= value <= 1.0


def test_equity_expected_return_est_le_taux_sans_risque_plus_la_prime():
    assumptions = load_market_assumptions()
    expected = assumptions.risk_free_rate_mean + assumptions.equity_risk_premium
    assert assumptions.equity_expected_return == pytest.approx(expected)


def test_real_estate_expected_return_est_le_taux_sans_risque_plus_la_prime():
    assumptions = load_market_assumptions()
    expected = assumptions.risk_free_rate_mean + assumptions.real_estate_risk_premium
    assert assumptions.real_estate_expected_return == pytest.approx(expected)
