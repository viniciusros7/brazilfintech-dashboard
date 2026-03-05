# =============================================================
# BrazilFintech — Fintech vs Traditional Banks
# Day 2: Analytics Models
# Assessment Task 3 (25%)
# =============================================================

import pandas as pd
import numpy as np
import pickle
import warnings
warnings.filterwarnings('ignore')

DATA_PATH = "data/"

print("=" * 60)
print("BRAZIL FINTECH — MODEL TRAINING")
print("=" * 60)

# =============================================================
# LOAD CLEAN DATA
# =============================================================

credit = pd.read_csv(DATA_PATH + "credit_clean.csv")
market = pd.read_csv(DATA_PATH + "market_clean.csv")
market_summary = pd.read_csv(DATA_PATH + "market_summary.csv")

market['Date'] = pd.to_datetime(market['Date'])
market_summary['Date'] = pd.to_datetime(market_summary['Date'])

print(f"\n✓ Data loaded: {len(credit):,} credit records, {len(market)} market rows")

# =============================================================
# MODEL 1 — RANDOM FOREST CLASSIFIER (Credit Default Prediction)
# This is the AI credit scoring engine
# =============================================================

print("\n--- Model 1: Random Forest Credit Scorer ---")

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score

# Prepare features
credit_model = credit.copy()

# Encode categorical columns
le_home = LabelEncoder()
le_intent = LabelEncoder()
le_grade = LabelEncoder()
le_default = LabelEncoder()

credit_model['home_enc']    = le_home.fit_transform(credit_model['person_home_ownership'])
credit_model['intent_enc']  = le_intent.fit_transform(credit_model['loan_intent'])
credit_model['grade_enc']   = le_grade.fit_transform(credit_model['loan_grade'])
credit_model['default_enc'] = le_default.fit_transform(credit_model['cb_person_default_on_file'])

# Feature set
features = [
    'person_age', 'person_income', 'person_emp_length',
    'loan_amnt', 'loan_int_rate', 'loan_percent_income',
    'cb_person_cred_hist_length', 'debt_to_income',
    'risk_tier', 'monthly_burden',
    'home_enc', 'intent_enc', 'grade_enc', 'default_enc'
]

X = credit_model[features]
y = credit_model['loan_status']

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"  Training on {len(X_train):,} records, testing on {len(X_test):,}")

# Train model
rf = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train, y_train)

# Evaluate
y_pred = rf.predict(X_test)
y_prob = rf.predict_proba(X_test)[:, 1]
auc = roc_auc_score(y_test, y_prob)

print(f"\n  Model Performance:")
print(f"    AUC-ROC Score:  {auc:.3f}")
print(f"    Accuracy:       {(y_pred == y_test).mean():.1%}")
print(f"\n  Classification Report:")
print(classification_report(y_test, y_pred, target_names=['No Default', 'Default']))

# Feature importance
importance_df = pd.DataFrame({
    'feature': features,
    'importance': rf.feature_importances_
}).sort_values('importance', ascending=False)

print(f"  Top 5 most important features:")
print(importance_df.head(5).to_string(index=False))

# Save model and encoders
with open(DATA_PATH + "rf_model.pkl", 'wb') as f:
    pickle.dump(rf, f)
with open(DATA_PATH + "encoders.pkl", 'wb') as f:
    pickle.dump({
        'home': le_home,
        'intent': le_intent,
        'grade': le_grade,
        'default': le_default,
        'features': features
    }, f)

print(f"\n✓ Random Forest saved → rf_model.pkl")

# =============================================================
# MODEL 2 — K-MEANS CLUSTERING (Customer Segmentation)
# Segments borrowers into risk profiles
# =============================================================

print("\n--- Model 2: K-Means Customer Segmentation ---")

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Features for clustering
cluster_features = [
    'person_age', 'person_income', 'loan_amnt',
    'loan_int_rate', 'debt_to_income', 'risk_tier', 'loan_status'
]

cluster_data = credit[cluster_features].copy()

# Scale features
scaler = StandardScaler()
cluster_scaled = scaler.fit_transform(cluster_data)

# Fit K-Means with 3 clusters
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
credit['cluster'] = kmeans.fit_predict(cluster_scaled)

# Label clusters by default rate
cluster_default = credit.groupby('cluster')['loan_status'].mean()
cluster_order = cluster_default.sort_values().index.tolist()

cluster_labels = {}
label_names = ['Low Risk', 'Medium Risk', 'High Risk']
for i, cluster_id in enumerate(cluster_order):
    cluster_labels[cluster_id] = label_names[i]

credit['risk_segment'] = credit['cluster'].map(cluster_labels)

# Summary
print(f"\n  Customer Segments:")
summary = credit.groupby('risk_segment').agg(
    Count=('loan_status', 'count'),
    Default_Rate=('loan_status', 'mean'),
    Avg_Income=('person_income', 'mean'),
    Avg_Loan=('loan_amnt', 'mean'),
    Avg_Interest=('loan_int_rate', 'mean')
).round(3)
print(summary.to_string())

# Save
credit.to_csv(DATA_PATH + "credit_clustered.csv", index=False)
with open(DATA_PATH + "kmeans_model.pkl", 'wb') as f:
    pickle.dump({'kmeans': kmeans, 'scaler': scaler, 'labels': cluster_labels}, f)

print(f"\n✓ K-Means saved → kmeans_model.pkl")

# =============================================================
# MODEL 3 — PROPHET TIME SERIES (Market Share Forecast)
# Forecasts fintech market share growth to 2027
# =============================================================

print("\n--- Model 3: Prophet Market Share Forecast ---")

from prophet import Prophet

# Prepare Prophet format (requires 'ds' and 'y' columns)
prophet_df = market_summary[['Date', 'Fintech_Total_Share']].copy()
prophet_df.columns = ['ds', 'y']

# Train Prophet
m = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=False,
    daily_seasonality=False,
    interval_width=0.95
)
m.fit(prophet_df)

# Forecast 12 quarters ahead (3 years to end of 2027)
future = m.make_future_dataframe(periods=12, freq='QS')
forecast = m.predict(future)

# Save forecast
forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_csv(
    DATA_PATH + "fintech_forecast.csv", index=False
)

# Print key predictions
future_only = forecast[forecast['ds'] > prophet_df['ds'].max()]
print(f"\n  Fintech market share forecast:")
for _, row in future_only.iloc[::4].iterrows():
           print(f"    {row['ds'].strftime('%Y-%m')}: "    
          f"{row['yhat']:.1f}% (range: {row['yhat_lower']:.1f}% - {row['yhat_upper']:.1f}%)")

print(f"\n✓ Prophet forecast saved → fintech_forecast.csv")

# =============================================================
# MODEL 4 — RECOMMENDATION ENGINE
# Recommends credit decision based on customer profile
# =============================================================

print("\n--- Model 4: Credit Recommendation Engine ---")

def recommend_credit(age, income, loan_amount, loan_intent,
                     interest_rate, emp_length, credit_history,
                     home_ownership='RENT', prior_default='N'):
    """
    AI-powered credit recommendation engine.
    Returns: decision, default probability, risk segment, reasoning
    """
    with open(DATA_PATH + "rf_model.pkl", 'rb') as f:
        model = pickle.load(f)
    with open(DATA_PATH + "encoders.pkl", 'rb') as f:
        enc = pickle.load(f)

    # Encode inputs
    try:
        home_enc    = enc['home'].transform([home_ownership])[0]
    except:
        home_enc = 0
    try:
        intent_enc  = enc['intent'].transform([loan_intent])[0]
    except:
        intent_enc = 0

    # Estimate grade from interest rate
    if interest_rate < 8:    grade = 'A'
    elif interest_rate < 11: grade = 'B'
    elif interest_rate < 14: grade = 'C'
    elif interest_rate < 17: grade = 'D'
    elif interest_rate < 20: grade = 'E'
    else:                    grade = 'F'

    try:
        grade_enc = enc['grade'].transform([grade])[0]
    except:
        grade_enc = 2

    try:
        default_enc = enc['default'].transform([prior_default])[0]
    except:
        default_enc = 0

    # Calculate derived features
    debt_to_income    = loan_amount / income
    loan_pct_income   = loan_amount / income
    risk_tier         = {'A':1,'B':2,'C':3,'D':4,'E':5,'F':6,'G':7}.get(grade, 3)
    monthly_burden    = loan_amount * (interest_rate/100/12) / (1-(1+interest_rate/100/12)**-36)

    features = [[
        age, income, emp_length, loan_amount, interest_rate,
        loan_pct_income, credit_history, debt_to_income,
        risk_tier, monthly_burden,
        home_enc, intent_enc, grade_enc, default_enc
    ]]

    prob_default = model.predict_proba(features)[0][1]

    # Decision logic
    if prob_default < 0.20:
        decision = "✅ APPROVE"
        reasoning = "Low default risk. Strong candidate."
    elif prob_default < 0.40:
        decision = "⚠️ APPROVE WITH CONDITIONS"
        reasoning = "Moderate risk. Consider lower loan amount or higher collateral."
    else:
        decision = "❌ DECLINE"
        reasoning = "High default risk. Does not meet credit criteria."

    return {
        'decision': decision,
        'default_probability': f"{prob_default:.1%}",
        'risk_grade': grade,
        'reasoning': reasoning,
        'debt_to_income': f"{debt_to_income:.2f}",
        'monthly_burden': f"€{monthly_burden:.0f}/month"
    }

# Test the engine with 3 example profiles
print(f"\n  Testing recommendation engine with 3 profiles:\n")

profiles = [
    {"name": "Profile A — Young professional",
     "age": 28, "income": 55000, "loan_amount": 8000,
     "loan_intent": "EDUCATION", "interest_rate": 9.5,
     "emp_length": 3, "credit_history": 4},
    {"name": "Profile B — Mid-career, higher risk",
     "age": 42, "income": 35000, "loan_amount": 20000,
     "loan_intent": "PERSONAL", "interest_rate": 16.0,
     "emp_length": 8, "credit_history": 10},
    {"name": "Profile C — Traditional bank would reject",
     "age": 24, "income": 22000, "loan_amount": 15000,
     "loan_intent": "VENTURE", "interest_rate": 19.5,
     "emp_length": 1, "credit_history": 2},
]

for p in profiles:
    result = recommend_credit(
        p['age'], p['income'], p['loan_amount'],
        p['loan_intent'], p['interest_rate'],
        p['emp_length'], p['credit_history']
    )
    print(f"  {p['name']}")
    print(f"    Decision:     {result['decision']}")
    print(f"    Default prob: {result['default_probability']}")
    print(f"    Reasoning:    {result['reasoning']}\n")

print(f"✓ Recommendation engine ready")

# =============================================================
# SUMMARY
# =============================================================

print("\n" + "=" * 60)
print("DAY 2 COMPLETE — All 4 models trained and saved")
print("=" * 60)
print(f"""
  Model 1: Random Forest Classifier  → rf_model.pkl
  Model 2: K-Means Clustering        → kmeans_model.pkl
  Model 3: Prophet Forecast          → fintech_forecast.csv
  Model 4: Recommendation Engine     → built into dashboard

  Assessment Task 3 (25%) — COMPLETE
""")
