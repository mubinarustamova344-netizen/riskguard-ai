# -*- coding: utf-8 -*-
"""Populates the database with 5,000 realistic synthetic assessments."""
import sys, os, json
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from database import Assessment
from model.risk_model import load_model, predict_risk

np.random.seed(2025)
model = load_model()

TARGET = 5000

with app.app_context():
    existing = Assessment.query.count()
    needed = max(0, TARGET - existing)
    print(f"Hozir: {existing} | Kerak: {needed} ta yangi yozuv")
    if needed == 0:
        print("Allaqachon 5000 ta yozuv bor.")
        sys.exit(0)

    # Realistic distributions
    ages        = np.random.choice(range(18,81), needed,
                    p=np.array([max(0.001,(1-abs(a-35)/62)) for a in range(18,81)]
                    )/sum([max(0.001,(1-abs(a-35)/62)) for a in range(18,81)]))
    vehicle_types  = np.random.choice(
        ['sedan','suv','sports','truck','van','motorcycle'], needed,
        p=[0.37, 0.25, 0.11, 0.12, 0.09, 0.06])
    locations      = np.random.choice(
        ['urban','suburban','rural','highway'], needed,
        p=[0.40, 0.32, 0.17, 0.11])
    marital_status = np.random.choice(
        ['single','married','divorced'], needed,
        p=[0.36, 0.50, 0.14])
    genders        = np.random.choice(['male','female'], needed, p=[0.53, 0.47])
    accidents      = np.random.choice([0,1,2,3,4,5], needed,
                       p=[0.58,0.22,0.11,0.05,0.03,0.01])
    violations     = np.random.choice([0,1,2,3,4,5,6], needed,
                       p=[0.52,0.23,0.13,0.07,0.03,0.01,0.01])
    experiences    = np.clip(ages - 18 - np.random.randint(0,6,needed), 0, 60)
    mileages       = np.random.randint(2000, 55000, needed)
    v_ages         = np.random.randint(0, 26, needed)
    nights         = np.random.randint(0, 101, needed)
    credits        = np.clip(np.random.normal(685, 105, needed), 300, 850).astype(int)

    # Spread created_at over last 6 months
    base_date = datetime.utcnow()
    time_offsets = np.random.randint(0, 180*24*60, needed)  # minutes in 6 months

    status_choices = np.random.choice(
        ['Pending','Reviewed','Approved'], needed,
        p=[0.55, 0.30, 0.15])

    batch_size = 100
    added = 0
    for i in range(needed):
        inp = {
            'driver_age':         int(ages[i]),
            'driving_experience': int(experiences[i]),
            'annual_mileage':     int(mileages[i]),
            'vehicle_age':        int(v_ages[i]),
            'previous_accidents': int(accidents[i]),
            'traffic_violations': int(violations[i]),
            'night_driving_pct':  int(nights[i]),
            'credit_score':       int(credits[i]),
            'vehicle_type':       vehicle_types[i],
            'primary_location':   locations[i],
            'marital_status':     marital_status[i],
            'gender':             genders[i],
        }
        try:
            result = predict_risk(model, inp)
        except Exception:
            continue

        created = base_date - timedelta(minutes=int(time_offsets[i]))

        rec = Assessment(
            driver_age         = inp['driver_age'],
            driving_experience = inp['driving_experience'],
            annual_mileage     = inp['annual_mileage'],
            vehicle_age        = inp['vehicle_age'],
            previous_accidents = inp['previous_accidents'],
            traffic_violations = inp['traffic_violations'],
            night_driving_pct  = inp['night_driving_pct'],
            credit_score       = inp['credit_score'],
            vehicle_type       = inp['vehicle_type'],
            primary_location   = inp['primary_location'],
            marital_status     = inp['marital_status'],
            gender             = inp['gender'],
            risk_score         = result['risk_score'],
            risk_category      = result['risk_category'],
            premium_multiplier = result['premium_multiplier'],
            claim_probability  = result['claim_probability'],
            confidence         = result.get('confidence', 85.0),
            recommendations_json = json.dumps(result['recommendations']),
            status             = str(status_choices[i]),
            notes              = '',
            created_at         = created,
        )
        db.session.add(rec)
        added += 1

        if added % batch_size == 0:
            db.session.commit()
            pct = added / needed * 100
            print(f"  {added}/{needed} ({pct:.0f}%) qo'shildi...")

    db.session.commit()
    total = Assessment.query.count()
    print(f"\nJami: {total} ta yozuv bor endi.")

    # Category distribution
    from sqlalchemy import func
    rows = db.session.query(Assessment.risk_category, func.count(Assessment.id))\
               .group_by(Assessment.risk_category).all()
    for cat, cnt in sorted(rows, key=lambda x: x[1], reverse=True):
        print(f"  {cat:<12} : {cnt:>5} ta ({cnt/total*100:.1f}%)")
