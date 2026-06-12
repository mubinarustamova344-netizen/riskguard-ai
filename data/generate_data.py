import numpy as np
import pandas as pd
import os


def generate_synthetic_data(n_samples=50000, seed=42):
    np.random.seed(seed)

    # ── Raw features ───────────────────────────────────────────────────────────
    driver_age          = np.random.randint(18, 81, n_samples)
    driving_experience  = np.clip(driver_age - 18 - np.random.randint(0, 6, n_samples), 0, 60)
    annual_mileage      = np.random.randint(2000, 60000, n_samples)
    vehicle_age         = np.random.randint(0, 26, n_samples)

    # More realistic (heavily right-skewed) accident/violation distributions
    previous_accidents  = np.random.choice(
        [0, 1, 2, 3, 4, 5],
        n_samples, p=[0.58, 0.22, 0.11, 0.05, 0.03, 0.01]
    )
    traffic_violations  = np.random.choice(
        [0, 1, 2, 3, 4, 5, 6],
        n_samples, p=[0.52, 0.23, 0.13, 0.07, 0.03, 0.01, 0.01]
    )
    night_driving_pct   = np.random.randint(0, 101, n_samples)
    credit_score        = np.clip(np.random.normal(680, 110, n_samples), 300, 850).astype(int)

    vehicle_types = np.random.choice(
        ['sedan', 'suv', 'sports', 'truck', 'van', 'motorcycle'],
        n_samples, p=[0.35, 0.25, 0.12, 0.12, 0.10, 0.06]
    )
    locations = np.random.choice(
        ['urban', 'suburban', 'rural', 'highway'],
        n_samples, p=[0.40, 0.30, 0.18, 0.12]
    )
    marital_status = np.random.choice(
        ['single', 'married', 'divorced'],
        n_samples, p=[0.38, 0.48, 0.14]
    )
    gender = np.random.choice(['male', 'female'], n_samples, p=[0.52, 0.48])

    # ── Domain-driven risk score ───────────────────────────────────────────────
    score = np.zeros(n_samples, dtype=float)

    # Age factor: U-shaped
    score += np.where(driver_age < 25, (25 - driver_age) * 1.8,
             np.where(driver_age > 65, (driver_age - 65) * 1.2, 0.0))

    # Experience factor
    score += np.where(driving_experience < 2,  18.0,
             np.where(driving_experience < 5,  10.0,
             np.where(driving_experience < 10,  4.0, 0.0)))

    # Accident history (strongest predictor)
    score += previous_accidents * 14.0

    # Traffic violations
    score += traffic_violations * 5.0

    # Mileage
    score += (annual_mileage - 2000) / 58000 * 12.0

    # Night driving
    score += night_driving_pct * 0.12

    # Vehicle type
    vtype_map = {'sedan': 0, 'van': 0, 'suv': 3, 'truck': 4, 'sports': 12, 'motorcycle': 18}
    score += np.array([vtype_map[v] for v in vehicle_types])

    # Vehicle age
    score += np.where(vehicle_age > 15, 6.0, np.where(vehicle_age > 10, 3.0, 0.0))

    # Location
    loc_map = {'suburban': 0, 'rural': 2, 'highway': 4, 'urban': 7}
    score += np.array([loc_map[l] for l in locations])

    # Credit score (inversely related)
    score += np.clip((700 - credit_score) / 40.0, -5.0, 10.0)

    # Marital status
    ms_map = {'married': -2, 'divorced': 2, 'single': 3}
    score += np.array([ms_map[m] for m in marital_status])

    # Gender
    score += np.where(gender == 'male', 2.0, 0.0)

    # ── Interaction effects (make patterns more complex for ML) ────────────────

    # Young driver + high-risk vehicle → compound penalty
    youth_vehicle = np.isin(vehicle_types, ['sports', 'motorcycle']) & (driver_age < 25)
    score += np.where(youth_vehicle, 9.0, 0.0)

    # Low experience + accident history → compounding risk
    exp_acc = (driving_experience < 3) & (previous_accidents > 0)
    score += np.where(exp_acc, previous_accidents * 5.0, 0.0)

    # Urban + high night driving → elevated risk
    urban_night = (locations == 'urban') & (night_driving_pct > 40)
    score += np.where(urban_night, (night_driving_pct - 40) * 0.1, 0.0)

    # Multiple violations + accident → flagged profile
    risk_combo = (previous_accidents > 1) & (traffic_violations > 2)
    score += np.where(risk_combo, 8.0, 0.0)

    # Old vehicle + high mileage → mechanical risk
    old_high = (vehicle_age > 12) & (annual_mileage > 30000)
    score += np.where(old_high, 4.0, 0.0)

    # Poor credit + accidents → compound financial/behavioural risk
    credit_acc = (credit_score < 580) & (previous_accidents > 0)
    score += np.where(credit_acc, 5.0, 0.0)

    # ── Heteroscedastic noise (higher variance for higher-risk profiles) ───────
    base_noise = np.random.normal(0, 3.5, n_samples)
    high_risk_noise = np.where(score > 50, np.random.normal(0, 2.0, n_samples), 0.0)
    score += base_noise + high_risk_noise

    # ── Normalise to 0–100 ─────────────────────────────────────────────────────
    score = np.clip((score - score.min()) / (score.max() - score.min()) * 100, 0.0, 100.0)

    # ── Risk category (percentile-based for balanced training data) ────────────
    # Targets: ~35% Low, ~35% Medium, ~20% High, ~10% Very High
    p35 = np.percentile(score, 35)
    p70 = np.percentile(score, 70)
    p90 = np.percentile(score, 90)

    def categorize(s):
        if s < p35: return 'Low'
        if s < p70: return 'Medium'
        if s < p90: return 'High'
        return 'Very High'

    risk_category      = np.array([categorize(s) for s in score])
    pm_map = {'Low': 1.0, 'Medium': 1.35, 'High': 1.75, 'Very High': 2.30}
    premium_multiplier = np.array([pm_map[c] for c in risk_category])
    claim_prob         = np.clip(1 / (1 + np.exp(-0.08 * (score - 50))), 0.02, 0.95)

    df = pd.DataFrame({
        'driver_age':          driver_age,
        'driving_experience':  driving_experience,
        'annual_mileage':      annual_mileage,
        'vehicle_age':         vehicle_age,
        'previous_accidents':  previous_accidents,
        'traffic_violations':  traffic_violations,
        'night_driving_pct':   night_driving_pct,
        'credit_score':        credit_score,
        'vehicle_type':        vehicle_types,
        'primary_location':    locations,
        'marital_status':      marital_status,
        'gender':              gender,
        'risk_score':          np.round(score, 2),
        'risk_category':       risk_category,
        'premium_multiplier':  premium_multiplier,
        'claim_probability':   np.round(claim_prob, 4),
    })
    return df


if __name__ == '__main__':
    df = generate_synthetic_data()
    out = os.path.join(os.path.dirname(__file__), 'accidents.csv')
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} records to {out}")
    print(df['risk_category'].value_counts())
