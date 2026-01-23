from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Define db here, but initialize it in __init__.py
db = SQLAlchemy()

class DatasetMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    rows = db.Column(db.Integer)
    cols = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)