# wsgi.py
from app.cian_dashboard import initialize_app

# Initialize the app
app = initialize_app()
server = app.server

if __name__ == '__main__':
    app.run_server(debug=True)