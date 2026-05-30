# -*- coding: utf-8 -*-
"""
Run this script once to:
  1. Generate synthetic training data (12,000 records)
  2. Train and evaluate four classifiers
  3. Save the best model and metrics to model/
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from data.generate_data import generate_synthetic_data
from model.risk_model import train_models

DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'accidents.csv')

print("=" * 60)
print("  Risk Assessment Model -- Setup Script")
print("=" * 60)

print("\n[1/3] Generating synthetic dataset ...")
df = generate_synthetic_data(n_samples=12000)
df.to_csv(DATA_PATH, index=False)
print(f"  Saved {len(df)} records to {DATA_PATH}")
print("  Category distribution:")
print(df['risk_category'].value_counts().to_string(index=True))

print("\n[2/3] Training and evaluating models ...")
pipeline, metrics = train_models(df)

print("\n[3/3] Setup complete!")
print(f"  Best model  : {metrics['best_model']}")
print(f"  Accuracy    : {metrics['best_accuracy']:.4f}")
print(f"  Train size  : {metrics['train_size']}")
print(f"  Test size   : {metrics['test_size']}")
print("\nYou can now start the application with:")
print("  python app.py")
print("\nThen open your browser at: http://127.0.0.1:5000")
