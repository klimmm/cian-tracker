# app/table_callbacks.py

import logging
import pandas as pd
from dash import Input, Output
import dash
from app.data_filter import DataFilterSorter
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
            logger.warning("No data available for table update")
            return [], []
    
        try:
            t0 = perf_counter()
    
            # Convert to DataFrame for processing
            df = pd.DataFrame(data)
            
            # Add debug logging
            logger.debug(f"DataFrame has {len(df)} rows and {len(df.columns)} columns")
            logger.debug(f"First 10 column names: {list(df.columns)[:10]}")
    
            # Log which input triggered the callback
            trigger = (
                ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
            )
            logger.debug(f"Table update triggered by: {trigger} with sort_by: {sort_by}")
    
            # Apply filtering and sorting
            df = DataFilterSorter.filter_and_sort_data(df, filters or {}, sort_by)
            logger.debug(f"After filtering: {len(df)} rows")
    
            # Define which columns to display
            visible_columns = [
                "update_title",
                "property_tags",
                "address_title",
                'condition_summary',            
                "price_text",
            ]
            
            # Check if these columns exist in the DataFrame
            for col in visible_columns:
                logger.debug(f"Column '{col}' exists in DataFrame: {col in df.columns}")
            
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
                'condition_summary',
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
            
            # Log final column configuration
            logger.debug(f"Final column configuration: {columns}")
            logger.debug(f"Column count after filtering: {len(columns)}")
    
            elapsed = perf_counter() - t0
            logger.info(f"[TIMER] update_table_content → {elapsed:.3f}s")
    
            return df.to_dict("records"), columns
    
        except Exception as e:
            logger.error(f"Error updating table: {e}", exc_info=True)
            return [], []
