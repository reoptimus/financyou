# FinancYou Complete Guide
## Comprehensive Documentation: From Economic Scenarios to Portfolio Optimization

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Complete Pipeline: Step-by-Step](#complete-pipeline-step-by-step)
4. [Input/Output Specifications](#inputoutput-specifications)
5. [Design Principles](#design-principles)
6. [Complete Working Examples](#complete-working-examples)
7. [Dummy Input Files](#dummy-input-files)
8. [Troubleshooting](#troubleshooting)

---

## Overview

FinancYou is a comprehensive financial planning system that:
- Generates realistic economic scenarios using stochastic models
- Applies tax treatment for different jurisdictions and account types
- Processes user profiles and creates investment plans
- Optimizes portfolio allocation across scenarios
- Generates detailed reports and visualizations

**The complete pipeline takes ~5 minutes to understand and ~2 minutes to run.**

---

## System Architecture

### The 5-Module Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     FINANCYOU COMPLETE PIPELINE                  │
└─────────────────────────────────────────────────────────────────┘

📥 INPUT FILES (JSON/YAML)
  ├─ scenario_config.json      → Economic scenario parameters
  ├─ tax_config.json           → Tax rules and account allocation
  └─ user_profile.json         → User information and preferences

              ↓

┌──────────────────────────────────────────────────────────────────┐
│ MODULE 1: Economic Scenario Generator (GSE)                      │
│ Input:  Scenario configuration                                   │
│ Output: 1000+ economic scenarios (stocks, bonds, real estate)    │
│ Time:   ~30 seconds                                              │
└──────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────┐
│ MODULE 2: Tax-Integrated Scenarios (GSE+)                        │
│ Input:  Economic scenarios + tax configuration                   │
│ Output: After-tax scenarios by account type                      │
│ Time:   ~10 seconds                                              │
└──────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────┐
│ MODULE 3: User Profile & Investment Time Series                  │
│ Input:  User profile + contribution/withdrawal schedules         │
│ Output: Validated profile + investment plan + risk assessment    │
│ Time:   ~5 seconds                                               │
└──────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────┐
│ MODULE 4: Portfolio Optimizer (MOCA)                             │
│ Input:  After-tax scenarios + user constraints + investment plan │
│ Output: Optimal portfolio + Monte Carlo simulations              │
│ Time:   ~45 seconds                                              │
└──────────────────────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────┐
│ MODULE 5: Visualization & Reporting                              │
│ Input:  All results from modules 1-4                            │
│ Output: HTML/PDF reports + charts + executive summary            │
│ Time:   ~10 seconds                                              │
└──────────────────────────────────────────────────────────────────┘

              ↓

📤 OUTPUT
  ├─ investment_report.html    → Complete analysis report
  ├─ figures/                  → All charts and visualizations
  └─ results.json              → Raw data for further analysis
```

---

## Complete Pipeline: Step-by-Step

### Step 1: Economic Scenario Generation

**What It Does**: Creates 1000+ possible futures for the economy

**Input**:
```python
{
    'num_scenarios': 1000,          # How many futures to simulate
    'time_horizon': 30,             # Years to project
    'timestep': 1.0,                # Annual (1.0) or monthly (1/12)
    'use_stochastic': True,         # Use advanced models (True) or simple (False)
    'currency': 'USD',              # USD, EUR, GBP
    'economic_params': {
        'equity_volatility': 0.18,  # Stock market volatility (18%)
        'inflation_mean': 0.025     # Expected inflation (2.5%)
    }
}
```

**Process**:
1. Calibrates models to current market conditions
2. Generates correlated random shocks
3. Simulates stock, bond, and real estate returns
4. Creates risk-neutral deflators for pricing

**Output**:
```python
{
    'scenarios': DataFrame with 30,000 rows (1000 scenarios × 30 years)
    Columns: ['scenario_id', 'time_period', 'interest_rate',
              'stock_return', 'bond_return', 'real_estate_return',
              'inflation', 'gdp_growth']

    'diagnostics': {
        'mean_returns': {'stock_return': 0.095, 'bond_return': 0.048, ...},
        'volatilities': {'stock_return': 0.179, ...},
        'correlations': DataFrame showing asset correlations
    }
}
```

**Example**:
```python
from investment_calculator.modules import scenario_generator

gen = scenario_generator.ScenarioGenerator(random_seed=42)
results = gen.generate({
    'num_scenarios': 1000,
    'time_horizon': 30,
    'timestep': 1.0,
    'use_stochastic': True
})

scenarios_df = results['scenarios']
print(f"Generated {scenarios_df['scenario_id'].nunique()} scenarios")
print(f"Mean stock return: {results['diagnostics']['mean_returns']['stock_return']:.2%}")
```

---

### Step 2: Tax Integration

**What It Does**: Applies realistic tax treatment to investment returns

**Input**:
```python
{
    'scenarios': scenarios_df,      # From Step 1
    'tax_config': {
        'jurisdiction': 'US',        # US, FR, UK, DE, CA
        'account_types': {
            'taxable': {
                'dividend_tax_rate': 0.15,
                'capital_gains_rate': 0.15
            },
            'tax_deferred': {
                'withdrawal_tax_rate': 0.25
            },
            'tax_free': {
                'contribution_limit': 6500
            }
        }
    },
    'investment_allocation': {
        'stocks': {
            'taxable': 0.60,         # 60% in taxable accounts
            'tax_deferred': 0.30,    # 30% in 401k/IRA
            'tax_free': 0.10         # 10% in Roth
        }
    }
}
```

**Process**:
1. Identifies which assets are in which account types
2. Calculates annual taxes on dividends, interest, capital gains
3. Tracks tax drag on performance
4. Suggests optimal withdrawal strategies

**Output**:
```python
{
    'after_tax_scenarios': DataFrame with after-tax returns,
    'tax_tables': {
        'effective_tax_rate': Average 18.5% across all scenarios,
        'annual_tax_by_account': Breakdown by account type,
        'cumulative_tax': Tax burden over time
    },
    'optimization_insights': {
        'optimal_withdrawal_sequence': [
            'taxable first',
            'tax_deferred second',
            'tax_free last'
        ]
    }
}
```

**Example**:
```python
from investment_calculator.modules import tax_engine

engine = tax_engine.TaxEngine()
tax_config = tax_engine.TaxConfigPreset.get_preset('US')

allocation = {
    'stocks': {'taxable': 0.6, 'tax_deferred': 0.3, 'tax_free': 0.1},
    'bonds': {'taxable': 0.4, 'tax_deferred': 0.5, 'tax_free': 0.1}
}

tax_results = engine.apply_taxes({
    'scenarios': scenarios_df,
    'tax_config': tax_config,
    'investment_allocation': allocation
})

print(f"Average tax drag: {tax_results['after_tax_scenarios']['annual_tax_drag'].mean():.2%}")
```

---

### Step 3: User Profile & Investment Plan

**What It Does**: Processes user information and creates personalized investment plan

**Input**:
```python
{
    'user_profile': {
        'personal_info': {
            'age': 35,
            'retirement_age': 65,
            'life_expectancy': 90
        },
        'financial_situation': {
            'current_savings': 50000,
            'annual_income': 75000,
            'annual_expenses': 50000
        },
        'investment_preferences': {
            'risk_tolerance': 'moderate',   # conservative, moderate, aggressive
            'investment_goal': 'retirement',
            'time_horizon': 30
        }
    },
    'contribution_schedule': [
        {
            'start_year': 0,
            'end_year': 30,
            'monthly_amount': 500,
            'annual_increase': 0.03,        # 3% annual increase
            'account_type': 'tax_deferred'
        }
    ]
}
```

**Process**:
1. Validates all inputs (age, income, contributions)
2. Calculates risk score (0-100)
3. Identifies life stages (accumulation, transition, distribution)
4. Creates year-by-year investment plan
5. Generates age-based glide path

**Output**:
```python
{
    'validated_profile': {/* cleaned and validated */},
    'investment_time_series': DataFrame with 55 rows (one per year),
    'risk_profile': {
        'score': 62,                    # Risk score out of 100
        'recommended_allocation': {
            'stocks': 0.65,
            'bonds': 0.25,
            'real_estate': 0.08,
            'cash': 0.02
        },
        'glide_path': DataFrame showing allocation changes over time
    },
    'life_stages': {
        'accumulation': {'start': 35, 'end': 55, 'duration': 20},
        'transition': {'start': 55, 'end': 65, 'duration': 10},
        'distribution': {'start': 65, 'end': 90, 'duration': 25}
    },
    'summary_statistics': {
        'total_contributions': 327000,
        'contribution_years': 30,
        'average_annual_contribution': 10900
    }
}
```

**Example**:
```python
from investment_calculator.modules import user_profile

manager = user_profile.UserProfileManager()

# Quick way
simple_profile = user_profile.create_simple_profile(
    age=35,
    annual_income=75000,
    current_savings=50000,
    risk_tolerance='moderate'
)

results = manager.process(simple_profile)

print(f"Risk score: {results['risk_profile']['score']}/100")
print(f"Recommended stocks: {results['risk_profile']['recommended_allocation']['stocks']:.0%}")
print(f"Total contributions: ${results['summary_statistics']['total_contributions']:,.0f}")
```

---

### Step 4: Portfolio Optimization

**What It Does**: Finds the best asset allocation and simulates outcomes

**Input**:
```python
{
    'scenarios': after_tax_scenarios,           # From Step 2
    'user_constraints': {
        'max_equity_allocation': 0.90,
        'min_bond_allocation': 0.10
    },
    'investment_time_series': time_series_df,   # From Step 3
    'optimization_objective': 'max_sharpe',     # or min_volatility, target_return
    'goal_amount': 2000000                      # Target $2M for retirement
}
```

**Process**:
1. Extracts returns for each asset class
2. Calculates mean returns and covariance matrix
3. Runs optimization (maximizes Sharpe ratio)
4. Generates efficient frontier (50 portfolios)
5. Simulates wealth across all 1000 scenarios
6. Calculates risk metrics (VaR, CVaR)

**Output**:
```python
{
    'optimal_portfolio': {
        'weights': {
            'stock': 0.62,
            'bond': 0.28,
            'real_estate': 0.10
        },
        'expected_return': 0.084,       # 8.4% expected return
        'expected_volatility': 0.132,   # 13.2% volatility
        'sharpe_ratio': 0.636,
        'max_drawdown': 0.28            # 28% worst drawdown
    },
    'simulation_results': {
        'statistics': {
            'median_terminal_wealth': 1850000,
            'percentiles': {
                '5': 980000,            # 5% chance < $980k
                '95': 3200000           # 5% chance > $3.2M
            },
            'var_95': 980000,
            'cvar_95': 720000
        }
    },
    'goal_analysis': {
        'goal_amount': 2000000,
        'probability_of_achieving': 0.68,  # 68% chance of success
        'expected_surplus_deficit': -150000
    },
    'efficient_frontier': DataFrame with 50 optimal portfolios
}
```

**Example**:
```python
from investment_calculator.modules import optimizer

opt = optimizer.PortfolioOptimizer()

results = opt.optimize({
    'scenarios': after_tax_scenarios,
    'user_constraints': profile_results['validated_profile']['constraints'],
    'investment_time_series': profile_results['investment_time_series'],
    'optimization_objective': 'max_sharpe',
    'goal_amount': 2000000
})

print(f"Optimal allocation:")
for asset, weight in results['optimal_portfolio']['weights'].items():
    print(f"  {asset}: {weight:.1%}")

print(f"\nExpected return: {results['optimal_portfolio']['expected_return']:.2%}")
print(f"Probability of reaching $2M: {results['goal_analysis']['probability_of_achieving']:.1%}")
```

---

### Step 5: Reporting & Visualization

**What It Does**: Creates comprehensive reports and charts

**Input**:
```python
{
    'scenarios': scenario_results,              # From Step 1
    'tax_results': tax_results,                 # From Step 2
    'user_profile': profile_results,            # From Step 3
    'optimization_results': optimization_results, # From Step 4
    'report_config': {
        'report_type': 'detailed',              # summary or detailed
        'format': 'html',                       # html, pdf, json
        'charts': [
            'wealth_trajectories',
            'efficient_frontier',
            'allocation_pie',
            'monte_carlo_histogram'
        ]
    }
}
```

**Process**:
1. Generates 5+ interactive charts
2. Creates summary tables
3. Writes executive summary
4. Assembles HTML/PDF report

**Output**:
```python
{
    'report': {
        'html': '<html>...</html>',
        'pdf_path': 'investment_report.pdf'
    },
    'figures': {
        'wealth_trajectories': {
            'figure': matplotlib.Figure,
            'path': 'wealth_trajectories.png'
        },
        'efficient_frontier': {...},
        'allocation_pie': {...},
        'monte_carlo_histogram': {...}
    },
    'executive_summary': {
        'one_page_summary': """
            INVESTMENT PLAN EXECUTIVE SUMMARY

            RECOMMENDED PORTFOLIO:
              Expected Return: 8.4%
              Expected Volatility: 13.2%
              Sharpe Ratio: 0.64

            PROJECTED OUTCOMES:
              Median Wealth: $1,850,000
              5th Percentile: $980,000
              95th Percentile: $3,200,000

            GOAL ANALYSIS:
              Target: $2,000,000
              Probability: 68%
        """,
        'key_findings': [
            'Diversified portfolio recommended based on moderate risk tolerance',
            '68% probability of reaching $2M retirement goal',
            'Tax-optimized allocation can save ~$45k in taxes'
        ],
        'recommendations': [
            'Maximize tax-deferred contributions early',
            'Rebalance annually or when drift exceeds 5%',
            'Review plan after major life changes'
        ]
    }
}
```

**Example**:
```python
from investment_calculator.modules import reporting

reporter = reporting.ReportGenerator()

report = reporter.generate({
    'scenarios': scenario_results,
    'tax_results': tax_results,
    'user_profile': profile_results,
    'optimization_results': optimization_results,
    'report_config': {
        'report_type': 'detailed',
        'format': 'html'
    }
})

print(report['executive_summary']['one_page_summary'])

# Save HTML report
with open('investment_report.html', 'w') as f:
    f.write(report['report']['html'])

# Show charts
report['figures']['wealth_trajectories']['figure'].savefig('wealth_chart.png')
```

---

## Input/Output Specifications

### Complete Type Definitions

```python
# Module 1 Input
ScenarioConfig = {
    'num_scenarios': int,           # Required: 100-10000
    'time_horizon': int,            # Required: 1-100 years
    'timestep': float,              # Required: 0.083 (monthly) to 1.0 (annual)
    'use_stochastic': bool,         # Optional: Default False
    'currency': str,                # Optional: Default 'USD'
    'calibration_date': str,        # Optional: Default today
    'economic_params': dict         # Optional: Override defaults
}

# Module 2 Input
TaxConfig = {
    'scenarios': pd.DataFrame,      # Required: From Module 1
    'tax_config': {
        'jurisdiction': str,        # Required: 'US', 'FR', 'UK', etc.
        'account_types': dict       # Required: Tax rates by account
    },
    'investment_allocation': dict   # Required: Asset allocation by account
}

# Module 3 Input
UserProfileConfig = {
    'user_profile': {
        'personal_info': dict,      # Required: Age, retirement age, etc.
        'financial_situation': dict, # Required: Income, savings, debt
        'investment_preferences': dict, # Required: Risk tolerance, goals
        'constraints': dict         # Optional: Allocation limits
    },
    'contribution_schedule': list,  # Optional: Defaults generated
    'withdrawal_schedule': list     # Optional: Defaults generated
}

# Module 4 Input
OptimizationConfig = {
    'scenarios': pd.DataFrame,      # Required: From Module 2
    'user_constraints': dict,       # Required: From Module 3
    'investment_time_series': pd.DataFrame, # Required: From Module 3
    'optimization_objective': str,  # Optional: Default 'max_sharpe'
    'optimization_params': dict,    # Optional: Override defaults
    'goal_amount': float           # Optional: Target wealth
}

# Module 5 Input
ReportConfig = {
    'scenarios': dict,              # Required: From Module 1
    'tax_results': dict,            # Required: From Module 2
    'user_profile': dict,           # Required: From Module 3
    'optimization_results': dict,   # Required: From Module 4
    'report_config': dict,          # Optional: Report preferences
    'visualization_preferences': dict # Optional: Chart styling
}
```

---

## Design Principles

### 1. **Modularity**
Each module is independent and can be used standalone:
```python
# Use only Module 1 for scenario generation
from investment_calculator.modules import scenario_generator
results = scenario_generator.quick_scenarios(1000, 30)

# Use only Module 4 for optimization
from investment_calculator.modules import optimizer
results = optimizer.quick_optimize(scenarios_df, 'max_sharpe')
```

### 2. **Clear Input/Output**
Every module has documented dictionary inputs and outputs:
```python
# Input: Simple dictionary
config = {'num_scenarios': 1000, 'time_horizon': 30, 'timestep': 1.0}

# Output: Predictable structure
results = {
    'scenarios': pd.DataFrame,
    'metadata': dict,
    'diagnostics': dict
}
```

### 3. **Sensible Defaults**
Minimal configuration required:
```python
# Full control
gen.generate({'num_scenarios': 1000, 'time_horizon': 30, 'timestep': 1.0, ...})

# Or quick with defaults
scenario_generator.quick_scenarios(1000, 30)
```

### 4. **Type Safety**
Type hints throughout:
```python
def process(self, config: Dict) -> Dict:
    validated_profile: Dict
    warnings: List[str]
    return {'validated_profile': validated_profile, 'warnings': warnings}
```

### 5. **Comprehensive Documentation**
Every function documented:
```python
def generate(self, config: Dict) -> Dict:
    """
    Generate economic scenarios.

    Args:
        config: Configuration with num_scenarios, time_horizon, etc.

    Returns:
        Dictionary with scenarios, deflators, metadata, diagnostics

    Example:
        >>> results = gen.generate({'num_scenarios': 1000, ...})
    """
```

### 6. **Fail-Fast Validation**
Errors caught early with helpful messages:
```python
if age < 18 or age > 100:
    warnings.append("Age outside reasonable range [18, 100], using default")

if retirement_age <= age:
    warnings.append("Retirement age must be > current age")
```

### 7. **Extensibility**
Easy to add features:
```python
# Add new optimization method
class OptimizationObjective(Enum):
    MAX_SHARPE = "max_sharpe"
    MIN_VOLATILITY = "min_volatility"
    MY_NEW_METHOD = "my_new_method"  # Just add here!
```

---

## Complete Working Examples

See the following files for complete runnable examples:

1. **`examples/complete_workflow_modules.py`**
   - Full pipeline from scenarios to reports
   - ~450 lines with extensive comments
   - Shows all 5 modules working together
   - Runtime: ~2 minutes

2. **`examples/slicing_capabilities_demo.py`**
   - Demonstrates both slicing types in Module 3
   - Domain-specific vs general-purpose slicing
   - Runtime: ~5 seconds

3. **`examples/complete_pipeline_with_files.py`** (NEW!)
   - Uses JSON input files
   - Complete end-to-end automation
   - Shows how to save/load results
   - Runtime: ~2 minutes

---

## Dummy Input Files

All example input files are in `examples/input_files/`:

1. **`scenario_config.json`** - Economic scenario parameters
2. **`tax_config_us.json`** - US tax configuration
3. **`tax_config_fr.json`** - French tax configuration
4. **`user_profile_conservative.json`** - Conservative investor
5. **`user_profile_aggressive.json`** - Aggressive investor
6. **`optimization_config.json`** - Optimization parameters

See [Dummy Input Files](#dummy-input-files-reference) section for details.

---

## Troubleshooting

### Common Issues

**1. Import Error: "No module named 'investment_calculator'"**
```bash
# Solution: Add to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/financyou"
# Or in Python:
import sys
sys.path.insert(0, '/path/to/financyou')
```

**2. TimeSeriesSlicer Error: "DataFrame must have DatetimeIndex"**
```python
# Solution: Specify time_column
slicer = TimeSeriesSlicer(df, time_column='period')
```

**3. Optimization Fails: "Target return not achievable"**
```python
# Solution: Check if target is realistic
print(f"Max possible return: {scenarios['stock_return'].mean():.2%}")
# Or use max_sharpe instead of target_return
```

**4. Memory Error with Large Scenarios**
```python
# Solution: Reduce number of scenarios
config = {'num_scenarios': 100, ...}  # Instead of 10000
```

**5. Negative Wealth in Simulations**
```python
# Solution: Check contribution schedule
# Make sure contributions > withdrawals in early years
```

---

## Quick Start (5 Minutes)

```bash
# 1. Navigate to financyou directory
cd /path/to/financyou

# 2. Run complete example
python examples/complete_pipeline_with_files.py

# 3. Check outputs
ls outputs/
# investment_report.html
# optimal_portfolio.json
# wealth_chart.png
# efficient_frontier.png

# 4. Open report
open outputs/investment_report.html
```

---

## Next Steps

1. **Customize Input Files**: Edit `examples/input_files/*.json` for your scenario
2. **Run Pipeline**: `python examples/complete_pipeline_with_files.py`
3. **Review Results**: Open `outputs/investment_report.html`
4. **Iterate**: Adjust parameters and re-run

---

## Support & Resources

- **Full Documentation**: See `ARCHITECTURE.md` and `MODULES_GUIDE.md`
- **Examples**: All examples in `examples/` directory
- **Tests**: Run `pytest tests/` to verify installation
- **Issues**: File at https://github.com/reoptimus/financyou/issues

---

**Last Updated**: 2025-11-22
**Version**: 2.0.0
