# -*- coding: utf-8 -*-
"""
Run once to:
  1. Generate 50,000-record synthetic dataset with interaction effects
  2. Train and compare 6 ML models (DT, LR, ExtraTrees, RF, GB, XGBoost)
  3. Save the best tuned model and full metrics to model/
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from data.generate_data import generate_synthetic_data
from model.risk_model import train_models, _XGBOOST_AVAILABLE

DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'accidents.csv')

SEP = "=" * 68

print(SEP)
print("  RiskGuard AI -- ML Model Training Pipeline")
print("  Pearson BTEC Level 6 | Independent Project")
print(SEP)

print("\n[1/3] Generating synthetic dataset (30,000 records) ...")
df = generate_synthetic_data(n_samples=30000)
df.to_csv(DATA_PATH, index=False)
print(f"  Saved   : {len(df):,} records -> {DATA_PATH}")
print(f"  Features: 12 input  +  6 engineered interaction features")
print(f"  XGBoost : {'available [OK]' if _XGBOOST_AVAILABLE else 'not installed (pip install xgboost)'}")
print("\n  Class distribution:")
dist = df['risk_category'].value_counts()
for cat in ['Low', 'Medium', 'High', 'Very High']:
    cnt = dist.get(cat, 0)
    pct = cnt / len(df) * 100
    bar = '#' * int(pct / 2)
    print(f"    {cat:<12} {cnt:>6,}  ({pct:4.1f}%)  {bar}")

print(f"\n[2/3] Training 6 models + GridSearchCV hyperparameter tuning ...")
print(f"      (this takes 3-6 minutes -- all CPU cores are used)\n")
pipeline, metrics = train_models(df)

best = metrics['best_model']
res  = metrics['all_results']

print(f"\n[3/3] Results summary")
print(SEP)
header = f"  {'Model':<30}  {'Acc':>6}  {'CV':>6}  {'F1':>6}  {'ROC-AUC':>8}  {'Type'}"
print(header)
print("  " + "-" * 64)
for name, r in res.items():
    star  = " [BEST]" if name == best else "  "
    kind  = "Tuned" if r.get('tuned') else "Baseline"
    roc   = f"{r['roc_auc']:.4f}" if r.get('roc_auc') else "  N/A  "
    print(f"  {name:<30}  {r['accuracy']*100:5.1f}%  {r['cv_accuracy']*100:5.1f}%  "
          f"{(r['f1'] or 0)*100:5.1f}%  {roc:>8}  {kind}{star}")
print(SEP)
print(f"  BEST MODEL : {best}")
print(f"  Accuracy   : {metrics['best_accuracy']*100:.2f}%")
best_roc = res[best].get('roc_auc')
if best_roc:
    print(f"  ROC-AUC    : {best_roc:.4f}")
print(f"  Train/Test : {metrics['train_size']:,} / {metrics['test_size']:,} samples")
print(f"  Features   : {metrics['n_engineered_features']} total (12 input + 6 engineered)")
print(SEP)
print("\n  Model  -> model/risk_model.pkl")
print("  Metrics -> model/model_metrics.pkl")
print("\n  Start the app:")
print("    python app.py   or   run.bat")
print("\n  Open: http://127.0.0.1:5000\n")
