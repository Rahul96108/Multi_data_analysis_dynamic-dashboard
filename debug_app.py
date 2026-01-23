import os
import pandas as pd
from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# --- CONFIGURATION ---
app = Flask(__name__)
# REPLACE 'your_password' with your actual PostgreSQL password
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///local_analytics.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists('uploads'):
    os.makedirs('uploads')

db = SQLAlchemy(app)

# --- MODEL ---
class DatasetMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    row_count = db.Column(db.Integer)

# --- HTML TEMPLATES ---
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="container mt-5">
    <div class="card p-4 shadow">
        <h2>Analytics App (Debug Mode)</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" class="form-control mb-3" required>
            <button type="submit" class="btn btn-primary">Upload & Process</button>
        </form>
    </div>
</body>
</html>
"""

# --- ROUTES ---
@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file: return "No file", 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Process
    ext = os.path.splitext(filename)[1].lower()
    try:
        if ext == '.csv': df = pd.read_csv(filepath)
        elif ext in ['.xls', '.xlsx']: df = pd.read_excel(filepath)
        else: return "Unsupported file", 400
        
        # Save to DB
        meta = DatasetMetadata(filename=filename, row_count=len(df))
        db.session.add(meta)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "filename": filename,
            "rows": len(df),
            "columns": list(df.columns)
        })
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001) # Using 5001 to avoid conflicts