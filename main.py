from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
import uuid
from datetime import datetime
import io
import zipfile

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/users.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

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
            first_name=first_name, last_name=last_name, email=email,
            phone=phone, user_type=user_type, crew_type=crew_type,
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
    user.email = request.form['email']
    user.phone = request.form['phone']
    avatar_file = request.files.get('avatar')
    if avatar_file and avatar_file.filename:
        filename = f"{uuid.uuid4().hex}_{secure_filename(avatar_file.filename)}"
        avatar_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        avatar_file.save(avatar_path)
        user.avatar = f"uploads/{filename}"
    db.session.commit()
    flash('Profile updated successfully.', 'success')
    return redirect(url_for('profile'))

@app.route('/add_report', methods=['POST'])
def add_report():
    user_id = session.get('user_id')
    if not user_id:
        flash('Please log in.', 'danger')
        return redirect(url_for('index'))
    user = User.query.get(user_id)
    data = request.form
    photos = request.files.getlist('photos')
    photo_filenames = []
    for photo in photos:
        if photo and photo.filename:
            filename = f"{uuid.uuid4().hex}_{secure_filename(photo.filename)}"
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo_filenames.append(filename)
    report = Report(
        date=data['date'], customer=data['customer'],
        project_number=data['project_number'], type_of_works=data['type_of_works'],
        reel_id=data['reel_id'], pages=data['pages'],
        production=data['production'], total=data['total'],
        last_production=(data.get('last_production') == 'yes'),
        photo_filenames=json.dumps(photo_filenames), user_id=user_id
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
    if 'manage' in user.user_type.lower():
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
    return send_file(memory_file, download_name=f'report_{report.id}_attachments.zip', as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)
