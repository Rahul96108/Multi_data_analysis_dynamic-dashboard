import os
from werkzeug.utils import secure_filename

# Configuration for allowed formats
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.json'}

def allowed_file(filename):
    """
    Checks if the file extension is in the allowed list.
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def save_and_get_path(file, upload_folder):
    """
    Sanitizes the filename, saves it to the upload folder, 
    and returns the full path and extension.
    """
    if file and allowed_file(file.filename):
        # secure_filename prevents users from uploading files like "../../../etc/passwd"
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        ext = os.path.splitext(filename)[1].lower()
        return filepath, ext
    
    return None, None