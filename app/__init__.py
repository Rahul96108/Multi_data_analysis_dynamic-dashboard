import os
from flask import Flask
from .models import db
from .routes import main_bp

def create_app():
    # Initialize the Flask app instance
    app = Flask(__name__)
    
    # Load configuration from config.py
    app.config.from_object('config.Config')

    # Ensure the upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Initialize the database extension
    db.init_app(app)

    # REGISTER BLUEPRINTS INSIDE THE FACTORY
    app.register_blueprint(main_bp)

    # Automatically create database tables
    with app.app_context():
        db.create_all()
    
    return app