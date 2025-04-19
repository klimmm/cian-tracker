import os
import threading
from pathlib import Path
from typing import Optional, Union

import dash
from flask_caching import Cache
import logging

from app.layout import create_app_layout
from app.dashboard_callbacks import register_all_callbacks
from app.app_config import AppConfig
from app.data_manager import data_manager

# ─── Logging configuration ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(H:%M:%S [%(levelname)s)] - %(message)s",
)
logger = logging.getLogger(__name__)

def initialize_app(data_dir: Optional[Union[str, Path]] = None) -> dash.Dash:
    """Initialize the Dash app with cached, TTL‑backed data loading."""
    # 1) AppConfig
    AppConfig.initialize(data_dir)
    logger.info(f"Using data directory: {AppConfig.get_data_dir()}")

    # 2) Prepare assets folder
    assets_path = _prepare_assets_directory()

    # 3) Create Dash app
    app = dash.Dash(
        __name__,
        title="Cian Apartment Dashboard",
        suppress_callback_exceptions=True,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
        assets_folder=assets_path,
    )
    server = app.server

    # 4) Filesystem cache (shared by all workers) with 5‑minute TTL
    os.makedirs("/tmp/flask_cache", exist_ok=True)
    cache = Cache(server, config={
        "CACHE_TYPE": "filesystem",
        "CACHE_DIR":  "/tmp/flask_cache",
        "CACHE_DEFAULT_TIMEOUT": 1,  # seconds
    })

    @cache.memoize()
    def get_df_and_time():
        """Load and memoize DataFrame + timestamp."""
        df, ts = data_manager.load_and_process_data()
        logger.info(f"Fetched {len(df)} rows at {ts}")
        #data_manager.debug_offer_id('316502880')

        return df, ts

    # 5) Layout callable: runs on every browser refresh
    def serve_layout():
        df, ts = get_df_and_time()
        # Remove this redundant line:
        # data_manager.update_main_fields_from_df(df)
        
        return create_app_layout(
            app,
            initial_records=df.to_dict("records"),
            initial_update_time=f"Обновлено: {ts}",
        )

    app.layout = serve_layout

    # 6) Assets & register callbacks
    _setup_image_directory(assets_path)
    register_all_callbacks(app)

    # 7) Preload detail files in background (optional)

    logger.info("Application initialized successfully")
    return app


# ─── Helper functions ───────────────────────────────────────────────────────

def _prepare_assets_directory() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    assets = os.path.join(here, "assets")
    os.makedirs(assets, exist_ok=True)
    logger.info(f"Using assets directory: {assets}")
    return assets


def _setup_image_directory(assets_path: str) -> None:
    """Ensure the images directory exists for Dash assets."""
    from app.app_config import AppConfig

    images_dir = AppConfig.get_images_path()
    target = os.path.join(assets_path, "images")
    if os.path.exists(target):
        logger.info(f"Images directory already exists: {target}")
        return
    try:
        os.makedirs(target, exist_ok=True)
        logger.info(f"Created images directory: {target}")
    except Exception as e:
        logger.error(f"Warning: Could not setup images directory: {e}")
        logger.info("Continuing without images directory setup")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app = initialize_app()
    logger.info(f"Starting server on port {port}")
    app.run_server(debug=True, host="0.0.0.0", port=port)