# FinancYou Modules

This directory contains the 5 core modules of the FinancYou system.

## Module Organization

```
modules/
├── __init__.py                 # Package initialization
├── scenario_generator.py       # Module 1: Economic Scenario Generator (GSE)
├── tax_engine.py              # Module 2: Tax-Integrated Scenarios (GSE+)
├── user_profile.py            # Module 3: User Input & Investment Time Series
├── optimizer.py               # Module 4: Portfolio Optimization (MOCA)
└── reporting.py               # Module 5: Visualization & Reporting
```

## Module Pipeline

```
User Input
    ↓
[Module 3: User Profile] ──→ Investment Plan
    ↓
[Module 1: Scenario Generator] ──→ Economic Scenarios
    ↓
[Module 2: Tax Engine] ──→ After-Tax Scenarios
    ↓
[Module 4: Optimizer] ──→ Optimal Portfolio + Simulations
    ↓
[Module 5: Reporting] ──→ Reports + Visualizations
```

## Quick Start

```python
from investment_calculator.modules import (
    scenario_generator,
    tax_engine,
    user_profile,
    optimizer,
    reporting
)

# Step 1: Generate scenarios
gen = scenario_generator.ScenarioGenerator()
scenarios = gen.generate({
    'num_scenarios': 1000,
    'time_horizon': 30,
    'timestep': 1.0,
    'use_stochastic': True
})

# Step 2: Apply taxes
engine = tax_engine.TaxEngine()
tax_results = engine.apply_taxes({
    'scenarios': scenarios['scenarios'],
    'tax_config': tax_engine.TaxConfigPreset.get_preset('US'),
    'investment_allocation': {...}
})

# Step 3: Process user profile
manager = user_profile.UserProfileManager()
profile_results = manager.process({
    'user_profile': {...},
    'contribution_schedule': [...],
    'withdrawal_schedule': [...]
})

# Step 4: Optimize
opt = optimizer.PortfolioOptimizer()
optimization_results = opt.optimize({
    'scenarios': tax_results['after_tax_scenarios'],
    'user_constraints': profile_results['validated_profile']['constraints'],
    'optimization_objective': 'max_sharpe'
})

# Step 5: Generate report
reporter = reporting.ReportGenerator()
report = reporter.generate({
    'scenarios': scenarios,
    'tax_results': tax_results,
    'user_profile': profile_results,
    'optimization_results': optimization_results
})
```

## Documentation

- **Architecture**: See `/ARCHITECTURE.md` for detailed input/output specifications
- **Guide**: See `/MODULES_GUIDE.md` for detailed usage guide
- **Examples**: See `/examples/complete_workflow_modules.py` for full workflow

## Design Principles

Each module follows these principles:

1. **Clear I/O**: Standardized dictionary input and output structures
2. **Independence**: Each module can be used standalone
3. **Documentation**: Comprehensive docstrings and type hints
4. **Testability**: Easy to test with mock data
5. **Extensibility**: Easy to add new features

## Testing

Run tests for all modules:

```bash
pytest tests/test_scenario_generator.py
pytest tests/test_tax_engine.py
pytest tests/test_user_profile.py
pytest tests/test_optimizer.py
pytest tests/test_reporting.py
```

Or all at once:

```bash
pytest tests/
```

## Version

Current version: 2.0.0

## License

See main repository LICENSE file.
