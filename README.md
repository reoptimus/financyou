# FinancYou

**Comprehensive Financial Planning & Portfolio Optimization System**

A powerful Python framework for generating economic scenarios, optimizing investment portfolios, and creating personalized financial plans with tax-aware analysis.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Overview

FinancYou is a complete financial planning system that takes you from economic scenario generation to optimized portfolio allocation with comprehensive tax analysis and visualization.

**Key Features:**
- 🎲 **Stochastic Economic Scenario Generation** - Monte Carlo simulation with Hull-White, Black-Scholes models
- 💰 **Multi-Jurisdiction Tax Analysis** - Support for US, France, UK, Germany, Canada
- 👤 **Personalized Investment Planning** - Risk profiling, life stage analysis, glide path generation
- 📊 **Portfolio Optimization** - Multiple methods (Max Sharpe, Min Volatility, Risk Parity)
- 📈 **Comprehensive Reporting** - HTML reports, charts, interactive dashboards
- ⚡ **Fast & Modular** - 5 independent modules, ~2 minute full pipeline

---

## 📦 Installation

### From Source

```bash
git clone https://github.com/reoptimus/financyou.git
cd financyou
pip install -e .
```

### Requirements

- Python >= 3.9
- pandas >= 1.3.0
- numpy >= 1.20.0
- scipy >= 1.7.0
- matplotlib >= 3.4.0

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
from investment_calculator.modules import (
    scenario_generator,
    tax_engine,
    user_profile,
    optimizer,
    reporting
)

# 1. Generate 1000 economic scenarios
gen = scenario_generator.ScenarioGenerator()
scenarios = gen.generate({
    'num_scenarios': 1000,
    'time_horizon': 30,
    'timestep': 1.0
})

# 2. Apply tax treatment (US)
engine = tax_engine.TaxEngine()
tax_config = tax_engine.TaxConfigPreset.get_preset('US')
after_tax = engine.apply_taxes({
    'scenarios': scenarios['scenarios'],
    'tax_config': tax_config,
    'investment_allocation': {
        'stocks': {'taxable': 0.6, 'tax_deferred': 0.3, 'tax_free': 0.1}
    }
})

# 3. Create user profile
manager = user_profile.UserProfileManager()
profile = manager.process(
    user_profile.create_simple_profile(
        age=35,
        annual_income=75000,
        risk_tolerance='moderate'
    )
)

# 4. Optimize portfolio
opt = optimizer.PortfolioOptimizer()
results = opt.optimize({
    'scenarios': after_tax['after_tax_scenarios'],
    'user_constraints': profile['validated_profile']['constraints'],
    'optimization_objective': 'max_sharpe',
    'goal_amount': 2000000
})

# 5. Generate report
reporter = reporting.ReportGenerator()
report = reporter.generate({
    'scenarios': scenarios,
    'tax_results': after_tax,
    'user_profile': profile,
    'optimization_results': results
})

print(report['executive_summary']['one_page_summary'])
```

---

## 🏗️ Architecture

FinancYou consists of 5 independent, modular components:

```
┌─────────────────────────────────────────────────────────────┐
│                    FINANCYOU PIPELINE                        │
└─────────────────────────────────────────────────────────────┘

Input Files (JSON)
      ↓
┌──────────────────────────────────────────┐
│ Module 1: Economic Scenario Generator   │  ~30 sec
│ • Hull-White interest rates             │
│ • Black-Scholes equities                │
│ • Correlated asset returns              │
└──────────────────────────────────────────┘
      ↓
┌──────────────────────────────────────────┐
│ Module 2: Tax-Integrated Scenarios      │  ~10 sec
│ • Multi-jurisdiction support            │
│ • Account type modeling                 │
│ • Tax drag analysis                     │
└──────────────────────────────────────────┘
      ↓
┌──────────────────────────────────────────┐
│ Module 3: User Profile & Time Series    │  ~5 sec
│ • Input validation                      │
│ • Risk profiling                        │
│ • Life stage analysis                   │
└──────────────────────────────────────────┘
      ↓
┌──────────────────────────────────────────┐
│ Module 4: Portfolio Optimizer           │  ~45 sec
│ • Multiple optimization methods         │
│ • Monte Carlo simulation                │
│ • Risk metrics (VaR, CVaR)             │
└──────────────────────────────────────────┘
      ↓
┌──────────────────────────────────────────┐
│ Module 5: Visualization & Reporting     │  ~10 sec
│ • HTML/PDF reports                      │
│ • Interactive charts                    │
│ • Executive summaries                   │
└──────────────────────────────────────────┘
      ↓
Output (HTML report + charts + JSON)
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| **[COMPLETE_GUIDE.md](COMPLETE_GUIDE.md)** | **START HERE** - Complete end-to-end guide |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture details |
| [MODULES_GUIDE.md](MODULES_GUIDE.md) | Per-module API reference |
| [examples/input_files/README.md](examples/input_files/README.md) | JSON configuration guide |

---

## 💡 Features

### Module 1: Economic Scenario Generator

- **Stochastic Models**: Hull-White (interest rates), Black-Scholes (equities), Real Estate
- **EIOPA Calibration**: Market-consistent yield curves
- **Correlation Engine**: Multi-asset correlation with Cholesky decomposition
- **Fast Mode**: Simple correlated normals for quick analysis
- **Advanced Mode**: Full stochastic model suite

### Module 2: Tax-Integrated Scenarios

- **Multi-Jurisdiction**: US, France, UK, Germany, Canada
- **Account Types**: Taxable, Tax-Deferred (401k/IRA), Tax-Free (Roth)
- **Tax Optimization**: Withdrawal sequencing, tax-loss harvesting
- **Realistic Modeling**: Dividend tax, capital gains, ordinary income

### Module 3: User Profile & Investment Planning

- **Risk Profiling**: Automated risk tolerance assessment
- **Life Stages**: Accumulation, Transition, Distribution phases
- **Glide Path**: Age-based asset allocation
- **Dual Slicing**: Domain-specific + general time series operations
- **Validation**: Comprehensive input validation with warnings

### Module 4: Portfolio Optimization

- **Optimization Methods**:
  - Maximum Sharpe Ratio
  - Minimum Volatility
  - Target Return
  - Risk Parity
  - Equal Weight
- **Efficient Frontier**: 50-point risk/return frontier
- **Monte Carlo**: Wealth simulation across all scenarios
- **Risk Metrics**: VaR, CVaR, drawdowns, probability of success

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

## 🎯 Use Cases

### Retirement Planning

```python
# Conservative investor approaching retirement
profile = user_profile.create_simple_profile(
    age=55,
    annual_income=120000,
    current_savings=500000,
    risk_tolerance='conservative',
    retirement_age=65
)

# Run analysis
results = run_complete_pipeline(profile)
print(f"Probability of comfortable retirement: {results['goal_probability']:.1%}")
```

### Wealth Building

```python
# Aggressive young investor
profile = user_profile.create_simple_profile(
    age=28,
    annual_income=85000,
    current_savings=25000,
    risk_tolerance='aggressive',
    retirement_age=60
)

# Long-term growth optimization
optimizer.optimize({
    'optimization_objective': 'max_return',
    'goal_amount': 5000000  # $5M wealth goal
})
```

### Tax Optimization

```python
# Compare US vs French tax treatment
us_results = apply_taxes_simple(scenarios, 'US', allocation_us)
fr_results = apply_taxes_simple(scenarios, 'FR', allocation_fr)

# Analyze tax drag
print(f"US tax drag: {us_results['tax_drag'].mean():.2%}")
print(f"FR tax drag: {fr_results['tax_drag'].mean():.2%}")
```

### Scenario Analysis

```python
# Generate scenarios with different assumptions
conservative = gen.generate({'equity_volatility': 0.15, ...})
aggressive = gen.generate({'equity_volatility': 0.25, ...})

# Compare outcomes
compare_scenarios(conservative, aggressive)
```

---

## 📁 Project Structure

```
financyou/
├── investment_calculator/
│   ├── modules/                    # 5 core modules
│   │   ├── scenario_generator.py  # Module 1: GSE
│   │   ├── tax_engine.py          # Module 2: GSE+
│   │   ├── user_profile.py        # Module 3: User Input
│   │   ├── optimizer.py           # Module 4: MOCA
│   │   └── reporting.py           # Module 5: Visualization
│   ├── stochastic_models/         # Advanced ESG models
│   │   ├── hull_white.py
│   │   ├── black_scholes.py
│   │   ├── real_estate.py
│   │   ├── correlation.py
│   │   └── calibration.py
│   ├── gse.py                     # Legacy GSE (deprecated)
│   ├── gse_plus.py                # Legacy GSE+ (deprecated)
│   ├── moca.py                    # Legacy MOCA (deprecated)
│   └── personal_variables.py      # User profile classes
├── time_series_slicer/            # Time series utilities
├── examples/
│   ├── complete_pipeline_with_files.py  # Full pipeline with JSON
│   ├── complete_workflow_modules.py     # In-code example
│   ├── slicing_capabilities_demo.py     # Slicing demo
│   └── input_files/                     # JSON configurations
│       ├── scenario_config.json
│       ├── tax_config_us.json
│       ├── tax_config_fr.json
│       ├── user_profile_conservative.json
│       ├── user_profile_aggressive.json
│       └── optimization_config.json
├── tests/                         # Comprehensive test suite
├── COMPLETE_GUIDE.md             # Complete documentation
├── ARCHITECTURE.md               # Architecture details
├── MODULES_GUIDE.md              # API reference
└── README.md                     # This file
```

---

## 🔧 Configuration

### JSON Input Files

FinancYou uses JSON configuration files for easy customization:

```bash
examples/input_files/
├── scenario_config.json          # Economic assumptions
├── tax_config_us.json           # US tax rules
├── user_profile_aggressive.json # Investor profile
└── optimization_config.json     # Optimization settings
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
pytest tests/test_tax_engine.py
pytest tests/test_user_profile.py
pytest tests/test_optimizer.py
pytest tests/test_reporting.py

# Run with coverage
pytest --cov=investment_calculator tests/
```

---

## 📊 Performance

- **1000 scenarios, 30 years**: ~2 minutes total
- **Module 1 (Scenarios)**: ~30 seconds
- **Module 2 (Taxes)**: ~10 seconds
- **Module 3 (Profile)**: ~5 seconds
- **Module 4 (Optimization)**: ~45 seconds
- **Module 5 (Reporting)**: ~10 seconds

---

## 🤝 Contributing

Contributions welcome! Please see our contributing guidelines.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Write tests for your changes
4. Commit your changes (`git commit -m 'Add AmazingFeature'`)
5. Push to the branch (`git push origin feature/AmazingFeature`)
6. Open a Pull Request

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
- Tax rules based on official tax codes

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
- [ ] Add comprehensive unit tests
- [ ] Build integration tests
- [ ] Develop web UI with Streamlit
- [ ] Deploy interactive dashboard
- [ ] Add more asset classes
- [ ] Extend to more jurisdictions

---

**Version**: 2.0.0
**Last Updated**: 2025-11-22

---

## Quick Links

- 📚 [Complete Guide](COMPLETE_GUIDE.md) - Start here!
- 🏗️ [Architecture](ARCHITECTURE.md) - Technical details
- 📖 [Modules Guide](MODULES_GUIDE.md) - API reference
- 💻 [Examples](examples/) - Runnable code
- ⚙️ [Config Files](examples/input_files/) - JSON configs
