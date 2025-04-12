# app/cian_dashboard.py
import os
import dash
from dash import dcc
import logging
import subprocess
from pathlib import Path
from typing import Optional, Union, Tuple

from app.layout import create_app_layout
from app.dashboard_callbacks import register_all_callbacks
from app.app_config import AppConfig
from app.utils import ErrorHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def initialize_app(data_dir: Optional[Union[str, Path]] = None) -> dash.Dash:
    """Initialize the Dash application with proper configuration."""
    # Initialize AppConfig
    AppConfig.initialize(data_dir)
    logger.info(f"Using data directory: {AppConfig.get_data_dir()}")
    
    # Get current directory for proper assets location
    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_path = os.path.join(current_dir, "assets")
    
    # Log the paths for debugging
    logger.info(f"Current directory: {current_dir}")
    logger.info(f"Assets path: {assets_path}")

    # Validate assets path
    validate_assets_exists(assets_path)

    # Initialize the app with proper assets configuration
    app = create_dash_app(assets_path)

    # Set up the app layout
    setup_app_layout(app)
    
    # Register callbacks
    register_all_callbacks(app)

    return app


def create_dash_app(assets_path: str) -> dash.Dash:
    """Create and configure the Dash application."""
    app = dash.Dash(
        __name__,
        title="Cian Apartment Dashboard",
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
        suppress_callback_exceptions=True,
        assets_folder=assets_path,
    )

    # Ensure assets directory exists
    if not os.path.exists(assets_path):
        os.makedirs(assets_path)
        logger.warning(f"Created missing assets directory: {assets_path}")

    # Link the image directory to the assets folder
    setup_image_directory(assets_path)

    # Add custom HTML template
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
    
    return app


def setup_app_layout(app: dash.Dash) -> None:
    """Set up the application layout."""
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


def validate_assets_exists(assets_path: str) -> bool:
    """Validate that the assets directory exists and contains required files."""
    # Check if directory exists
    if not os.path.exists(assets_path):
        logger.warning(f"Assets directory not found: {assets_path}")
        try:
            os.makedirs(assets_path)
            logger.info(f"Created assets directory: {assets_path}")
        except Exception as e:
            logger.error(f"Failed to create assets directory: {e}")
            return False
    
    # Check for specific assets
    expected_files = ["custom.css", "tag_click.js"]
    found_files = []
    
    for file in expected_files:
        file_path = os.path.join(assets_path, file)
        if os.path.exists(file_path):
            found_files.append(file)
    
    if len(found_files) == len(expected_files):
        logger.info(f"All expected assets found: {', '.join(found_files)}")
    else:
        missing = [f for f in expected_files if f not in found_files]
        logger.warning(f"Missing assets: {', '.join(missing)}")
        
    return len(found_files) == len(expected_files)


def setup_image_directory(assets_path: str) -> None:
    """Set up image directory with proper linking."""
    # Get image directory from AppConfig
    images_dir = AppConfig.get_images_path()
    assets_images_dir = os.path.join(assets_path, "images")

    logger.info(f"Source images directory: {images_dir}")
    logger.info(f"Target assets images directory: {assets_images_dir}")

    if os.path.exists(images_dir) and not os.path.exists(assets_images_dir):
        ErrorHandler.try_operation(
            logger, 
            "image_directory_setup", 
            _create_directory_link,
            images_dir, assets_images_dir
        )
    elif os.path.exists(assets_images_dir):
        logger.info(f"Assets images directory already exists: {assets_images_dir}")
    else:
        logger.warning(f"Source images directory not found: {images_dir}")


def _create_directory_link(source_dir: Union[str, Path], target_dir: Union[str, Path]) -> None:
    """Create a platform-appropriate directory link."""
    try:
        if os.name == "nt":  # Windows
            try:
                # Try directory junction on Windows
                subprocess.run(
                    ["mklink", "/J", str(target_dir), str(source_dir)], 
                    shell=True, 
                    check=False
                )
                logger.info(f"Created Windows directory junction from {source_dir} to {target_dir}")
            except Exception as e:
                logger.warning(f"Could not create directory junction: {e}")
                # Fall back to creating a folder with a note
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                    with open(os.path.join(target_dir, "README.txt"), "w") as f:
                        f.write(f"Images should be accessed from: {source_dir}")
                    logger.warning(f"Created placeholder directory with README at {target_dir}")
        else:  # Unix-like
            try:
                # Create a symbolic link
                os.symlink(source_dir, target_dir)
                logger.info(f"Created symlink from {source_dir} to {target_dir}")
            except Exception as e:
                logger.warning(f"Could not create symlink: {e}")
    except Exception as e:
        raise RuntimeError(f"Error creating directory link: {e}")


def run_server(app: dash.Dash, debug: bool = True, port: int = 8050) -> None:
    """Run the Dash server with specified configuration."""
    port = int(os.environ.get("PORT", port))
    app.run_server(debug=debug, host="0.0.0.0", port=port)


if __name__ == "__main__":
    app = initialize_app()
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))