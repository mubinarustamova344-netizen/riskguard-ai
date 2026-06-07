from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


class Assessment(db.Model):
    __tablename__ = 'assessments'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Input fields
    driver_age = db.Column(db.Integer)
    driving_experience = db.Column(db.Integer)
    annual_mileage = db.Column(db.Integer)
    vehicle_age = db.Column(db.Integer)
    previous_accidents = db.Column(db.Integer)
    traffic_violations = db.Column(db.Integer)
    night_driving_pct = db.Column(db.Integer)
    credit_score = db.Column(db.Integer)
    vehicle_type = db.Column(db.String(20))
    primary_location = db.Column(db.String(20))
    marital_status = db.Column(db.String(20))
    gender = db.Column(db.String(10))

    # Output
    risk_score = db.Column(db.Float)
    risk_category = db.Column(db.String(20), index=True)
    premium_multiplier = db.Column(db.Float)
    claim_probability = db.Column(db.Float)
    recommendations_json = db.Column(db.Text)

    # Admin fields
    status = db.Column(db.String(20), default='Pending')
    notes = db.Column(db.Text, default='')

    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'driver_age': self.driver_age,
            'driving_experience': self.driving_experience,
            'annual_mileage': self.annual_mileage,
            'vehicle_age': self.vehicle_age,
            'previous_accidents': self.previous_accidents,
            'traffic_violations': self.traffic_violations,
            'night_driving_pct': self.night_driving_pct,
            'credit_score': self.credit_score,
            'vehicle_type': self.vehicle_type,
            'primary_location': self.primary_location,
            'marital_status': self.marital_status,
            'gender': self.gender,
            'risk_score': self.risk_score,
            'risk_category': self.risk_category,
            'premium_multiplier': self.premium_multiplier,
            'claim_probability': self.claim_probability,
            'recommendations': json.loads(self.recommendations_json or '[]'),
            'status': self.status or 'Pending',
            'notes': self.notes or '',
        }
