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

# Папки
os.makedirs('static/uploads', exist_ok=True)
os.makedirs('instance', exist_ok=True)

# Конфіг Flask
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ініціалізація бази
db = SQLAlchemy(app)
with app.app_context():
    db.create_all()
    print("✅ Database created!")

# Додаток буде підхоплено gunicorn через: application = app
application = app
