# FinancYou Modules

This directory holds the pipeline GSE → GSE+ → GSE++ → Markowitz → wealth
projection → report. The unit of optimisation is the **placement** (a support
held in a tax wrapper, e.g. "PEA actions" or "assurance-vie fonds euros"); see
`docs/adr/0002-le-placement-est-l-unite-d-optimisation.md`.

## Module Organization

```
modules/
├── scenario_generator.py   # GSE: stock, bond, rate and inflation scenarios
├── placements.py           # GSE+: annual return of each placement, net of annual fees
├── net_returns.py          # GSE++: return net of fees and exit tax, per scenario × horizon
├── user_profile.py         # User profile and contribution/withdrawal time series
├── placement_optimizer.py  # Markowitz on GSE++ moments, under wrapper caps
├── wealth_simulation.py    # Projection of the user's actual flows
├── placement_plan.py       # Orchestration of the above, report-ready output
└── reporting.py            # Charts and reports
```

Placements and their fees come from a catalogue,
`investment_calculator/placement_catalogs/<id>.json` (`fr-2026`: CTO actions,
CTO obligations, PEA actions, AV fonds euros, AV UC actions, Livret A). Taxes
come from the tax regime the catalogue names
(`investment_calculator/tax_regimes/fr-2026.json`), applied per wrapper by
`investment_calculator/wrapper_tax.py`. No rate lives in the code.

## Pipeline

```
GSE (scenario_generator)
    ↓ stock_return, bond_return, interest_rate, inflation
GSE+ (placements.build_gross_placements)
    ↓ annual return per placement, before tax
GSE++ (net_returns.build_net_returns)      ← TaxProfile (amount invested, couple, seniority)
    ↓ net multiple per scenario × horizon × placement
Markowitz (placement_optimizer.optimize_horizon)   ← placement_constraints (wrapper caps)
    ↓ weights per placement
Projection (wealth_simulation.simulate_wealth)     ← user_profile flows
    ↓
Report (reporting.ReportGenerator)
```

`placement_plan.plan_placements` chains GSE+ to the projection in one call.

## Quick Start

```python
from investment_calculator.modules import reporting, scenario_generator, user_profile
from investment_calculator.modules.placement_plan import plan_placements
from investment_calculator.placement_catalog import load_placement_catalog

scenarios = scenario_generator.ScenarioGenerator(random_seed=42).generate({
    'num_scenarios': 1000, 'time_horizon': 30, 'timestep': 1.0, 'use_stochastic': False,
})
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
catalog = load_placement_catalog('fr-2026')
results = plan_placements(
    scenarios['scenarios'], catalog, profile['investment_time_series'],
    horizon=30, objective='mean_variance', risk_aversion=5.0,
    risk_free_placement='livret_a', goal_amount=500_000,
)
report = reporting.ReportGenerator().generate({
    'optimization_results': results, 'report_config': {'format': 'html'},
})
```

Objectives: `mean_variance` (needs `risk_aversion`), `min_volatility`,
`target_return` (needs `target_return`), `max_sharpe` (needs
`risk_free_placement`). Without a reference placement the Sharpe ratio is not
computed and is `None`.

`results` contains `optimal_portfolio` (weights, `expected_return`,
`expected_volatility`, `sharpe_ratio`, `max_drawdown`, `horizon`…),
`efficient_frontier`, `simulation_results` (wealth paths before exit tax,
terminal wealth net of tax, statistics), `constraints_explanation`,
`known_gaps` and, when a goal is given, `goal_analysis`.

## Documentation

- **Architecture**: `/ARCHITECTURE.md`
- **Guide**: `/MODULES_GUIDE.md`
- **Examples**: `/examples/complete_pipeline_with_files.py`, `/examples/complete_workflow_modules.py`

## Testing

```bash
pytest tests/test_placements.py tests/test_net_returns.py tests/test_placement_optimizer.py \
       tests/test_wealth_simulation.py tests/test_placement_plan.py
pytest tests/   # everything
```
