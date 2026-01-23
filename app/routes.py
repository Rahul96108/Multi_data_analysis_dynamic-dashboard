import os
import pandas as pd
from flask import Blueprint, render_template, request, current_app, jsonify
from werkzeug.utils import secure_filename
from .models import db, DatasetMetadata
from .processor import DataService
from .processor import TransformationService
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if not file or file.filename == '':
        return "DEBUG: No file was received by the server.", 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # REMOVED the try/except block here so we can see the REAL error in the browser
    df = pd.read_csv(filepath) if filename.endswith('.csv') else pd.read_excel(filepath)
    
    # This is where the crash is likely happening
    analysis = DataService.analyze_dataframe(df)
    
    # Database Logging
    meta = DatasetMetadata(filename=filename, rows=len(df), cols=len(df.columns))
    db.session.add(meta)
    db.session.commit()

    return render_template('dashboard.html', 
                           filename=filename, 
                           analysis=analysis, 
                           rows=len(df), 
                           cols=len(df.columns),
                           table=df.head(5).to_html(classes='table table-sm'))

@main_bp.route('/generate_plot', methods=['POST'])
def generate_plot():
    filename = request.form.get('filename')
    plot_type = request.form.get('plot_type')
    x_col = request.form.get('x_col')
    y_col = request.form.get('y_col')

    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    try:
        df = pd.read_csv(filepath) if filename.endswith('.csv') else pd.read_excel(filepath)
        plot_b64 = DataService.generate_custom_plot(df, plot_type, x_col, y_col)
        return jsonify({"success": True, "plot_data": plot_b64})
    except Exception as e:
        # In debug mode, throw the specific exception
        return jsonify({"success": False, "error": f"No such plot can be plotted: {str(e)}"}), 400
    
@main_bp.route('/check_nulls', methods=['POST'])
def check_nulls():
    filename = request.form.get('filename')
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    df = pd.read_csv(filepath)
    report = TransformationService.get_null_report(df)
    return jsonify({"success": True, "null_report": report})

# ----------------------------------------------------------
@main_bp.route('/transform', methods=['POST'])
def transform_data():
    filename = request.form.get('filename')
    action = request.form.get('action')
    params = request.form.to_dict()
    
    # Logic: Always prefer the 'transformed_' file if it exists
    original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    transformed_filename = f"transformed_{filename.split('transformed_')[-1]}"
    transformed_path = os.path.join(current_app.config['UPLOAD_FOLDER'], transformed_filename)
    
    current_path = transformed_path if os.path.exists(transformed_path) else original_path
    
    try:
        df = pd.read_csv(current_path)
        new_df, error = TransformationService.apply_transform(df, action, params)
        if error: return jsonify({"success": False, "error": error})
        
        # Save change to copy
        new_df.to_csv(transformed_path, index=False)
        
        # Re-analyze the NEW dataframe
        analysis = DataService.analyze_dataframe(new_df)
        table_html = new_df.head(10).to_html(classes='table table-sm table-striped border', index=False)
        
        return jsonify({
            "success": True, 
            "new_table": table_html,
            "new_rows": len(new_df),
            "new_cols": len(new_df.columns),
            "new_filename": transformed_filename,
            "analysis": analysis,
            "all_cols": list(new_df.columns) # Essential for updating dropdowns
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    

@main_bp.route('/delete_dataset', methods=['POST'])
def delete_dataset():
    filename = request.form.get('filename')
    if not filename:
        return jsonify({"success": False, "error": "No filename provided"}), 400

    try:
        # 1. Define paths for both original and transformed versions
        # We strip 'transformed_' prefix to find the root name for DB cleanup
        root_name = filename.replace('transformed_', '')
        original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], root_name)
        transformed_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        # 2. Physically remove files from the 'uploads' folder
        for path in [original_path, transformed_path]:
            if os.path.exists(path):
                os.remove(path)

        # 3. Remove metadata from Database
        record = DatasetMetadata.query.filter_by(filename=root_name).first()
        if record:
            db.session.delete(record)
            db.session.commit()

        return jsonify({"success": True, "message": "Dataset purged successfully"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500