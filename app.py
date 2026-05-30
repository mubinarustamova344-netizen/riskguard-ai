# -*- coding: utf-8 -*-
import os
import io
import csv
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import db, Assessment
from model.risk_model import load_model, load_metrics, predict_risk, compute_factor_contributions
from model.chatbot_engine import RiskChatbot

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'assessments.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['ADMIN_USERNAME'] = os.environ['ADMIN_USERNAME']
app.config['ADMIN_PASSWORD_HASH'] = generate_password_hash(os.environ['ADMIN_PASSWORD'])
CORS(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


class AdminUser(UserMixin):
    id = 'admin'


ADMIN_USER = AdminUser()


@login_manager.user_loader
def load_user(user_id):
    if user_id == 'admin':
        return ADMIN_USER
    return None

db.init_app(app)

# Load trained model once at startup
try:
    model = load_model()
    print("Risk model loaded successfully.")
except FileNotFoundError:
    model = None
    print("WARNING: Model not found. Run: python setup.py")

chatbot = RiskChatbot()

REQUIRED_FIELDS = [
    'driver_age', 'driving_experience', 'annual_mileage', 'vehicle_age',
    'previous_accidents', 'traffic_violations', 'night_driving_pct',
    'credit_score', 'vehicle_type', 'primary_location', 'marital_status', 'gender',
]


# ── DB init ────────────────────────────────────────────────────────────────────
@app.before_request
def ensure_tables():
    db.create_all()


# ── Error handlers ─────────────────────────────────────────────────────────────
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500


# ── Auth ───────────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if (username == app.config['ADMIN_USERNAME'] and
                check_password_hash(app.config['ADMIN_PASSWORD_HASH'], password)):
            login_user(ADMIN_USER, remember=request.form.get('remember') == 'on')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ── Pages ──────────────────────────────────────────────────────────────────────
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


# ── API ────────────────────────────────────────────────────────────────────────
@app.route('/api/assess', methods=['POST'])
def api_assess():
    if model is None:
        return jsonify({'error': 'Model not loaded. Run: python setup.py'}), 503

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    for field in REQUIRED_FIELDS:
        if field not in data or data[field] == '' or data[field] is None:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Coerce numeric fields
    try:
        numeric_inputs = {
            'driver_age': int(data['driver_age']),
            'driving_experience': int(data['driving_experience']),
            'annual_mileage': int(data['annual_mileage']),
            'vehicle_age': int(data['vehicle_age']),
            'previous_accidents': int(data['previous_accidents']),
            'traffic_violations': int(data['traffic_violations']),
            'night_driving_pct': int(data['night_driving_pct']),
            'credit_score': int(data['credit_score']),
        }
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid numeric value: {e}'}), 400

    input_data = {**numeric_inputs,
                  'vehicle_type': str(data['vehicle_type']),
                  'primary_location': str(data['primary_location']),
                  'marital_status': str(data['marital_status']),
                  'gender': str(data['gender'])}

    try:
        result = predict_risk(model, input_data)
    except Exception as e:
        return jsonify({'error': f'Prediction error: {str(e)}'}), 500

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
    db.session.commit()

    result['assessment_id'] = record.id
    return jsonify(result)


@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    message = str(data.get('message', '')).strip()
    if not message:
        return jsonify({'error': 'Empty message'}), 400
    response = chatbot.chat(message)
    return jsonify(response)


@app.route('/api/chat/reset', methods=['POST'])
def api_chat_reset():
    chatbot.reset()
    return jsonify({'status': 'ok'})


@app.route('/api/model-metrics')
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
def api_history():
    records = Assessment.query.order_by(Assessment.created_at.desc()).limit(200).all()
    return jsonify([r.to_dict() for r in records])


@app.route('/api/stats')
def api_stats():
    all_records = Assessment.query.all()
    if not all_records:
        return jsonify({'total': 0, 'message': 'No assessments yet'})

    cats = {'Low': 0, 'Medium': 0, 'High': 0, 'Very High': 0}
    scores, ages = [], []
    vtypes, locs, monthly = {}, {}, {}

    for r in all_records:
        cats[r.risk_category] = cats.get(r.risk_category, 0) + 1
        scores.append(r.risk_score)
        ages.append(r.driver_age)
        vtypes[r.vehicle_type] = vtypes.get(r.vehicle_type, 0) + 1
        locs[r.primary_location] = locs.get(r.primary_location, 0) + 1
        month = r.created_at.strftime('%Y-%m')
        monthly[month] = monthly.get(month, 0) + 1

    return jsonify({
        'total': len(all_records),
        'category_distribution': cats,
        'avg_risk_score': round(sum(scores) / len(scores), 1),
        'max_risk_score': round(max(scores), 1),
        'min_risk_score': round(min(scores), 1),
        'age_distribution': ages,
        'vehicle_type_distribution': vtypes,
        'location_distribution': locs,
        'monthly_assessments': monthly,
    })


@app.route('/quote')
@login_required
def quote():
    return render_template('quote.html')


@app.route('/compare')
@login_required
def compare():
    return render_template('compare.html')


@app.route('/api/compare', methods=['POST'])
def api_compare():
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 503
    data = request.get_json(silent=True)
    if not data or 'profile_a' not in data or 'profile_b' not in data:
        return jsonify({'error': 'Need profile_a and profile_b'}), 400
    try:
        result_a = predict_risk(model, data['profile_a'])
        result_b = predict_risk(model, data['profile_b'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'profile_a': result_a, 'profile_b': result_b})


@app.route('/api/export-csv')
def api_export_csv():
    cat_filter = request.args.get('category', '').strip()
    query = Assessment.query.order_by(Assessment.created_at.desc())
    if cat_filter:
        query = query.filter_by(risk_category=cat_filter)
    records = query.all()

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

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=riskguard_assessments.csv'}
    )


@app.route('/api/age-distribution')
def api_age_distribution():
    records = Assessment.query.all()
    buckets = {'18-24': 0, '25-34': 0, '35-44': 0, '45-54': 0, '55-64': 0, '65+': 0}
    for r in records:
        a = r.driver_age
        if a < 25:      buckets['18-24'] += 1
        elif a < 35:    buckets['25-34'] += 1
        elif a < 45:    buckets['35-44'] += 1
        elif a < 55:    buckets['45-54'] += 1
        elif a < 65:    buckets['55-64'] += 1
        else:           buckets['65+']   += 1
    return jsonify(buckets)


@app.route('/api/score-distribution')
def api_score_distribution():
    records = Assessment.query.all()
    buckets = {'0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0}
    for r in records:
        s = r.risk_score
        if s <= 20:     buckets['0-20']   += 1
        elif s <= 40:   buckets['21-40']  += 1
        elif s <= 60:   buckets['41-60']  += 1
        elif s <= 80:   buckets['61-80']  += 1
        else:           buckets['81-100'] += 1
    return jsonify(buckets)


if __name__ == '__main__':
    import socket

    with app.app_context():
        db.create_all()

    # Try port 5000 first, fall back to 5001–5009
    chosen = 5000
    for p in [5000, 5001, 5002, 5003, 5004, 5005]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.3)
        in_use = (sock.connect_ex(('127.0.0.1', p)) == 0)
        sock.close()
        if not in_use:
            chosen = p
            break

    print('')
    print('  ================================================')
    print(f'  Browser da oching:  http://127.0.0.1:{chosen}')
    print('  To\'xtatish uchun:   Ctrl+C')
    print('  ================================================')
    print('')
    app.run(debug=False, port=chosen, host='127.0.0.1')
