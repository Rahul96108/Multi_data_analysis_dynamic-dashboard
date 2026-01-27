import os
from flask import Flask
from .models import db  # Ensure db is imported from your models.py

def create_app():
    app = Flask(__name__)

    # --- 1. CONFIGURATION ---
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Logic for the 'uploads' folder path
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

    # --- 2. INITIALIZE DATABASE ---
    db.init_app(app)

    # --- 3. REGISTER ROUTES (The fix for 404) ---
    from .routes import main_bp
    # Ensure url_prefix is NOT used if you want the home page at '/'
    app.register_blueprint(main_bp)

    # --- 4. CREATE TABLES & FOLDERS ---
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        
    with app.app_context():
        db.create_all()

    return app
