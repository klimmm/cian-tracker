# app/table_callbacks.py

import logging
import pandas as pd
from dash import Input, Output, State
import dash
from app.data_filter import DataFilterSorter
from app.data_manager import ImageLoader
from app.config import CONFIG
from time import perf_counter

logger = logging.getLogger(__name__)


def register_data_callbacks(app):

    @app.callback(
        Output("preload-status-store", "data"),
        Input("apartment-data-store", "data"),
        prevent_initial_call=False,
    )
    def start_background_preloading(main_data):
        """Start background preloading after data is available"""
        # Only start preloading if we have main data
        if not main_data or len(main_data) == 0:
            return {"status": "waiting_for_data"}

        return {"status": "loading_started"}

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
        """Begin preloading images for apartments that are actually visible in the table, with pagination support."""
        # Skip if no data
        if not table_data or len(table_data) == 0:
            return current_status or {"status": "no_data", "preloading_started": False}

        # Check if we've already started preloading from current status
        # This keeps state in the store itself rather than using nonlocal variables
        if current_status and current_status.get("preloading_started"):
            return current_status

        # Calculate visible page if pagination is active
        start_idx = 0
        end_idx = 10  # Default to first 10 if pagination not set

        if page_current is not None and page_size is not None:
            start_idx = page_current * page_size
            end_idx = start_idx + page_size

        # Ensure end_idx is within bounds
        end_idx = min(end_idx, len(table_data))

        # Start a background thread to preload images
        import threading

        def background_image_loader():
            try:
                # Extract offer_ids from the visible apartments
                visible_apartments = table_data[start_idx:end_idx]
                offer_ids = [
                    row.get("offer_id")
                    for row in visible_apartments
                    if row.get("offer_id")
                ]

                if offer_ids:
                    logger.info(
                        f"🚀 IMAGE PRELOAD: Starting preload of {min(3, len(offer_ids))} visible apartments: {offer_ids[:3]}"
                    )
                    # Start with just the first 3 for immediate response
                    first_batch = offer_ids[:3]
                    ImageLoader.preload_images_for_apartments(first_batch, limit=3)

                    # After a brief delay, load the rest
                    import time

                    time.sleep(1)

                    # Load the next batch
                    next_batch = offer_ids[3:]
                    if next_batch:
                        logger.info(
                            f"🚀 IMAGE PRELOAD: Starting second batch of {len(next_batch)} more visible apartments"
                        )
                        ImageLoader.preload_images_for_apartments(
                            next_batch, limit=len(next_batch)
                        )
            except Exception as e:
                logger.error(f"❌ IMAGE PRELOAD: Error in background preloader: {e}")

        # Start background thread
        logger.info(
            f"🚀 IMAGE PRELOAD: Initializing preloader for page {page_current}, size {page_size}"
        )
        thread = threading.Thread(target=background_image_loader)
        thread.daemon = True
        thread.start()

        return {"status": "preloading_started", "preloading_started": True}

def register_table_callbacks(app):

    @app.callback(
        [
            Output("apartment-table", "data"),
            Output("apartment-table", "columns"),
        ],
        [
            Input("filter-store", "data"),
            Input("apartment-data-store", "data"),
            Input("apartment-table", "sort_by"),
        ],
        running=[
            (
                Output("table-container", "className"),
                "table-responsive table-loading",
                "table-responsive",
            )
        ],
    )
    def update_table_content(filters, data, sort_by):
        """Update table based on filters, data and sorting in a single callback."""
        ctx = dash.callback_context

        # Always process if we have data
        if not data:
            return [], []

        try:
            t0 = perf_counter()

            # Convert to DataFrame for processing
            df = pd.DataFrame(data)

            # Log which input triggered the callback
            trigger = (
                ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
            )
            logger.info(f"Table update triggered by: {trigger} with sort_by: {sort_by}")

            # Apply filtering and sorting
            df = DataFilterSorter.filter_and_sort_data(df, filters or {}, sort_by)

            # Define which columns to display
            visible_columns = [
                "update_title",
                "property_tags",
                "address_title",
                "price_text",
            ]
            numeric_columns = {
                "distance",
                "price_value_formatted",
                "cian_estimation_formatted",
                "price_difference_formatted",
                "monthly_burden_formatted",
            }
            markdown_columns = {
                "price_change_formatted",
                "address_title",
                "offer_link",
                "price_info",
                "update_title",
                "property_tags",
                "price_change",
                "walking_time",
                "price_text",
                "days_active",
                "activity_date",
            }

            # Build the column definitions
            columns = [
                {
                    "name": CONFIG["columns"]["headers"].get(c, c),
                    "id": c,
                    "type": "numeric" if c in numeric_columns else "text",
                    "presentation": "markdown" if c in markdown_columns else None,
                }
                for c in visible_columns
                if c in df.columns
            ]

            elapsed = perf_counter() - t0
            logger.info(f"[TIMER] update_table_content → {elapsed:.3f}s")

            return df.to_dict("records"), columns

        except Exception as e:
            logger.error(f"Error updating table: {e}")
            return [], []
