"""
Unit tests for the Investment Calculator package

Tests all major components: GSE, GSE+, MOCA, Personal Variables, and Utilities
"""

import unittest
import numpy as np
import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from investment_calculator import (
    PersonalVariables,
    InvestmentProfile,
    RiskTolerance,
    InvestmentGoal,
    GlobalScenarioEngine,
    EconomicScenario,
    ScenarioType,
    TaxIntegratedScenarioEngine,
    TaxConfig,
    AccountType,
    MOCA,
    OptimizationMethod,
    PortfolioOptimizer,
    validate_inputs,
    validate_allocation,
    calculate_returns,
)


class TestPersonalVariables(unittest.TestCase):
    """Test PersonalVariables class"""

    def test_valid_creation(self):
        """Test creating valid PersonalVariables"""
        pv = PersonalVariables(
            age=35,
            annual_income=100000,
            current_savings=50000,
            monthly_contribution=1500,
            investment_horizon=30,
        )

        self.assertEqual(pv.age, 35)
        self.assertEqual(pv.annual_income, 100000)
        self.assertEqual(pv.current_savings, 50000)

    def test_invalid_age(self):
        """Test that invalid age raises error"""
        with self.assertRaises(ValueError):
            PersonalVariables(
                age=150,  # Invalid
                annual_income=100000,
                investment_horizon=30,
            )

    def test_negative_income(self):
        """Test that negative income raises error"""
        with self.assertRaises(ValueError):
            PersonalVariables(
                age=35,
                annual_income=-50000,  # Invalid
                investment_horizon=30,
            )

    def test_risk_score_calculation(self):
        """Test risk score calculation"""
        pv = PersonalVariables(
            age=30,
            annual_income=75000,
            risk_tolerance=RiskTolerance.AGGRESSIVE,
            investment_horizon=30,
        )

        score = pv.get_risk_score()
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_years_to_retirement(self):
        """Test years to retirement calculation"""
        pv = PersonalVariables(
            age=40,
            annual_income=100000,
            investment_horizon=25,
        )

        years = pv.years_to_retirement
        self.assertEqual(years, 25)


class TestInvestmentProfile(unittest.TestCase):
    """Test InvestmentProfile class"""

    def setUp(self):
        """Set up test profile"""
        self.pv = PersonalVariables(
            age=35,
            annual_income=100000,
            current_savings=50000,
            monthly_contribution=1500,
            investment_horizon=30,
            emergency_fund_months=6,
            debt_to_income_ratio=0.2,
        )

        self.profile = InvestmentProfile(
            personal_vars=self.pv,
            primary_goal=InvestmentGoal.RETIREMENT,
        )

    def test_profile_creation(self):
        """Test profile creation"""
        self.assertIsNotNone(self.profile)
        self.assertEqual(self.profile.primary_goal, InvestmentGoal.RETIREMENT)

    def test_recommended_allocation(self):
        """Test recommended allocation generation"""
        allocation = self.profile.get_recommended_asset_allocation()

        self.assertIsInstance(allocation, dict)
        total = sum(allocation.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_investment_readiness(self):
        """Test investment readiness check"""
        ready, warnings = self.profile.is_ready_to_invest()

        self.assertIsInstance(ready, bool)
        self.assertIsInstance(warnings, list)


class TestGlobalScenarioEngine(unittest.TestCase):
    """Test GlobalScenarioEngine class"""

    def setUp(self):
        """Set up GSE with fixed seed"""
        self.gse = GlobalScenarioEngine(random_seed=42)

    def test_baseline_scenario(self):
        """Test baseline scenario generation"""
        scenario = self.gse.generate_baseline_scenario(years=30)

        self.assertIsInstance(scenario, EconomicScenario)
        self.assertEqual(scenario.years, 30)
        self.assertEqual(len(scenario.stock_returns), 30)
        self.assertEqual(scenario.scenario_type, ScenarioType.BASELINE)

    def test_optimistic_scenario(self):
        """Test optimistic scenario generation"""
        scenario = self.gse.generate_optimistic_scenario(years=30)

        self.assertEqual(scenario.scenario_type, ScenarioType.OPTIMISTIC)
        self.assertEqual(scenario.years, 30)

    def test_pessimistic_scenario(self):
        """Test pessimistic scenario generation"""
        scenario = self.gse.generate_pessimistic_scenario(years=30)

        self.assertEqual(scenario.scenario_type, ScenarioType.PESSIMISTIC)
        self.assertEqual(scenario.years, 30)

    def test_monte_carlo_scenarios(self):
        """Test Monte Carlo scenario generation"""
        scenarios = self.gse.generate_monte_carlo_scenarios(
            years=30,
            n_scenarios=10,
        )

        self.assertEqual(len(scenarios), 10)
        self.assertTrue(all(s.scenario_type == ScenarioType.MONTE_CARLO for s in scenarios))

    def test_standard_scenarios(self):
        """Test standard scenarios generation"""
        scenarios = self.gse.generate_standard_scenarios(years=30)

        self.assertEqual(len(scenarios), 3)  # Pessimistic, baseline, optimistic

    def test_scenario_statistics(self):
        """Test scenario statistics calculation"""
        scenario = self.gse.generate_baseline_scenario(years=30)
        stats = scenario.get_summary_statistics()

        self.assertIn("stock_returns", stats)
        self.assertIn("mean", stats["stock_returns"])
        self.assertIn("std", stats["stock_returns"])

    def test_scenario_to_dataframe(self):
        """Test scenario conversion to DataFrame"""
        scenario = self.gse.generate_baseline_scenario(years=30)
        df = scenario.to_dataframe()

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 30)
        self.assertIn("stock_return", df.columns)


class TestTaxIntegratedScenarioEngine(unittest.TestCase):
    """Test TaxIntegratedScenarioEngine class"""

    def setUp(self):
        """Set up GSE+ with fixed seed"""
        self.gse = GlobalScenarioEngine(random_seed=42)
        self.tax_config = TaxConfig(
            ordinary_income_rate=0.25,
            long_term_cap_gains_rate=0.15,
            state_tax_rate=0.05,
        )
        self.gse_plus = TaxIntegratedScenarioEngine(
            tax_config=self.tax_config,
            gse=self.gse,
        )

    def test_tax_integrated_scenario_taxable(self):
        """Test tax-integrated scenario for taxable account"""
        base_scenario = self.gse.generate_baseline_scenario(years=30)

        tax_scenario = self.gse_plus.generate_tax_integrated_scenario(
            scenario=base_scenario,
            account_type=AccountType.TAXABLE,
        )

        self.assertEqual(tax_scenario.account_type, AccountType.TAXABLE)
        self.assertEqual(len(tax_scenario.after_tax_stock_returns), 30)

        # After-tax returns should be less than pre-tax for taxable account
        self.assertLess(
            np.mean(tax_scenario.after_tax_bond_returns),
            np.mean(base_scenario.bond_returns),
        )

    def test_tax_integrated_scenario_tax_free(self):
        """Test tax-integrated scenario for tax-free account"""
        base_scenario = self.gse.generate_baseline_scenario(years=30)

        tax_scenario = self.gse_plus.generate_tax_integrated_scenario(
            scenario=base_scenario,
            account_type=AccountType.TAX_FREE,
        )

        # Tax-free account should have no tax drag
        self.assertTrue(np.allclose(tax_scenario.tax_drag, 0))

    def test_withdrawal_tax_calculation(self):
        """Test withdrawal tax calculation"""
        base_scenario = self.gse.generate_baseline_scenario(years=30)

        tax_scenario = self.gse_plus.generate_tax_integrated_scenario(
            scenario=base_scenario,
            account_type=AccountType.TAX_DEFERRED,
        )

        withdrawal_tax = tax_scenario.calculate_withdrawal_tax(
            withdrawal_amount=100000,
            is_qualified_withdrawal=True,
        )

        self.assertGreater(withdrawal_tax, 0)

    def test_account_type_comparison(self):
        """Test comparison of account types"""
        comparison = self.gse_plus.compare_account_types(
            years=30,
            initial_investment=50000,
            annual_contribution=12000,
        )

        self.assertIsInstance(comparison, pd.DataFrame)
        self.assertEqual(len(comparison), 3)  # 3 account types


class TestMOCA(unittest.TestCase):
    """Test MOCA class"""

    def setUp(self):
        """Set up MOCA instance"""
        pv = PersonalVariables(
            age=35,
            annual_income=100000,
            current_savings=50000,
            monthly_contribution=1500,
            investment_horizon=30,
        )

        self.profile = InvestmentProfile(personal_vars=pv)

        self.gse = GlobalScenarioEngine(random_seed=42)
        self.tax_config = TaxConfig()
        self.gse_plus = TaxIntegratedScenarioEngine(tax_config=self.tax_config)

        # Generate test scenarios
        base_scenarios = self.gse.generate_standard_scenarios(years=30)
        self.tax_scenarios = [
            self.gse_plus.generate_tax_integrated_scenario(s, AccountType.TAXABLE)
            for s in base_scenarios
        ]

        self.moca = MOCA(investment_profile=self.profile)

    def test_simulate_investment(self):
        """Test single investment simulation"""
        allocation = {"stocks": 0.7, "bonds": 0.25, "real_estate": 0.05}

        result = self.moca.simulate_investment(
            scenario=self.tax_scenarios[0],
            asset_allocation=allocation,
        )

        self.assertGreater(result.final_balance, 0)
        self.assertEqual(len(result.balances), 30)

    def test_run_scenarios(self):
        """Test running multiple scenarios"""
        allocation = {"stocks": 0.6, "bonds": 0.3, "real_estate": 0.1}

        results = self.moca.run_scenarios(
            scenarios=self.tax_scenarios,
            asset_allocation=allocation,
        )

        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.final_balance > 0 for r in results))

    def test_calculate_statistics(self):
        """Test statistics calculation"""
        allocation = {"stocks": 0.7, "bonds": 0.25, "real_estate": 0.05}
        results = self.moca.run_scenarios(self.tax_scenarios, allocation)

        stats = self.moca.calculate_statistics(results)

        self.assertGreater(stats.mean_final_balance, 0)
        self.assertGreater(stats.median_final_balance, 0)
        self.assertGreaterEqual(stats.probability_of_loss, 0)
        self.assertLessEqual(stats.probability_of_loss, 1)

    def test_portfolio_optimization(self):
        """Test portfolio optimization"""
        optimal_allocation, stats = self.moca.optimize_portfolio(
            scenarios=self.tax_scenarios,
            method=OptimizationMethod.MAX_SHARPE,
        )

        # Check allocation sums to 1
        total = sum(optimal_allocation.values())
        self.assertAlmostEqual(total, 1.0, places=5)

        # Check all weights are non-negative
        self.assertTrue(all(w >= 0 for w in optimal_allocation.values()))

    def test_generate_report(self):
        """Test report generation"""
        allocation = {"stocks": 0.7, "bonds": 0.25, "real_estate": 0.05}
        self.moca.run_scenarios(self.tax_scenarios, allocation)

        report = self.moca.generate_report()

        self.assertIsInstance(report, str)
        self.assertIn("MOCA", report)


class TestPortfolioOptimizer(unittest.TestCase):
    """Test PortfolioOptimizer class"""

    def setUp(self):
        """Set up test data"""
        np.random.seed(42)

        # Generate sample returns
        n_periods = 100
        returns_data = {
            "stocks": np.random.normal(0.10, 0.18, n_periods),
            "bonds": np.random.normal(0.05, 0.07, n_periods),
            "real_estate": np.random.normal(0.08, 0.12, n_periods),
        }

        self.returns_df = pd.DataFrame(returns_data)
        self.optimizer = PortfolioOptimizer(
            asset_returns=self.returns_df,
            asset_names=["stocks", "bonds", "real_estate"],
        )

    def test_min_volatility_optimization(self):
        """Test minimum volatility optimization"""
        allocation = self.optimizer.optimize_min_volatility()

        total = sum(allocation.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_max_sharpe_optimization(self):
        """Test maximum Sharpe ratio optimization"""
        allocation = self.optimizer.optimize_max_sharpe()

        total = sum(allocation.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_risk_parity_optimization(self):
        """Test risk parity optimization"""
        allocation = self.optimizer.optimize_risk_parity()

        total = sum(allocation.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_portfolio_stats_calculation(self):
        """Test portfolio statistics calculation"""
        weights = np.array([0.6, 0.3, 0.1])

        ret, vol, sharpe = self.optimizer.calculate_portfolio_stats(weights)

        self.assertIsInstance(ret, float)
        self.assertIsInstance(vol, float)
        self.assertIsInstance(sharpe, float)


class TestUtilities(unittest.TestCase):
    """Test utility functions"""

    def test_validate_inputs(self):
        """Test input validation"""
        valid, errors = validate_inputs(
            age=35,
            investment_horizon=30,
            current_savings=50000,
            monthly_contribution=1500,
        )

        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

        # Test invalid inputs
        valid, errors = validate_inputs(
            age=150,  # Invalid
            investment_horizon=30,
            current_savings=50000,
            monthly_contribution=1500,
        )

        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)

    def test_validate_allocation(self):
        """Test allocation validation"""
        # Valid allocation
        valid, errors = validate_allocation(
            {"stocks": 0.7, "bonds": 0.25, "real_estate": 0.05}
        )

        self.assertTrue(valid)

        # Invalid: doesn't sum to 1
        valid, errors = validate_allocation(
            {"stocks": 0.5, "bonds": 0.3}
        )

        self.assertFalse(valid)

    def test_calculate_returns(self):
        """Test return calculation"""
        returns = calculate_returns(
            initial_value=100000,
            final_value=150000,
            years=5,
            contributions=20000,
        )

        self.assertIn("total_return", returns)
        self.assertIn("annualized_return", returns)
        self.assertGreater(returns["total_return"], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflows"""

    def test_complete_workflow(self):
        """Test complete investment analysis workflow"""
        # Step 1: Create profile
        pv = PersonalVariables(
            age=35,
            annual_income=100000,
            current_savings=50000,
            monthly_contribution=1500,
            investment_horizon=30,
        )

        profile = InvestmentProfile(personal_vars=pv)

        # Step 2: Generate scenarios
        gse = GlobalScenarioEngine(random_seed=42)
        scenarios = gse.generate_standard_scenarios(years=30)

        # Step 3: Apply taxes
        tax_config = TaxConfig()
        gse_plus = TaxIntegratedScenarioEngine(tax_config=tax_config)

        tax_scenarios = [
            gse_plus.generate_tax_integrated_scenario(s, AccountType.TAXABLE)
            for s in scenarios
        ]

        # Step 4: Optimize and analyze
        moca = MOCA(investment_profile=profile)

        optimal_allocation, stats = moca.optimize_portfolio(
            scenarios=tax_scenarios,
            method=OptimizationMethod.MAX_SHARPE,
        )

        # Verify results
        self.assertIsNotNone(optimal_allocation)
        self.assertIsNotNone(stats)
        self.assertGreater(stats.mean_final_balance, pv.current_savings)


def suite():
    """Create test suite"""
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPersonalVariables))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestInvestmentProfile))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGlobalScenarioEngine))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTaxIntegratedScenarioEngine))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMOCA))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPortfolioOptimizer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestUtilities))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIntegration))

    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
