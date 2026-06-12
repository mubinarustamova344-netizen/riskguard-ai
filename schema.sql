-- RiskGuard AI — Database Schema
-- Engine: SQLite 3
-- ORM: SQLAlchemy (models defined in database.py)

CREATE TABLE IF NOT EXISTS assessments (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Driver profile
    driver_age         INTEGER  NOT NULL,
    driving_experience INTEGER  NOT NULL,
    gender             TEXT     NOT NULL,   -- 'male' | 'female'
    marital_status     TEXT     NOT NULL,   -- 'single' | 'married' | 'divorced'

    -- Vehicle
    vehicle_type       TEXT     NOT NULL,   -- 'sedan'|'suv'|'sports'|'truck'|'van'|'motorcycle'
    vehicle_age        INTEGER  NOT NULL,

    -- Driving behaviour
    annual_mileage     INTEGER  NOT NULL,
    night_driving_pct  INTEGER  NOT NULL,
    previous_accidents INTEGER  NOT NULL,
    traffic_violations INTEGER  NOT NULL,
    primary_location   TEXT     NOT NULL,   -- 'urban'|'suburban'|'rural'|'highway'

    -- Financial
    credit_score       INTEGER  NOT NULL,

    -- ML outputs
    risk_score         REAL     NOT NULL,   -- 0.0 – 100.0
    risk_category      TEXT     NOT NULL,   -- 'Low'|'Medium'|'High'|'Very High'
    premium_multiplier REAL     NOT NULL,   -- 1.0 / 1.35 / 1.75 / 2.30
    claim_probability  REAL     NOT NULL,   -- 0.0 – 1.0
    confidence         REAL     NOT NULL,   -- model confidence %
    recommendations    TEXT,               -- JSON array
    factor_contributions TEXT,             -- JSON array
    improvement_roadmap  TEXT              -- JSON array
);

-- Useful indexes for dashboard queries
CREATE INDEX IF NOT EXISTS idx_assessments_created  ON assessments(created_at);
CREATE INDEX IF NOT EXISTS idx_assessments_category ON assessments(risk_category);
CREATE INDEX IF NOT EXISTS idx_assessments_score    ON assessments(risk_score);
