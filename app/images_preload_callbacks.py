import logging
from dash import Input, Output, State
from app.image_loader import ImageLoader

logger = logging.getLogger(__name__)


def images_preload_callbacks(app):
    @app.callback(
        Output("image-preload-trigger", "data"),
        [
            Input("apartment-table", "data"),
            Input("apartment-table", "page_current"),
            Input("apartment-table", "page_size"),
        ],
        [State("image-preload-trigger", "data")],
        prevent_initial_call=False,
    )
    def start_image_preloading(table_data, page_current, page_size, current_status):
        """Begin preloading images for apartments that are visible in the table."""
        # Skip if no data
        if not table_data or len(table_data) == 0:
            return current_status or {"status": "no_data", "preloading_started": False}
            
        # Check if we've already started preloading from current status
        # This keeps state in the store itself rather than using nonlocal variables
        if current_status and current_status.get("preloading_started"):
            return current_status
            
        # Use the ImageLoader's new method to handle preloading
        preloading_success = ImageLoader.preload_visible_apartments(
            table_data, 
            page_current, 
            page_size
        )
        
        # Return the updated status
        return {"status": "preloading_started" if preloading_success else "preload_failed", 
                "preloading_started": preloading_success}