# FinancYou Architecture

## Overview

FinancYou projects a household's wealth after tax. Its logic is a chain of
three scenario layers, and the optimisation runs on the last one:

```
    ┌──────────────────────────────┐
    │  GSE (scenario_generator)    │  stock, bond, rate, inflation
    └──────────────┬───────────────┘
                   ▼
    ┌──────────────────────────────┐
    │  GSE+ (placements)           │  return of each household placement
    │                              │  (CTO, PEA, assurance-vie, Livret A),
    │                              │  net of annual fees, before tax
    └──────────────┬───────────────┘
                   ▼
    ┌──────────────────────────────┐         ┌──────────────────────┐
    │  GSE++ (net_returns)         │◄────────│  User profile        │
    │  net of fees and exit tax,   │         │  (user_profile,      │
    │  per scenario × horizon      │         │   web UI)            │
    └──────────────┬───────────────┘         └──────────────────────┘
                   ▼
    ┌──────────────────────────────┐
    │  Markowitz                   │  mean and volatility of GSE++ at H,
    │  (placement_optimizer)       │  under wrapper caps
    └──────────────┬───────────────┘
                   ▼
    ┌──────────────────────────────┐
    │  Projection                  │  user's actual flows
    │  (wealth_simulation)         │
    └──────────────┬───────────────┘
                   ▼
    ┌──────────────────────────────┐
    │  Reporting                   │
    └──────────────────────────────┘
```

`placement_plan.plan_placements` runs GSE+ → projection. Taxes and placements
are input data: `investment_calculator/tax_regimes/` and
`investment_calculator/placement_catalogs/`. Decisions:
`docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md`,
`docs/adr/0002-le-placement-est-l-unite-d-optimisation.md`.

## Module Specifications

### Module 1: Economic Scenario Generator (GSE)

**Location**: `investment_calculator/modules/scenario_generator.py`

**Purpose**: Generate Monte Carlo economic scenarios for all asset classes using advanced stochastic models.

**Input Structure**:
```python
{
    'num_scenarios': int,           # Number of Monte Carlo scenarios (e.g., 1000)
    'time_horizon': int,            # Years to simulate (e.g., 30)
    'timestep': float,              # Time step in years (e.g., 1/12 for monthly)
    'use_stochastic': bool,         # Use advanced ESG models vs simple
    'calibration_date': str,        # Date for EIOPA curve calibration (YYYY-MM-DD)
    'currency': str,                # Currency for calibration (e.g., 'EUR', 'USD')
    'correlation_matrix': dict,     # Cross-asset correlations (optional)
    'economic_params': {
        'mean_reversion_speed': float,    # Hull-White parameter
        'volatility': float,              # Interest rate volatility
        'equity_drift': float,            # Equity expected return
        'equity_volatility': float,       # Equity volatility
        'real_estate_drift': float,       # Real estate expected return
        'real_estate_volatility': float,  # Real estate volatility
        'inflation_mean': float,          # Long-term inflation target
        'inflation_volatility': float     # Inflation volatility
    }
}
```

**Output Structure**:
```python
{
    'scenarios': pd.DataFrame,      # Shape: (num_scenarios, time_steps, asset_classes)
                                   # Columns: ['scenario_id', 'time_period',
                                   #          'interest_rate', 'stock_return',
                                   #          'bond_return', 'real_estate_return',
                                   #          'inflation', 'gdp_growth']

    'deflators': pd.DataFrame,     # Risk-neutral deflators for pricing
                                   # Shape: (num_scenarios, time_steps)

    'metadata': {
        'generation_timestamp': datetime,
        'calibration_info': dict,
        'model_versions': dict,
        'random_seed': int
    },

    'diagnostics': {
        'mean_returns': dict,       # Average returns per asset class
        'volatilities': dict,       # Volatilities per asset class
        'correlations': pd.DataFrame, # Realized correlations
        'martingale_test': dict     # Martingale property tests
    }
}
```

**Key Components**:
- Hull-White interest rate model
- Black-Scholes equity model
- Real estate stochastic model
- Correlation engine (Cholesky decomposition)
- EIOPA curve calibration

**Dependencies**: NumPy, Pandas, SciPy

---

### Module 2: Placements and Taxes (GSE+ and GSE++)

**Location**: `investment_calculator/modules/placements.py`,
`investment_calculator/modules/net_returns.py`, `investment_calculator/wrapper_tax.py`

**Purpose**: GSE+ maps each placement of the catalogue to its underlying GSE
variable and subtracts its annual fees. GSE++ applies, per wrapper, the exit
tax of the regime the catalogue names, for the user's `TaxProfile` (amount
invested, couple, wrapper seniority) and for each horizon.

**Input**: GSE scenarios, a `PlacementCatalog` (`load_placement_catalog('fr-2026')`),
a `TaxProfile`, a list of horizons.

**Output**:
- GSE+: DataFrame indexed by `(scenario_id, time_period)`, one column per placement;
- GSE++: net multiples per scenario × horizon × placement, with
  `annualized(h)` for annualised net returns.

Draft catalogues and regimes are refused at load time. Gaps are declared in
`known_gaps`. Detail and examples: `MODULES_GUIDE.md`.

---

### Module 3: User Input & Investment Time Series

**Location**: `investment_calculator/modules/user_profile.py`

**Purpose**: Capture user profile from web UI, validate inputs, create time-series investment plan with slicing.

**Input Structure**:
```python
{
    'user_profile': {
        'personal_info': {
            'age': int,
            'retirement_age': int,
            'life_expectancy': int,
            'country': str,
            'currency': str
        },

        'financial_situation': {
            'current_savings': float,
            'annual_income': float,
            'annual_expenses': float,
            'debt': {
                'mortgage': float,
                'student_loans': float,
                'other': float
            }
        },

        'investment_preferences': {
            'risk_tolerance': str,      # 'conservative', 'moderate', 'aggressive'
            'investment_goal': str,     # 'retirement', 'wealth', 'income', 'education'
            'time_horizon': int,        # Years
            'esg_preferences': bool,    # Environmental/Social/Governance
            'liquidity_needs': float    # % of portfolio needed liquid
        },

        'constraints': {
            'max_equity_allocation': float,   # e.g., 0.80
            'min_bond_allocation': float,     # e.g., 0.10
            'exclude_sectors': list,          # Sectors to exclude
            'rebalancing_frequency': str      # 'monthly', 'quarterly', 'annual'
        }
    },

    'contribution_schedule': [
        {
            'start_year': int,
            'end_year': int,
            'monthly_amount': float,
            'annual_increase': float,     # Inflation-adjusted or nominal increase
            'account_type': str           # 'taxable', 'tax_deferred', 'tax_free'
        }
    ],

    'withdrawal_schedule': [
        {
            'year': int,
            'amount': float,
            'purpose': str,               # 'retirement', 'education', 'home', 'other'
            'account_preference': str     # Which account to withdraw from
        }
    ]
}
```

**Output Structure**:
```python
{
    'validated_profile': dict,      # Validated and sanitized user profile

    'investment_time_series': pd.DataFrame,  # Monthly/Annual investment plan
                                            # Columns: ['period', 'contribution',
                                            #          'withdrawal', 'net_flow',
                                            #          'account_type', 'purpose']

    'life_stages': {
        'accumulation': {'start': int, 'end': int},    # Working years
        'transition': {'start': int, 'end': int},      # Pre-retirement
        'distribution': {'start': int, 'end': int}     # Retirement
    },

    'risk_profile': {
        'score': float,                 # 0-100 risk score
        'recommended_allocation': {
            'stocks': float,
            'bonds': float,
            'real_estate': float,
            'cash': float
        },
        'glide_path': pd.DataFrame     # Age-based allocation changes
    },

    'sliced_plans': {
        'by_life_stage': dict,         # Investment plan sliced by life stage
        'by_goal': dict,               # Sliced by investment goal
        'by_account_type': dict        # Sliced by account type
    },

    'time_series_slicer': TimeSeriesSlicer,  # General-purpose time series slicing
                                             # Provides: slice_by_time(), slice_by_index(),
                                             #          slice_by_window(), split_by_ratio(),
                                             #          slice_by_value()

    'validation_warnings': list,       # Any issues found during validation

    'summary_statistics': {
        'total_contributions': float,
        'total_withdrawals': float,
        'contribution_years': int,
        'retirement_duration': int
    }
}
```

**Key Features**:
- Input validation and sanitization
- Risk tolerance assessment
- **Dual slicing capabilities**:
  - Domain-specific: By life stage, goal, account type
  - General-purpose: Time range, index, window, ratio, value-based
- Glide path generation (age-based allocation)
- Integration with web UI API
- Integration with `time_series_slicer` library for advanced operations

**Dependencies**: Module 2, Pandas, time_series_slicer

---

### Module 4: Portfolio Optimization and Projection

**Location**: `investment_calculator/modules/placement_optimizer.py`,
`investment_calculator/modules/wealth_simulation.py`,
`investment_calculator/modules/placement_plan.py`

**Purpose**: Markowitz by placement on the moments of GSE++ at horizon H
(objectives `mean_variance`, `min_volatility`, `target_return`, `max_sharpe`),
under the wrapper contribution caps only; efficient frontier; projection of the
user's contributions with the chosen weights.

**Input** (`plan_placements`): GSE scenarios, catalogue, `investment_time_series`,
`horizon`, `objective` and its parameters, optional `risk_free_placement`
and `goal_amount`.

**Output**: `optimal_portfolio`, `efficient_frontier`, `simulation_results`,
`constraints_explanation`, `known_gaps`, `goal_analysis`. Field list:
`MODULES_GUIDE.md`.

---

### Module 5: Visualization & Reporting

**Location**: `investment_calculator/modules/reporting.py`

**Purpose**: Generate comprehensive charts, graphs, and reports from all module outputs.

**Input Structure**:
```python
{
    'scenarios': dict,              # From Module 1
    'tax_results': dict,            # Optional; the pipeline passes {}
    'user_profile': dict,           # From Module 3
    'optimization_results': dict,   # From plan_placements

    'report_config': {
        'report_type': str,         # 'summary', 'detailed', 'regulatory', 'custom'
        'language': str,            # 'en', 'fr', 'es', etc.
        'format': str,              # 'html', 'pdf', 'interactive', 'json'
        'charts': list,             # List of chart types to include
        'include_sections': list    # Sections to include in report
    },

    'visualization_preferences': {
        'color_scheme': str,        # 'default', 'colorblind', 'grayscale'
        'chart_style': str,         # 'modern', 'classic', 'minimal'
        'interactive': bool,        # Use interactive plots (Plotly) vs static (Matplotlib)
        'save_figures': bool,       # Save individual figures
        'figure_dpi': int          # Resolution for saved figures
    }
}
```

**Output Structure**:
```python
{
    'report': {
        'html': str,                # Full HTML report
        'pdf_path': str,            # Path to PDF report (if generated)
        'json': dict,               # Structured data for custom rendering
        'markdown': str             # Markdown version
    },

    'figures': {
        'wealth_trajectories': {
            'figure': matplotlib.Figure or plotly.Figure,
            'path': str,            # Path to saved file
            'data': pd.DataFrame    # Underlying data
        },

        'efficient_frontier': {...},

        'allocation_pie_chart': {...},

        'risk_return_scatter': {...},

        'monte_carlo_histogram': {...},

        'drawdown_analysis': {...},

        'tax_impact_waterfall': {...},

        'goal_probability_gauge': {...},

        'contribution_timeline': {...},

        'asset_performance_comparison': {...}
    },

    'tables': {
        'summary_statistics': pd.DataFrame,
        'optimal_allocation': pd.DataFrame,
        'tax_summary': pd.DataFrame,
        'scenario_analysis': pd.DataFrame,
        'rebalancing_schedule': pd.DataFrame
    },

    'executive_summary': {
        'one_page_summary': str,    # Text summary for executives
        'key_findings': list,       # Bullet points
        'recommendations': list,    # Action items
        'risks_and_warnings': list  # Important disclaimers
    },

    'interactive_dashboard': {
        'url': str,                 # URL to interactive dashboard (if deployed)
        'html_file': str           # Standalone HTML file with dashboard
    }
}
```

**Chart Types**:
1. **Wealth Trajectory Fan Chart**: Show percentile ranges of wealth over time
2. **Efficient Frontier**: Risk-return tradeoff visualization
3. **Monte Carlo Distribution**: Histogram of terminal wealth outcomes
4. **Allocation Breakdown**: Pie/bar charts of portfolio composition
5. **Drawdown Analysis**: Maximum drawdown over time
6. **Tax Impact Waterfall**: Visualization of tax drag on returns
7. **Goal Probability Gauge**: Visual indicator of goal achievement probability
8. **Scenario Comparison**: Side-by-side scenario analysis
9. **Correlation Heatmap**: Asset correlation matrix
10. **Time Series Performance**: Historical/projected performance charts

**Key Features**:
- Multi-format output (HTML, PDF, interactive)
- Customizable chart styles
- Accessibility (colorblind-friendly palettes)
- Regulatory compliance reporting
- Interactive dashboards
- Export to PowerPoint/Excel

**Dependencies**: Modules 1-4; Matplotlib, Plotly, Seaborn, Jinja2 (for templates),
                 WeasyPrint (for PDF), pandas, numpy

---

## Data Flow Example

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

# Access results
print(results['optimal_portfolio']['weights'])
html = report['report']['html']
```

## Design Principles

1. **Clear Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Standardized I/O**: All modules use dictionary inputs and outputs with documented schemas
3. **Type Safety**: Use type hints throughout for better IDE support and error catching
4. **Comprehensive Documentation**: Every function, class, and module has detailed docstrings
5. **Testability**: Each module can be tested independently with mock data
6. **Extensibility**: Easy to add new asset classes, tax jurisdictions, optimization methods
7. **Performance**: Vectorized operations, caching, and parallel processing where applicable
8. **Error Handling**: Graceful degradation with informative error messages

## Technology Stack

- **Core**: Python 3.11+
- **Numerical**: NumPy, SciPy, Pandas
- **Optimization**: cvxpy, scipy.optimize
- **Visualization**: Matplotlib, Plotly, Seaborn
- **Reporting**: Jinja2, WeasyPrint, python-pptx
- **Testing**: pytest, pytest-cov
- **Documentation**: Sphinx, autodoc
- **Web API** (future): FastAPI, Pydantic

## Next Steps

1. Implement each module following this specification
2. Create comprehensive unit tests for each module
3. Build integration tests for the full pipeline
4. Develop web UI/API layer
5. Deploy interactive dashboard
6. Add real estate and Michaud resampling
