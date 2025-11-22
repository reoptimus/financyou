# FinancYou Web Interface

Interactive Streamlit dashboard for comprehensive financial planning and portfolio optimization.

## Features

- 📊 **Interactive Input Forms**: Capture user profile, financial situation, and investment preferences
- 💼 **Portfolio Optimization**: Real-time portfolio optimization with multiple objectives
- 📈 **Scenario Analysis**: Monte Carlo simulations across economic scenarios
- 💰 **Tax Optimization**: Multi-jurisdiction tax treatment (US, FR, UK)
- 🎯 **Goal Tracking**: Goal achievement probability analysis
- 📄 **Comprehensive Reports**: Detailed HTML reports with visualizations

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Running the Dashboard

```bash
# From the web_ui directory
streamlit run app.py

# Or from project root
streamlit run web_ui/app.py
```

The dashboard will open in your default browser at `http://localhost:8501`

## Usage

### 1. **Personal Information**
   - Enter age, retirement age, life expectancy
   - Select country and currency

### 2. **Financial Situation**
   - Current savings and annual income
   - Annual expenses
   - Debt (mortgage, student loans, etc.)

### 3. **Investment Preferences**
   - Risk tolerance (conservative/moderate/aggressive)
   - Investment goals (retirement/wealth/income/education)
   - Time horizon
   - ESG preferences
   - Liquidity needs

### 4. **Investment Constraints**
   - Maximum equity allocation
   - Minimum bond allocation
   - Rebalancing frequency

### 5. **Contribution Schedule**
   - Monthly contribution amount
   - Annual increase rate
   - Account type (taxable/tax-deferred/tax-free)

### 6. **Run Analysis**
   - Click "Run Analysis" to generate comprehensive financial plan
   - View results across multiple tabs:
     - **Overview**: Key metrics and summary
     - **Portfolio**: Optimal asset allocation
     - **Projections**: Future portfolio value projections
     - **Goals**: Goal achievement analysis
     - **Report**: Comprehensive detailed report

## Features in Detail

### Tax Optimization
Choose from multiple tax jurisdictions:
- **US**: Federal and state tax treatment, 401(k)/IRA/Roth accounts
- **France**: PFU flat tax, PEA accounts, wealth tax (IFI)
- **UK**: Income tax, capital gains, ISA accounts

### Portfolio Optimization Objectives
- Maximum Sharpe Ratio (default)
- Minimum Volatility
- Equal Weight
- Target Return
- Risk Parity

### Scenario Generation
- Configurable number of Monte Carlo scenarios
- Stochastic economic modeling
- Multi-asset class projections (stocks, bonds, real estate)

## Example Profiles

Load pre-configured example profiles:
- **Aggressive Investor**: Age 28, high risk tolerance
- **Conservative Investor**: Age 55, conservative risk profile

## Deployment

### Local Deployment
```bash
streamlit run app.py
```

### Production Deployment

#### Streamlit Cloud
1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Deploy directly from repository

#### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t financyou-web .
docker run -p 8501:8501 financyou-web
```

## Architecture

The web UI integrates with the FinancYou modular system:

```
User Input → Streamlit Forms
    ↓
Profile Processing (Module 3)
    ↓
Scenario Generation (Module 1)
    ↓
Tax Engine (Module 2)
    ↓
Portfolio Optimization (Module 4)
    ↓
Report Generation (Module 5)
    ↓
Interactive Dashboard Display
```

## Customization

### Modify Optimization Settings
Edit `run_analysis()` function in `app.py`:
- Change number of scenarios
- Add custom optimization objectives
- Modify tax allocation defaults

### Add Custom Visualizations
Extend the `display_*()` functions:
- `display_overview()`: Summary metrics
- `display_portfolio()`: Portfolio charts
- `display_projections()`: Time series projections
- `display_goals()`: Goal analysis
- `display_report()`: Full report rendering

### Custom Themes
Create `.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

## Troubleshooting

### Port Already in Use
```bash
streamlit run app.py --server.port=8502
```

### Module Import Errors
Ensure you're running from the correct directory and the parent package is in PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
streamlit run app.py
```

### Performance Issues
Reduce number of scenarios in sidebar settings (default: 100)

## Support

For issues or questions:
- Check the main FinancYou documentation
- Review test files for usage examples
- See `examples/complete_pipeline_with_files.py` for command-line usage

## License

Same as FinancYou main project.
