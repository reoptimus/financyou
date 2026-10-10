# FinancYou

**Comprehensive Financial Planning & Portfolio Optimization System**

A powerful Python framework for generating economic scenarios, optimizing investment portfolios, and creating personalized financial plans with tax-aware analysis.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Overview

FinancYou is a complete financial planning system that takes you from economic scenario generation to optimized portfolio allocation with comprehensive tax analysis and visualization.

**Key Features:**
- 🎲 **Stochastic Economic Scenario Generation (GSE)** - Monte Carlo simulation with Hull-White, Black-Scholes models
- 🏦 **Household placements (GSE+)** - CTO, PEA, assurance-vie, Livret A, net of their fees
- 💰 **After-tax returns (GSE++)** - Exit tax per wrapper, from a dated tax regime (`fr-2026`)
- 📊 **Markowitz by placement** - Mean-variance, min volatility, target return, max Sharpe, under wrapper caps
- 📈 **Reporting** - HTML reports, charts, Streamlit web UI

---

## 📦 Installation

### From Source

```bash
git clone https://github.com/reoptimus/financyou.git
cd financyou
pip install -e .
```

### Requirements

- Python >= 3.11
- pandas, numpy, scipy, matplotlib, openpyxl, jsonschema (bounds in `pyproject.toml`)
- Web UI: `pip install -e ".[web]"` (streamlit, plotly)

---

## 🚀 Quick Start

### Run Complete Pipeline (2 minutes)

```bash
# Navigate to FinancYou directory
cd financyou

# Run complete example with JSON configs
python examples/complete_pipeline_with_files.py

# Open generated report
open outputs/investment_report.html
```

### Basic Usage

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

---

## 🏗️ Architecture

FinancYou consists of 5 independent, modular components:

```
GSE (Module 1: scenario_generator)
    stock, bond, interest rate and inflation scenarios
      ↓
GSE+ (placements)
    annual return of each placement of the catalogue, net of annual fees, before tax
      ↓
GSE++ (net_returns)                      ← user's tax situation
    return net of fees and exit tax, per scenario × horizon × placement
      ↓
Markowitz (placement_optimizer)          ← wrapper caps (PEA, Livret A…)
    mean and volatility of GSE++ → weights per placement
      ↓
Projection (wealth_simulation)           ← user's contributions (Module 3: user_profile)
      ↓
Report (Module 5: reporting)
```

`placement_plan.plan_placements` runs GSE+ → projection in one call. Taxes are
input data (`investment_calculator/tax_regimes/`), placements and fees too
(`investment_calculator/placement_catalogs/`). See
[ADR 0001](docs/adr/0001-le-regime-fiscal-est-une-donnee-d-entree.md) and
[ADR 0002](docs/adr/0002-le-placement-est-l-unite-d-optimisation.md).

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| **[COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)** | **START HERE** - Complete end-to-end guide |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture details |
| [MODULES_GUIDE.md](MODULES_GUIDE.md) | Per-module API reference |
| [REOPTIMUS_THEORY.md](REOPTIMUS_THEORY.md) | Mathematical foundations and optimization theory |
| [examples/input_files/README.md](examples/input_files/README.md) | JSON configuration guide |

---

## 💡 Features

### Module 1: Economic Scenario Generator

- **Stochastic Models**: Hull-White (interest rates), Black-Scholes (equities), Real Estate
- **EIOPA Calibration**: Market-consistent yield curves
- **Correlation Engine**: Multi-asset correlation with Cholesky decomposition
- **Fast Mode**: Simple correlated normals for quick analysis
- **Advanced Mode**: Full stochastic model suite

### GSE+ and GSE++: Placements and Taxes

- **Catalogue `fr-2026`**: CTO actions, CTO obligations, PEA actions, AV fonds euros, AV UC actions, Livret A
- **Fees**: annual fees of each placement, sourced in the catalogue
- **Exit tax per wrapper**: PFU on CTO, PEA after 5 years, assurance-vie allowance after 8 years, Livret A exempt
- **France only** for now; a new country is a new data file, not new code
- **Declared gaps**: each catalogue lists its `known_gaps`

### Module 3: User Profile & Investment Planning

- **Risk Profiling**: Automated risk tolerance assessment
- **Life Stages**: Accumulation, Transition, Distribution phases
- **Glide Path**: Age-based asset allocation
- **Dual Slicing**: Domain-specific + general time series operations
- **Validation**: Comprehensive input validation with warnings

### Module 4: Portfolio Optimization

- **Unit**: the placement, with mean and volatility computed on GSE++ at horizon H
- **Objectives**: mean-variance (risk aversion λ), minimum volatility, target return, maximum Sharpe (reference placement, e.g. Livret A)
- **Constraints**: wrapper contribution caps only
- **Efficient Frontier**: from minimum volatility to the highest reachable return
- **Projection**: wealth paths of the user's actual contributions, terminal wealth net of exit tax, probability of reaching a goal

### Module 5: Visualization & Reporting

- **Charts**:
  - Wealth trajectory fan charts
  - Efficient frontier
  - Monte Carlo histograms
  - Allocation pie charts
  - Tax impact waterfalls
- **Reports**: HTML, PDF, JSON, Markdown
- **Accessibility**: Colorblind-friendly palettes
- **Executive Summary**: One-page summaries with key findings

---

## 📁 Project Structure

```
financyou/
├── investment_calculator/
│   ├── modules/                    # Pipeline
│   │   ├── scenario_generator.py  # GSE
│   │   ├── placements.py          # GSE+
│   │   ├── net_returns.py         # GSE++
│   │   ├── user_profile.py        # User input
│   │   ├── placement_optimizer.py # Markowitz by placement
│   │   ├── wealth_simulation.py   # Wealth projection
│   │   ├── placement_plan.py      # Orchestration
│   │   └── reporting.py           # Visualization
│   ├── placement_catalogs/        # Placements and fees (data)
│   ├── tax_regimes/               # Tax regimes (data)
│   ├── wrapper_tax.py             # Exit tax per wrapper
│   ├── stochastic_models/         # Advanced ESG models
│   ├── gse.py, gse_plus.py, moca.py  # Older layer, not used by the pipeline
│   └── personal_variables.py      # User profile classes
├── time_series_slicer/            # Time series utilities
├── web_ui/app_enhanced.py         # Streamlit application
├── examples/
│   ├── complete_pipeline_with_files.py  # Full pipeline with JSON
│   ├── complete_workflow_modules.py     # In-code example
│   ├── slicing_capabilities_demo.py     # Slicing demo
│   └── input_files/                     # JSON configurations
├── docs/adr/                      # Architecture decisions
├── tests/
├── COMPLETE_GUIDE.md
├── ARCHITECTURE.md
├── MODULES_GUIDE.md
└── README.md
```

---

## 🔧 Configuration

### JSON Input Files

FinancYou uses JSON configuration files for easy customization:

```bash
examples/input_files/
├── scenario_config.json           # Economic assumptions
├── user_profile_aggressive.json   # Investor profile
├── user_profile_conservative.json
└── optimization_config.json       # Catalogue, objective, horizon goal
```

Edit these files to customize your analysis without changing code.

See [examples/input_files/README.md](examples/input_files/README.md) for details.

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific module tests
pytest tests/test_scenario_generator.py
pytest tests/test_placements.py tests/test_net_returns.py
pytest tests/test_placement_optimizer.py tests/test_placement_plan.py
pytest tests/test_user_profile.py tests/test_display_outputs.py

# Run with coverage
pytest --cov=investment_calculator tests/
```

---

## 📊 Performance

`tests/test_performance.py` measures the full pipeline; run it for current figures.

---

## 🤝 Contributing

Read [CLAUDE.md](CLAUDE.md) first: one PR per sub-step, each with its proof,
no silent numerical regression, taxes as data only.

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 👥 Authors

- **FinancYou Contributors**
- Ported from legacy R codebase (~5,500 lines) to modern Python modules

---

## 🙏 Acknowledgments

- Built with NumPy, Pandas, SciPy, Matplotlib
- Stochastic models based on academic literature
- EIOPA curve calibration for realistic interest rates
- Tax rules: sourced and validated per regime file (`tax_regimes/`)

---

## 📧 Support

- **Documentation**: See [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)
- **Issues**: [GitHub Issues](https://github.com/reoptimus/financyou/issues)
- **Examples**: All in `examples/` directory

---

## 🗺️ Roadmap

- [x] Refactor into 5 modular components
- [x] Create comprehensive documentation
- [x] Add JSON configuration files
- [x] Integrate time_series_slicer
- [x] Unit and end-to-end tests
- [x] Develop web UI with Streamlit
- [x] Optimise placements on after-tax returns (GSE → GSE+ → GSE++)
- [ ] Calibrate the fonds euros return
- [ ] Apply the profile constraints to the optimiser
- [ ] Michaud resampling
- [ ] Real estate placement
- [ ] Deploy interactive dashboard
- [ ] Add more asset classes
- [ ] Extend to more jurisdictions

---

**Version**: 2.0.0
**Last Updated**: 2026-10-10

---

## Quick Links

- 📚 [Complete Guide](COMPLETE_GUIDE.md) - Start here!
- 🏗️ [Architecture](ARCHITECTURE.md) - Technical details
- 📖 [Modules Guide](MODULES_GUIDE.md) - API reference
- 🧮 [Réoptimus Theory](REOPTIMUS_THEORY.md) - Mathematical foundations
- 💻 [Examples](examples/) - Runnable code
- ⚙️ [Config Files](examples/input_files/) - JSON configs
