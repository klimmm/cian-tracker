# wsgi.py
import os
import sys

# Ensure the current directory is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the application initialization function
from app.cian_dashboard import initialize_app

# Initialize the app with explicit path to data directory
app = initialize_app(data_dir=os.environ.get('DATA_DIR', os.path.dirname(os.path.abspath(__file__))))

# Get the server instance from the app
server = app.server

# Run the app if this file is executed directly
if __name__ == '__main__':
    app.run_server(debug=True)