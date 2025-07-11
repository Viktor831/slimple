import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Move database file to tmp folder for Render compatibility
os.makedirs('tmp', exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tmp/users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    avatar = db.Column(db.String(200))
    user_type = db.Column(db.String(20), default="worker")
    reports = db.relationship('Report', backref='user', lazy=True)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    customer = db.Column(db.String(100))
    project_number = db.Column(db.String(100))
    type_of_works = db.Column(db.String(200))
    reel_id = db.Column(db.String(100))
    pages = db.Column(db.String(50))
    production = db.Column(db.Text)
    total = db.Column(db.Text)
    last_production = db.Column(db.Boolean, default=False)
    photo_paths = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Routes here (not shown for brevity)...

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
