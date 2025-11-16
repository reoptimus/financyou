# Legacy Files

This directory contains legacy R scripts and data files from earlier versions of the project. These files are kept for reference and historical purposes.

## Directory Structure

### R_scripts/ (58 files)
R scripts for economic scenario generation and financial modeling, including:
- `ActionBS_*.R` - Action Black-Scholes models
- `Calib_*.R` - Calibration scripts for various models
- `HullWhite_*.R` - Hull-White interest rate models
- `ImmoBS_*.R` - Real estate (Immobilier) Black-Scholes models
- `Assembl_*.R` - Assembly/aggregation scripts
- `Deflator_*.R` - Deflator calculations
- And various other financial modeling scripts

### R_data/ (17 files)
R data files (.Rda format) containing:
- `Tr-*.Rda` - Transition matrices
- `Epsilon.Rda` - Epsilon parameters
- `PMR.Rda` - PMR (Portfolio Management Rules) data
- `P0t.Rda` - P0t parameters
- And other calibration/model data

### excel_files/ (11 files)
Excel files including:
- `EIOPA_*.xlsx` - EIOPA (European Insurance and Occupational Pensions Authority) data
- `Call_V1*.xlsx` - Call option models
- `Table_*.xlsx` - Various data tables
- `Corr_ResidAhlgrim_*.xlsx` - Correlation matrices
- And other reference data

### csv_files/ (13 files)
CSV and text files including:
- `Swaptions_*.csv` - Swaption market data
- `Bond S&P Matrice transition.csv` - Bond transition matrices
- `Exemple*.csv` - Example data files
- `Rdt_immo_*.txt` - Real estate return data
- And other data files

## Notes

These files represent earlier work on:
- Economic Scenario Generation (ESG)
- Interest rate modeling (Hull-White, Black-Scholes)
- Asset pricing and calibration
- Portfolio management

The current Python package (`time_series_slicer` and `investment_calculator`) provides modern implementations of financial modeling and portfolio optimization that supersede these legacy scripts.

## Migration Status

These files are **not used** by the current Python package. They are preserved for:
1. Historical reference
2. Validation of new implementations
3. Understanding original modeling approaches

If you need to use any of these files, you'll need R and appropriate R packages installed.
