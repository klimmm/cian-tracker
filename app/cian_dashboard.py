# app/cian_dashboard.py
import os
import dash
from dash import dcc
import logging
from app.layout import create_app_layout
from app.dashboard_callbacks import register_all_callbacks
from app.app_config import AppConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def initialize_app(data_dir=None):
    """Initialize the Dash application with proper configuration."""
    # Initialize AppConfig
    AppConfig.initialize(data_dir)
    logger.info(f"Using data directory: {AppConfig.get_data_dir()}")
    
    # Get assets path from AppConfig
    assets_path = AppConfig.get_path("assets")
    logger.info(f"Assets path: {assets_path}")
    
    # Ensure the assets directory exists
    if not os.path.exists(assets_path):
        os.makedirs(assets_path)

    # Initialize the app with proper assets configuration
    app = dash.Dash(
        __name__,
        title="Cian Apartment Dashboard",
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
        suppress_callback_exceptions=True,
        assets_folder=str(assets_path),
    )

    # Set up images directory links
    setup_image_directory(assets_path)

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

    # Add our data store to the layout
    if isinstance(base_layout, dash.html.Div) and hasattr(base_layout, "children"):
        if isinstance(base_layout.children, list):
            base_layout.children.append(apartment_data_store)
        else:
            base_layout.children = [base_layout.children, apartment_data_store]

    # Set the app layout
    app.layout = base_layout

    # Register callbacks
    register_all_callbacks(app)

    return app


def setup_image_directory(assets_path):
    """Set up image directory with proper linking."""
    # Get image directories
    images_dir = AppConfig.get_images_path()
    assets_images_dir = assets_path / "images"

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
                        ["mklink", "/J", str(assets_images_dir), str(images_dir)], 
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
    app = initialize_app()
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))