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
- Turns them into the returns of household placements (CTO, PEA, assurance-vie, Livret A), net of fees (GSE+)
- Applies the exit tax of each wrapper for the user's situation (GSE++)
- Processes user profiles and creates investment plans
- Optimizes the allocation between placements on the mean and volatility of GSE++ (Markowitz)
- Generates detailed reports and visualizations

**The complete pipeline takes ~5 minutes to understand and ~2 minutes to run.**

---

## System Architecture

### The Pipeline

```
📥 INPUT FILES (examples/input_files/)
  ├─ scenario_config.json      → Economic scenario parameters
  ├─ user_profile_*.json       → User information and flows
  └─ optimization_config.json  → Catalogue, objective, goal
📚 INPUT DATA (investment_calculator/)
  ├─ placement_catalogs/fr-2026.json  → Placements and fees
  └─ tax_regimes/fr-2026.json         → Tax rules per wrapper

              ↓
GSE   (scenario_generator)  → stock, bond, rate, inflation per scenario
              ↓
GSE+  (placements)          → return of each placement, net of fees, before tax
              ↓
GSE++ (net_returns)         → return net of fees and exit tax, per horizon
              ↓                ← user profile (user_profile)
Markowitz (placement_optimizer) → weights per placement, efficient frontier
              ↓
Projection (wealth_simulation)  → wealth of the user's actual flows
              ↓
Reporting (reporting)       → HTML report + charts

📤 OUTPUT (outputs/)
  ├─ investment_report.html
  ├─ optimal_portfolio.json
  └─ charts (PNG)
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

### Step 2: Placements and Taxes (GSE+ and GSE++)

**What It Does**: Maps each placement of the catalogue to its GSE variable,
subtracts its annual fees (GSE+), then applies the exit tax of its wrapper
for the user's situation and each horizon (GSE++). Rates, thresholds and
allowances come from `tax_regimes/fr-2026.json`, never from the code.

**Example**:
```python
from investment_calculator.modules.net_returns import TaxProfile, build_net_returns
from investment_calculator.modules.placements import build_gross_placements
from investment_calculator.placement_catalog import load_placement_catalog

catalog = load_placement_catalog('fr-2026')
gross = build_gross_placements(scenario_results['scenarios'], catalog)   # GSE+
net = build_net_returns(gross, catalog, TaxProfile(invested_amount=180_000), [30])  # GSE++

print(net.annualized(30).mean())  # mean net return per placement at 30 years
print(net.annualized(30).std())   # net volatility per placement at 30 years
```

`plan_placements` (Step 4) runs this step itself.

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

**What It Does**: Classic Markowitz between placements on the mean and
volatility of GSE++ at horizon H, under the wrapper contribution caps, then
projection of the user's contributions with the chosen weights.

**Example**:
```python
from investment_calculator.modules.placement_plan import plan_placements

results = plan_placements(
    scenario_results['scenarios'], catalog, profile_results['investment_time_series'],
    horizon=30, objective='mean_variance', risk_aversion=5.0,
    risk_free_placement='livret_a', goal_amount=500_000,
)

for placement, weight in results['optimal_portfolio']['weights'].items():
    print(f"  {placement}: {weight:.1%}")
print(f"Expected net return: {results['optimal_portfolio']['expected_return']:.2%}")
print(f"Probability of reaching the goal: {results['goal_analysis']['probability_of_achieving']:.1%}")
```

Objectives: `mean_variance` (`risk_aversion`), `min_volatility`,
`target_return` (`target_return`), `max_sharpe` (needs `risk_free_placement`).
The output keys are listed in `MODULES_GUIDE.md`. The profile constraints
(`max_equity`, `min_bonds`) are not applied yet.

---

### Step 5: Reporting & Visualization

**What It Does**: Creates comprehensive reports and charts

**Input**: `optimization_results` from Step 4, plus an optional
`report_config` (`format`: html, json…) and `visualization_preferences`.

**Output**: `report` (HTML…), `figures` (wealth trajectories, efficient
frontier, allocation, terminal wealth histogram), `tables`,
`executive_summary`.

**Example**:
```python
from investment_calculator.modules import reporting

reporter = reporting.ReportGenerator()

report = reporter.generate({
    'user_profile': profile_results,
    'optimization_results': results,
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

# Module 2: see Step 2 (catalogue + TaxProfile + horizons)

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

# Module 4: plan_placements(scenarios, catalog, time_series, *, horizon,
#     objective, risk_aversion=None, target_return=None,
#     risk_free_placement=None, goal_amount=None, couple=False,
#     wrapper_seniority=None, frontier_points=20)

# Module 5 Input
ReportConfig = {
    'optimization_results': dict,   # Required: from plan_placements
    'user_profile': dict,           # Optional: From Module 3
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
2. **`user_profile_conservative.json`** - Conservative investor
3. **`user_profile_aggressive.json`** - Aggressive investor
4. **`optimization_config.json`** - Catalogue, objective and goal

Taxes are not an input file of the example: they come from the regime the
catalogue names (`investment_calculator/tax_regimes/`).

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
print(net.annualized(30).mean().max())  # best mean net return of a placement
# Or use mean_variance instead of target_return
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
# wealth_trajectories.png, efficient_frontier.png,
# allocation_pie_chart.png, monte_carlo_histogram.png

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

**Last Updated**: 2026-10-10
**Version**: 2.0.0
