# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**RiskGuard AI** is a Flask web application for road accident risk assessment targeted at insurance companies. It uses a trained ML model to predict driver risk profiles, calculate premium multipliers, and provide recommendations.

## Environment Setup

Requires a `.env` file with:
```
SECRET_KEY=<any random secret>
ADMIN_USERNAME=<username>
ADMIN_PASSWORD=<password>
ANTHROPIC_API_KEY=<optional – enables AI chatbot>
EMAIL_USER=<optional Gmail>
EMAIL_PASS=<optional Gmail app password>
```

Install dependencies:
```
pip install -r requirements.txt
pip install reportlab werkzeug flask-wtf  # not in requirements.txt but used in app.py
```

## Key Commands

**First-time setup** (generates 12,000-record synthetic dataset and trains the ML model — takes 30–60 seconds):
```
python setup.py
```

**Run the app:**
```
python app.py
```
App auto-selects a free port starting from 5000. Open `http://127.0.0.1:5000`.

**Windows one-click launcher** (checks deps, trains model if missing, starts app):
```
run.bat
```

There is no test suite. The app logs to `app.log` (rotating, 1 MB limit).

## Architecture

### ML Pipeline (`model/`)

- **`setup.py`** → `data/generate_data.py` → `model/risk_model.py` → saves `model/risk_model.pkl` + `model/model_metrics.pkl`
- Training compares Decision Tree, Logistic Regression, Random Forest, and Gradient Boosting (tuned via GridSearchCV). The tuned Gradient Boosting pipeline is always saved as the production model.
- `predict_risk()` returns a risk score derived from class probabilities weighted by category midpoints (`Low=15`, `Medium=38`, `High=63`, `Very High=88`). The category is then re-derived from the score, ensuring score and category are always consistent.
- `compute_factor_contributions()` uses rule-based heuristics (not the ML model) to produce the per-factor breakdown shown in the UI.
- `compute_improvement_roadmap()` runs counterfactual simulations through the ML model to estimate score savings per fixable factor.

### Flask App (`app.py`)

Single-file Flask app with:
- **Auth**: Single admin user loaded from env vars; `flask-login` session management; rate-limited to 10 login attempts/minute.
- **CSRF**: `flask-wtf` CSRFProtect is active app-wide; API routes that accept JSON POST calls use `@csrf.exempt`.
- **Database**: SQLite via SQLAlchemy (`assessments.db`). Tables are created automatically on first request via `before_request`. The single model is `Assessment` in `database.py`.
- **Chatbot** (`model/chatbot_engine.py`): Falls back to regex-based intent matching when `ANTHROPIC_API_KEY` is absent. With a key, uses `claude-haiku-4-5-20251001` with the last 10 conversation turns as context.
- **i18n** (`lang.py`): English/Uzbek translations injected into every template via `inject_lang()` context processor. Language toggled via `/set-lang/<lang>` route stored in session.

### Input Validation

`REQUIRED_FIELDS`, `NUMERIC_RANGES`, and the `VALID_*` sets at the top of `app.py` define all accepted input. Any change to valid vehicle types, locations, marital status, or genders must be updated in both these constants and `data/generate_data.py` (training data) and `model/risk_model.py` (feature lists).

### PDF Generation

`/report/<id>/pdf` uses `reportlab` to build a styled PDF in-memory. `reportlab` is not in `requirements.txt` and must be installed separately.

### Feature Inputs (12 fields)

Numeric: `driver_age`, `driving_experience`, `annual_mileage`, `vehicle_age`, `previous_accidents`, `traffic_violations`, `night_driving_pct`, `credit_score`

Categorical: `vehicle_type` (`sedan|suv|sports|truck|van|motorcycle`), `primary_location` (`urban|suburban|rural|highway`), `marital_status` (`single|married|divorced`), `gender` (`male|female`)
