"""
Calibration Hull-White sur une surface de swaptions (étape 1.B.5, version de
développement — voir docs/journal-1b-calibration.md, point 8).

La surface utilisée (eur-synthetic-2026-08) est SYNTHÉTIQUE : ces tests
vérifient que le pricer et le calibrateur sont mathématiquement corrects,
pas qu'une calibration de marché réelle a été obtenue. Deux repères
indépendants accompagnent la surface (voir HANDOFF_surface_swaptions.md,
section 4) : reproduire ces deux repères avec notre propre implémentation
(pricer fermé par décomposition de Jamshidian, pas le pricer Monte-Carlo R
d'origine, dont les scripts dépendants sont absents de legacy/) est le test
de non-régression disponible en l'absence de R.
"""

from __future__ import annotations

import numpy as np
import pytest

from investment_calculator.stochastic_models.calibration import (
    SwaptionCalibrator,
    hull_white_payer_swaption_price,
    hull_white_zero_coupon_bond_put_price,
    nelson_siegel_curve_functions,
)
from investment_calculator.swaption_surface import (
    SwaptionSurfaceSyntheticNotAllowedError,
    load_swaption_surface,
)

SURFACE_ID = "eur-synthetic-2026-08"


@pytest.fixture
def surface():
    return load_swaption_surface(SURFACE_ID, allow_synthetic=True)


@pytest.fixture
def curve(surface):
    ref = surface.reference_curve
    return nelson_siegel_curve_functions(ref["beta0"], ref["beta1"], ref["beta2"], ref["tau"])


@pytest.fixture
def calibrator(surface, curve):
    curve_p0, curve_f0 = curve
    return SwaptionCalibrator(surface, curve_p0, curve_f0, allow_synthetic=True)


class TestGardeFouSynthetique:
    def test_construire_le_calibrateur_sans_opt_in_est_refuse(self, surface, curve):
        curve_p0, curve_f0 = curve
        with pytest.raises(SwaptionSurfaceSyntheticNotAllowedError):
            SwaptionCalibrator(surface, curve_p0, curve_f0)


class TestForwardEtAnnuite:
    """
    Vérifié contre les feuilles Forwards_ATM/Annuites du classeur fourni
    (calculées indépendamment) — voir HANDOFF_surface_swaptions.md.
    """

    def test_1m_1y(self, calibrator):
        instrument = next(
            i for i in calibrator.instruments
            if i.expiry_label == "1M" and i.tenor_label == "1Y"
        )
        assert instrument.forward_rate == pytest.approx(0.0198539275724824, abs=1e-9)
        assert instrument.annuity == pytest.approx(0.979015902299157, abs=1e-9)

    def test_1m_5y(self, calibrator):
        instrument = next(
            i for i in calibrator.instruments
            if i.expiry_label == "1M" and i.tenor_label == "5Y"
        )
        assert instrument.forward_rate == pytest.approx(0.0238341128708213, abs=1e-9)
        assert instrument.annuity == pytest.approx(4.67092115727771, abs=1e-9)


class TestPrixDeReference:
    """La formule ATM Bachelier réduite (prix = annuité·σ·√(T/2π)) donne le
    prix affiché dans la feuille 'Detail' du classeur — vérifie que forward,
    annuité, et la mise à l'échelle bp sont cohérents, indépendamment de tout
    pricing Hull-White."""

    def test_prime_atm_bachelier_1m_5y(self, calibrator):
        instrument = next(
            i for i in calibrator.instruments
            if i.expiry_label == "1M" and i.tenor_label == "5Y"
        )
        prime_bp = (
            instrument.annuity * instrument.market_vol_bp
            * np.sqrt(instrument.expiry_years / (2 * np.pi))
        )
        assert prime_bp == pytest.approx(29.316929440077462, abs=1e-6)


class TestPricingHullWhite:
    def test_le_prix_tend_vers_zero_quand_sigma_tend_vers_zero_a_la_monnaie(self, calibrator):
        """
        À la monnaie (strike = forward), le prix d'une swaption tend vers 0
        quand sigma tend vers 0 : plus de valeur temps, et la valeur
        intrinsèque d'une option ATM est nulle par construction.
        """
        instrument = next(
            i for i in calibrator.instruments
            if i.expiry_label == "2Y" and i.tenor_label == "5Y"
        )
        price = calibrator.model_price(a=0.05, sigma=1e-8, instrument=instrument)
        assert abs(price) < 1e-4

    def test_le_prix_est_positif_pour_une_swaption_a_la_monnaie(self, curve):
        curve_p0, curve_f0 = curve
        price = hull_white_payer_swaption_price(
            a=0.05, sigma=0.008, expiry_years=2.0, n_payments=5,
            fixed_rate=0.025, curve_p0=curve_p0, curve_f0=curve_f0,
        )
        assert price > 0

    def test_zero_coupon_bond_put_price_est_positif(self, curve):
        curve_p0, _ = curve
        price = hull_white_zero_coupon_bond_put_price(
            a=0.05, sigma=0.008, t=0.0, T=2.0, S=7.0, strike=0.85, curve_p0=curve_p0,
        )
        assert price > 0

    def test_round_trip_prix_vol_est_coherent(self, calibrator):
        """
        Le prix modèle reconverti en vol implicite (Bachelier ATM, sans
        recherche de racine car toutes les swaptions sont à la monnaie) doit
        redonner exactement le prix de départ une fois repricé.
        """
        instrument = calibrator.instruments[20]
        a, sigma = 0.06, 0.009
        price = calibrator.model_price(a, sigma, instrument)
        vol_bp = calibrator.model_vol_bp(a, sigma, instrument)
        reconstructed_price = (
            instrument.annuity * (vol_bp / 10000) * np.sqrt(instrument.expiry_years / (2 * np.pi))
        )
        assert reconstructed_price == pytest.approx(price, rel=1e-9)


class TestCalibrationReproduitLesReperesDuHandoff:
    """
    Repères fournis avec la surface (HANDOFF_surface_swaptions.md, section
    4), calculés par une implémentation indépendante. Tolérance large (pas
    un test à 1 % comme pour un portage R exact) : deux implémentations
    distinctes d'un même pricer fermé peuvent converger vers un optimum
    légèrement différent, en particulier sur le cube complet où la
    dégénérescence de `a` rend l'optimum plat (voir la docstring de
    SwaptionCalibrator).
    """

    def test_cube_complet_degenere_a_vers_zero(self, calibrator):
        # maxiter réduit : Nelder-Mead atteint déjà le voisinage de l'optimum
        # (vérifié manuellement stable entre maxiter=30 et 100) bien avant le
        # défaut de la classe — un test n'a pas besoin de la précision totale.
        result = calibrator.calibrate(initial_a=0.05, initial_sigma_bp=50.0, maxiter=40)
        assert result.n_instruments == 99
        assert result.a < 0.01  # dégénérescence attendue, voir HANDOFF section 4
        assert result.sigma_bp == pytest.approx(61, abs=5)
        assert result.rmse_bp == pytest.approx(8.5, abs=2)

    def test_bande_co_terminale_10_ans_donne_un_a_raisonnable(self, calibrator):
        band = calibrator.select_co_terminal_band(10.0)
        result = calibrator.calibrate(band, initial_a=0.08, initial_sigma_bp=90.0)
        assert 0.05 <= result.a <= 0.15  # ordre de grandeur EIOPA cité par le handoff
        assert result.sigma_bp == pytest.approx(95, abs=10)
        assert result.rmse_bp < 10.0

    def test_fixer_a_ne_calibre_que_sigma(self, calibrator):
        band = calibrator.select_co_terminal_band(10.0)
        result = calibrator.calibrate(band, fixed_a=0.1)
        assert result.a == 0.1
        assert result.rmse_bp < 10.0


class TestSelectCoTerminalBand:
    def test_une_swaption_par_echeance(self, calibrator):
        band = calibrator.select_co_terminal_band(10.0)
        assert len(band) == len(calibrator.surface.expiries)
        assert len({inst.expiry_label for inst in band}) == len(band)

    def test_les_tenors_choisis_se_rapprochent_de_la_cible(self, calibrator):
        """
        Pour la plupart des échéances, un ténor de la grille amène tout près
        de la cible. Exception attendue : les échéances longues (15Y, 20Y)
        pour lesquelles aucun ténor >= 1Y ne peut rapprocher de 10 ans — le
        ténor le plus court disponible (1Y) est alors le meilleur choix
        possible, pas une anomalie de l'algorithme.
        """
        band = calibrator.select_co_terminal_band(10.0)
        for inst in band:
            distance = abs(inst.expiry_years + inst.n_payments - 10.0)
            if inst.expiry_years < 10.0:
                assert distance <= 5.0, inst
            else:
                assert inst.tenor_label == "1Y"  # ténor le plus court possible
