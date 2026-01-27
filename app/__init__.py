import os
from flask import Flask

def create_app():
    app = Flask(__name__)

    # Logic: If running on a cloud server, use the Volume path. 
    # If running on your laptop, use a local folder.
    if os.environ.get('RENDER') or os.environ.get('RAILWAY_STATIC_URL'):
        # This points to the "Bucket" / Volume we just created
        app.config['UPLOAD_FOLDER'] = '/app/uploads'
    else:
        # This points to your local folder on your computer
        app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

    # Ensure the folder actually exists inside the Volume
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ... (rest of your init_app and blueprints)
    return app
