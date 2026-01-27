import os
import pandas as pd
from flask import Blueprint, render_template, request, current_app, jsonify
from werkzeug.utils import secure_filename

# Relative imports for the App Factory structure
from .processor import DataService, TransformationService
from .models import db, DatasetMetadata

# Define the Blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Main upload page"""
    return render_template('index.html')

@main_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handles the file upload and initial analysis"""
    # 1. Grab the file from the request
    # 'file' must match the 'name' attribute in your HTML <input>
    file = request.files.get('file')
    
    if not file or file.filename == '':
        return render_template('index.html', error="No file selected. Please try again.")
    
    # 2. Secure the filename and build the path
    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    try:
        # 3. Save the physical file to the server
        file.save(filepath)
        
        # 4. Load into Pandas based on file type
        if filename.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(filepath)
        else:
            return render_template('index.html', error="Unsupported file format.")

        # 5. Log the upload in our Database (Metadata)
        # Check if record already exists to avoid duplicates
        existing = DatasetMetadata.query.filter_by(filename=filename).first()
        if not existing:
            new_dataset = DatasetMetadata(filename=filename)
            db.session.add(new_dataset)
            db.session.commit()

        # 6. Run the Initial Analysis Service
        analysis = DataService.analyze_dataframe(df)
        
        # 7. Render the Dashboard with the data
        return render_template(
            'dashboard.html', 
            filename=filename, 
            analysis=analysis, 
            rows=len(df), 
            cols=len(df.columns),
            table=df.head(10).to_html(classes='table table-sm table-striped border', index=False)
        )

    except Exception as e:
        # If anything fails, return to index and show the error instead of crashing
        print(f"Deployment Error: {str(e)}")
        return render_template('index.html', error=f"Processing Error: {str(e)}")

@main_bp.route('/check_nulls', methods=['POST'])
def check_nulls():
    """Returns a JSON report of missing values"""
    filename = request.form.get('filename')
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    try:
        df = pd.read_csv(filepath) if filename.endswith('.csv') else pd.read_excel(filepath)
        report = TransformationService.get_null_report(df)
        return jsonify({"success": True, "null_report": report})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@main_bp.route('/transform', methods=['POST'])
def transform_data():
    """Handles data cleaning like dropping columns or nulls"""
    filename = request.form.get('filename')
    action = request.form.get('action')
    params = request.form.to_dict()
    
    # Path logic: Use transformed file if it already exists, otherwise original
    original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    transformed_filename = f"transformed_{filename.split('transformed_')[-1]}"
    transformed_path = os.path.join(current_app.config['UPLOAD_FOLDER'], transformed_filename)
    
    load_path = transformed_path if os.path.exists(transformed_path) else original_path
    
    try:
        df = pd.read_csv(load_path) if load_path.endswith('.csv') else pd.read_excel(load_path)
        
        # Apply the transformation from the Service
        new_df, error = TransformationService.apply_transform(df, action, params)
        if error:
            return jsonify({"success": False, "error": error})

        # Save to the transformed path
        if transformed_path.endswith('.csv'):
            new_df.to_csv(transformed_path, index=False)
        else:
            new_df.to_excel(transformed_path, index=False)
            
        # Re-run analysis for the updated UI
        analysis = DataService.analyze_dataframe(new_df)
        table_html = new_df.head(10).to_html(classes='table table-sm table-striped border', index=False)
        
        return jsonify({
            "success": True, 
            "new_table": table_html,
            "new_rows": len(new_df),
            "new_cols": len(new_df.columns),
            "new_filename": transformed_filename,
            "analysis": analysis,
            "all_cols": list(new_df.columns)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@main_bp.route('/generate_plot', methods=['POST'])
def generate_plot():
    """Handles dynamic plot generation via AJAX"""
    filename = request.form.get('filename')
    plot_type = request.form.get('plot_type')
    x_col = request.form.get('x_col')
    y_col = request.form.get('y_col')
    
    # Check transformed file first
    transformed_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    try:
        df = pd.read_csv(transformed_path) if filename.endswith('.csv') else pd.read_excel(transformed_path)
        plot_b64 = DataService.generate_custom_plot(df, plot_type, x_col, y_col)
        return jsonify({"success": True, "plot_data": plot_b64})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@main_bp.route('/delete_dataset', methods=['POST'])
def delete_dataset():
    """Removes files and database records"""
    filename = request.form.get('filename')
    try:
        # Clean up files
        root_name = filename.replace('transformed_', '')
        original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], root_name)
        transformed_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        for path in [original_path, transformed_path]:
            if os.path.exists(path):
                os.remove(path)

        # Clean up DB
        DatasetMetadata.query.filter_by(filename=root_name).delete()
        db.session.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
