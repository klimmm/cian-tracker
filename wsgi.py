# wsgi.py
import os
import sys

# Ensure the current directory is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.cian_dashboard import initialize_app, register_callbacks

# Initialize the app with explicit path to data directory
app = initialize_app(data_dir=os.environ.get('DATA_DIR', os.path.dirname(os.path.abspath(__file__))))

# Register callbacks after app initialization
register_callbacks(app)

server = app.server

if __name__ == '__main__':
    app.run_server(debug=True)