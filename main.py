from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json
import uuid
import io
import zipfile

app = Flask(__name__)

os.makedirs('static/uploads', exist_ok=True)
app.secret_key = 'your_secret_key_here'

# Use DATABASE_URL from environment if available
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    avatar = db.Column(db.String(300))
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    user_type = db.Column(db.String(50), nullable=False)
    crew_type = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)

class WorkSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    start_lat = db.Column(db.Float)
    start_lon = db.Column(db.Float)
    end_lat = db.Column(db.Float)
    end_lon = db.Column(db.Float)

    user = db.relationship('User', backref='work_sessions')

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    customer = db.Column(db.String(100), nullable=False)
    project_number = db.Column(db.String(100), nullable=False)
    type_of_works = db.Column(db.String(100), nullable=False)
    reel_id = db.Column(db.String(100))
    pages = db.Column(db.String(100))
    production = db.Column(db.Text, nullable=False)
    total = db.Column(db.Text, nullable=False)
    last_production = db.Column(db.Boolean, nullable=False)
    photo_filenames = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='reports')
    status = db.Column(db.String(50), default="Received")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash(f'Welcome, {user.first_name}!', 'success')
            if 'manage' in user.user_type.lower():
                return redirect(url_for('manager_dashboard'))
            else:
                return redirect(url_for('worker_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('index.html')

@app.route('/worker_dashboard')
def worker_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'danger')
        return redirect(url_for('index'))
    user = User.query.get(user_id)
    return render_template('worker_dashboard.html', user=user)

@app.route('/manager_dashboard')
def manager_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'danger')
        return redirect(url_for('index'))
    user = User.query.get(user_id)
    return render_template('manager_dashboard.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        user_type = request.form['user_type']
        crew_type = request.form.get('crew_type')
        password = request.form['password']
        password_hash = generate_password_hash(password)

        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            user_type=user_type,
            crew_type=crew_type,
            password_hash=password_hash
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('User registered successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration error: {e}', 'danger')
    return render_template('register.html')

@app.route('/profile')
def profile():
    return redirect(url_for('worker_dashboard'))

@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'danger')
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    new_email = request.form['email']
    new_phone = request.form['phone']
    avatar_file = request.files.get('avatar')

    if avatar_file and avatar_file.filename:
        filename = f"{uuid.uuid4().hex}_{secure_filename(avatar_file.filename)}"
        avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        avatar_file.save(avatar_path)
        user.avatar = f"/{avatar_path}"

    user.email = new_email
    user.phone = new_phone
    db.session.commit()

    flash('Profile updated successfully.', 'success')
    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/add_report', methods=['POST'])
def add_report():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'danger')
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    date = request.form['date']
    customer = request.form['customer']
    project_number = request.form['project_number']
    type_of_works = request.form['type_of_works']
    reel_id = request.form['reel_id']
    pages = request.form['pages']
    production = request.form['production']
    total = request.form['total']
    last_production = request.form.get('last_production') == 'yes'

    photos = request.files.getlist('photos')
    photo_filenames = []
    for photo in photos:
        if photo and photo.filename:
            filename = f"{uuid.uuid4().hex}_{secure_filename(photo.filename)}"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)
            photo_filenames.append(filename)

    report = Report(
        date=date,
        customer=customer,
        project_number=project_number,
        type_of_works=type_of_works,
        reel_id=reel_id,
        pages=pages,
        production=production,
        total=total,
        last_production=last_production,
        photo_filenames=json.dumps(photo_filenames),
        user_id=user_id
    )
    db.session.add(report)
    db.session.commit()
    flash('Report added successfully.', 'success')
    return redirect(url_for('worker_dashboard'))

@app.route('/my_reports')
def my_reports():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'danger')
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    if user.user_type and 'manage' in user.user_type.lower():
        reports = Report.query.order_by(Report.date.desc()).all()
    else:
        reports = Report.query.filter_by(user_id=user_id).order_by(Report.date.desc()).all()

    return render_template('my_reports.html', reports=reports, user=user)

@app.route('/report/<int:report_id>')
def view_report(report_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'danger')
        return redirect(url_for('index'))

    report = Report.query.get_or_404(report_id)
    user = User.query.get(user_id)

    if report.user_id != user_id and 'manage' not in user.user_type.lower():
        flash('You do not have access to this report.', 'danger')
        return redirect(url_for('my_reports'))

    photos = json.loads(report.photo_filenames or "[]")
    return render_template('view_report.html', report=report, photos=photos, user=user)

@app.route('/download_all_photos/<int:report_id>')
def download_all_photos(report_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'danger')
        return redirect(url_for('index'))

    report = Report.query.get_or_404(report_id)
    user = User.query.get(user_id)

    if report.user_id != user_id and 'manage' not in user.user_type.lower():
        flash('You do not have access to this report.', 'danger')
        return redirect(url_for('my_reports'))

    photos = json.loads(report.photo_filenames or "[]")
    if not photos:
        flash('No attachments to download.', 'info')
        return redirect(url_for('view_report', report_id=report_id))

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for filename in photos:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                zf.write(file_path, arcname=filename)

    memory_file.seek(0)

    return send_file(
        memory_file,
        download_name=f'report_{report.id}_attachments.zip',
        as_attachment=True
    )

@app.route('/update_status/<int:report_id>', methods=['POST'])
def update_status(report_id):
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'danger')
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    if not user or 'manage' not in user.user_type.lower():
        flash('You do not have permission to change status.', 'danger')
        return redirect(url_for('view_report', report_id=report_id))

    report = Report.query.get_or_404(report_id)
    new_status = request.form['status']
    report.status = new_status
    db.session.commit()
    flash('Status updated.', 'success')
    return redirect(url_for('view_report', report_id=report_id))

@app.route('/start_session', methods=['POST'])
def start_session():
    user_id = session.get('user_id')
    if not user_id:
        return 'Unauthorized', 401

    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')

    existing = WorkSession.query.filter_by(user_id=user_id, end_time=None).first()
    if existing:
        return 'Session already started', 400

    session_rec = WorkSession(
        user_id=user_id,
        start_time=datetime.utcnow(),
        start_lat=lat,
        start_lon=lon
    )
    db.session.add(session_rec)
    db.session.commit()
    return 'Started', 200

@app.route('/finish_session', methods=['POST'])
def finish_session():
    user_id = session.get('user_id')
    if not user_id:
        return 'Unauthorized', 401

    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')

    session_rec = WorkSession.query.filter_by(user_id=user_id, end_time=None).first()
    if not session_rec:
        return 'No active session', 400

    session_rec.end_time = datetime.utcnow()
    session_rec.end_lat = lat
    session_rec.end_lon = lon
    db.session.commit()
    return 'Session finished successfully.', 200

@app.route('/my_sessions')
def my_sessions():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'danger')
        return redirect(url_for('index'))

    user = User.query.get(user_id)
    sessions = WorkSession.query.filter_by(user_id=user_id).order_by(WorkSession.start_time.desc()).all()
    return render_template('my_sessions.html', user=user, sessions=sessions)
