import os
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (classification_report, accuracy_score,
                             confusion_matrix, roc_auc_score, f1_score,
                             precision_score, recall_score)
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

try:
    from xgboost import XGBClassifier as _XGBClassifier
    _XGBOOST_AVAILABLE = True
except ImportError:
    _XGBOOST_AVAILABLE = False


class XGBStringLabelClassifier(BaseEstimator):
    """XGBClassifier wrapper that handles string class labels transparently."""

    def __init__(self, n_estimators=100, max_depth=6, learning_rate=0.1,
                 subsample=1.0, colsample_bytree=1.0,
                 random_state=42, eval_metric='mlogloss', verbosity=0):
        self.n_estimators    = n_estimators
        self.max_depth       = max_depth
        self.learning_rate   = learning_rate
        self.subsample       = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state    = random_state
        self.eval_metric     = eval_metric
        self.verbosity       = verbosity

    def fit(self, X, y):
        self._le  = LabelEncoder()
        y_enc     = self._le.fit_transform(y)
        self._xgb = _XGBClassifier(
            n_estimators=self.n_estimators, max_depth=self.max_depth,
            learning_rate=self.learning_rate, subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state, eval_metric=self.eval_metric,
            verbosity=self.verbosity,
        )
        self._xgb.fit(X, y_enc)
        self.classes_ = self._le.classes_
        return self

    def predict(self, X):
        return self._le.inverse_transform(self._xgb.predict(X))

    def predict_proba(self, X):
        return self._xgb.predict_proba(X)

    def get_params(self, deep=True):
        return dict(n_estimators=self.n_estimators, max_depth=self.max_depth,
                    learning_rate=self.learning_rate, subsample=self.subsample,
                    colsample_bytree=self.colsample_bytree,
                    random_state=self.random_state, eval_metric=self.eval_metric,
                    verbosity=self.verbosity)

    def set_params(self, **params):
        for k, v in params.items():
            setattr(self, k, v)
        return self

MODEL_PATH   = os.path.join(os.path.dirname(__file__), 'risk_model.pkl')
METRICS_PATH = os.path.join(os.path.dirname(__file__), 'model_metrics.pkl')

CATEGORICAL_FEATURES = ['vehicle_type', 'primary_location', 'marital_status', 'gender']
NUMERIC_FEATURES = ['driver_age', 'driving_experience', 'annual_mileage',
                    'vehicle_age', 'previous_accidents', 'traffic_violations',
                    'night_driving_pct', 'credit_score']
ALL_FEATURES   = NUMERIC_FEATURES + CATEGORICAL_FEATURES
DERIVED_NUMERIC = ['acc_per_exp', 'viol_per_exp', 'youth_risk',
                   'senior_risk', 'risk_combo', 'high_risk_vehicle']
TARGET         = 'risk_category'
CATEGORY_ORDER = ['Low', 'Medium', 'High', 'Very High']


class EngineerFeatures(BaseEstimator, TransformerMixin):
    """Adds 6 interaction features to the 12 base inputs inside the pipeline.
    Input/output interface remains unchanged: still accepts the 12 original fields."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        df = X.copy() if isinstance(X, pd.DataFrame) else pd.DataFrame(X, columns=ALL_FEATURES)
        acc  = df['previous_accidents'].astype(float)
        viol = df['traffic_violations'].astype(float)
        exp  = df['driving_experience'].clip(lower=1).astype(float)
        age  = df['driver_age'].astype(float)
        df['acc_per_exp']       = acc / exp
        df['viol_per_exp']      = viol / exp
        df['youth_risk']        = (age < 25).astype(float) * (acc + viol)
        df['senior_risk']       = (age > 65).astype(float) * acc
        df['risk_combo']        = acc * viol
        df['high_risk_vehicle'] = df['vehicle_type'].isin(['sports', 'motorcycle']).astype(float) * acc
        return df


def build_preprocessor():
    extended_numeric = NUMERIC_FEATURES + DERIVED_NUMERIC
    return ColumnTransformer([
        ('num', StandardScaler(), extended_numeric),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CATEGORICAL_FEATURES),
    ])


def _make_pipe(clf):
    return Pipeline([
        ('engineer',     EngineerFeatures()),
        ('preprocessor', build_preprocessor()),
        ('classifier',   clf),
    ])


def _evaluate(pipe, X_test, y_test) -> dict:
    y_pred  = pipe.predict(X_test)
    y_proba = pipe.predict_proba(X_test)
    acc  = accuracy_score(y_test, y_pred)
    f1   = f1_score(y_test, y_pred, average='weighted')
    prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
    rec  = recall_score(y_test, y_pred, average='weighted', zero_division=0)
    cm   = confusion_matrix(y_test, y_pred, labels=CATEGORY_ORDER)
    report = classification_report(y_test, y_pred, output_dict=True)
    try:
        roc = round(roc_auc_score(y_test, y_proba,
                                  multi_class='ovr', average='macro'), 4)
    except Exception:
        roc = None
    return {
        'accuracy': round(acc, 4), 'cv_accuracy': 0.0,
        'f1': round(f1, 4), 'precision': round(prec, 4),
        'recall': round(rec, 4), 'roc_auc': roc,
        'report': report, 'confusion_matrix': cm.tolist(), 'tuned': False,
    }


def train_models(df):
    X = df[ALL_FEATURES]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    results = {}

    # ── Baseline classifiers ───────────────────────────────────────────────────
    baselines = {
        'Decision Tree': DecisionTreeClassifier(
            max_depth=12, random_state=42, class_weight='balanced'),
        'Logistic Regression': LogisticRegression(
            max_iter=1000, C=1.0, random_state=42, class_weight='balanced'),
        'Extra Trees': ExtraTreesClassifier(
            n_estimators=200, max_depth=14, random_state=42, class_weight='balanced', n_jobs=-1),
        'Random Forest': RandomForestClassifier(
            n_estimators=300, max_depth=14, min_samples_split=4,
            random_state=42, class_weight='balanced', n_jobs=-1),
    }
    for name, clf in baselines.items():
        pipe = _make_pipe(clf)
        pipe.fit(X_train, y_train)
        res = _evaluate(pipe, X_test, y_test)
        cv  = cross_val_score(_make_pipe(clf), X_train, y_train,
                              cv=3, scoring='accuracy', n_jobs=-1).mean()
        res['cv_accuracy'] = round(cv, 4)
        results[name] = res
        print(f"  {name}: acc={res['accuracy']:.4f}  cv={cv:.4f}  "
              f"f1={res['f1']:.4f}  roc={res['roc_auc']}")

    tuned_pipelines = {}

    # ── Gradient Boosting with GridSearchCV ────────────────────────────────────
    print("\n  [GridSearchCV] Tuning Gradient Boosting ...")
    gb_grid = {
        'classifier__n_estimators':  [200, 300],
        'classifier__max_depth':     [3, 5],
        'classifier__learning_rate': [0.05, 0.1],
    }
    gb_search = GridSearchCV(
        _make_pipe(GradientBoostingClassifier(random_state=42)),
        gb_grid, cv=3, scoring='accuracy', n_jobs=-1, refit=True, verbose=0,
    )
    gb_search.fit(X_train, y_train)
    gb_res = _evaluate(gb_search.best_estimator_, X_test, y_test)
    gb_res.update({
        'tuned': True,
        'cv_accuracy': round(gb_search.best_score_, 4),
        'best_params': {k.replace('classifier__', ''): v
                        for k, v in gb_search.best_params_.items()},
        'grid_search_best_score': round(gb_search.best_score_, 4),
    })
    results['Gradient Boosting (Tuned)'] = gb_res
    tuned_pipelines['Gradient Boosting (Tuned)'] = gb_search.best_estimator_
    print(f"  Gradient Boosting (Tuned): acc={gb_res['accuracy']:.4f}  "
          f"roc={gb_res['roc_auc']}  best={gb_search.best_params_}")

    # ── XGBoost with GridSearchCV (if installed) ───────────────────────────────
    if _XGBOOST_AVAILABLE:
        print("\n  [GridSearchCV] Tuning XGBoost ...")
        xgb_grid = {
            'classifier__n_estimators': [200, 300],
            'classifier__max_depth':    [4, 6],
            'classifier__learning_rate': [0.05, 0.1],
        }
        xgb_search = GridSearchCV(
            _make_pipe(XGBStringLabelClassifier()),
            xgb_grid, cv=3, scoring='accuracy', n_jobs=-1, refit=True, verbose=0,
        )
        xgb_search.fit(X_train, y_train)
        xgb_res = _evaluate(xgb_search.best_estimator_, X_test, y_test)
        xgb_res.update({
            'tuned': True,
            'cv_accuracy': round(xgb_search.best_score_, 4),
            'best_params': {k.replace('classifier__', ''): v
                            for k, v in xgb_search.best_params_.items()},
            'grid_search_best_score': round(xgb_search.best_score_, 4),
        })
        results['XGBoost (Tuned)'] = xgb_res
        tuned_pipelines['XGBoost (Tuned)'] = xgb_search.best_estimator_
        print(f"  XGBoost (Tuned): acc={xgb_res['accuracy']:.4f}  "
              f"roc={xgb_res['roc_auc']}  best={xgb_search.best_params_}")

    # ── Select best tuned model ────────────────────────────────────────────────
    best_name     = max(tuned_pipelines, key=lambda k: results[k]['accuracy'])
    best_pipeline = tuned_pipelines[best_name]
    best_acc      = results[best_name]['accuracy']

    # ── Feature importance (via RF with engineered features) ──────────────────
    rf_imp = _make_pipe(RandomForestClassifier(n_estimators=300, max_depth=14,
                                               random_state=42, n_jobs=-1))
    rf_imp.fit(X_train, y_train)
    ohe_feats    = (rf_imp.named_steps['preprocessor']
                    .named_transformers_['cat']
                    .get_feature_names_out(CATEGORICAL_FEATURES).tolist())
    feature_names = NUMERIC_FEATURES + DERIVED_NUMERIC + ohe_feats
    importances   = rf_imp.named_steps['classifier'].feature_importances_
    feat_imp = dict(sorted(zip(feature_names, importances),
                            key=lambda x: x[1], reverse=True)[:15])

    metrics = {
        'best_model':             best_name,
        'best_accuracy':          best_acc,
        'all_results':            results,
        'feature_importance':     feat_imp,
        'test_size':              len(y_test),
        'train_size':             len(X_train),
        'class_distribution':     y.value_counts().to_dict(),
        'best_params':            results[best_name].get('best_params', {}),
        'grid_search_best_score': results[best_name].get('grid_search_best_score', 0),
        'n_samples':              len(df),
        'n_features':             len(ALL_FEATURES),
        'n_engineered_features':  len(ALL_FEATURES) + len(DERIVED_NUMERIC),
        'xgboost_available':      _XGBOOST_AVAILABLE,
    }
    joblib.dump(best_pipeline, MODEL_PATH)
    joblib.dump(metrics, METRICS_PATH)
    print(f"\n  Best model: {best_name}  accuracy={best_acc:.4f}  "
          f"roc_auc={results[best_name]['roc_auc']}")
    return best_pipeline, metrics


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("Model not found. Run setup.py first.")
    return joblib.load(MODEL_PATH)


def load_metrics():
    if not os.path.exists(METRICS_PATH):
        return {}
    return joblib.load(METRICS_PATH)


def compute_factor_contributions(input_data: dict) -> list:
    """Returns list of factor contribution dicts for chart visualisation."""
    items = []

    age = float(input_data.get('driver_age', 35))
    if age < 25:
        items.append({'factor': f'Young Driver Age ({int(age)}yrs)', 'value': round((25 - age) * 1.8, 1), 'type': 'risk'})
    elif age > 65:
        items.append({'factor': f'Senior Driver Age ({int(age)}yrs)', 'value': round((age - 65) * 1.2, 1), 'type': 'risk'})
    else:
        items.append({'factor': f'Driver Age ({int(age)}yrs) – Optimal', 'value': 3.0, 'type': 'safe'})

    exp = float(input_data.get('driving_experience', 5))
    if exp < 2:
        items.append({'factor': f'Experience ({int(exp)}yr) – Very Low', 'value': 18.0, 'type': 'risk'})
    elif exp < 5:
        items.append({'factor': f'Experience ({int(exp)}yr) – Low', 'value': 10.0, 'type': 'risk'})
    elif exp < 10:
        items.append({'factor': f'Experience ({int(exp)}yr) – Moderate', 'value': 4.0, 'type': 'risk'})
    else:
        items.append({'factor': f'Experience ({int(exp)}yr) – Strong', 'value': 4.0, 'type': 'safe'})

    acc = float(input_data.get('previous_accidents', 0))
    if acc == 0:
        items.append({'factor': 'No Previous Accidents', 'value': 5.0, 'type': 'safe'})
    else:
        items.append({'factor': f'Previous Accidents ({int(acc)})', 'value': round(acc * 14, 1), 'type': 'risk'})

    viol = float(input_data.get('traffic_violations', 0))
    if viol == 0:
        items.append({'factor': 'No Traffic Violations', 'value': 2.0, 'type': 'safe'})
    else:
        items.append({'factor': f'Traffic Violations ({int(viol)})', 'value': round(viol * 5, 1), 'type': 'risk'})

    mileage = float(input_data.get('annual_mileage', 15000))
    m_val = round((mileage - 3000) / 52000 * 10, 1)
    if mileage > 25000:
        items.append({'factor': f'High Mileage ({int(mileage):,}/yr)', 'value': max(m_val, 0.1), 'type': 'risk'})
    else:
        items.append({'factor': f'Low Mileage ({int(mileage):,}/yr)', 'value': 2.0, 'type': 'safe'})

    night = float(input_data.get('night_driving_pct', 20))
    n_val = round(night * 0.12, 1)
    if night > 30:
        items.append({'factor': f'Night Driving ({int(night)}%)', 'value': max(n_val, 0.1), 'type': 'risk'})
    else:
        items.append({'factor': f'Low Night Driving ({int(night)}%)', 'value': 1.0, 'type': 'safe'})

    vtype = input_data.get('vehicle_type', 'sedan')
    vtype_scores = {'sedan': 0, 'van': 0, 'suv': 3, 'truck': 4, 'sports': 12, 'motorcycle': 18}
    v_val = vtype_scores.get(vtype, 0)
    if v_val > 0:
        items.append({'factor': f'Vehicle: {vtype.title()}', 'value': float(v_val), 'type': 'risk'})
    else:
        items.append({'factor': f'Vehicle: {vtype.title()} – Low Risk', 'value': 2.0, 'type': 'safe'})

    loc = input_data.get('primary_location', 'suburban')
    loc_scores = {'suburban': 0, 'rural': 2, 'highway': 4, 'urban': 7}
    l_val = loc_scores.get(loc, 0)
    if l_val > 0:
        items.append({'factor': f'Location: {loc.title()}', 'value': float(l_val), 'type': 'risk'})
    else:
        items.append({'factor': 'Location: Suburban – Safe', 'value': 1.0, 'type': 'safe'})

    credit = float(input_data.get('credit_score', 680))
    c_val = max(0.0, round((700 - credit) / 40, 1))
    if credit >= 700:
        items.append({'factor': f'Good Credit Score ({int(credit)})', 'value': 3.0, 'type': 'safe'})
    else:
        items.append({'factor': f'Credit Score ({int(credit)}) – Low', 'value': max(c_val, 0.1), 'type': 'risk'})

    risk_items = sorted([i for i in items if i['type'] == 'risk'], key=lambda x: x['value'], reverse=True)
    safe_items = sorted([i for i in items if i['type'] == 'safe'], key=lambda x: x['value'], reverse=True)
    return risk_items + safe_items


def compute_improvement_roadmap(model, input_data: dict, current_score: float) -> list:
    """Simulate score reduction for each improveable factor."""
    roadmap = []
    tweaks = [
        ('previous_accidents', 0,   'Accidents (3yr)',      'Maintain clean record for 3 years'),
        ('traffic_violations', 0,   'Traffic Violations',   'Avoid violations for 12 months'),
        ('night_driving_pct', 10,   'Night Driving',        'Reduce night driving to 10%'),
        ('annual_mileage',    8000, 'Annual Mileage',       'Drive under 8,000 miles/year'),
        ('credit_score',      750,  'Credit Score',         'Improve credit score to 750+'),
    ]
    for field, target_val, label, action in tweaks:
        current_val = input_data.get(field, target_val)
        try:
            current_val = float(current_val)
        except (TypeError, ValueError):
            continue
        if current_val <= target_val and field not in ('credit_score',):
            continue
        if field == 'credit_score' and current_val >= target_val:
            continue
        sim = dict(input_data)
        sim[field] = target_val
        try:
            sim_result = predict_risk(model, sim)
            new_score = sim_result['risk_score']
            saving = round(current_score - new_score, 1)
            if saving > 0.5:
                roadmap.append({
                    'label': label,
                    'action': action,
                    'current': round(current_val, 1),
                    'target': target_val,
                    'saving': saving,
                    'new_score': new_score,
                    'new_category': sim_result['risk_category'],
                })
        except Exception:
            pass
    roadmap.sort(key=lambda x: x['saving'], reverse=True)
    return roadmap[:5]


def predict_risk(model, input_data: dict) -> dict:
    df = pd.DataFrame([input_data])
    for col in NUMERIC_FEATURES:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    proba = model.predict_proba(df[ALL_FEATURES])[0]
    classes = model.classes_.tolist()

    # Risk score derived from ML class probabilities (weighted by category midpoints)
    # This guarantees score and category are always consistent
    CATEGORY_CENTERS = {'Low': 15.0, 'Medium': 38.0, 'High': 63.0, 'Very High': 88.0}
    risk_score = float(sum(
        float(proba[i]) * CATEGORY_CENTERS.get(classes[i], 50.0)
        for i in range(len(classes))
    ))
    risk_score = round(min(max(risk_score, 0.0), 100.0), 1)

    # Derive category from score (always consistent)
    if risk_score < 26:
        risk_category = 'Low'
    elif risk_score < 51:
        risk_category = 'Medium'
    elif risk_score < 76:
        risk_category = 'High'
    else:
        risk_category = 'Very High'

    pm_map = {'Low': 1.0, 'Medium': 1.35, 'High': 1.75, 'Very High': 2.30}
    premium_multiplier = pm_map[risk_category]

    # Claim probability: probability of High or Very High risk
    high_idx = [i for i, c in enumerate(classes) if c in ('High', 'Very High')]
    claim_prob = round(float(sum(proba[i] for i in high_idx)), 3)
    claim_prob = max(0.01, min(0.99, claim_prob))

    recommendations = _get_recommendations(risk_category, input_data)
    factor_contributions = compute_factor_contributions(input_data)

    confidence = round(float(max(proba)) * 100, 1)

    return {
        'risk_category': risk_category,
        'risk_score': risk_score,
        'premium_multiplier': premium_multiplier,
        'claim_probability': claim_prob,
        'confidence': confidence,
        'class_probabilities': {c: round(float(p), 3) for c, p in zip(classes, proba)},
        'recommendations': recommendations,
        'factor_contributions': factor_contributions,
    }


def _get_recommendations(category: str, data: dict) -> list:
    recs = []
    acc = int(data.get('previous_accidents', 0))
    viol = int(data.get('traffic_violations', 0))
    age = int(data.get('driver_age', 35))
    exp = int(data.get('driving_experience', 0))
    night = int(data.get('night_driving_pct', 20))
    mileage = int(data.get('annual_mileage', 15000))
    credit = int(data.get('credit_score', 680))
    vtype = data.get('vehicle_type', 'sedan')

    if category in ('High', 'Very High'):
        recs.append("Consider enrolling in an advanced defensive driving course to reduce premium.")
    if acc > 0:
        recs.append(f"With {acc} prior accident(s), installing a telematics device may lower your premium by up to 15%.")
    if viol > 1:
        recs.append("Reducing traffic violations over the next 12 months will significantly lower your risk score.")
    if age < 25:
        recs.append("Young drivers qualify for a 'Good Student Discount' with proof of academic performance.")
    if exp < 3:
        recs.append("Completing an accredited driver training programme can reduce premiums for new drivers.")
    if night > 40:
        recs.append("Reducing night-time driving will lower your accident probability. Consider daytime-only policies.")
    if mileage > 30000:
        recs.append("High annual mileage increases exposure. Low-mileage discounts are available below 10,000 miles.")
    if credit < 600:
        recs.append("Improving your credit score above 650 can positively affect your insurance risk rating.")
    if vtype in ('sports', 'motorcycle'):
        recs.append(f"Your {vtype} vehicle attracts a higher risk rating. Comprehensive safety features can offset this.")
    if category == 'Low':
        recs.append("Excellent risk profile! You qualify for our Preferred Driver Programme with maximum discounts.")
    if not recs:
        recs.append("Your risk profile is within acceptable limits. Maintain your safe driving record.")
    return recs
