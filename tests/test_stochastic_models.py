"""
Unit tests for stochastic models module.

Tests cover:
- Hull-White interest rate model
- Correlated random variable generation
- Black-Scholes equity model
- Real estate model
- EIOPA calibration
"""

import unittest
import numpy as np
import sys
import os
import warnings

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator.stochastic_models import (
    HullWhiteModel,
    CorrelatedRandomGenerator,
    BlackScholesEquity,
    RealEstateModel,
    EIOPACalibrator
)
from investment_calculator.stochastic_models.correlation import (
    AHLGRIM_2005_CORRELATION,
    CONSERVATIVE_CORRELATION
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
        # Not positive definite
        invalid = np.array([[1.0, 0.9, 0.9], [0.9, 1.0, 0.9], [0.9, 0.9, 1.0]])
        # This should work but might give warning

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
