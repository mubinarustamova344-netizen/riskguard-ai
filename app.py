# -*- coding: utf-8 -*-
import os
import io
import csv
import json
import logging
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from database import db, Assessment
from model.risk_model import load_model, load_metrics, predict_risk, compute_factor_contributions
from model.chatbot_engine import RiskChatbot

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Logging ────────────────────────────────────────────────────────────────────
_log_handler = RotatingFileHandler(
    os.path.join(BASE_DIR, 'app.log'), maxBytes=1_000_000, backupCount=3
)
_log_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(_log_handler)

# ── App ────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(BASE_DIR, 'assessments.db')}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.environ['SECRET_KEY'],
    ADMIN_USERNAME=os.environ['ADMIN_USERNAME'],
    ADMIN_PASSWORD_HASH=generate_password_hash(os.environ['ADMIN_PASSWORD']),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    WTF_CSRF_TIME_LIMIT=3600,
)

CORS(app, resources={r"/api/*": {"origins": ["http://127.0.0.1", "http://localhost"]}})
csrf = CSRFProtect(app)

# ── Auth ───────────────────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

# ── Rate limiting ──────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri='memory://',
)


class AdminUser(UserMixin):
    id = 'admin'


ADMIN_USER = AdminUser()


@login_manager.user_loader
def load_user(user_id):
    if user_id == 'admin':
        return ADMIN_USER
    return None


db.init_app(app)

# ── Model ──────────────────────────────────────────────────────────────────────
try:
    model = load_model()
    logger.info('Risk model loaded successfully')
    print('Risk model loaded successfully.')
except FileNotFoundError:
    model = None
    logger.warning('Model not found — run: python setup.py')
    print('WARNING: Model not found. Run: python setup.py')

chatbot = RiskChatbot()

# ── Validation constants ───────────────────────────────────────────────────────
REQUIRED_FIELDS = [
    'driver_age', 'driving_experience', 'annual_mileage', 'vehicle_age',
    'previous_accidents', 'traffic_violations', 'night_driving_pct',
    'credit_score', 'vehicle_type', 'primary_location', 'marital_status', 'gender',
]

NUMERIC_RANGES = {
    'driver_age':           (18, 80),
    'driving_experience':   (0, 62),
    'annual_mileage':       (0, 200_000),
    'vehicle_age':          (0, 30),
    'previous_accidents':   (0, 20),
    'traffic_violations':   (0, 20),
    'night_driving_pct':    (0, 100),
    'credit_score':         (300, 850),
}

VALID_VEHICLE_TYPES  = {'sedan', 'suv', 'sports', 'truck', 'van', 'motorcycle'}
VALID_LOCATIONS      = {'urban', 'suburban', 'rural', 'highway'}
VALID_MARITAL_STATUS = {'single', 'married', 'divorced'}
VALID_GENDERS        = {'male', 'female'}
VALID_CATEGORIES     = {'Low', 'Medium', 'High', 'Very High'}


# ── DB init ────────────────────────────────────────────────────────────────────
@app.before_request
def ensure_tables():
    db.create_all()


# ── Security headers ───────────────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


# ── Error handlers ─────────────────────────────────────────────────────────────
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(429)
def rate_limited(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Too many requests. Please slow down.'}), 429
    flash('Too many requests. Please wait a moment.', 'warning')
    return redirect(url_for('login'))


@app.errorhandler(500)
def internal_error(e):
    logger.exception('Internal server error')
    db.session.rollback()
    return render_template('500.html'), 500


# ── Auth routes ────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if (username == app.config['ADMIN_USERNAME'] and
                check_password_hash(app.config['ADMIN_PASSWORD_HASH'], password)):
            login_user(ADMIN_USER, remember=request.form.get('remember') == 'on')
            logger.info('Successful login from %s', request.remote_addr)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        logger.warning('Failed login attempt for "%s" from %s', username, request.remote_addr)
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logger.info('Logout from %s', request.remote_addr)
    logout_user()
    return redirect(url_for('login'))


# ── Page routes ────────────────────────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    total = Assessment.query.count()
    recent = Assessment.query.order_by(Assessment.created_at.desc()).limit(5).all()
    cats = {c: Assessment.query.filter_by(risk_category=c).count()
            for c in ['Low', 'Medium', 'High', 'Very High']}
    return render_template('index.html', total=total, recent=recent, cats=cats)


@app.route('/assessment')
@login_required
def assessment():
    return render_template('assessment.html')


@app.route('/dashboard')
@login_required
def dashboard():
    metrics = load_metrics()
    return render_template('dashboard.html', metrics=metrics)


@app.route('/chatbot')
@login_required
def chatbot_page():
    return render_template('chatbot.html')


@app.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    cat_filter = request.args.get('category', '').strip()
    if cat_filter and cat_filter not in VALID_CATEGORIES:
        cat_filter = ''
    query = Assessment.query.order_by(Assessment.created_at.desc())
    if cat_filter:
        query = query.filter_by(risk_category=cat_filter)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('history.html',
                           assessments=pagination.items,
                           pagination=pagination,
                           cat_filter=cat_filter)


@app.route('/about')
@login_required
def about():
    return render_template('about.html')


@app.route('/report/<int:assessment_id>')
@login_required
def report(assessment_id):
    record = Assessment.query.get_or_404(assessment_id)
    return render_template('report.html', assessment=record.to_dict())


@app.route('/quote')
@login_required
def quote():
    return render_template('quote.html')


@app.route('/compare')
@login_required
def compare():
    return render_template('compare.html')


# ── API routes ─────────────────────────────────────────────────────────────────
@app.route('/api/assess', methods=['POST'])
@csrf.exempt
@login_required
@limiter.limit('30 per minute')
def api_assess():
    if model is None:
        return jsonify({'error': 'Model not loaded. Run: python setup.py'}), 503

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    for field in REQUIRED_FIELDS:
        if field not in data or data[field] == '' or data[field] is None:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    try:
        numeric_inputs = {k: int(data[k]) for k in [
            'driver_age', 'driving_experience', 'annual_mileage', 'vehicle_age',
            'previous_accidents', 'traffic_violations', 'night_driving_pct', 'credit_score',
        ]}
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid numeric value: {e}'}), 400

    for field, (lo, hi) in NUMERIC_RANGES.items():
        v = numeric_inputs[field]
        if not (lo <= v <= hi):
            return jsonify({'error': f'{field} must be between {lo} and {hi}'}), 400

    vehicle_type    = str(data['vehicle_type']).lower().strip()
    primary_location = str(data['primary_location']).lower().strip()
    marital_status  = str(data['marital_status']).lower().strip()
    gender          = str(data['gender']).lower().strip()

    if vehicle_type not in VALID_VEHICLE_TYPES:
        return jsonify({'error': f'Invalid vehicle_type: {vehicle_type}'}), 400
    if primary_location not in VALID_LOCATIONS:
        return jsonify({'error': f'Invalid primary_location: {primary_location}'}), 400
    if marital_status not in VALID_MARITAL_STATUS:
        return jsonify({'error': f'Invalid marital_status: {marital_status}'}), 400
    if gender not in VALID_GENDERS:
        return jsonify({'error': f'Invalid gender: {gender}'}), 400

    input_data = {**numeric_inputs,
                  'vehicle_type': vehicle_type,
                  'primary_location': primary_location,
                  'marital_status': marital_status,
                  'gender': gender}

    try:
        result = predict_risk(model, input_data)
    except Exception:
        logger.exception('Prediction error for input: %s', input_data)
        return jsonify({'error': 'Prediction failed. Please check your input values.'}), 500

    record = Assessment(
        driver_age=input_data['driver_age'],
        driving_experience=input_data['driving_experience'],
        annual_mileage=input_data['annual_mileage'],
        vehicle_age=input_data['vehicle_age'],
        previous_accidents=input_data['previous_accidents'],
        traffic_violations=input_data['traffic_violations'],
        night_driving_pct=input_data['night_driving_pct'],
        credit_score=input_data['credit_score'],
        vehicle_type=input_data['vehicle_type'],
        primary_location=input_data['primary_location'],
        marital_status=input_data['marital_status'],
        gender=input_data['gender'],
        risk_score=result['risk_score'],
        risk_category=result['risk_category'],
        premium_multiplier=result['premium_multiplier'],
        claim_probability=result['claim_probability'],
        recommendations_json=json.dumps(result['recommendations']),
    )
    try:
        db.session.add(record)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Failed to save assessment')
        return jsonify({'error': 'Database error — assessment not saved.'}), 500

    logger.info('Assessment #%d saved: %s (score=%.1f)', record.id,
                result['risk_category'], result['risk_score'])
    result['assessment_id'] = record.id
    return jsonify(result)


@app.route('/api/chat', methods=['POST'])
@csrf.exempt
@login_required
@limiter.limit('60 per minute')
def api_chat():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    message = str(data.get('message', '')).strip()
    if not message:
        return jsonify({'error': 'Empty message'}), 400
    if len(message) > 2000:
        return jsonify({'error': 'Message too long (max 2000 characters)'}), 400
    response = chatbot.chat(message)
    return jsonify(response)


@app.route('/api/chat/reset', methods=['POST'])
@csrf.exempt
@login_required
def api_chat_reset():
    chatbot.reset()
    return jsonify({'status': 'ok'})


@app.route('/api/model-metrics')
@login_required
def api_model_metrics():
    metrics = load_metrics()
    if not metrics:
        return jsonify({'error': 'Metrics not found. Run: python setup.py'}), 404

    def _safe(obj):
        if hasattr(obj, 'item'):
            return obj.item()
        if isinstance(obj, dict):
            return {k: _safe(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_safe(i) for i in obj]
        return obj

    return jsonify(_safe(metrics))


@app.route('/api/history')
@login_required
def api_history():
    records = Assessment.query.order_by(Assessment.created_at.desc()).limit(200).all()
    return jsonify([r.to_dict() for r in records])


@app.route('/api/stats')
@login_required
def api_stats():
    total = Assessment.query.count()
    if not total:
        return jsonify({'total': 0, 'message': 'No assessments yet'})

    cat_rows = db.session.query(
        Assessment.risk_category, func.count(Assessment.id)
    ).group_by(Assessment.risk_category).all()
    cats = {'Low': 0, 'Medium': 0, 'High': 0, 'Very High': 0}
    for cat, cnt in cat_rows:
        cats[cat] = cnt

    score_agg = db.session.query(
        func.avg(Assessment.risk_score),
        func.max(Assessment.risk_score),
        func.min(Assessment.risk_score),
    ).one()

    vtype_rows = db.session.query(
        Assessment.vehicle_type, func.count(Assessment.id)
    ).group_by(Assessment.vehicle_type).all()

    loc_rows = db.session.query(
        Assessment.primary_location, func.count(Assessment.id)
    ).group_by(Assessment.primary_location).all()

    monthly_rows = db.session.query(
        func.strftime('%Y-%m', Assessment.created_at),
        func.count(Assessment.id)
    ).group_by(func.strftime('%Y-%m', Assessment.created_at)).all()

    ages = [r[0] for r in db.session.query(Assessment.driver_age).all()]

    return jsonify({
        'total': total,
        'category_distribution': cats,
        'avg_risk_score': round(score_agg[0] or 0, 1),
        'max_risk_score': round(score_agg[1] or 0, 1),
        'min_risk_score': round(score_agg[2] or 0, 1),
        'age_distribution': ages,
        'vehicle_type_distribution': dict(vtype_rows),
        'location_distribution': dict(loc_rows),
        'monthly_assessments': dict(monthly_rows),
    })


@app.route('/api/compare', methods=['POST'])
@csrf.exempt
@login_required
def api_compare():
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 503
    data = request.get_json(silent=True)
    if not data or 'profile_a' not in data or 'profile_b' not in data:
        return jsonify({'error': 'Need profile_a and profile_b'}), 400
    try:
        result_a = predict_risk(model, data['profile_a'])
        result_b = predict_risk(model, data['profile_b'])
    except Exception:
        logger.exception('Compare prediction error')
        return jsonify({'error': 'Prediction failed'}), 500
    return jsonify({'profile_a': result_a, 'profile_b': result_b})


@app.route('/api/export-csv')
@login_required
def api_export_csv():
    cat_filter = request.args.get('category', '').strip()
    if cat_filter and cat_filter not in VALID_CATEGORIES:
        return jsonify({'error': 'Invalid category filter'}), 400
    query = Assessment.query.order_by(Assessment.created_at.desc())
    if cat_filter:
        query = query.filter_by(risk_category=cat_filter)
    records = query.limit(10_000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Date', 'Age', 'Experience', 'Gender', 'Marital Status',
                     'Vehicle Type', 'Vehicle Age', 'Annual Mileage', 'Location',
                     'Prev Accidents', 'Violations', 'Night Driving %', 'Credit Score',
                     'Risk Score', 'Risk Category', 'Premium Multiplier', 'Claim Probability'])
    for r in records:
        writer.writerow([r.id, r.created_at.strftime('%Y-%m-%d %H:%M'),
                         r.driver_age, r.driving_experience, r.gender, r.marital_status,
                         r.vehicle_type, r.vehicle_age, r.annual_mileage, r.primary_location,
                         r.previous_accidents, r.traffic_violations, r.night_driving_pct,
                         r.credit_score, r.risk_score, r.risk_category,
                         r.premium_multiplier, r.claim_probability])

    logger.info('CSV export: %d records (filter=%r) from %s',
                len(records), cat_filter or 'none', request.remote_addr)
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=riskguard_assessments.csv'}
    )


@app.route('/api/age-distribution')
@login_required
def api_age_distribution():
    buckets = {'18-24': 0, '25-34': 0, '35-44': 0, '45-54': 0, '55-64': 0, '65+': 0}
    for (a,) in db.session.query(Assessment.driver_age).all():
        if a < 25:    buckets['18-24'] += 1
        elif a < 35:  buckets['25-34'] += 1
        elif a < 45:  buckets['35-44'] += 1
        elif a < 55:  buckets['45-54'] += 1
        elif a < 65:  buckets['55-64'] += 1
        else:         buckets['65+']   += 1
    return jsonify(buckets)


@app.route('/api/score-distribution')
@login_required
def api_score_distribution():
    buckets = {'0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0}
    for (s,) in db.session.query(Assessment.risk_score).all():
        if s <= 20:    buckets['0-20']   += 1
        elif s <= 40:  buckets['21-40']  += 1
        elif s <= 60:  buckets['41-60']  += 1
        elif s <= 80:  buckets['61-80']  += 1
        else:          buckets['81-100'] += 1
    return jsonify(buckets)


if __name__ == '__main__':
    import socket

    with app.app_context():
        db.create_all()

    chosen = 5000
    for p in [5000, 5001, 5002, 5003, 5004, 5005]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.3)
        in_use = (sock.connect_ex(('127.0.0.1', p)) == 0)
        sock.close()
        if not in_use:
            chosen = p
            break

    print(f'\n  App running at: http://127.0.0.1:{chosen}\n')
    app.run(debug=False, port=chosen, host='127.0.0.1')
