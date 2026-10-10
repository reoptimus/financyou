# Input Files for FinancYou Pipeline

This directory contains JSON configuration files for running the complete FinancYou pipeline.

## Files Overview

| File | Purpose | Used By |
|------|---------|---------|
| `scenario_config.json` | Economic scenario parameters | Module 1 (GSE) |
| `user_profile_conservative.json` | Conservative investor (age 55) | Module 3 (User Profile) |
| `user_profile_aggressive.json` | Aggressive investor (age 28) | Module 3 (User Profile) |
| `optimization_config.json` | Catalogue, objective and goal | Module 4 (Optimizer) |

Taxes and placements are not example files: they are model data, in
`investment_calculator/tax_regimes/` and `investment_calculator/placement_catalogs/`.

## File Descriptions

### scenario_config.json

Controls how economic scenarios are generated.

**Key Parameters**:
- `num_scenarios` (1000): Number of Monte Carlo scenarios to generate
- `time_horizon` (30): Years to project into the future
- `timestep` (1.0): 1.0 = annual, 0.5 = semi-annual, 0.083 = monthly
- `use_stochastic` (false): Use advanced stochastic models (slower) or simple models (faster)
- `currency` (USD): Currency for calibration
- `economic_params`: Override default economic assumptions

**When to Edit**:
- Change number of scenarios for more/less precision
- Adjust time horizon for different planning periods
- Modify economic assumptions for sensitivity analysis

---

### user_profile_conservative.json

Conservative investor approaching retirement.

**Profile**:
- Age: 55 years old
- Retirement: Age 65 (10 years away)
- Current savings: $500,000
- Income: $120,000/year
- Risk tolerance: Conservative
- Max equity: 50%
- Min bonds: 40% (equity and bond limits are not applied by the optimiser yet)

**Contribution**:
- $2,000/month for next 10 years
- 2% annual increase

**When to Use**:
- Modeling older investors
- Conservative strategies
- Pre-retirement planning

---

### user_profile_aggressive.json

Aggressive young investor building wealth.

**Profile**:
- Age: 28 years old
- Retirement: Age 60 (32 years away)
- Current savings: $25,000
- Income: $85,000/year
- Student loans: $35,000
- Risk tolerance: Aggressive
- Max equity: 95%
- Min bonds: 5% (equity and bond limits are not applied by the optimiser yet)

**Contribution**:
- Phase 1: $750/month (years 1-15, 4% annual increase)
- Phase 2: $1,500/month (years 16-32, 3% annual increase)

**When to Use**:
- Modeling young investors
- Aggressive growth strategies
- Long-term wealth building

---

### optimization_config.json

Portfolio optimization parameters (Markowitz on GSE++, see
`docs/adr/0002-le-placement-est-l-unite-d-optimisation.md`).

**Key Parameters**:
- `placement_catalog` (`fr-2026`): placements, fees, tax regime and wrapper caps
- `optimization_objective`: method to use
  - `mean_variance`: maximise mean − λ/2 × variance, λ = `optimization_params.risk_aversion`
  - `min_volatility`: minimise risk
  - `target_return`: minimise risk for `optimization_params.target_return`
  - `max_sharpe`: maximise the Sharpe ratio against `risk_free_placement`
- `risk_free_placement` (`livret_a`): reference placement of the Sharpe ratio
- `goal_amount`: target wealth at the horizon, net of exit tax

The horizon is the profile's, capped by the scenarios' duration.

**When to Edit**:
- Try different optimization objectives or risk aversion
- Change target wealth goal

---

## Usage

### Running with Default Files

```bash
python examples/complete_pipeline_with_files.py
```

This uses:
- `scenario_config.json`
- `user_profile_aggressive.json`
- `optimization_config.json`

### Customizing the Run

1. **Edit configuration files** in this directory
2. **Run the pipeline**:
   ```bash
   python examples/complete_pipeline_with_files.py
   ```
3. **Check outputs** in `outputs/` directory

### Example: Conservative Investor

In `complete_pipeline_with_files.py`, change:
```python
user_profile_data = load_json_config('user_profile_aggressive.json')
```
to:
```python
user_profile_data = load_json_config('user_profile_conservative.json')
```

---

## Creating Your Own Profile

1. **Copy an existing file**:
   ```bash
   cp user_profile_aggressive.json user_profile_custom.json
   ```

2. **Edit your profile**:
   - Change age, income, savings
   - Adjust risk tolerance
   - Modify contribution schedule

3. **Update the pipeline** to use your profile:
   ```python
   user_profile_data = load_json_config('user_profile_custom.json')
   ```

4. **Run**:
   ```bash
   python examples/complete_pipeline_with_files.py
   ```

---

## Validation

All input files are validated when loaded:
- Age must be 18-100
- Retirement age must be > current age
- Contribution amounts must be positive
- Allocation percentages must sum to 1.0

If validation fails, you'll see warnings in the output.

---

## Tips

1. **Start with default files** to understand the pipeline
2. **Make small changes** one parameter at a time
3. **Compare results** before/after changes
4. **Save custom profiles** for different scenarios
5. **Use version control** to track changes

---

## Support

For questions about:
- File format: See `COMPLETE_GUIDE.md`
- Parameter meanings: See `ARCHITECTURE.md`
- Module details: See `MODULES_GUIDE.md`

---

**Last Updated**: 2026-10-10
