# -*- coding: utf-8 -*-
import os
import io
import csv
import json
import logging
from datetime import timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
from model.risk_model import load_model, load_metrics, predict_risk, compute_factor_contributions, compute_improvement_roadmap
from model.chatbot_engine import RiskChatbot
from lang import TRANSLATIONS, get_lang

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Logging ────────────────────────────────────────────────────────────────────
_fmt = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_stdout_handler = logging.StreamHandler()
_stdout_handler.setFormatter(_fmt)
logger.addHandler(_stdout_handler)
try:
    _file_handler = RotatingFileHandler(
        os.path.join(BASE_DIR, 'app.log'), maxBytes=1_000_000, backupCount=3
    )
    _file_handler.setFormatter(_fmt)
    logger.addHandler(_file_handler)
except OSError:
    pass

# ── App ────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(BASE_DIR, 'assessments.db')}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.environ.get('SECRET_KEY', 'change-me-in-production'),
    ADMIN_USERNAME=os.environ.get('ADMIN_USERNAME', 'admin'),
    ADMIN_PASSWORD_HASH=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123')),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    WTF_CSRF_TIME_LIMIT=3600,
)

CORS(app, resources={r"/api/*": {"origins": "*"}})
csrf = CSRFProtect(app)


GITHUB_URL = "https://github.com/mubinarustamova344-netizen/riskguard-ai"
LIVE_URL   = "https://riskguard-ai.onrender.com"

@app.context_processor
def inject_lang():
    from flask import session as _s
    lang = get_lang(_s)
    return dict(
        t=TRANSLATIONS.get(lang, TRANSLATIONS['en']),
        lang=lang,
        GITHUB_URL=GITHUB_URL,
        LIVE_URL=LIVE_URL,
    )

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


@app.route('/set-lang/<lang>')
def set_lang(lang):
    from flask import session as _s
    if lang in ('en', 'uz'):
        _s['lang'] = lang
    return redirect(request.referrer or url_for('index'))


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
    return render_template('chatbot.html', ai_enabled=chatbot.ai_enabled)


@app.route('/history')
@login_required
def history():
    from datetime import datetime as dt
    page = request.args.get('page', 1, type=int)
    per_page = 15
    cat_filter  = request.args.get('category', '').strip()
    date_from   = request.args.get('date_from', '').strip()
    date_to     = request.args.get('date_to', '').strip()
    if cat_filter and cat_filter not in VALID_CATEGORIES:
        cat_filter = ''
    query = Assessment.query.order_by(Assessment.created_at.desc())
    if cat_filter:
        query = query.filter_by(risk_category=cat_filter)
    if date_from:
        try:
            query = query.filter(Assessment.created_at >= dt.strptime(date_from, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Assessment.created_at <= dt.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            pass
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template('history.html',
                           assessments=pagination.items,
                           pagination=pagination,
                           cat_filter=cat_filter,
                           date_from=date_from,
                           date_to=date_to)


@app.route('/model-report')
@login_required
def model_report():
    metrics = load_metrics()
    return render_template('model_report.html', metrics=metrics)


@app.route('/about')
@login_required
def about():
    return render_template('about.html')


@app.route('/report/<int:assessment_id>')
@login_required
def report(assessment_id):
    record = db.get_or_404(Assessment, assessment_id)
    data = record.to_dict()

    # Benchmark: % of drivers with higher risk score
    total = Assessment.query.count()
    worse = Assessment.query.filter(Assessment.risk_score > record.risk_score).count()
    data['benchmark_pct'] = round((worse / total * 100) if total else 50, 1)

    # Improvement roadmap
    if model:
        input_data = {
            'driver_age': record.driver_age, 'driving_experience': record.driving_experience,
            'annual_mileage': record.annual_mileage, 'vehicle_age': record.vehicle_age,
            'previous_accidents': record.previous_accidents, 'traffic_violations': record.traffic_violations,
            'night_driving_pct': record.night_driving_pct, 'credit_score': record.credit_score,
            'vehicle_type': record.vehicle_type, 'primary_location': record.primary_location,
            'marital_status': record.marital_status, 'gender': record.gender,
        }
        data['roadmap'] = compute_improvement_roadmap(model, input_data, record.risk_score)
        data['confidence'] = predict_risk(model, input_data).get('confidence', 85.0)
    else:
        data['roadmap'] = []
        data['confidence'] = 85.0

    # Trend: last 8 assessments (most recent first)
    trend = Assessment.query.order_by(Assessment.created_at.desc()).limit(8).all()
    data['trend'] = [{'date': r.created_at.strftime('%d %b'), 'score': r.risk_score} for r in reversed(trend)]

    return render_template('report.html', assessment=data)


@app.route('/simulator')
@login_required
def simulator():
    return render_template('simulator.html')


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
        confidence=result.get('confidence', 85.0),
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


@app.route('/api/chat/stream', methods=['POST'])
@csrf.exempt
@login_required
@limiter.limit('60 per minute')
def api_chat_stream():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    message = str(data.get('message', '')).strip()
    if not message:
        return jsonify({'error': 'Empty message'}), 400
    if len(message) > 2000:
        return jsonify({'error': 'Message too long (max 2000 characters)'}), 400

    def generate():
        try:
            for chunk in chatbot.stream_chat(message):
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


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


@app.route('/api/assessment/<int:assessment_id>', methods=['DELETE'])
@csrf.exempt
@login_required
def api_delete_assessment(assessment_id):
    record = db.get_or_404(Assessment, assessment_id)
    db.session.delete(record)
    db.session.commit()
    logger.info('Assessment #%d deleted by admin', assessment_id)
    return jsonify({'status': 'deleted', 'id': assessment_id})


@app.route('/api/assessment/<int:assessment_id>/status', methods=['PATCH'])
@csrf.exempt
@login_required
def api_update_status(assessment_id):
    record = db.get_or_404(Assessment, assessment_id)
    data = request.get_json(silent=True) or {}
    new_status = data.get('status', '')
    if new_status not in ('Pending', 'Reviewed', 'Approved'):
        return jsonify({'error': 'Invalid status'}), 400
    record.status = new_status
    db.session.commit()
    return jsonify({'status': new_status})


@app.route('/api/assessment/<int:assessment_id>/notes', methods=['PATCH'])
@csrf.exempt
@login_required
def api_update_notes(assessment_id):
    record = db.get_or_404(Assessment, assessment_id)
    data = request.get_json(silent=True) or {}
    record.notes = str(data.get('notes', ''))[:1000]
    db.session.commit()
    return jsonify({'notes': record.notes})


@app.route('/api/bulk-delete', methods=['POST'])
@csrf.exempt
@login_required
def api_bulk_delete():
    data = request.get_json(silent=True) or {}
    ids = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
    if not ids:
        return jsonify({'error': 'No IDs provided'}), 400
    deleted = Assessment.query.filter(Assessment.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    logger.info('Bulk delete: %d records by admin', deleted)
    return jsonify({'deleted': deleted})


@app.route('/report/<int:assessment_id>/pdf')
@login_required
def download_pdf(assessment_id):
    r = db.get_or_404(Assessment, assessment_id)
    buf = io.BytesIO()

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    navy = colors.HexColor('#0d1b2a')
    accent = colors.HexColor('#f59e0b')
    cat_color = {'Low': colors.HexColor('#22c55e'),
                 'Medium': colors.HexColor('#f59e0b'),
                 'High': colors.HexColor('#ef4444'),
                 'Very High': colors.HexColor('#7c3aed')}.get(r.risk_category, colors.grey)

    title_style = ParagraphStyle('title', fontSize=20, textColor=colors.white,
                                 fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4)
    sub_style   = ParagraphStyle('sub',   fontSize=10, textColor=colors.HexColor('#94a3b8'),
                                 alignment=TA_CENTER, spaceAfter=0)
    h2_style    = ParagraphStyle('h2',    fontSize=12, textColor=navy,
                                 fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=6)
    body_style  = ParagraphStyle('body',  fontSize=9,  textColor=colors.HexColor('#334155'),
                                 leading=14)
    rec_style   = ParagraphStyle('rec',   fontSize=9,  textColor=colors.HexColor('#1e293b'),
                                 leading=13, leftIndent=8)

    story = []

    # ── Header banner ──
    header_data = [[Paragraph('RiskGuard AI', title_style)],
                   [Paragraph('Assessment Report', sub_style)],
                   [Paragraph(f'#{r.id}  •  {r.created_at.strftime("%d %B %Y  %H:%M")}', sub_style)]]
    ht = Table(header_data, colWidths=[17*cm])
    ht.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), navy),
        ('TOPPADDING',    (0,0), (-1,0), 14),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 14),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
    ]))
    story.append(ht)
    story.append(Spacer(1, 0.4*cm))

    # ── Risk score box ──
    score_data = [[
        Paragraph(f'<font size=30><b>{r.risk_score}</b></font><br/><font size=9 color="#94a3b8">Risk Score</font>', styles['Normal']),
        Paragraph(f'<font size=16><b>{r.risk_category} Risk</b></font><br/><font size=9 color="#94a3b8">Category</font>', styles['Normal']),
        Paragraph(f'<font size=16><b>{r.premium_multiplier}×</b></font><br/><font size=9 color="#94a3b8">Premium Multiplier</font>', styles['Normal']),
        Paragraph(f'<font size=16><b>{round(r.claim_probability*100)}%</b></font><br/><font size=9 color="#94a3b8">Claim Probability</font>', styles['Normal']),
    ]]
    st = Table(score_data, colWidths=[4*cm, 5*cm, 4*cm, 4*cm])
    st.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX',        (0,0), (-1,-1), 1.5, cat_color),
        ('TEXTCOLOR',  (0,0), (0,0), cat_color),
        ('TEXTCOLOR',  (1,0), (1,0), cat_color),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(st)
    story.append(Spacer(1, 0.4*cm))

    # ── Driver & Vehicle details ──
    story.append(Paragraph('Driver Profile', h2_style))
    driver_rows = [
        ['Age', f'{r.driver_age} years',          'Experience', f'{r.driving_experience} years'],
        ['Gender', r.gender.capitalize(),          'Marital Status', r.marital_status.capitalize()],
        ['Credit Score', str(r.credit_score),      'Annual Mileage', f'{r.annual_mileage:,} miles'],
    ]
    detail_style = TableStyle([
        ('FONTNAME',    (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',    (2,0), (2,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR',   (0,0), (0,-1), colors.HexColor('#64748b')),
        ('TEXTCOLOR',   (2,0), (2,-1), colors.HexColor('#64748b')),
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
        ('TOPPADDING',  (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('BOX',         (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID',   (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
    ])
    dt = Table(driver_rows, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
    dt.setStyle(detail_style)
    story.append(dt)
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph('Vehicle & Driving History', h2_style))
    veh_rows = [
        ['Vehicle Type', r.vehicle_type.capitalize(), 'Vehicle Age', f'{r.vehicle_age} years'],
        ['Location',     r.primary_location.capitalize(), 'Night Driving', f'{r.night_driving_pct}%'],
        ['Prev. Accidents', str(r.previous_accidents), 'Traffic Violations', str(r.traffic_violations)],
    ]
    vt = Table(veh_rows, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
    vt.setStyle(detail_style)
    story.append(vt)
    story.append(Spacer(1, 0.3*cm))

    # ── Recommendations ──
    recs = json.loads(r.recommendations_json or '[]')
    if recs:
        story.append(Paragraph('Personalised Recommendations', h2_style))
        story.append(HRFlowable(width='100%', thickness=0.5, color=accent))
        story.append(Spacer(1, 0.2*cm))
        for rec in recs:
            story.append(Paragraph(f'✔  {rec}', rec_style))
            story.append(Spacer(1, 0.15*cm))

    # ── Footer ──
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
    story.append(Paragraph(
        'RiskGuard AI  •  Road Accident Risk Assessment System  •  Generated automatically',
        ParagraphStyle('footer', fontSize=7, textColor=colors.HexColor('#94a3b8'),
                       alignment=TA_CENTER, spaceBefore=6)
    ))

    doc.build(story)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='application/pdf',
                    headers={'Content-Disposition':
                             f'attachment; filename=riskguard_report_{assessment_id}.pdf'})


# ── Batch CSV Upload ──────────────────────────────────────────────────────────
@app.route('/batch-upload')
@login_required
def batch_upload():
    return render_template('batch_upload.html')


@app.route('/api/batch-upload', methods=['POST'])
@csrf.exempt
@login_required
def api_batch_upload():
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 503
    f = request.files.get('file')
    if not f or not f.filename.endswith('.csv'):
        return jsonify({'error': 'Please upload a CSV file'}), 400

    try:
        content = f.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        results = []
        errors  = []
        required = ['driver_age','driving_experience','annual_mileage','vehicle_age',
                    'previous_accidents','traffic_violations','night_driving_pct',
                    'credit_score','vehicle_type','primary_location','marital_status','gender']

        for i, row in enumerate(reader, 1):
            try:
                input_data = {
                    'driver_age':          int(float(row.get('driver_age', 0))),
                    'driving_experience':  int(float(row.get('driving_experience', 0))),
                    'annual_mileage':      int(float(row.get('annual_mileage', 10000))),
                    'vehicle_age':         int(float(row.get('vehicle_age', 3))),
                    'previous_accidents':  int(float(row.get('previous_accidents', 0))),
                    'traffic_violations':  int(float(row.get('traffic_violations', 0))),
                    'night_driving_pct':   int(float(row.get('night_driving_pct', 20))),
                    'credit_score':        int(float(row.get('credit_score', 680))),
                    'vehicle_type':        str(row.get('vehicle_type', 'sedan')).lower().strip(),
                    'primary_location':    str(row.get('primary_location', 'suburban')).lower().strip(),
                    'marital_status':      str(row.get('marital_status', 'single')).lower().strip(),
                    'gender':              str(row.get('gender', 'male')).lower().strip(),
                }
                result = predict_risk(model, input_data)
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
                db.session.add(record)
                results.append({'row': i, 'risk_score': result['risk_score'],
                                 'risk_category': result['risk_category'],
                                 'premium': result['premium_multiplier']})
            except Exception as e:
                errors.append({'row': i, 'error': str(e)})

        db.session.commit()
        return jsonify({'saved': len(results), 'errors': len(errors),
                        'results': results[:100], 'error_list': errors[:20]})
    except Exception as e:
        return jsonify({'error': f'File processing failed: {str(e)}'}), 500


# ── Risk Certificate ──────────────────────────────────────────────────────────
@app.route('/certificate/<int:assessment_id>')
@login_required
def certificate(assessment_id):
    record = db.get_or_404(Assessment, assessment_id)
    return render_template('certificate.html', a=record)


# ── API Documentation ─────────────────────────────────────────────────────────
@app.route('/api-docs')
@login_required
def api_docs():
    return render_template('api_docs.html')


# ── Email Report ──────────────────────────────────────────────────────────────
@app.route('/api/send-email/<int:assessment_id>', methods=['POST'])
@csrf.exempt
@login_required
def send_email_report(assessment_id):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    record = db.get_or_404(Assessment, assessment_id)
    data   = request.get_json(silent=True) or {}
    to_email = data.get('email', '').strip()
    if not to_email or '@' not in to_email:
        return jsonify({'error': 'Invalid email address'}), 400

    gmail_user = os.environ.get('EMAIL_USER', '')
    gmail_pass = os.environ.get('EMAIL_PASS', '')
    if not gmail_user or not gmail_pass:
        return jsonify({'error': 'Email not configured. Add EMAIL_USER and EMAIL_PASS to .env'}), 503

    cat_emoji = {'Low': '🟢', 'Medium': '🟡', 'High': '🔴', 'Very High': '🟣'}
    emoji = cat_emoji.get(record.risk_category, '⚪')

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <div style="background:linear-gradient(135deg,#04080f,#0f1e35);padding:2rem;border-radius:16px 16px 0 0;text-align:center;">
        <h1 style="color:#ff9f0a;margin:0;font-size:1.6rem;">🛡️ RiskGuard AI</h1>
        <p style="color:rgba(255,255,255,.6);margin:.5rem 0 0;">Risk Assessment Report #{record.id}</p>
      </div>
      <div style="background:#f8fafc;padding:2rem;border-radius:0 0 16px 16px;border:1px solid #e2e8f0;">
        <div style="text-align:center;margin-bottom:1.5rem;">
          <div style="font-size:3rem;font-weight:900;color:{'#10b981' if record.risk_category=='Low' else '#f59e0b' if record.risk_category=='Medium' else '#ef4444' if record.risk_category=='High' else '#7c3aed'};">
            {record.risk_score}
          </div>
          <div style="font-size:1rem;color:#64748b;">Risk Score / 100</div>
          <div style="display:inline-block;padding:.4rem 1.2rem;border-radius:20px;background:{'#10b98120' if record.risk_category=='Low' else '#f59e0b20' if record.risk_category=='Medium' else '#ef444420'};color:{'#10b981' if record.risk_category=='Low' else '#d97706' if record.risk_category=='Medium' else '#dc2626'};font-weight:700;margin-top:.5rem;">
            {emoji} {record.risk_category} Risk
          </div>
        </div>
        <table style="width:100%;border-collapse:collapse;margin-bottom:1rem;">
          <tr><td style="padding:.5rem;color:#64748b;font-size:.9rem;">Premium Multiplier</td><td style="padding:.5rem;font-weight:700;">{record.premium_multiplier}×</td></tr>
          <tr style="background:#fff;"><td style="padding:.5rem;color:#64748b;font-size:.9rem;">Claim Probability</td><td style="padding:.5rem;font-weight:700;">{round(record.claim_probability*100)}%</td></tr>
          <tr><td style="padding:.5rem;color:#64748b;font-size:.9rem;">Driver Age</td><td style="padding:.5rem;font-weight:700;">{record.driver_age} years</td></tr>
          <tr style="background:#fff;"><td style="padding:.5rem;color:#64748b;font-size:.9rem;">Vehicle Type</td><td style="padding:.5rem;font-weight:700;text-transform:capitalize;">{record.vehicle_type}</td></tr>
          <tr><td style="padding:.5rem;color:#64748b;font-size:.9rem;">Assessment Date</td><td style="padding:.5rem;font-weight:700;">{record.created_at.strftime('%d %B %Y %H:%M')}</td></tr>
        </table>
        <p style="color:#94a3b8;font-size:.78rem;text-align:center;">
          Generated by RiskGuard AI Risk Intelligence Platform<br>
          Pearson BTEC Level 6 Diploma in Digital Technologies
        </p>
      </div>
    </div>"""

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'RiskGuard AI — Assessment Report #{record.id} ({record.risk_category} Risk)'
        msg['From']    = gmail_user
        msg['To']      = to_email
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.send_message(msg)
        logger.info('Email report sent to %s for assessment #%d', to_email, assessment_id)
        return jsonify({'status': 'sent', 'to': to_email})
    except Exception as e:
        logger.error('Email error: %s', str(e))
        return jsonify({'error': f'Email failed: {str(e)}'}), 500


# ── Notification badge count ──────────────────────────────────────────────────
@app.route('/api/notifications')
@login_required
def api_notifications():
    high_count = Assessment.query.filter(
        Assessment.risk_category.in_(['High', 'Very High']),
        Assessment.status == 'Pending'
    ).count()
    return jsonify({'high_pending': high_count})


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
