import os
import io
import base64
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import google.generativeai as genai
from flask import Blueprint, render_template, request, current_app, jsonify
from werkzeug.utils import secure_filename
from .models import db, DatasetMetadata

# Configuration for plots
plt.switch_backend('Agg') 
sns.set_theme(style="whitegrid")

main_bp = Blueprint('main', __name__)

# --- HELPER LOGIC: AI ANALYST ---
def get_gemini_analysis(data_summary, context="initial upload"):
    """Internal logic to talk to Gemini without a separate file."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "AI Insights: API Key missing in Environment Variables."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Context: {context}
        System: You are a professional data scientist.
        Data Summary: {data_summary}
        
        Task: Provide 3-4 bullet points of high-level insights. 
        Focus on trends, potential outliers, and a suggestion for a visualization.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"

# --- ROUTES ---

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/upload', methods=['POST'])
def upload_file():
    # 1. SECURITY GUARD: Check if the 'file' key exists in HTML
    if 'file' not in request.files:
        return render_template('index.html', error="No file part. Check your HTML 'name' attribute.")

    file = request.files['file']

    if file.filename == '':
        return render_template('index.html', error="No file selected.")

    if file:
        try:
            # 2. PATH LOGIC: Get the absolute path to the 'uploads' folder
            # This is the #1 reason for refreshes on cloud servers
            upload_dir = current_app.config['UPLOAD_FOLDER']
            
            # Create the folder if it's missing (Crucial for Render/Railway)
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)

            filename = secure_filename(file.filename)
            filepath = os.path.join(upload_dir, filename)

            # 3. SAVE ACTION
            file.save(filepath)

            # 4. PANDAS PROCESSING
            if filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)

            # Generate stats for the dashboard
            analysis = {
                "columns": list(df.columns),
                "summary": df.describe().to_html(classes='table table-sm')
            }

            # 5. GEMINI AI: Get the initial story
            summary_for_ai = df.describe(include='all').to_string()
            ai_insights = get_gemini_analysis(summary_for_ai)

            return render_template(
                'dashboard.html',
                filename=filename,
                analysis=analysis,
                ai_insights=ai_insights,
                rows=len(df),
                cols=len(df.columns),
                table=df.head(10).to_html(classes='table table-sm table-striped', index=False)
            )

        except Exception as e:
            # If it crashes here, it shows the error instead of refreshing
            print(f"UPLOAD CRASH: {str(e)}")
            return render_template('index.html', error=f"File Error: {str(e)}")

@main_bp.route('/transform', methods=['POST'])
def transform_data():
    """Handles the 'Group By' and 'Filter' logic directly."""
    filename = request.form.get('filename')
    action = request.form.get('action')
    
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    try:
        df = pd.read_csv(filepath) if filename.endswith('.csv') else pd.read_excel(filepath)
        
        # --- TRANSFORMATION LOGIC ---
        new_df = df.copy() # Protect original data
        
        if action == 'groupby':
            group_col = request.form.get('group_col')
            agg_col = request.form.get('agg_col')
            agg_func = request.form.get('agg_func', 'mean').lower()
            
            if group_col and agg_col:
                new_df = new_df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
            else:
                return jsonify({"success": False, "error": "Missing columns for aggregation."})

        elif action == 'drop_na':
            new_df = new_df.dropna()

        # Save the result
        new_filename = f"transformed_{filename}"
        new_path = os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename)
        new_df.to_csv(new_path, index=False) if new_filename.endswith('.csv') else new_df.to_excel(new_path, index=False)

        # Re-run AI for the new data shape
        ai_update = get_gemini_analysis(new_df.head(20).to_string(), context=f"Analysis after {action} operation")

        return jsonify({
            "success": True,
            "new_table": new_df.head(10).to_html(classes='table table-sm', index=False),
            "new_filename": new_filename,
            "ai_insights": ai_update,
            "new_rows": len(new_df),
            "new_cols": len(new_df.columns),
            "all_cols": list(new_df.columns)
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@main_bp.route('/generate_plot', methods=['POST'])
def generate_plot():
    """Handles the Matplotlib/Seaborn logic directly."""
    filename = request.form.get('filename')
    plot_type = request.form.get('plot_type')
    x_col = request.form.get('x_col')
    y_col = request.form.get('y_col')

    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    try:
        df = pd.read_csv(filepath) if filename.endswith('.csv') else pd.read_excel(filepath)
        
        # --- PLOTTING LOGIC ---
        plt.figure(figsize=(10, 6))
        
        if plot_type == 'bar':
            sns.barplot(data=df, x=x_col, y=y_col)
        elif plot_type == 'scatter':
            sns.scatterplot(data=df, x=x_col, y=y_col)
        elif plot_type == 'line':
            sns.lineplot(data=df, x=x_col, y=y_col)
        elif plot_type == 'hist':
            sns.histplot(data=df, x=x_col, kde=True)

        plt.xticks(rotation=45)
        plt.tight_layout()

        # Convert plot to Base64 String
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf8')
        plt.close()

        return jsonify({"success": True, "plot_data": f"data:image/png;base64,{plot_url}"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@main_bp.route('/delete_dataset', methods=['POST'])
def delete_dataset():
    filename = request.form.get('filename')
    try:
        # File deletion logic
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(path):
            os.remove(path)
            
        # DB deletion logic
        DatasetMetadata.query.filter_by(filename=filename.replace('transformed_', '')).delete()
        db.session.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

