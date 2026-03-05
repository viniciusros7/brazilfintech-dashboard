# =============================================================
# BrazilFintech — Fintech vs Traditional Banks
# Day 1: Data Wrangling, Cleaning & Feature Engineering
# Assessment Task 2 (15%)
# =============================================================

import pandas as pd
import numpy as np

DATA_PATH = "data/"

print("=" * 60)
print("BRAZIL FINTECH — DATA WRANGLING")
print("=" * 60)

# =============================================================
# STEP 1 — LOAD DATASETS
# =============================================================

# --- 1a. Credit Risk Dataset (Kaggle) ---
credit_raw = pd.read_csv(DATA_PATH + "credit_risk_dataset.csv")
print(f"\n✓ Credit risk dataset loaded: {credit_raw.shape[0]:,} rows x {credit_raw.shape[1]} columns")
print(f"  Columns: {credit_raw.columns.tolist()}")

# --- 1b. BCB Market Share (synthetic) ---
market_raw = pd.read_csv(DATA_PATH + "bcb_market_share.csv")
print(f"\n✓ Market share dataset loaded: {market_raw.shape[0]:,} rows x {market_raw.shape[1]} columns")
print(f"  Institutions: {market_raw['Institution'].unique().tolist()}")

# =============================================================
# STEP 2 — CLEAN CREDIT RISK DATASET
# =============================================================

print("\n--- Cleaning Credit Risk Dataset ---")

credit = credit_raw.copy()

# Check missing values
missing = credit.isnull().sum()
print(f"\n  Missing values:")
print(missing[missing > 0])

# Drop rows with missing values
credit = credit.dropna()
print(f"  Rows after dropping nulls: {len(credit):,}")

# Remove outliers
credit = credit[credit['person_age'] <= 80]
credit = credit[credit['person_age'] >= 18]
credit = credit[credit['person_emp_length'] <= 60]
credit = credit[credit['person_income'] <= 500_000]

print(f"  Rows after removing outliers: {len(credit):,}")

# =============================================================
# STEP 3 — FEATURE ENGINEERING
# =============================================================

print("\n--- Feature Engineering ---")

# Debt-to-income ratio
credit['debt_to_income'] = (credit['loan_amnt'] / credit['person_income']).round(4)

# Risk tier from loan grade
grade_risk = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7}
credit['risk_tier'] = credit['loan_grade'].map(grade_risk)

# High risk flag (grades D-G = customers traditional banks often rejected)
credit['high_risk_flag'] = (credit['risk_tier'] >= 4).astype(int)

# Income bracket
credit['income_bracket'] = pd.cut(
    credit['person_income'],
    bins=[0, 30000, 60000, 100000, 500000],
    labels=['Low', 'Medium', 'High', 'Very High']
)

# Monthly loan burden estimate
credit['monthly_burden'] = (
    credit['loan_amnt'] * (credit['loan_int_rate'] / 100 / 12) /
    (1 - (1 + credit['loan_int_rate'] / 100 / 12) ** -36)
).round(2)

print(f"  Features added: debt_to_income, risk_tier, high_risk_flag, income_bracket, monthly_burden")

print(f"\n  Default rate by loan grade:")
print(credit.groupby('loan_grade')['loan_status'].mean().round(3))

print(f"\n  Default rate high-risk (D-G): {credit[credit['high_risk_flag']==1]['loan_status'].mean():.1%}")
print(f"  Default rate low-risk  (A-C): {credit[credit['high_risk_flag']==0]['loan_status'].mean():.1%}")

# =============================================================
# STEP 4 — CLEAN MARKET SHARE DATASET
# =============================================================

print("\n--- Cleaning Market Share Dataset ---")

market = market_raw.copy()
market['Date'] = pd.to_datetime(market['Date'])
market = market.sort_values(['Institution', 'Date']).reset_index(drop=True)
market['Year'] = market['Date'].dt.year

# Fintech vs traditional totals per quarter
fintech_total = (
    market[market['Type'] == 'fintech']
    .groupby('Date')['Market_Share_Pct'].sum()
    .reset_index().rename(columns={'Market_Share_Pct': 'Fintech_Total_Share'})
)

traditional_total = (
    market[market['Type'] == 'traditional']
    .groupby('Date')['Market_Share_Pct'].sum()
    .reset_index().rename(columns={'Market_Share_Pct': 'Traditional_Total_Share'})
)

market_summary = fintech_total.merge(traditional_total, on='Date')
market_summary['Disruption_Gap'] = (
    market_summary['Traditional_Total_Share'] - market_summary['Fintech_Total_Share']
).round(3)

print(f"  Fintech share: {market_summary.iloc[0]['Fintech_Total_Share']:.1f}% (2018) -> {market_summary.iloc[-1]['Fintech_Total_Share']:.1f}% (2024)")

# =============================================================
# STEP 5 — THE SMOKING GUN
# =============================================================

print("\n--- The Smoking Gun ---")
fintech_avg_default = market[market['Type']=='fintech']['Default_Rate_Pct'].mean()
trad_avg_default    = market[market['Type']=='traditional']['Default_Rate_Pct'].mean()
print(f"  Fintechs average default rate:     {fintech_avg_default:.2f}%")
print(f"  Traditional banks default rate:    {trad_avg_default:.2f}%")
print(f"  Fintechs served riskier customers AND had lower default rates.")
print(f"  This is the power of AI credit scoring.")

# =============================================================
# STEP 6 — SAVE
# =============================================================

credit.to_csv(DATA_PATH + "credit_clean.csv", index=False)
market.to_csv(DATA_PATH + "market_clean.csv", index=False)
market_summary.to_csv(DATA_PATH + "market_summary.csv", index=False)

print(f"\n✓ credit_clean.csv saved        ({len(credit):,} rows)")
print(f"✓ market_clean.csv saved        ({len(market):,} rows)")
print(f"✓ market_summary.csv saved      ({len(market_summary):,} rows)")
print("\n" + "=" * 60)
print("DAY 1 COMPLETE — All datasets ready for modelling")
print("=" * 60)
