# app/cian_dashboard.py - Improved version
import os
import threading
from pathlib import Path
from typing import Optional, Union

import dash
from dash import html, dcc, clientside_callback, ClientsideFunction
from flask_caching import Cache
import logging
import json

from app.layout import create_app_layout
from app.dashboard_callbacks import register_all_callbacks
from app.app_config import AppConfig
from app.data_manager import DataManager

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(H:%M:%S [%(levelname)s)] - %(message)s",
)
logger = logging.getLogger(__name__)


def initialize_app(data_dir: Optional[Union[str, Path]] = None) -> dash.Dash:
    """Initialize the Dash app with improved asynchronous data loading."""
    try:
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

        # 4) Simple in‑process cache with 5-minute TTL
        cache = Cache(app.server, config={
            "CACHE_TYPE": "simple",
            "CACHE_DEFAULT_TIMEOUT": 300,
        })

        @cache.memoize()
        def _get_main_df_and_time():
            """Use DataManager — runs at most once per TTL."""
            df, update_time = DataManager.load_and_process_data()
            logger.info(f"→ DataManager returned {len(df)} rows, updated at {update_time}")
            return df, update_time

        # 5) Layout function - returns shell immediately
        def serve_layout():
            try:
                return create_app_layout(
                    app,
                    initial_records=[],  # Empty initially
                    initial_update_time="Загрузка данных...",
                )
            except Exception as e:
                logger.error(f"Error in serve_layout: {e}", exc_info=True)
                return html.Div(
                    [
                        html.H2("Error building layout", style={"color": "red"}),
                        html.Pre(str(e), style={"whiteSpace": "pre-wrap", "padding": "1em"}),
                    ]
                )

        app.layout = serve_layout

        # 6) Assets & callbacks
        _setup_image_directory(assets_path)
        register_all_callbacks(app)
        
        # 7) Background data loading using clientside approach
        def prime_cache_in_background():
            try:
                logger.info("Background thread: Priming DataManager cache...")
                df, update_time = _get_main_df_and_time()
                
                logger.info(f"Background thread: DataManager cache primed with {len(df)} rows.")
                
                # Also start preloading detail files after main data is loaded
                DataManager.preload_detail_files()
            except Exception as e:
                logger.error(f"Background thread: Failed to prime cache: {e}", exc_info=True)
        
        # Start background thread for asynchronous cache priming
        threading.Thread(target=prime_cache_in_background, daemon=True).start()
        logger.info("Started background cache priming thread")


        @app.callback(
            [
                dash.Output("apartment-data-store", "data"),
                dash.Output("last-update-time", "children"),
                dash.Output("data-check-interval", "disabled"),
            ],
            [dash.Input("data-check-interval", "n_intervals")],
            prevent_initial_call=False,
        )
        def update_data_when_ready(n_intervals):
            logger.debug(f"[data-check] tick #{n_intervals}")
            try:
                df, update_time = _get_main_df_and_time()
        
                # still loading?
                if df.empty:
                    return [], "Загрузка данных...", False
        
                # success: we have rows
                if "details" not in df.columns:
                    df["details"] = "🔍"
                records = df.to_dict("records")
                logger.info(f"Data loaded to UI: {len(records)} records")
        
                # only disable after successful load
                return records, f"Обновлено: {update_time}", True
        
            except Exception as e:
                logger.error(f"Error loading data: {e}", exc_info=True)
                # keep polling on transient errors
                return [], f"Ошибка загрузки данных: {e}", False


        logger.info("Application initialized successfully")
        return app

    except Exception as e:
        logger.error(f"Error initializing application: {e}", exc_info=True)
        fallback = dash.Dash(__name__, title="Error")
        fallback.layout = html.Div(
            [
                html.H2("Error Initializing Application", style={"color": "red"}),
                html.Pre(str(e), style={"whiteSpace": "pre-wrap", "padding": "1em"}),
            ]
        )
        return fallback


def _prepare_assets_directory() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    assets = os.path.join(here, "assets")
    os.makedirs(assets, exist_ok=True)
    logger.info(f"Using assets directory: {assets}")
    return assets


def _setup_image_directory(assets_path: str) -> None:
    """Setup image directory with better error handling for cloud environments."""
    from app.app_config import AppConfig

    images_dir = AppConfig.get_images_path()
    target = os.path.join(assets_path, "images")
    
    # Skip if target already exists
    if os.path.exists(target):
        logger.info(f"Images directory already exists: {target}")
        return
        
    try:
        # First try to create the directory without symlink
        os.makedirs(target, exist_ok=True)
        logger.info(f"Created images directory: {target}")
        
        # If we need to copy/link files from images_dir to target,
        # we could do that here in a future enhancement
    except Exception as e:
        # Log but don't fail the app initialization
        logger.error(f"Warning: Could not setup images directory: {e}")
        logger.info("Continuing without images directory setup")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app = initialize_app()
    logger.info(f"Starting server on port {port}")
    app.run_server(debug=True, host="0.0.0.0", port=port)