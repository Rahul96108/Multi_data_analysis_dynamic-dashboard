import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Initialize the database object globally
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # --- 1. CONFIGURATION ---
    # In production, the cloud provides a 'PORT' and 'DATABASE_URL'
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_123')
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- 2. AUTOMATIC FOLDER CREATION ---
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # --- 3. INITIALIZE PLUGINS ---
    db.init_app(app)

    # --- 4. REGISTER BLUEPRINTS ---
    # We import inside the function to avoid "Circular Imports"
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app
