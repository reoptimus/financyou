## Investment Calculator

A comprehensive investment analysis and portfolio optimization toolkit for calculating optimal investment strategies based on personal variables, economic scenarios, and tax implications.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
  - [GSE (Global Scenario Engine)](#gse-global-scenario-engine)
  - [GSE+ (Tax-Integrated Scenario Engine)](#gse-tax-integrated-scenario-engine)
  - [MOCA (Moteur de Calcul)](#moca-moteur-de-calcul)
  - [Personal Variables](#personal-variables)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Detailed Usage](#detailed-usage)
- [Input Requirements](#input-requirements)
- [Output Description](#output-description)
- [Missing Features / Future Enhancements](#missing-features--future-enhancements)
- [Examples](#examples)

---

## Overview

The Investment Calculator is a sophisticated financial planning toolkit that helps investors make informed decisions by:

1. **Generating economic scenarios** (inflation, interest rates, market returns)
2. **Applying tax calculations** to model after-tax returns
3. **Optimizing portfolio allocations** using classical techniques
4. **Calculating statistics** (expected returns, volatility, VaR, Sharpe ratio)
5. **Running Monte Carlo simulations** for probabilistic analysis

### Key Features

- **Scenario-based analysis**: Generate baseline, optimistic, pessimistic, and Monte Carlo scenarios
- **Tax integration**: Model different account types (taxable, tax-deferred, tax-free)
- **Portfolio optimization**: Mean-variance, max Sharpe, min volatility, risk parity
- **Risk metrics**: Sharpe ratio, Sortino ratio, max drawdown, VaR, CVaR
- **Retirement planning**: Calculate sustainable withdrawal rates and goal achievement probability

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Investment Calculator                     │
└─────────────────────────────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐
  │     GSE       │  │   GSE+ (Tax)  │  │    MOCA      │
  │   (Scenario   │  │  (Tax Engine) │  │ (Optimizer)  │
  │   Generator)  │  │               │  │              │
  └───────────────┘  └───────────────┘  └──────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ Personal Variables│
                  │  & Utilities      │
                  └──────────────────┘
```

### Workflow

1. **Input**: Personal variables (age, income, risk tolerance, etc.)
2. **GSE**: Generate economic scenarios (multiple possible futures)
3. **GSE+**: Apply tax calculations to scenarios
4. **MOCA**: Run simulations and optimize portfolio
5. **Output**: Recommended allocation, expected outcomes, risk metrics

---

## Components

### GSE (Global Scenario Engine)

**Purpose**: Generate economic scenarios for investment analysis

**Key Classes**:
- `EconomicScenario`: Represents a single economic scenario
- `GlobalScenarioEngine`: Generates scenarios using various methods

**Scenario Types**:
1. **Baseline**: Expected/mean economic conditions
2. **Optimistic**: Above-average growth, lower volatility
3. **Pessimistic**: Below-average growth, higher volatility
4. **Monte Carlo**: Thousands of simulated scenarios
5. **Custom**: User-defined economic parameters

**Economic Indicators**:
- Inflation rates
- Interest rates (risk-free rate)
- Stock market returns
- Bond market returns
- Real estate returns
- GDP growth rates

**Example**:
```python
from investment_calculator import GlobalScenarioEngine

gse = GlobalScenarioEngine(random_seed=42)

# Generate standard scenarios
scenarios = gse.generate_standard_scenarios(years=30)

# Generate Monte Carlo scenarios
mc_scenarios = gse.generate_monte_carlo_scenarios(years=30, n_scenarios=1000)

# Create custom scenario
custom = gse.create_custom_scenario(
    scenario_id="custom_recession",
    years=30,
    stocks=np.array([...]),  # Custom stock returns
    bonds=np.array([...]),   # Custom bond returns
)
```

**Outputs**:
- `EconomicScenario` objects containing year-by-year economic indicators
- Summary statistics (mean, std, min, max, median)
- Scenario comparison DataFrame

---

### GSE+ (Tax-Integrated Scenario Engine)

**Purpose**: Apply tax calculations to economic scenarios

**Key Classes**:
- `TaxConfig`: Tax configuration for different jurisdictions
- `TaxIntegratedScenario`: Economic scenario with tax calculations
- `TaxIntegratedScenarioEngine`: Generates tax-integrated scenarios

**Account Types**:
1. **Taxable**: Regular brokerage account (taxed annually)
2. **Tax-Deferred**: Traditional IRA/401k (tax on withdrawal)
3. **Tax-Free**: Roth IRA (no taxes on qualified withdrawals)
4. **Tax-Advantaged Education**: 529 plans

**Tax Calculations**:
- **Ordinary income tax**: Applied to bond interest, non-qualified dividends
- **Capital gains tax**: Applied to stock/real estate appreciation
- **Dividend tax**: Applied to stock dividends
- **State/local taxes**: Additional tax layer
- **Withdrawal penalties**: For early withdrawals

**Example**:
```python
from investment_calculator import TaxIntegratedScenarioEngine, TaxConfig, AccountType

# Configure taxes
tax_config = TaxConfig(
    country_code="US",
    ordinary_income_rate=0.25,
    long_term_cap_gains_rate=0.15,
    state_tax_rate=0.05,
)

# Create GSE+ engine
gse_plus = TaxIntegratedScenarioEngine(tax_config=tax_config)

# Generate tax-integrated scenario
tax_scenario = gse_plus.generate_tax_integrated_scenario(
    scenario=economic_scenario,
    account_type=AccountType.TAXABLE,
)

# Compare account types
comparison = gse_plus.compare_account_types(
    years=30,
    initial_investment=50000,
    annual_contribution=12000,
)
```

**Outputs**:
- After-tax returns for each asset class
- Tax drag (difference between pre-tax and after-tax returns)
- Cumulative taxes paid over time
- Withdrawal tax estimates
- Account type comparison

---

### MOCA (Moteur de Calcul)

**Purpose**: Portfolio optimization and statistical analysis engine

**Key Classes**:
- `MOCA`: Main calculation engine
- `PortfolioOptimizer`: Portfolio optimization using various methods
- `InvestmentResult`: Results from a single scenario simulation
- `PortfolioStatistics`: Statistical analysis across scenarios

**Optimization Methods**:
1. **Mean-Variance (Markowitz)**: Minimize volatility for target return
2. **Max Sharpe Ratio**: Maximize risk-adjusted returns
3. **Min Volatility**: Minimize portfolio volatility
4. **Max Return**: Maximize expected return
5. **Risk Parity**: Equal risk contribution from each asset
6. **Equal Weight**: Simple equal-weighted portfolio

**Statistical Metrics**:
- **Return metrics**: Mean, median, annualized returns
- **Risk metrics**: Volatility, max drawdown, VaR, CVaR
- **Risk-adjusted**: Sharpe ratio, Sortino ratio
- **Probability metrics**: Probability of loss, probability of reaching target

**Example**:
```python
from investment_calculator import MOCA, OptimizationMethod

# Create MOCA instance
moca = MOCA(investment_profile=profile)

# Run scenarios with specific allocation
allocation = {"stocks": 0.7, "bonds": 0.25, "real_estate": 0.05}
results = moca.run_scenarios(tax_scenarios, allocation)

# Calculate statistics
stats = moca.calculate_statistics(target_balance=1000000)

# Optimize portfolio
optimal_allocation, stats = moca.optimize_portfolio(
    scenarios=tax_scenarios,
    method=OptimizationMethod.MAX_SHARPE,
    asset_classes=["stocks", "bonds", "real_estate"],
)

# Generate report
print(moca.generate_report())
```

**Outputs**:
- Optimal asset allocation
- Expected final balance (mean, median, percentiles)
- Expected returns and volatility
- Sharpe ratio
- Probability distributions
- Efficient frontier
- Comprehensive investment report

---

### Personal Variables

**Purpose**: Define investor characteristics and preferences

**Key Classes**:
- `PersonalVariables`: Personal financial information
- `InvestmentProfile`: Complete investment profile with goals
- `RiskTolerance`: Enum for risk tolerance levels
- `InvestmentGoal`: Enum for investment goals

**Required Inputs**:
- **Age**: Current age (18-100)
- **Annual Income**: Gross annual income
- **Current Savings**: Existing investment portfolio value
- **Monthly Contribution**: Monthly investment amount
- **Risk Tolerance**: Conservative, Moderate, Balanced, Aggressive, Very Aggressive
- **Investment Horizon**: Time horizon in years
- **Tax Bracket**: Marginal tax rate
- **Capital Gains Rate**: Long-term capital gains tax rate

**Optional Inputs**:
- Country code
- Emergency fund months
- Debt-to-income ratio
- Existing portfolio allocation
- Tax-advantaged account availability

**Example**:
```python
from investment_calculator import PersonalVariables, InvestmentProfile, RiskTolerance, InvestmentGoal

personal_vars = PersonalVariables(
    age=35,
    annual_income=100000,
    current_savings=50000,
    monthly_contribution=1500,
    risk_tolerance=RiskTolerance.BALANCED,
    investment_horizon=30,
    tax_bracket=0.25,
    capital_gains_rate=0.15,
)

profile = InvestmentProfile(
    personal_vars=personal_vars,
    primary_goal=InvestmentGoal.RETIREMENT,
    target_retirement_income=80000,
)

# Get recommended allocation
allocation = profile.get_recommended_asset_allocation()

# Check investment readiness
ready, warnings = profile.is_ready_to_invest()
```

**Outputs**:
- Risk score (0-100)
- Recommended asset allocation
- Investment readiness assessment
- Profile summary

---

## Installation

### Requirements

```
python >= 3.8
numpy >= 1.20.0
pandas >= 1.3.0
scipy >= 1.7.0
```

### Install Dependencies

```bash
pip install numpy pandas scipy
```

### Usage

```python
from investment_calculator import (
    PersonalVariables,
    InvestmentProfile,
    GlobalScenarioEngine,
    TaxIntegratedScenarioEngine,
    TaxConfig,
    MOCA,
)
```

---

## Quick Start

```python
from investment_calculator import *

# 1. Define personal variables
personal_vars = PersonalVariables(
    age=30,
    annual_income=75000,
    current_savings=20000,
    monthly_contribution=1000,
    risk_tolerance=RiskTolerance.MODERATE,
    investment_horizon=30,
    tax_bracket=0.22,
    capital_gains_rate=0.15,
)

profile = InvestmentProfile(personal_vars=personal_vars)

# 2. Generate scenarios
gse = GlobalScenarioEngine(random_seed=42)
scenarios = gse.generate_standard_scenarios(years=30)

# 3. Apply taxes
tax_config = TaxConfig(ordinary_income_rate=0.22, long_term_cap_gains_rate=0.15)
gse_plus = TaxIntegratedScenarioEngine(tax_config=tax_config)
tax_scenarios = [gse_plus.generate_tax_integrated_scenario(s, AccountType.TAXABLE) for s in scenarios]

# 4. Run optimization
moca = MOCA(investment_profile=profile)
optimal_allocation, stats = moca.optimize_portfolio(
    scenarios=tax_scenarios,
    method=OptimizationMethod.MAX_SHARPE,
)

# 5. View results
print(moca.generate_report())
```

---

## Detailed Usage

### 1. Creating an Investment Profile

```python
from investment_calculator import PersonalVariables, InvestmentProfile, RiskTolerance, InvestmentGoal

# Define personal variables
personal_vars = PersonalVariables(
    age=40,
    annual_income=120000,
    current_savings=200000,
    monthly_contribution=2500,
    risk_tolerance=RiskTolerance.AGGRESSIVE,
    investment_horizon=25,
    tax_bracket=0.28,
    capital_gains_rate=0.15,
    has_tax_advantaged_account=True,
    emergency_fund_months=6,
    debt_to_income_ratio=0.2,
)

# Create investment profile
profile = InvestmentProfile(
    personal_vars=personal_vars,
    primary_goal=InvestmentGoal.RETIREMENT,
    target_retirement_income=90000,
)

# View profile summary
print(profile.summary())

# Get recommended allocation
allocation = profile.get_recommended_asset_allocation()
```

### 2. Generating Economic Scenarios

```python
from investment_calculator import GlobalScenarioEngine

# Create GSE with fixed random seed for reproducibility
gse = GlobalScenarioEngine(random_seed=42)

# Generate standard scenarios (pessimistic, baseline, optimistic)
scenarios = gse.generate_standard_scenarios(years=30)

# Generate Monte Carlo scenarios for robust analysis
mc_scenarios = gse.generate_monte_carlo_scenarios(
    years=30,
    n_scenarios=1000,
)

# Analyze scenarios
comparison = gse.analyze_scenarios(scenarios)
print(comparison)
```

### 3. Applying Tax Calculations

```python
from investment_calculator import TaxIntegratedScenarioEngine, TaxConfig, AccountType

# Configure tax rates
tax_config = TaxConfig(
    country_code="US",
    ordinary_income_rate=0.28,
    long_term_cap_gains_rate=0.15,
    state_tax_rate=0.06,
    social_security_rate=0.062,
    medicare_rate=0.0145,
)

# Create GSE+ engine
gse_plus = TaxIntegratedScenarioEngine(tax_config=tax_config, gse=gse)

# Generate tax-integrated scenarios
tax_scenarios = []
for scenario in scenarios:
    tax_scenario = gse_plus.generate_tax_integrated_scenario(
        scenario=scenario,
        account_type=AccountType.TAX_DEFERRED,  # or TAXABLE, TAX_FREE
    )
    tax_scenarios.append(tax_scenario)

# Compare account types
account_comparison = gse_plus.compare_account_types(
    years=30,
    initial_investment=200000,
    annual_contribution=30000,
    asset_allocation={"stocks": 0.7, "bonds": 0.25, "real_estate": 0.05},
)
```

### 4. Running Portfolio Optimization

```python
from investment_calculator import MOCA, OptimizationMethod

# Create MOCA instance
moca = MOCA(investment_profile=profile)

# Optimize portfolio using different methods
methods = [
    OptimizationMethod.MAX_SHARPE,
    OptimizationMethod.MIN_VOLATILITY,
    OptimizationMethod.RISK_PARITY,
]

for method in methods:
    optimal_allocation, stats = moca.optimize_portfolio(
        scenarios=tax_scenarios,
        method=method,
        asset_classes=["stocks", "bonds", "real_estate"],
    )

    print(f"\n{method.value} Optimization:")
    print(f"Allocation: {optimal_allocation}")
    print(f"Expected Return: {stats.mean_return:.2%}")
    print(f"Sharpe Ratio: {stats.mean_sharpe:.2f}")
```

### 5. Analyzing Results

```python
# Run scenarios with optimal allocation
results = moca.run_scenarios(tax_scenarios, optimal_allocation)

# Calculate statistics
stats = moca.calculate_statistics(
    results=results,
    target_balance=1500000,  # $1.5M target
)

# Access specific metrics
print(f"Expected Final Balance: ${stats.mean_final_balance:,.2f}")
print(f"5th Percentile: ${stats.percentile_5:,.2f}")
print(f"95th Percentile: ${stats.percentile_95:,.2f}")
print(f"Probability of Loss: {stats.probability_of_loss:.1%}")
print(f"Probability of Target: {stats.probability_of_target:.1%}")

# Generate comprehensive report
report = moca.generate_report()
print(report)
```

---

## Input Requirements

### Minimum Required Inputs

| Input | Type | Description | Example |
|-------|------|-------------|---------|
| Age | int | Current age (18-100) | 35 |
| Annual Income | float | Gross annual income | 100000 |
| Investment Horizon | int | Years until goal (1-60) | 30 |
| Risk Tolerance | RiskTolerance | Risk level | MODERATE |
| Tax Bracket | float | Marginal tax rate (0-1) | 0.25 |
| Capital Gains Rate | float | LTCG tax rate (0-1) | 0.15 |

### Recommended Additional Inputs

| Input | Type | Description | Default |
|-------|------|-------------|---------|
| Current Savings | float | Existing portfolio | 0.0 |
| Monthly Contribution | float | Monthly investment | 0.0 |
| Emergency Fund | int | Months of expenses saved | 6 |
| Debt-to-Income | float | Ratio of debt to income | 0.0 |
| Country Code | str | Tax jurisdiction | "US" |

### Optional Inputs

- **Existing Portfolio**: Current asset allocation
- **Target Retirement Income**: Desired annual retirement income
- **Custom Tax Rates**: State, social security, Medicare rates
- **Custom Economic Parameters**: Override default scenario parameters
- **Portfolio Constraints**: Min/max weights for specific assets

---

## Output Description

### Primary Outputs

#### 1. Optimal Asset Allocation
```python
{
    "stocks": 0.60,
    "bonds": 0.30,
    "real_estate": 0.10
}
```

#### 2. Portfolio Statistics
- **Mean Final Balance**: Expected portfolio value
- **Median Final Balance**: Median outcome
- **Standard Deviation**: Portfolio volatility
- **Percentiles**: 5th, 25th, 75th, 95th percentile outcomes
- **Probability of Loss**: Chance of losing money
- **Probability of Target**: Chance of reaching goal

#### 3. Risk Metrics
- **Expected Return**: Annualized return
- **Return Volatility**: Standard deviation of returns
- **Sharpe Ratio**: Risk-adjusted return
- **Max Drawdown**: Largest peak-to-trough decline
- **Value at Risk (VaR)**: 95% VaR
- **Conditional VaR (CVaR)**: Expected shortfall

#### 4. Investment Results
For each scenario:
- Year-by-year balance
- Cumulative contributions
- Annual returns
- Total gains
- Annualized return

#### 5. Comprehensive Report
Text report including:
- Investment profile summary
- Portfolio allocation
- Expected outcomes
- Risk analysis
- Recommendations

---

## Missing Features / Future Enhancements

### Currently Missing

1. **Historical Data Integration**
   - Not yet: Load real historical market data
   - Needed for: Backtesting strategies

2. **Advanced Asset Classes**
   - Not yet: Commodities, crypto, alternatives
   - Currently: Stocks, bonds, real estate only

3. **Dynamic Rebalancing**
   - Not yet: Simulate periodic rebalancing strategies
   - Currently: Static allocation

4. **International Tax Systems**
   - Not yet: Full support for non-US tax codes
   - Currently: US-centric tax calculations

5. **Multi-Goal Optimization**
   - Not yet: Optimize for multiple simultaneous goals
   - Currently: Single primary goal

6. **Inflation-Adjusted Contributions**
   - Not yet: Contributions that increase with inflation
   - Currently: Fixed contribution amounts

7. **Social Security Integration**
   - Not yet: Include Social Security projections
   - Currently: Manual target income setting

8. **Healthcare Cost Modeling**
   - Not yet: Retirement healthcare expenses
   - Currently: User must adjust target income

9. **Estate Planning**
   - Not yet: Inheritance, estate taxes
   - Currently: Focus on accumulation phase

10. **Real-time Market Data**
    - Not yet: Live market data integration
    - Currently: Simulated scenarios only

### Recommended Data Inputs (Not Yet Implemented)

1. **Historical market data** (CSV or API)
2. **Social Security statement data**
3. **Pension information**
4. **Healthcare cost estimates**
5. **Real estate holdings** (separate from RE allocation)
6. **Other income sources** (rental, side business)

### Enhancements in Progress

- ✅ Core GSE, GSE+, MOCA implementation
- ✅ Basic tax calculations
- ✅ Portfolio optimization
- ⏳ GUI/Web interface
- ⏳ Database for storing scenarios
- ⏳ PDF report generation
- ⏳ Historical data backtesting
- ⏳ Cryptocurrency integration

---

## Examples

See the `examples/` directory for complete examples:

1. **quick_start.py**: Minimal example to get started
2. **complete_workflow.py**: Comprehensive examples including:
   - Basic workflow
   - Portfolio optimization comparison
   - Account type comparison
   - Retirement planning scenario

Run examples:
```bash
python investment_calculator/examples/quick_start.py
python investment_calculator/examples/complete_workflow.py
```

---

## API Reference

### Classes

#### PersonalVariables
```python
PersonalVariables(
    age: int,
    annual_income: float,
    current_savings: float = 0.0,
    monthly_contribution: float = 0.0,
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE,
    investment_horizon: int = 30,
    tax_bracket: float = 0.25,
    capital_gains_rate: float = 0.15,
    # ... other optional parameters
)
```

#### GlobalScenarioEngine
```python
gse = GlobalScenarioEngine(random_seed: Optional[int] = None)
gse.generate_baseline_scenario(years: int) -> EconomicScenario
gse.generate_monte_carlo_scenarios(years: int, n_scenarios: int = 1000) -> List[EconomicScenario]
```

#### TaxIntegratedScenarioEngine
```python
gse_plus = TaxIntegratedScenarioEngine(tax_config: TaxConfig, gse: Optional[GlobalScenarioEngine] = None)
gse_plus.generate_tax_integrated_scenario(scenario: EconomicScenario, account_type: AccountType) -> TaxIntegratedScenario
```

#### MOCA
```python
moca = MOCA(investment_profile: InvestmentProfile)
moca.run_scenarios(scenarios: List[TaxIntegratedScenario], asset_allocation: Dict[str, float]) -> List[InvestmentResult]
moca.optimize_portfolio(scenarios: List[TaxIntegratedScenario], method: OptimizationMethod) -> Tuple[Dict, PortfolioStatistics]
```

---

## Support

For issues, questions, or contributions, please refer to the main project documentation.

---

## License

See main project LICENSE file.
