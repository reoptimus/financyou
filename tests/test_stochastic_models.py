"""
Unit tests for stochastic models module.

Tests cover:
- Hull-White interest rate model
- Correlated random variable generation
- Black-Scholes equity model
- Real estate model
- EIOPA calibration
"""

import os
import sys
import unittest
import warnings

import numpy as np
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator.stochastic_models import (
    BlackScholesEquity,
    CorrelatedRandomGenerator,
    EIOPACalibrator,
    HullWhiteModel,
    RealEstateModel,
)
from investment_calculator.stochastic_models.correlation import (
    AHLGRIM_2005_CORRELATION,
)


class TestHullWhiteModel(unittest.TestCase):
    """Tests for Hull-White interest rate model."""

    def setUp(self):
        """Set up test fixtures."""
        # Create simple forward curve and bond prices
        self.n_steps = 20
        self.f0t = np.linspace(0.02, 0.03, self.n_steps)
        self.P0t = np.exp(-np.cumsum(self.f0t) * 0.5)

        self.model = HullWhiteModel(
            a=0.1,
            sigma=0.01,
            f0t=self.f0t,
            P0t=self.P0t,
            dt=0.5,
            n_scenarios=100,
            T=10
        )

    def test_initialization(self):
        """Test model initialization."""
        self.assertEqual(self.model.a, 0.1)
        self.assertEqual(self.model.sigma, 0.01)
        self.assertEqual(self.model.n_scenarios, 100)
        self.assertEqual(self.model.n_steps, 20)

    def test_invalid_parameters(self):
        """Test that invalid parameters raise errors."""
        with self.assertRaises(ValueError):
            HullWhiteModel(a=-0.1, sigma=0.01, f0t=self.f0t, P0t=self.P0t)

        with self.assertRaises(ValueError):
            HullWhiteModel(a=0.1, sigma=-0.01, f0t=self.f0t, P0t=self.P0t)

    def test_K_function(self):
        """Test Hull-White K function."""
        K = HullWhiteModel.K(1.0, 0.1)
        expected = (1 - np.exp(-0.1)) / 0.1
        self.assertAlmostEqual(K, expected, places=10)

        # Test edge case: a=0
        K_zero = HullWhiteModel.K(2.0, 0.0)
        self.assertEqual(K_zero, 2.0)

    def test_L_function(self):
        """Test Hull-White L function."""
        L = HullWhiteModel.L(1.0, 0.01, 0.1)
        expected = (0.01**2 / (2 * 0.1)) * (1 - np.exp(-2 * 0.1))
        self.assertAlmostEqual(L, expected, places=10)

    def test_generate_scenarios(self):
        """Test scenario generation."""
        results = self.model.generate_scenarios()

        # Check output shapes
        self.assertEqual(results['rt'].shape, (100, 20))
        self.assertEqual(results['Rt'].shape, (100, 20))
        self.assertEqual(results['deflators'].shape, (100, 20))
        self.assertEqual(results['residuals'].shape, (100, 20))

        # Check initial values
        np.testing.assert_array_almost_equal(
            results['rt'][:, 0], self.f0t[0], decimal=10
        )

        # Check deflators are decreasing (mostly)
        # Deflators should start at ~1 and decrease
        self.assertTrue(np.all(results['deflators'][:, 0] <= 1.0))
        self.assertTrue(np.all(results['deflators'] > 0))

    def test_bond_price(self):
        """Test bond price calculation."""
        rt = 0.02
        t = 0
        T = 1

        price = self.model.bond_price(t, T, rt)

        # Price should be between 0 and 1
        self.assertGreater(price, 0)
        self.assertLess(price, 1)

    def test_antithetic_variates(self):
        """Test that antithetic variates are used correctly."""
        np.random.seed(42)
        results_anti = self.model.generate_scenarios(use_antithetic=True)

        np.random.seed(42)
        results_no_anti = self.model.generate_scenarios(use_antithetic=False)

        # Shapes should be the same
        self.assertEqual(results_anti['rt'].shape, results_no_anti['rt'].shape)

        # Results should be different (different random generation)
        # (Note: they won't be exactly opposite because of filtering)


class TestCorrelatedRandomGenerator(unittest.TestCase):
    """Tests for correlated random variable generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = CorrelatedRandomGenerator(
            correlation_matrix=AHLGRIM_2005_CORRELATION,
            n_scenarios=1000,
            n_steps=100,
            random_seed=42
        )

    def test_initialization(self):
        """Test generator initialization."""
        self.assertEqual(self.generator.n_assets, 5)
        self.assertEqual(self.generator.n_scenarios, 1000)
        self.assertEqual(self.generator.n_steps, 100)

    def test_correlation_matrix_validation(self):
        """Test correlation matrix validation."""
        # Asymmetric matrix should be symmetrized
        asymmetric = np.array([[1.0, 0.5], [0.6, 1.0]])

        # This should work with a warning about symmetrization
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            gen = CorrelatedRandomGenerator(
                correlation_matrix=asymmetric,
                asset_names=['asset1', 'asset2'],
                n_scenarios=10,
                n_steps=10
            )

        np.testing.assert_array_almost_equal(
            gen.correlation_matrix,
            gen.correlation_matrix.T
        )

    def test_invalid_correlation_matrix(self):
        """Test that invalid correlation matrices raise errors."""
        # Non-square matrix should fail
        with self.assertRaises(ValueError):
            CorrelatedRandomGenerator(
                correlation_matrix=np.array([[1.0, 0.5]]),
                n_scenarios=10,
                n_steps=10
            )

    def test_generate_shocks(self):
        """Test shock generation."""
        results = self.generator.generate()

        # Check shape
        self.assertEqual(results['shocks'].shape, (5, 1000, 100))

        # Check mean close to zero
        means = np.mean(results['shocks'], axis=(1, 2))
        np.testing.assert_array_almost_equal(means, np.zeros(5), decimal=1)

        # Check standard deviation close to 1
        stds = np.std(results['shocks'], axis=(1, 2))
        np.testing.assert_array_almost_equal(stds, np.ones(5), decimal=1)

    def test_with_rate_residuals(self):
        """Test generation with pre-specified rate residuals."""
        rate_residuals = np.random.normal(0, 1, (1000, 100))

        results = self.generator.generate(rate_residuals=rate_residuals)

        # First asset should use rate residuals
        # results['shocks'] has shape (n_assets, n_scenarios, n_steps)
        # rate_residuals has shape (n_scenarios, n_steps)
        np.testing.assert_array_almost_equal(
            results['shocks'][0, :, :],
            rate_residuals
        )

    def test_correlation_structure(self):
        """Test that generated shocks have correct correlation."""
        results = self.generator.generate()

        # Verify correlation
        verification = self.generator.verify_correlation(results['shocks'])

        # Differences should be small (within Monte Carlo error)
        self.assertTrue(np.all(np.abs(verification['Difference']) < 0.05))

    def test_get_asset_shocks(self):
        """Test extraction of asset-specific shocks."""
        results = self.generator.generate()

        equity_shocks = self.generator.get_asset_shocks(
            results['shocks'], 'equity'
        )

        self.assertEqual(equity_shocks.shape, (1000, 100))

    def test_reorder_assets(self):
        """Test asset reordering."""
        original_order = self.generator.asset_names.copy()

        # Reorder: move last to first
        new_order = [4, 0, 1, 2, 3]
        self.generator.reorder_assets(new_order)

        self.assertEqual(self.generator.asset_names[0], original_order[4])


class TestBlackScholesEquity(unittest.TestCase):
    """Tests for Black-Scholes equity model."""

    def setUp(self):
        """Set up test fixtures."""
        self.model = BlackScholesEquity(
            sigma=0.18,
            dividend_yield=0.02,
            dt=0.5,
            n_scenarios=100,
            T=10
        )

        # Create test short rates
        self.short_rates = np.full((100, 20), 0.03)

    def test_initialization(self):
        """Test model initialization."""
        self.assertEqual(self.model.sigma, 0.18)
        self.assertEqual(self.model.dividend_yield, 0.02)
        self.assertEqual(self.model.n_scenarios, 100)

    def test_invalid_parameters(self):
        """Test that invalid parameters raise errors."""
        with self.assertRaises(ValueError):
            BlackScholesEquity(sigma=-0.1)

        with self.assertRaises(ValueError):
            BlackScholesEquity(sigma=0.1, dividend_yield=-0.01)

    def test_generate_returns(self):
        """Test return generation."""
        results = self.model.generate_returns(self.short_rates)

        # Check shapes
        self.assertEqual(results['total_returns'].shape, (100, 20))
        self.assertEqual(results['price_returns'].shape, (100, 20))
        self.assertEqual(results['dividend_returns'].shape, (100, 20))

        # Total returns = price + dividend
        np.testing.assert_array_almost_equal(
            results['total_returns'],
            results['price_returns'] + results['dividend_returns']
        )

    def test_simulate_prices(self):
        """Test price simulation."""
        results = self.model.generate_returns(self.short_rates)

        prices = self.model.simulate_prices(results['total_returns'], initial_price=100)

        # Check initial price
        np.testing.assert_array_almost_equal(prices[:, 0], 100.0)

        # All prices should be positive
        self.assertTrue(np.all(prices > 0))

    def test_drift_uses_short_rate_as_a_period_return_not_annualized(self):
        """
        Régression du bug corrigé à l'étape 1.B.3, vérifiée analytiquement
        (chocs nuls, pas de bruit Monte-Carlo) : short_rates[:, t] est déjà
        un rendement de période (voir HullWhiteModel._calculate_deflators,
        qui l'accumule sans le multiplier par dt) ; seuls risk_premium et la
        correction -σ²/2 sont des taux annualisés, à mettre à l'échelle par
        dt. Avant l'étape 1.B.3, short_rates était multiplié par dt une
        seconde fois, cassant la propriété de martingale même une fois le
        signe de -σ²/2 corrigé isolément (vérifié empiriquement : ~1,18 de
        déviation avec le signe seul corrigé, contre ~1,0003 avec les deux
        corrections combinées — voir docs/journal-1b-calibration.md).
        """
        zero_shocks = np.zeros((100, 20))
        results = self.model.generate_returns(self.short_rates, equity_shocks=zero_shocks)

        # short_rates est constant à 0.03 (rendement de période) ; avec des
        # chocs nuls, chaque pas (hors t=0) doit valoir exactement
        # short_rates[t] + (0 - sigma^2/2)*dt, PAS (short_rates[t] - sigma^2/2)*dt.
        # (total_returns, pas price_returns, pour ne pas mélanger avec le
        # dividende constant qui s'ajoute séparément.)
        expected_step = 0.03 + (0.0 - self.model.sigma**2 / 2) * self.model.dt
        np.testing.assert_allclose(results['total_returns'][:, 1:], expected_step)

    def test_risk_premium_adds_an_annualized_drift(self):
        """risk_premium est un taux annualisé : mis à l'échelle par dt, comme -σ²/2."""
        zero_shocks = np.zeros((100, 20))
        risk_premium = 0.05

        baseline = self.model.generate_returns(self.short_rates, equity_shocks=zero_shocks)
        with_premium = self.model.generate_returns(
            self.short_rates, equity_shocks=zero_shocks, risk_premium=risk_premium
        )

        expected_extra = risk_premium * self.model.dt
        np.testing.assert_allclose(
            with_premium['price_returns'][:, 1:] - baseline['price_returns'][:, 1:],
            expected_extra,
        )

    def test_calculate_percentiles(self):
        """Test percentile calculation."""
        results = self.model.generate_returns(self.short_rates)

        percentiles = self.model.calculate_percentiles(
            results['total_returns'],
            percentiles=[5, 50, 95]
        )

        self.assertIn(5, percentiles)
        self.assertIn(50, percentiles)
        self.assertIn(95, percentiles)

        # 95th percentile should be >= 50th >= 5th (element-wise)
        self.assertTrue(np.all(percentiles[95] >= percentiles[50]))
        self.assertTrue(np.all(percentiles[50] >= percentiles[5]))


class TestRealEstateModel(unittest.TestCase):
    """Tests for real estate model."""

    def setUp(self):
        """Set up test fixtures."""
        self.model = RealEstateModel(
            a=0.15,
            sigma=0.12,
            rental_yield=0.03,
            inflation_adjustment=0.02,
            dt=0.5,
            n_scenarios=100,
            T=10
        )

        # Create test short rates and forward curve
        self.short_rates = np.full((100, 20), 0.03)
        self.f0t = np.full(20, 0.03)

    def test_initialization(self):
        """Test model initialization."""
        self.assertEqual(self.model.a, 0.15)
        self.assertEqual(self.model.sigma, 0.12)
        self.assertEqual(self.model.rental_yield, 0.03)

    def test_generate_returns(self):
        """Test return generation."""
        results = self.model.generate_returns(self.short_rates, self.f0t)

        # Check shapes
        self.assertEqual(results['total_returns'].shape, (100, 20))
        self.assertEqual(results['price_returns'].shape, (100, 20))
        self.assertEqual(results['rental_returns'].shape, (100, 20))

        # Total returns = price + rental
        np.testing.assert_array_almost_equal(
            results['total_returns'],
            results['price_returns'] + results['rental_returns']
        )

    def test_rental_returns_increase_with_inflation(self):
        """Test that rental returns increase with inflation."""
        results = self.model.generate_returns(self.short_rates, self.f0t)

        # Rental returns should increase over time due to inflation
        rental = results['rental_returns'][0, :]

        # Later periods should have higher rental income (on average)
        self.assertGreater(rental[10], rental[1])

    def test_calculate_cap_rate(self):
        """Test cap rate calculation."""
        cap_rate = self.model.calculate_cap_rate(
            rental_income=30000,
            property_value=1000000
        )

        self.assertEqual(cap_rate, 0.03)


class TestEIOPACalibrator(unittest.TestCase):
    """Tests for EIOPA calibration."""

    def setUp(self):
        """Set up test fixtures."""
        # Create synthetic spot curve
        maturities = np.arange(1, 51)
        spot_rates = 0.02 + 0.01 * (1 - np.exp(-maturities / 10))

        self.calibrator = EIOPACalibrator(
            spot_rates=spot_rates,
            maturities=maturities,
            dt=0.5
        )

    def test_initialization(self):
        """Test calibrator initialization."""
        self.assertEqual(len(self.calibrator.spot_rates), 50)
        self.assertEqual(self.calibrator.dt, 0.5)

    def test_calibrate(self):
        """Test calibration process."""
        self.calibrator.calibrate()

        # Check that outputs are generated
        self.assertIsNotNone(self.calibrator.P0t)
        self.assertIsNotNone(self.calibrator.P0t_interp)
        self.assertIsNotNone(self.calibrator.f0t)

        # Bond prices should be decreasing (generally)
        # P(0,0) = 1
        self.assertAlmostEqual(self.calibrator.P0t[0], 1.0)

        # P(0,T) should be less than 1 for T > 0 (positive rates)
        self.assertTrue(np.all(self.calibrator.P0t[1:] < 1.0))
        self.assertTrue(np.all(self.calibrator.P0t > 0))

    def test_get_forward_curve(self):
        """Test forward curve retrieval."""
        self.calibrator.calibrate()

        f0t = self.calibrator.get_forward_curve()

        self.assertIsInstance(f0t, np.ndarray)
        self.assertGreater(len(f0t), 0)

        # Can specify number of steps
        f0t_10 = self.calibrator.get_forward_curve(n_steps=10)
        self.assertEqual(len(f0t_10), 10)

    def test_get_bond_prices(self):
        """Test bond price retrieval."""
        self.calibrator.calibrate()

        P0t = self.calibrator.get_bond_prices()

        self.assertIsInstance(P0t, np.ndarray)
        self.assertGreater(len(P0t), 0)


class TestEIOPACalibratorFromExcel(unittest.TestCase):
    """
    Régression de l'étape 1.B.2 : EIOPACalibrator.from_excel n'avait jamais
    été appelée en pratique. Ses anciens défauts (sheet_name="RFR_spot_no_VA",
    qui n'existe pas dans le classeur réel ; country_column=2, qui pointe
    vers le choc de courbe "YCU" et non la courbe centrale "BaseLine";
    start_row=10, qui saute neuf lignes de données valides) le prouvaient.
    """

    EIOPA_FILE = os.path.join(
        os.path.dirname(__file__), "..", "legacy", "excel_files",
        "EIOPA_avril_2018_FRANCE.xlsx",
    )

    def test_from_excel_loads_the_real_workbook(self):
        calibrator = EIOPACalibrator.from_excel(self.EIOPA_FILE)

        # Feuille "RFR" : 150 maturités (1 à 150 ans), une ligne d'en-tête.
        self.assertEqual(len(calibrator.spot_rates), 150)
        # Colonne "BaseLine" : la courbe d'avril 2018 démarre en taux négatif.
        self.assertLess(calibrator.spot_rates[0], 0)
        self.assertAlmostEqual(calibrator.spot_rates[0], -0.00358, places=5)

    def test_from_excel_produces_a_coherent_curve(self):
        calibrator = EIOPACalibrator.from_excel(self.EIOPA_FILE, dt=0.5)
        calibrator.calibrate()

        p0t = calibrator.P0t_interp
        f0t = calibrator.f0t

        self.assertTrue(np.isfinite(p0t).all())
        self.assertTrue(np.isfinite(f0t).all())
        self.assertAlmostEqual(p0t[0], 1.0, places=6)

        # Taux courts négatifs en avril 2018 : P(0,t) peut légèrement
        # dépasser 1 sur les premières maturités, mais pas déraisonnablement.
        self.assertLess(p0t.max(), 1.10)
        self.assertGreater(p0t.min(), 0)

        # Une fois la zone de taux négatifs de court terme dépassée,
        # P(0,t) doit décroître jusqu'à la fin de la courbe (150 ans).
        tail = p0t[len(p0t) // 2:]
        self.assertTrue((np.diff(tail) <= 1e-9).all())

    def test_from_excel_wrong_sheet_name_raises_a_clear_error(self):
        with self.assertRaises(ValueError):
            EIOPACalibrator.from_excel(self.EIOPA_FILE, sheet_name="RFR_spot_no_VA")


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple models."""

    def test_full_scenario_generation(self):
        """Test complete scenario generation pipeline."""
        # 1. Set up EIOPA calibration
        maturities = np.arange(1, 31)
        spot_rates = 0.02 + 0.01 * (1 - np.exp(-maturities / 10))
        eiopa = EIOPACalibrator(spot_rates=spot_rates, maturities=maturities, dt=0.5)
        eiopa.calibrate()

        f0t = eiopa.get_forward_curve(n_steps=60)
        P0t = eiopa.get_bond_prices(n_steps=60)

        # 2. Generate Hull-White rates
        hw_model = HullWhiteModel(
            a=0.1,
            sigma=0.01,
            f0t=f0t,
            P0t=P0t,
            dt=0.5,
            n_scenarios=100,
            T=30
        )

        hw_results = hw_model.generate_scenarios()

        # 3. Generate correlated shocks
        corr_gen = CorrelatedRandomGenerator(
            n_scenarios=100,
            n_steps=60,
            random_seed=42
        )

        corr_results = corr_gen.generate(rate_residuals=hw_results['residuals'])

        # 4. Generate equity returns
        equity_model = BlackScholesEquity(sigma=0.18, dt=0.5, n_scenarios=100, T=30)

        equity_shocks = corr_gen.get_asset_shocks(corr_results['shocks'], 'equity')
        equity_results = equity_model.generate_returns(
            hw_results['Rt'],
            equity_shocks=equity_shocks
        )

        # 5. Generate real estate returns
        re_model = RealEstateModel(a=0.15, sigma=0.12, dt=0.5, n_scenarios=100, T=30)

        re_price_shocks = corr_gen.get_asset_shocks(
            corr_results['shocks'], 'real_estate'
        )
        # Use inflation shocks for rental component
        re_rental_shocks = corr_gen.get_asset_shocks(
            corr_results['shocks'], 'inflation'
        )

        re_results = re_model.generate_returns(
            hw_results['Rt'],
            f0t,
            re_price_shocks=re_price_shocks,
            re_rental_shocks=re_rental_shocks
        )

        # Verify all outputs have correct shapes
        self.assertEqual(hw_results['Rt'].shape, (100, 60))
        self.assertEqual(equity_results['total_returns'].shape, (100, 60))
        self.assertEqual(re_results['total_returns'].shape, (100, 60))

        # Verify correlations exist between assets
        # Stack all returns
        all_returns = np.stack([
            hw_results['Rt'],
            equity_results['total_returns'],
            re_results['total_returns']
        ])  # Shape: (3, 100, 60)

        # Flatten for correlation
        flat_returns = all_returns.reshape(3, -1)

        # Calculate correlation matrix
        corr_matrix = np.corrcoef(flat_returns)

        # Should have some correlation structure (not identity matrix)
        off_diagonal = corr_matrix - np.eye(3)
        self.assertGreater(np.abs(off_diagonal).max(), 0.01)


def run_tests():
    """Run all tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()


def _immo_hw_v2_r(a2, sigma2, f0t, r0, alea_r2_shocks, alea_rr2_shocks, dt, rental_yield, infl):
    """Transcription ligne à ligne de la boucle d'ImmoHW_V2.R (périodes i = 1..Tf)."""
    nb, tf = alea_rr2_shocks.shape
    k2t_t2a = (1 - np.exp(-2 * a2 * dt)) / (2 * a2)
    k2t_t = (1 - np.exp(-a2 * dt)) / a2
    eta2 = (sigma2 / a2) * (dt - 2 * k2t_t + k2t_t2a) ** 0.5
    l0_p0 = np.log(1 + rental_yield) * dt
    infl = infl * dt
    r0_2 = np.full(nb, r0)
    rdt_immo = np.zeros((nb, tf))
    rdt_immo_l = np.zeros((nb, tf))
    for i in range(1, tf + 1):
        kimmo = f0t[i - 1]
        rdt_immo[:, i - 1] = kimmo * dt + (r0_2 - kimmo) * k2t_t + eta2 * alea_rr2_shocks[:, i - 1]
        r0_2 = (r0_2 * np.exp(-a2 * dt) + kimmo * (1 - np.exp(-a2 * dt))
                + sigma2 * k2t_t2a ** 0.5 * alea_r2_shocks[:, i - 1])
        rdt_immo_l[:, i - 1] = l0_p0 + i * infl
    return rdt_immo, rdt_immo_l, rdt_immo - rdt_immo_l


def test_immobilier_conforme_a_immo_hw_v2_r():
    # Mêmes chocs : le rendement total, le loyer et le prix suivent le R, décalés
    # d'une colonne (la colonne 0 est t = 0, comme pour les taux et les actions).
    rng = np.random.default_rng(7)
    n, steps, dt = 50, 40, 0.5
    f0t = 0.02 + 0.0005 * np.arange(steps)
    price_shocks, rate_shocks = rng.standard_normal((2, n, steps))
    model = RealEstateModel(a=0.5, sigma=0.037, rental_yield=0.01, inflation_adjustment=0.0,
                            dt=dt, n_scenarios=n, T=int(steps * dt))
    out = model.generate_returns(np.zeros((n, steps)), f0t, re_price_shocks=price_shocks,
                                 re_rental_shocks=rate_shocks)
    total, rent, price = _immo_hw_v2_r(0.5, 0.037, f0t, f0t[0], rate_shocks, price_shocks,
                                       dt, 0.01, 0.0)
    np.testing.assert_allclose(out['total_returns'][:, 1:], total[:, :-1], rtol=1e-12)
    np.testing.assert_allclose(out['rental_returns'][:, 1:], rent[:, :-1], rtol=1e-12)
    np.testing.assert_allclose(out['price_returns'][:, 1:], price[:, :-1], rtol=1e-12)
    assert not out['total_returns'][:, 0].any()


def test_le_loyer_n_est_pas_compte_deux_fois():
    # Le loyer est une part du rendement total : changer le loyer déplace le
    # partage entre prix et loyer, pas le total.
    rng = np.random.default_rng(1)
    shocks = rng.standard_normal((2, 20, 30))
    totals = [
        RealEstateModel(a=0.5, sigma=0.037, rental_yield=y, inflation_adjustment=0.02,
                        dt=0.5, n_scenarios=20, T=15).generate_returns(
            np.zeros((20, 30)), np.full(30, 0.03), re_price_shocks=shocks[0],
            re_rental_shocks=shocks[1])['total_returns']
        for y in (0.0, 0.05)
    ]
    np.testing.assert_array_equal(totals[0], totals[1])


def test_calage_immobilier_sur_la_serie_insee_france():
    from pathlib import Path

    from investment_calculator.stochastic_models.real_estate import calibrate_from_annual_returns

    series = np.loadtxt(Path(__file__).parent.parent / "legacy" / "csv_files"
                        / "Rdt_immo_France_horsinfla_INSEE_20172510.txt")
    a, sigma = calibrate_from_annual_returns(series)
    assert (round(a, 3), round(sigma, 4)) == (0.145, 0.0379)
    # Le script R ne retenait que l'écart-type des résidus d'un AR(1) : 3,78 %,
    # le 3,7 % de Param_immo2.Rda.
    slope, intercept = np.polyfit(series[:-1], series[1:], 1)
    residuals = series[1:] - (slope * series[:-1] + intercept)
    assert round(residuals.std(ddof=1), 4) == 0.0378
    # Le modèle simulé au pas d'un an retrouve l'autocorrélation et l'écart-type.
    rng = np.random.default_rng(0)
    n, steps = 2_000, 200
    model = RealEstateModel(a=a, sigma=sigma, rental_yield=0.0, dt=1.0, n_scenarios=n, T=steps)
    shocks = rng.standard_normal((2, n, steps))
    returns = model.generate_returns(np.zeros((n, steps)), np.zeros(steps),
                                     re_price_shocks=shocks[0],
                                     re_rental_shocks=shocks[1])['total_returns'][:, 50:]
    centered = returns - returns.mean()
    rho = (centered[:, 1:] * centered[:, :-1]).sum() / (centered**2).sum()
    assert abs(rho - 0.787) < 0.02
    assert abs(returns.std() - series.std(ddof=1)) < 0.004


def test_calage_immobilier_refuse_une_serie_impossible():
    from investment_calculator.stochastic_models.real_estate import calibrate_from_annual_returns

    with pytest.raises(ValueError, match="autocorrélation"):
        calibrate_from_annual_returns(np.array([0.1, -0.1, 0.1, -0.1, 0.1, -0.1]))


def _eiopa_hull_white(n_scenarios: int, n_steps: int, extra_steps: int) -> HullWhiteModel:
    """Hull-White sur la courbe EIOPA par défaut, pas annuel, courbe allongée de extra_steps."""
    from investment_calculator.yield_curve import load_yield_curve

    curve = load_yield_curve("eiopa-fr-2018-04", dt=1.0)
    return HullWhiteModel(
        a=0.1,
        sigma=0.01,
        f0t=curve.get_forward_curve(n_steps=n_steps + extra_steps),
        P0t=curve.get_bond_prices(n_steps=n_steps + extra_steps),
        dt=1.0,
        n_scenarios=n_scenarios,
        T=n_steps + 0.5,
    )


def test_zero_coupon_prices_coherents_avec_les_deflateurs():
    """
    Les prix zéro-coupon en forme fermée doivent vérifier E[D(t)·P(t, T)] = P(0, T) :
    c'est ce qui garantit que le fonds obligataire est valorisé dans le même
    univers que les déflateurs.
    """
    np.random.seed(42)
    model = _eiopa_hull_white(n_scenarios=20_000, n_steps=11, extra_steps=8)
    results = model.generate_scenarios(filter_explosive=False)
    for i in (1, 5, 10):
        prices = model.zero_coupon_prices(results['rt'][:, i], i, 7)
        deflated = (results['deflators'][:, i][:, None] * prices).mean(axis=0)
        np.testing.assert_allclose(deflated, model.P0t[i + 1:i + 8], rtol=0.005)


def test_fonds_obligataire_d_un_pas_rend_le_taux_court():
    """Une obligation d'un pas rachetée à échéance rend exactement le taux court simple."""
    np.random.seed(42)
    model = _eiopa_hull_white(n_scenarios=200, n_steps=11, extra_steps=1)
    results = model.generate_scenarios(filter_explosive=False)
    total, coupons = model.bond_fund_returns(results['rt'], maturity_steps=1)
    np.testing.assert_allclose(total[:, 1:], np.expm1(results['Rt'][:, 1:]), atol=1e-12)
    np.testing.assert_allclose(coupons, total, atol=1e-12)
    assert np.all(total[:, 0] == 0.0)


def test_fonds_obligataire_porte_un_risque_de_taux():
    """À sept ans, le fonds a une duration : son excès de rendement sur le taux court varie."""
    np.random.seed(42)
    model = _eiopa_hull_white(n_scenarios=2000, n_steps=11, extra_steps=7)
    results = model.generate_scenarios(filter_explosive=False)
    total, coupons = model.bond_fund_returns(results['rt'], maturity_steps=7)
    short = np.expm1(results['Rt'][:, 1:])
    # Une variation de taux de 1 point déplace le prix d'environ 6 % (duration).
    assert (total[:, 1:] - short).std(axis=0).min() > 0.02
    assert np.all(coupons[:, 1:] > -0.05)
