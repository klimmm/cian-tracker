# app/cian_dashboard.py
import os
import dash
from dash import dcc
import logging
from app.layout import create_app_layout
from app.dashboard_callbacks import register_all_callbacks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Get the root directory (where main.py is located)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

                
def initialize_app():
    """Initialize the Dash application with proper configuration."""
    # Get current directory to set up assets properly
    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_path = os.path.join(current_dir, "assets")

    # Initialize the app with proper assets configuration
    app = dash.Dash(
        __name__,
        title="",
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
        suppress_callback_exceptions=True,
        assets_folder=assets_path,
    )

    # Create assets directory structure if it doesn't exist
    if not os.path.exists(assets_path):
        os.makedirs(assets_path)

    # Link the root images directory to the assets folder
    setup_image_directory(ROOT_DIR, assets_path)

    server = app.server

    # Add custom CSS for styling
    app.index_string = """
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    """

    # Create additional data store components for caching
    apartment_data_store = dcc.Store(
        id="apartment-data-store", storage_type="memory", data=[]
    )

    # Get base layout from layout module
    base_layout = create_app_layout(app)

    # Add our new data store to the layout
    if isinstance(base_layout, dash.html.Div) and hasattr(base_layout, "children"):
        if isinstance(base_layout.children, list):
            base_layout.children.append(apartment_data_store)
        else:
            base_layout.children = [base_layout.children, apartment_data_store]

    # Set the app layout
    app.layout = base_layout

    return app


def setup_image_directory(root_dir, assets_path):
    """Set up image directory with proper linking."""
    # Point to images directory in ROOT_DIR
    images_dir = os.path.join(root_dir, "images")
    assets_images_dir = os.path.join(assets_path, "images")

    logger.info(f"Source images directory: {images_dir}")
    logger.info(f"Target assets images directory: {assets_images_dir}")

    if os.path.exists(images_dir) and not os.path.exists(assets_images_dir):
        try:
            # Create platform-appropriate symlinks
            if os.name == "nt":  # Windows
                try:
                    # Try directory junction on Windows
                    import subprocess
                    subprocess.run(
                        ["mklink", "/J", assets_images_dir, images_dir], 
                        shell=True, 
                        check=False
                    )
                    logger.info(f"Created Windows directory junction from {images_dir} to {assets_images_dir}")
                except Exception as e:
                    logger.warning(f"Could not create directory junction: {e}")
                    # Fall back to creating a folder with a note
                    if not os.path.exists(assets_images_dir):
                        os.makedirs(assets_images_dir)
                        with open(os.path.join(assets_images_dir, "README.txt"), "w") as f:
                            f.write(f"Images should be accessed from: {images_dir}")
                        logger.warning(f"Created placeholder directory with README at {assets_images_dir}")
            else:  # Unix-like
                try:
                    # Create a symbolic link
                    os.symlink(images_dir, assets_images_dir)
                    logger.info(f"Created symlink from {images_dir} to {assets_images_dir}")
                except Exception as e:
                    logger.warning(f"Could not create symlink: {e}")
        except Exception as e:
            logger.error(f"Error setting up image directory: {e}")
    elif os.path.exists(assets_images_dir):
        logger.info(f"Assets images directory already exists: {assets_images_dir}")
    else:
        logger.warning(f"Source images directory not found: {images_dir}")


def run_server(app, debug=True, port=8050):
    """Run the Dash server with specified configuration."""
    port = int(os.environ.get("PORT", port))
    app.run_server(debug=debug, host="0.0.0.0", port=port)


if __name__ == "__main__":
    # Initialize the application
    app = initialize_app()
    
    # Register all callbacks
    register_all_callbacks(app)
    
    # Run the server
    run_server(app, debug=True)