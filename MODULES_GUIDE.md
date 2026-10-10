

# FinancYou Modules Guide

## Overview

FinancYou chains GSE → GSE+ → GSE++ → Markowitz → projection → report. Each module has standardized input/output structures documented in `ARCHITECTURE.md`.

## Module Summary

| Step | Module | Input | Output |
|------|--------|-------|--------|
| **GSE** | `scenario_generator` | Config dict | Scenarios DataFrame (stock, bond, rate, inflation) |
| **GSE+** | `placements` | Scenarios + placement catalogue | Annual return per placement, net of fees |
| **GSE++** | `net_returns` | GSE+ + catalogue + `TaxProfile` + horizons | Net multiple per scenario × horizon × placement |
| **User profile** | `user_profile` | User profile dict | Investment time series |
| **Optimizer** | `placement_optimizer` | GSE++ + wrapper caps | Weights per placement, efficient frontier |
| **Projection** | `wealth_simulation` | GSE+ + weights + flows | Wealth paths, terminal wealth net of tax |
| **Orchestration** | `placement_plan` | All of the above | Report-ready dict |
| **Reporting** | `reporting` | Optimization results | Reports + Charts |

The unit of optimisation is the placement; see
`docs/adr/0002-le-placement-est-l-unite-d-optimisation.md`.

## Module Details

### Module 1: Economic Scenario Generator (GSE)

**File**: `investment_calculator/modules/scenario_generator.py`

**Purpose**: Generate Monte Carlo economic scenarios for all asset classes

**Key Classes**:
- `ScenarioGenerator` - Main class for scenario generation

**Input Structure**:
```python
config = {
    'num_scenarios': 1000,        # Number of scenarios
    'time_horizon': 30,           # Years to simulate
    'timestep': 1.0,              # Annual timestep
    'use_stochastic': True,       # Use advanced ESG models
    'currency': 'USD',            # Currency
    'economic_params': {          # Optional overrides
        'equity_volatility': 0.18,
        'mean_reversion_speed': 0.1,
        # ... more parameters
    }
}
```

**Output Structure**:
```python
results = {
    'scenarios': pd.DataFrame,    # Scenarios × time periods
    'deflators': pd.DataFrame,    # Risk-neutral deflators
    'metadata': dict,             # Generation info
    'diagnostics': dict           # Correlation, means, etc.
}
```

**Usage Example**:
```python
from investment_calculator.modules import scenario_generator

# Create generator
gen = scenario_generator.ScenarioGenerator(random_seed=42)

# Generate scenarios
config = {
    'num_scenarios': 1000,
    'time_horizon': 30,
    'timestep': 1.0,
    'use_stochastic': True,
    'currency': 'EUR'
}

results = gen.generate(config)
scenarios_df = results['scenarios']

# Quick usage
scenarios_df = scenario_generator.quick_scenarios(
    num_scenarios=1000,
    time_horizon=30,
    use_stochastic=True
)
```

**Key Features**:
- Two modes: Simple (fast) or Stochastic (realistic)
- Hull-White interest rates
- Black-Scholes equity model
- Correlated asset returns
- EIOPA curve calibration

---

### Module 2: Placements and Taxes (GSE+ and GSE++)

**Files**: `investment_calculator/modules/placements.py`, `investment_calculator/modules/net_returns.py`,
`investment_calculator/wrapper_tax.py`

**Purpose**: Turn GSE variables into the returns of placements a household can
buy (GSE+), then into returns net of the exit tax, which depends on the user
(GSE++).

**Data**:
- Placement catalogue `investment_calculator/placement_catalogs/fr-2026.json`:
  `cto_actions`, `cto_obligations`, `pea_actions`, `av_fonds_euros`,
  `av_uc_actions`, `livret_a`, each with its wrapper, underlying and annual
  fees, plus `known_gaps`. `list_placement_catalogs()` lists validated catalogues.
- Tax regime named by the catalogue, `investment_calculator/tax_regimes/fr-2026.json`.
  No rate, threshold or allowance lives in the code.

**Key Functions**:
- `build_gross_placements(scenarios, catalog)` - GSE+, indexed by
  `(scenario_id, time_period)`, one column per placement
- `TaxProfile(invested_amount, couple=False, wrapper_seniority={})` - the
  user's tax situation
- `build_net_returns(gross, catalog, profile, horizons)` - GSE++; its
  `annualized(h)` method gives annualised net returns at horizon `h`
- `wrapper_tax.liquidation_tax(...)` - exit tax of one wrapper

**Usage Example**:
```python
from investment_calculator.modules.net_returns import TaxProfile, build_net_returns
from investment_calculator.modules.placements import build_gross_placements
from investment_calculator.placement_catalog import load_placement_catalog

catalog = load_placement_catalog('fr-2026')
gross = build_gross_placements(scenarios['scenarios'], catalog)       # GSE+
net = build_net_returns(gross, catalog, TaxProfile(invested_amount=180_000), [10, 30])  # GSE++
print(net.annualized(30).mean())   # expected net return per placement at 30 years
print(net.annualized(30).std())    # net volatility per placement at 30 years
```

---

### Module 3: User Input & Investment Time Series

**File**: `investment_calculator/modules/user_profile.py`

**Purpose**: Process user profile and create investment time series

**Key Classes**:
- `UserProfileManager` - Main profile processing class
- `LifeStage` - Enum for life stages
- `RebalancingFrequency` - Enum for rebalancing frequency

**Input Structure**:
```python
config = {
    'user_profile': {
        'personal_info': {
            'age': 35,
            'retirement_age': 65,
            'life_expectancy': 90,
            'country': 'US',
            'currency': 'USD'
        },
        'financial_situation': {
            'current_savings': 50000,
            'annual_income': 75000,
            'annual_expenses': 50000,
            'debt': {
                'mortgage': 200000,
                'student_loans': 0,
                'other': 0
            }
        },
        'investment_preferences': {
            'risk_tolerance': 'moderate',  # 'conservative', 'moderate', 'aggressive'
            'investment_goal': 'retirement',
            'time_horizon': 30,
            'esg_preferences': False,
            'liquidity_needs': 0.05
        },
        'constraints': {
            'max_equity_allocation': 0.9,
            'min_bond_allocation': 0.1,
            'exclude_sectors': [],
            'rebalancing_frequency': 'annual'
        }
    },
    'contribution_schedule': [
        {
            'start_year': 0,
            'end_year': 30,
            'monthly_amount': 500,
            'annual_increase': 0.03,
            'account_type': 'tax_deferred'
        }
    ],
    'withdrawal_schedule': []
}
```

**Output Structure**:
```python
results = {
    'validated_profile': dict,             # Validated and sanitized profile
    'investment_time_series': pd.DataFrame, # Year-by-year plan
    'life_stages': {
        'accumulation': {'start': 35, 'end': 55, ...},
        'transition': {'start': 55, 'end': 65, ...},
        'distribution': {'start': 65, 'end': 90, ...}
    },
    'risk_profile': {
        'score': 65.0,
        'recommended_allocation': {...},
        'glide_path': pd.DataFrame
    },
    'sliced_plans': {                      # Domain-specific slicing
        'by_life_stage': {...},
        'by_goal': {...},
        'by_account_type': {...}
    },
    'time_series_slicer': TimeSeriesSlicer, # General-purpose slicing (NEW!)
    'validation_warnings': [...],
    'summary_statistics': {...}
}
```

**Usage Example**:
```python
from investment_calculator.modules import user_profile

# Create manager
manager = user_profile.UserProfileManager()

# Process profile
config = {...}  # See above
results = manager.process(config)

# Access outputs
time_series = results['investment_time_series']
risk_profile = results['risk_profile']
warnings = results['validation_warnings']

# DOMAIN-SPECIFIC SLICING (Investment planning-specific)
sliced_plans = results['sliced_plans']

# Get accumulation phase data
accumulation_data = sliced_plans['by_life_stage']['accumulation']

# Get retirement contributions only
retirement_plan = sliced_plans['by_goal']['retirement']

# Get tax-deferred account contributions
tax_deferred = sliced_plans['by_account_type']['tax_deferred']

# GENERAL TIME SERIES SLICING (Generic time series operations)
slicer = results['time_series_slicer']

# Slice by index (first 10 years)
first_10_years = slicer.slice_by_index(0, 10)

# Slice by value (contributions > $5000)
large_contributions = slicer.slice_by_value('contribution', min_value=5000)

# Rolling windows (5-year windows)
for window in slicer.slice_by_window(window_size=5, overlap=False):
    avg_contribution = window['contribution'].mean()
    print(f"5-year average contribution: ${avg_contribution:,.0f}")

# Train/test split (70/30)
train_data, test_data = slicer.split_by_ratio([0.7, 0.3])

# Quick usage
simple_config = user_profile.create_simple_profile(
    age=35,
    annual_income=75000,
    current_savings=50000,
    risk_tolerance='moderate',
    retirement_age=65
)
results = manager.process(simple_config)
```

**Key Features**:
- Input validation and sanitization
- Life stage identification (accumulation, transition, distribution)
- Risk profiling and glide path generation
- **Domain-specific slicing**: By life stage, goal, and account type
- **General time series slicing**: Index, window, ratio, and value-based slicing
- Default schedules for contributions/withdrawals
- Integration with `time_series_slicer` library for advanced operations

---

### Module 4: Portfolio Optimization and Projection

**Files**: `investment_calculator/modules/placement_optimizer.py`,
`investment_calculator/modules/wealth_simulation.py`,
`investment_calculator/modules/placement_plan.py`

**Purpose**: Classic Markowitz on the mean and volatility of GSE++ at horizon
H, then projection of the user's actual contributions.

**Key Functions**:
- `placement_constraints(catalog, placement_ids, total_contributions, n_periods)` -
  wrapper contribution caps, the only constraints, with a text explanation
- `optimize_horizon(net, horizon, constraints, objective=...)` - objectives
  `mean_variance` (`risk_aversion`), `min_volatility`, `target_return`
  (`target_return`), `max_sharpe` (`risk_free_rate`)
- `optimize_by_horizon(...)` - one allocation per horizon
- `efficient_frontier(net, horizon, constraints, n_points=20)`
- `simulate_wealth(gross, catalog, profile, weights, flows, horizon)` - wealth
  paths before exit tax, terminal wealth net of tax
- `plan_placements(scenarios, catalog, time_series, horizon=..., objective=...)` -
  the whole chain, output ready for `ReportGenerator`

**Output of `plan_placements`**:
```python
results = {
    'optimal_portfolio': {
        'weights': {placement_id: float},
        'expected_return': float,      # mean annualised net return at H
        'expected_volatility': float,  # its standard deviation over scenarios
        'sharpe_ratio': float | None,  # None without risk_free_placement
        'risk_free_rate': float | None,
        'risk_free_placement': str | None,
        'max_drawdown': float,         # median over scenarios, on GSE+
        'horizon': int,
        'objective': str,
        'placement_catalog': str,
    },
    'efficient_frontier': pd.DataFrame,  # columns return, volatility
    'simulation_results': {
        'wealth_paths': pd.DataFrame,    # scenario_id, '0'..'H', before exit tax
        'wealth_paths_label': str,
        'terminal_wealth': pd.DataFrame, # scenario_id, wealth (net of tax)
        'statistics': dict,
    },
    'constraints_explanation': str,
    'known_gaps': list,
    'goal_analysis': {...},              # when goal_amount is given
}
```

**Usage Example**:
```python
from investment_calculator.modules import reporting, scenario_generator, user_profile
from investment_calculator.modules.placement_plan import plan_placements
from investment_calculator.placement_catalog import load_placement_catalog

# 1. GSE: economic scenarios
scenarios = scenario_generator.ScenarioGenerator(random_seed=42).generate({
    'num_scenarios': 1000,
    'time_horizon': 30,
    'timestep': 1.0,
    'use_stochastic': False,
})

# 2. User profile and contributions
profile = user_profile.UserProfileManager().process({
    'user_profile': {
        'personal_info': {'age': 35, 'retirement_age': 65, 'life_expectancy': 90},
        'financial_situation': {'current_savings': 0, 'annual_income': 60000,
                                'annual_expenses': 40000},
        'investment_preferences': {'risk_tolerance': 'moderate', 'time_horizon': 30},
    },
    'contribution_schedule': [{'start_year': 0, 'end_year': 30, 'monthly_amount': 500}],
    'withdrawal_schedule': [],
})

# 3. GSE+ -> GSE++ -> Markowitz by placement -> wealth projection
catalog = load_placement_catalog('fr-2026')
results = plan_placements(
    scenarios['scenarios'],
    catalog,
    profile['investment_time_series'],
    horizon=30,
    objective='mean_variance',
    risk_aversion=5.0,
    risk_free_placement='livret_a',
    goal_amount=500_000,
)
print(results['optimal_portfolio']['weights'])
print(results['simulation_results']['statistics']['median_terminal_wealth'])

# 4. Report
report = reporting.ReportGenerator().generate({
    'optimization_results': results,
    'report_config': {'format': 'html'},
})
print(len(report['report']['html']))
```

**Limits**: the profile constraints (`max_equity`, `min_bonds`) are not applied
yet; the catalogue's `known_gaps` lists the rest.

---

### Module 5: Visualization & Reporting

**File**: `investment_calculator/modules/reporting.py`

**Purpose**: Generate comprehensive reports and visualizations

**Key Classes**:
- `ReportGenerator` - Main reporting engine
- `ColorScheme` - Color schemes for visualization

**Input Structure**:
```python
config = {
    'scenarios': dict,              # From Module 1
    'tax_results': dict,            # Optional; the pipeline passes {}
    'user_profile': dict,           # From Module 3
    'optimization_results': dict,   # From plan_placements
    'report_config': {
        'report_type': 'detailed',  # 'summary', 'detailed', 'regulatory'
        'language': 'en',
        'format': 'html',           # 'html', 'pdf', 'json', 'markdown'
        'charts': [
            'wealth_trajectories',
            'efficient_frontier',
            'allocation_pie',
            'monte_carlo_histogram',
            'tax_impact_waterfall'
        ],
        'include_sections': ['summary', 'optimization', 'risk', 'tax']
    },
    'visualization_preferences': {
        'color_scheme': 'default',   # 'default', 'colorblind', 'grayscale'
        'chart_style': 'modern',
        'interactive': False,
        'save_figures': True,
        'figure_dpi': 150
    }
}
```

**Output Structure**:
```python
results = {
    'report': {
        'html': str,              # HTML report
        'pdf_path': str,          # Path to PDF (if generated)
        'json': str,              # JSON structured data
        'markdown': str           # Markdown version
    },
    'figures': {
        'wealth_trajectories': {
            'figure': matplotlib.Figure,
            'path': 'wealth_trajectories.png',
            'data': pd.DataFrame
        },
        'efficient_frontier': {...},
        'allocation_pie_chart': {...},
        'monte_carlo_histogram': {...},
        'tax_impact_waterfall': {...}
    },
    'tables': {
        'summary_statistics': pd.DataFrame,
        'optimal_allocation': pd.DataFrame,
        'tax_summary': pd.DataFrame
    },
    'executive_summary': {
        'one_page_summary': str,
        'key_findings': list,
        'recommendations': list,
        'risks_and_warnings': list
    },
    'interactive_dashboard': {
        'url': str,
        'html_file': str
    }
}
```

**Usage Example**:
```python
from investment_calculator.modules import reporting

# Create reporter
reporter = reporting.ReportGenerator()

# Generate report
config = {
    'scenarios': scenario_results,
    'user_profile': profile_results,
    'optimization_results': optimization_results,
    'report_config': {
        'report_type': 'detailed',
        'format': 'html',
        'charts': ['wealth_trajectories', 'efficient_frontier', 'allocation_pie']
    },
    'visualization_preferences': {
        'color_scheme': 'colorblind',
        'save_figures': True,
        'figure_dpi': 150
    }
}

report = reporter.generate(config)

# Access outputs
print(report['executive_summary']['one_page_summary'])
report['figures']['wealth_trajectories']['figure'].show()
html_report = report['report']['html']

# Quick usage
summary_text = reporting.quick_report(optimization_results)
print(summary_text)
```

**Key Features**:
- Multiple report formats (HTML, PDF, JSON, Markdown)
- Customizable visualizations
- Colorblind-friendly palettes
- Executive summary generation
- Interactive dashboards

---

## Complete Workflow Example

See `examples/complete_workflow_modules.py` for a full end-to-end example using all 5 modules.

## Testing

Each module has corresponding tests in `tests/`:
- `test_scenario_generator.py`
- `test_placements.py`, `test_net_returns.py`, `test_wrapper_tax.py`
- `test_user_profile.py`
- `test_placement_optimizer.py`, `test_wealth_simulation.py`, `test_placement_plan.py`
- `test_display_outputs.py` (reporting)

Run tests with:
```bash
pytest tests/
```

## API Reference

For detailed API documentation, see:
- `ARCHITECTURE.md` - Overall system architecture
- Module docstrings - Detailed parameter descriptions
- `examples/` - Usage examples

## Migration from Legacy Code

If you're migrating from the legacy code:

| Legacy | New Module | Notes |
|--------|-----------|-------|
| `gse.py` | Module 1 | Use `ScenarioGenerator` |
| `gse_plus.py` | GSE+ / GSE++ | Use `build_gross_placements` and `build_net_returns` |
| `personal_variables.py` | Module 3 | Use `UserProfileManager` |
| `moca.py` | Module 4 | Use `placement_plan.plan_placements` |
| Custom plotting code | Module 5 | Use `ReportGenerator` |

## Support

For issues or questions:
- File an issue on GitHub
- Consult the `ARCHITECTURE.md` document
- Check example files in `examples/`
