

# FinancYou Modules Guide

## Overview

FinancYou consists of 5 independent, well-documented modules that work together in a clear pipeline. Each module has standardized input/output structures documented in `ARCHITECTURE.md`.

## Module Summary

| Module | Purpose | Input | Output |
|--------|---------|-------|--------|
| **Module 1: Scenario Generator** | Generate economic scenarios | Config dict | Scenarios DataFrame |
| **Module 2: Tax Engine** | Apply tax treatment | Scenarios + Tax config | After-tax scenarios |
| **Module 3: User Profile** | Process user input | User profile dict | Investment time series |
| **Module 4: Optimizer** | Optimize portfolio | Scenarios + Constraints | Optimal portfolio |
| **Module 5: Reporting** | Generate reports | All results | Reports + Charts |

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

### Module 2: Tax-Integrated Scenario Engine (GSE+)

**File**: `investment_calculator/modules/tax_engine.py`

**Purpose**: Apply tax treatment to economic scenarios

**Key Classes**:
- `TaxEngine` - Main tax calculation engine
- `TaxConfigPreset` - Preset configurations for different countries

**Input Structure**:
```python
config = {
    'scenarios': pd.DataFrame,    # From Module 1
    'tax_config': {
        'jurisdiction': 'US',     # 'US', 'FR', 'UK'
        'account_types': {
            'taxable': {...},
            'tax_deferred': {...},
            'tax_free': {...}
        },
        'social_charges': 0.0765,
        'wealth_tax': {...}
    },
    'investment_allocation': {
        'stocks': {
            'taxable': 0.6,
            'tax_deferred': 0.3,
            'tax_free': 0.1
        },
        'bonds': {...},
        'real_estate': {...}
    }
}
```

**Output Structure**:
```python
results = {
    'after_tax_scenarios': pd.DataFrame,  # Scenarios with after-tax returns
    'tax_tables': {
        'annual_tax_by_account': pd.DataFrame,
        'cumulative_tax': pd.DataFrame,
        'tax_drag': pd.DataFrame,
        'effective_tax_rate': pd.DataFrame
    },
    'account_balances': {
        'taxable': pd.DataFrame,
        'tax_deferred': pd.DataFrame,
        'tax_free': pd.DataFrame
    },
    'optimization_insights': {
        'tax_loss_harvesting_opportunities': list,
        'optimal_withdrawal_sequence': list
    }
}
```

**Usage Example**:
```python
from investment_calculator.modules import tax_engine

# Create tax engine
engine = tax_engine.TaxEngine()

# Use preset configuration
tax_config = tax_engine.TaxConfigPreset.get_preset('US')

# Define allocation
allocation = {
    'stocks': {'taxable': 0.6, 'tax_deferred': 0.3, 'tax_free': 0.1},
    'bonds': {'taxable': 0.4, 'tax_deferred': 0.5, 'tax_free': 0.1},
    'real_estate': {'taxable': 0.8, 'tax_deferred': 0.1, 'tax_free': 0.1}
}

# Apply taxes
results = engine.apply_taxes({
    'scenarios': scenarios_df,
    'tax_config': tax_config,
    'investment_allocation': allocation
})

# Quick usage
results = tax_engine.apply_taxes_simple(
    scenarios_df,
    jurisdiction='FR'
)
```

**Key Features**:
- Multi-jurisdiction support (US, FR, UK, DE, CA)
- Account type modeling (taxable, IRA, 401k, Roth, PEA)
- Tax drag analysis
- Withdrawal strategy optimization

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

### Module 4: Portfolio Optimization (MOCA)

**File**: `investment_calculator/modules/optimizer.py`

**Purpose**: Optimize portfolio and simulate outcomes

**Key Classes**:
- `PortfolioOptimizer` - Main optimization engine
- `OptimizationObjective` - Enum for optimization methods

**Input Structure**:
```python
config = {
    'scenarios': pd.DataFrame,          # After-tax scenarios from Module 2
    'user_constraints': dict,           # From Module 3
    'investment_time_series': pd.DataFrame,
    'optimization_objective': 'max_sharpe',  # Or 'min_volatility', 'target_return', etc.
    'optimization_params': {
        'target_return': 0.08,
        'risk_aversion': 5.0,
        'confidence_level': 0.95,
        'min_weight': 0.0,
        'max_weight': 1.0,
        'transaction_costs': {
            'stocks': 0.001,
            'bonds': 0.0005,
            'real_estate': 0.002
        },
        'rebalancing_threshold': 0.05
    },
    'goal_amount': 2000000  # Optional target
}
```

**Output Structure**:
```python
results = {
    'optimal_portfolio': {
        'weights': {'stock': 0.6, 'bond': 0.3, ...},
        'expected_return': 0.08,
        'expected_volatility': 0.12,
        'sharpe_ratio': 0.67,
        'max_drawdown': 0.25
    },
    'efficient_frontier': pd.DataFrame,
    'simulation_results': {
        'terminal_wealth': pd.DataFrame,
        'wealth_paths': pd.DataFrame,
        'statistics': {
            'mean_terminal_wealth': 1500000,
            'median_terminal_wealth': 1350000,
            'percentiles': {...},
            'var_95': 800000,
            'cvar_95': 600000
        }
    },
    'rebalancing_schedule': pd.DataFrame,
    'sensitivity_analysis': {...},
    'goal_analysis': {
        'goal_amount': 2000000,
        'probability_of_achieving': 0.72,
        'expected_surplus_deficit': -50000
    }
}
```

**Usage Example**:
```python
from investment_calculator.modules import optimizer

# Create optimizer
opt = optimizer.PortfolioOptimizer()

# Run optimization
config = {
    'scenarios': after_tax_scenarios_df,
    'user_constraints': profile_results['validated_profile']['constraints'],
    'investment_time_series': profile_results['investment_time_series'],
    'optimization_objective': 'max_sharpe',
    'goal_amount': 2000000
}

results = opt.optimize(config)

# Access results
optimal_weights = results['optimal_portfolio']['weights']
terminal_wealth_stats = results['simulation_results']['statistics']

# Quick usage
results = optimizer.quick_optimize(
    after_tax_scenarios_df,
    objective='max_sharpe'
)
```

**Key Features**:
- Multiple optimization methods (Max Sharpe, Min Volatility, Target Return, Risk Parity)
- Efficient frontier generation
- Monte Carlo simulation
- VaR and CVaR calculation
- Goal achievement probability
- Sensitivity analysis

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
    'tax_results': dict,            # From Module 2
    'user_profile': dict,           # From Module 3
    'optimization_results': dict,   # From Module 4
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
    'tax_results': tax_results,
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
- `test_tax_engine.py`
- `test_user_profile.py`
- `test_optimizer.py`
- `test_reporting.py`

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
| `gse_plus.py` | Module 2 | Use `TaxEngine` |
| `personal_variables.py` | Module 3 | Use `UserProfileManager` |
| `moca.py` | Module 4 | Use `PortfolioOptimizer` |
| Custom plotting code | Module 5 | Use `ReportGenerator` |

## Support

For issues or questions:
- File an issue on GitHub
- Consult the `ARCHITECTURE.md` document
- Check example files in `examples/`
