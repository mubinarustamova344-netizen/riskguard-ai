import numpy as np
import pandas as pd
import os

def generate_synthetic_data(n_samples=12000, seed=42):
    np.random.seed(seed)

    # --- Raw features ---
    driver_age = np.random.randint(18, 81, n_samples)
    driving_experience = np.clip(driver_age - 18 - np.random.randint(0, 5, n_samples), 0, 60)
    annual_mileage = np.random.randint(3000, 55000, n_samples)
    vehicle_age = np.random.randint(0, 26, n_samples)
    previous_accidents = np.random.choice([0, 1, 2, 3, 4], n_samples,
                                          p=[0.55, 0.25, 0.12, 0.05, 0.03])
    traffic_violations = np.random.choice([0, 1, 2, 3, 4, 5], n_samples,
                                          p=[0.50, 0.25, 0.14, 0.07, 0.03, 0.01])
    night_driving_pct = np.random.randint(0, 101, n_samples)
    credit_score = np.clip(np.random.normal(680, 100, n_samples), 300, 850).astype(int)

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

    # --- Risk score calculation (domain-driven) ---
    score = np.zeros(n_samples, dtype=float)

    # Age factor: U-shaped — very young and very old are riskier
    age_factor = np.where(driver_age < 25, (25 - driver_age) * 1.8,
                 np.where(driver_age > 65, (driver_age - 65) * 1.2, 0))
    score += age_factor

    # Experience factor
    exp_factor = np.where(driving_experience < 2, 18,
                 np.where(driving_experience < 5, 10,
                 np.where(driving_experience < 10, 4, 0)))
    score += exp_factor

    # Accident history is the strongest predictor
    score += previous_accidents * 14

    # Traffic violations
    score += traffic_violations * 5

    # Mileage factor
    mileage_factor = (annual_mileage - 3000) / 52000 * 10
    score += mileage_factor

    # Night driving
    score += night_driving_pct * 0.12

    # Vehicle type
    vtype_map = {'sedan': 0, 'van': 0, 'suv': 3, 'truck': 4,
                 'sports': 12, 'motorcycle': 18}
    score += np.array([vtype_map[v] for v in vehicle_types])

    # Vehicle age
    score += np.where(vehicle_age > 15, 6, np.where(vehicle_age > 10, 3, 0))

    # Location
    loc_map = {'suburban': 0, 'rural': 2, 'highway': 4, 'urban': 7}
    score += np.array([loc_map[l] for l in locations])

    # Credit score (inversely related)
    score += np.clip((700 - credit_score) / 40, -5, 10)

    # Marital status
    ms_map = {'married': -2, 'divorced': 2, 'single': 3}
    score += np.array([ms_map[m] for m in marital_status])

    # Gender
    score += np.where(gender == 'male', 2, 0)

    # Noise
    score += np.random.normal(0, 4, n_samples)

    # Normalize to 0–100
    score = np.clip((score - score.min()) / (score.max() - score.min()) * 100, 0, 100)

    # Risk category
    def categorize(s):
        if s < 26: return 'Low'
        if s < 51: return 'Medium'
        if s < 76: return 'High'
        return 'Very High'

    risk_category = np.array([categorize(s) for s in score])

    # Premium multiplier
    pm_map = {'Low': 1.0, 'Medium': 1.35, 'High': 1.75, 'Very High': 2.30}
    premium_multiplier = np.array([pm_map[c] for c in risk_category])

    # Claim probability (sigmoid of score)
    claim_prob = np.clip(1 / (1 + np.exp(-0.08 * (score - 50))), 0.02, 0.95)

    df = pd.DataFrame({
        'driver_age': driver_age,
        'driving_experience': driving_experience,
        'annual_mileage': annual_mileage,
        'vehicle_age': vehicle_age,
        'previous_accidents': previous_accidents,
        'traffic_violations': traffic_violations,
        'night_driving_pct': night_driving_pct,
        'credit_score': credit_score,
        'vehicle_type': vehicle_types,
        'primary_location': locations,
        'marital_status': marital_status,
        'gender': gender,
        'risk_score': np.round(score, 2),
        'risk_category': risk_category,
        'premium_multiplier': premium_multiplier,
        'claim_probability': np.round(claim_prob, 4),
    })
    return df


if __name__ == '__main__':
    df = generate_synthetic_data()
    out = os.path.join(os.path.dirname(__file__), 'accidents.csv')
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} records to {out}")
    print(df['risk_category'].value_counts())
