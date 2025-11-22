# FinancYou Architecture

## Overview

FinancYou is a comprehensive financial planning and investment optimization system composed of 5 distinct modules that work together in a clear pipeline:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FINANCYOU WORKFLOW                              │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────┐
    │  MODULE 1: GSE               │
    │  Economic Scenario Generator │
    │                              │
    │  Input:  Simulation Params   │
    │  Output: Economic Scenarios  │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │  MODULE 2: GSE+              │
    │  Tax-Integrated Scenarios    │
    │                              │
    │  Input:  Scenarios + Taxes   │
    │  Output: After-Tax Tables    │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐         ┌──────────────────────┐
    │  MODULE 3: User Input        │◄────────│  Web UI / API        │
    │  Investment Time Series      │         │                      │
    │                              │         └──────────────────────┘
    │  Input:  User Profile + UI   │
    │  Output: Investment Plan     │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │  MODULE 4: MOCA              │
    │  Portfolio Optimizer         │
    │                              │
    │  Input:  Scenarios + Plan    │
    │  Output: Optimized Portfolio │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │  MODULE 5: Visualization     │
    │  Reporting & Graphics        │
    │                              │
    │  Input:  All Results         │
    │  Output: Charts & Reports    │
    └──────────────────────────────┘
```

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

### Module 2: Tax-Integrated Scenario Engine (GSE+)

**Location**: `investment_calculator/modules/tax_engine.py`

**Purpose**: Apply tax treatment to economic scenarios based on account types and jurisdiction rules.

**Input Structure**:
```python
{
    'scenarios': pd.DataFrame,      # From Module 1

    'tax_config': {
        'jurisdiction': str,        # Country code (e.g., 'FR', 'US', 'UK')
        'account_types': {
            'taxable': {
                'income_tax_rate': float,         # e.g., 0.30
                'capital_gains_rate': float,      # e.g., 0.15
                'dividend_tax_rate': float,       # e.g., 0.25
                'interest_tax_rate': float        # e.g., 0.30
            },
            'tax_deferred': {
                'contribution_deduction': bool,   # Tax deduction on contributions
                'withdrawal_tax_rate': float      # Tax on withdrawals
            },
            'tax_free': {
                'contribution_limit': float,      # Annual limit
                'age_restrictions': dict          # Withdrawal rules
            }
        },
        'social_charges': float,    # Social security taxes (e.g., 0.172 for France)
        'wealth_tax': {
            'enabled': bool,
            'threshold': float,     # Wealth tax threshold
            'rate': float          # Wealth tax rate
        }
    },

    'investment_allocation': {
        'stocks': {'taxable': float, 'tax_deferred': float, 'tax_free': float},
        'bonds': {...},
        'real_estate': {...}
    }
}
```

**Output Structure**:
```python
{
    'after_tax_scenarios': pd.DataFrame,  # Same structure as scenarios but after-tax
                                         # Columns include original + '_after_tax' versions

    'tax_tables': {
        'annual_tax_by_account': pd.DataFrame,  # Annual taxes paid per account type
        'cumulative_tax': pd.DataFrame,         # Cumulative tax burden over time
        'tax_drag': pd.DataFrame,              # Performance drag due to taxes
        'effective_tax_rate': pd.DataFrame     # Effective tax rate per scenario
    },

    'account_balances': {
        'taxable': pd.DataFrame,      # After-tax balances by scenario and time
        'tax_deferred': pd.DataFrame,
        'tax_free': pd.DataFrame,
        'total': pd.DataFrame         # Total across all accounts
    },

    'optimization_insights': {
        'tax_loss_harvesting_opportunities': list,
        'optimal_withdrawal_sequence': list,  # Which account to draw from first
        'roth_conversion_analysis': dict      # Tax-deferred to tax-free conversion
    }
}
```

**Key Features**:
- Multi-jurisdiction tax rules
- Account type modeling (taxable, IRA, Roth, 401k, PEA, etc.)
- Tax-advantaged rebalancing
- Withdrawal strategy optimization

**Dependencies**: Module 1, NumPy, Pandas

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

### Module 4: Portfolio Optimization (MOCA)

**Location**: `investment_calculator/modules/optimizer.py`

**Purpose**: Optimize portfolio allocation and simulate investment outcomes across scenarios.

**Input Structure**:
```python
{
    'scenarios': pd.DataFrame,          # After-tax scenarios from Module 2

    'user_constraints': dict,           # From Module 3 validated profile

    'investment_time_series': pd.DataFrame,  # From Module 3

    'optimization_objective': str,      # 'max_return', 'max_sharpe', 'min_volatility',
                                       # 'min_cvar', 'risk_parity', 'target_return'

    'optimization_params': {
        'target_return': float,         # If using target return objective
        'risk_aversion': float,         # Risk aversion coefficient (1-10)
        'confidence_level': float,      # For VaR/CVaR (e.g., 0.95)
        'min_weight': float,           # Minimum asset weight (e.g., 0.0)
        'max_weight': float,           # Maximum asset weight (e.g., 1.0)
        'transaction_costs': {
            'stocks': float,
            'bonds': float,
            'real_estate': float
        },
        'rebalancing_threshold': float  # Trigger rebalancing when drift exceeds %
    },

    'asset_universe': {
        'stocks': {
            'instruments': list,        # List of stock indices/funds
            'constraints': dict
        },
        'bonds': {...},
        'real_estate': {...},
        'alternatives': {...}
    }
}
```

**Output Structure**:
```python
{
    'optimal_portfolio': {
        'weights': dict,                # Optimal allocation {asset: weight}
        'expected_return': float,       # Annualized expected return
        'expected_volatility': float,   # Annualized volatility
        'sharpe_ratio': float,
        'max_drawdown': float
    },

    'efficient_frontier': pd.DataFrame,  # Risk-return efficient frontier
                                        # Columns: ['return', 'volatility', 'sharpe',
                                        #          'stock_weight', 'bond_weight', ...]

    'simulation_results': {
        'terminal_wealth': pd.DataFrame,    # Final wealth for each scenario
                                           # Columns: ['scenario_id', 'wealth',
                                           #          'real_wealth', 'percentile']

        'wealth_paths': pd.DataFrame,       # Full wealth trajectory
                                           # Shape: (scenarios, time_periods)

        'statistics': {
            'mean_terminal_wealth': float,
            'median_terminal_wealth': float,
            'std_terminal_wealth': float,
            'percentiles': {
                '5': float,
                '25': float,
                '50': float,
                '75': float,
                '95': float
            },
            'probability_of_success': float,  # % scenarios meeting goal
            'shortfall_risk': float,         # Average shortfall in bad scenarios
            'var_95': float,                 # Value at Risk (95%)
            'cvar_95': float                 # Conditional VaR (95%)
        }
    },

    'rebalancing_schedule': pd.DataFrame,   # When and how to rebalance
                                           # Columns: ['period', 'action',
                                           #          'from_asset', 'to_asset',
                                           #          'amount', 'cost']

    'sensitivity_analysis': {
        'return_sensitivity': dict,    # Impact of return assumptions
        'volatility_sensitivity': dict, # Impact of volatility assumptions
        'correlation_sensitivity': dict # Impact of correlation assumptions
    },

    'goal_analysis': {
        'goal_amount': float,          # Target wealth from user profile
        'probability_of_achieving': float,
        'expected_surplus_deficit': float,
        'years_to_goal': dict          # Probability distribution of time to goal
    }
}
```

**Key Features**:
- Multiple optimization methods (mean-variance, max Sharpe, CVaR, etc.)
- Monte Carlo simulation across all scenarios
- Efficient frontier generation
- Risk metrics (VaR, CVaR, drawdowns)
- Dynamic rebalancing with transaction costs
- Sensitivity analysis

**Dependencies**: Modules 2, 3; NumPy, Pandas, SciPy, cvxpy (for optimization)

---

### Module 5: Visualization & Reporting

**Location**: `investment_calculator/modules/reporting.py`

**Purpose**: Generate comprehensive charts, graphs, and reports from all module outputs.

**Input Structure**:
```python
{
    'scenarios': dict,              # From Module 1
    'tax_results': dict,            # From Module 2
    'user_profile': dict,           # From Module 3
    'optimization_results': dict,   # From Module 4

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
# Step 1: Generate economic scenarios
from investment_calculator.modules import scenario_generator

gse = scenario_generator.ScenarioGenerator()
scenarios = gse.generate({
    'num_scenarios': 1000,
    'time_horizon': 30,
    'timestep': 1/12,
    'use_stochastic': True,
    'calibration_date': '2025-01-01',
    'currency': 'EUR'
})

# Step 2: Apply taxes
from investment_calculator.modules import tax_engine

tax_eng = tax_engine.TaxEngine()
after_tax = tax_eng.apply_taxes({
    'scenarios': scenarios['scenarios'],
    'tax_config': {
        'jurisdiction': 'FR',
        'account_types': {...}
    },
    'investment_allocation': {...}
})

# Step 3: Get user input
from investment_calculator.modules import user_profile

user_input = user_profile.UserProfileManager()
profile = user_input.process({
    'user_profile': {...},  # From web UI
    'contribution_schedule': [...],
    'withdrawal_schedule': [...]
})

# Step 4: Optimize portfolio
from investment_calculator.modules import optimizer

moca = optimizer.PortfolioOptimizer()
optimal = moca.optimize({
    'scenarios': after_tax['after_tax_scenarios'],
    'user_constraints': profile['validated_profile']['constraints'],
    'investment_time_series': profile['investment_time_series'],
    'optimization_objective': 'max_sharpe'
})

# Step 5: Generate reports
from investment_calculator.modules import reporting

reporter = reporting.ReportGenerator()
report = reporter.generate({
    'scenarios': scenarios,
    'tax_results': after_tax,
    'user_profile': profile,
    'optimization_results': optimal,
    'report_config': {
        'report_type': 'detailed',
        'format': 'html',
        'language': 'en'
    }
})

# Access results
print(report['executive_summary']['one_page_summary'])
report['figures']['wealth_trajectories']['figure'].show()
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

- **Core**: Python 3.9+
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
6. Add more asset classes and strategies
