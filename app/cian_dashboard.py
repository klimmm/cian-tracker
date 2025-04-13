# app/cian_dashboard.py
import os
import dash
import logging
from pathlib import Path
from typing import Optional, Union

from app.layout import create_app_layout
from app.dashboard_callbacks import register_all_callbacks
from app.app_config import AppConfig
from app.utils import ErrorHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

def initialize_app(data_dir: Optional[Union[str, Path]] = None) -> dash.Dash:
    """Initialize the Dash application."""
    # Initialize configuration
    AppConfig.initialize(data_dir)
    logger.info(f"Using data directory: {AppConfig.get_data_dir()}")
    
    # Prepare assets
    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_path = os.path.join(current_dir, "assets")
    
    # Ensure assets directory exists
    if not os.path.exists(assets_path):
        os.makedirs(assets_path)
        logger.info(f"Created assets directory: {assets_path}")

    # Create Dash app
    app = dash.Dash(
        __name__,
        title="Cian Apartment Dashboard",
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
        suppress_callback_exceptions=True,
        assets_folder=assets_path,
    )

    # Setup image directory
    _setup_image_directory(assets_path)
    
    # Set up app layout
    app.layout = create_app_layout(app)
    
    # Register callbacks
    register_all_callbacks(app)

    return app

def _setup_image_directory(assets_path: str) -> None:
    """Set up image directory with proper linking."""
    # Link images directory to assets
    images_dir = AppConfig.get_images_path()
    assets_images_dir = os.path.join(assets_path, "images")

    # Skip if target directory already exists
    if os.path.exists(assets_images_dir):
        logger.info(f"Assets images directory already exists: {assets_images_dir}")
        return

    # Only attempt to create link if source exists
    if os.path.exists(images_dir):
        try:
            if os.name == "nt":  # Windows
                import subprocess
                subprocess.run(["mklink", "/J", str(assets_images_dir), str(images_dir)], 
                               shell=True, check=False)
            else:  # Unix-like
                os.symlink(images_dir, assets_images_dir)
            logger.info(f"Created link from {images_dir} to {assets_images_dir}")
        except Exception as e:
            logger.warning(f"Could not create directory link: {e}")
            # Create directory instead of link if linking fails
            try:
                os.makedirs(assets_images_dir, exist_ok=True)
                logger.info(f"Created directory instead of link: {assets_images_dir}")
            except Exception as e2:
                logger.error(f"Failed to create images directory: {e2}")
                # Continue without failing - non-critical error
    else:
        # Create empty directory if source doesn't exist
        try:
            os.makedirs(assets_images_dir, exist_ok=True)
            logger.info(f"Created images directory: {assets_images_dir}")
        except Exception as e:
            logger.warning(f"Failed to create images directory: {e}")
            # Continue without failing - non-critical error

if __name__ == "__main__":
    app = initialize_app()
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=True, host="0.0.0.0", port=port)