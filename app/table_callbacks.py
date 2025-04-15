from dash.dependencies import Input, Output, State
import logging
import pandas as pd
from app.data_manager import DataManager
from app.config import CONFIG
logger = logging.getLogger(__name__)


def register_table_callbacks(app):
    @app.callback(
        [
            Output("apartment-table", "data"),
            Output("apartment-table", "columns"),
        ],
        [Input("filter-store", "data"), Input("apartment-data-store", "data")],
    )
    def update_table_content(filters, data):
        """Update table based on filters and data with added debugging."""
        if not data:
            return [], []

        try:
            # Convert to DataFrame for processing
            df = pd.DataFrame(data)

            # Apply filtering and sorting
            df = DataManager.filter_and_sort_data(df, filters or {})

            # Define which columns to display
            visible_columns = ["update_title", "address_title", "price_text", "property_tags", 'details']
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

            # Add a details column with a button if it doesn't exist
            if "details" not in df.columns:
                df["details"] = "🔍"

            # Build the column definitions
            columns = [
                {
                    "name": CONFIG["columns"]["headers"].get(
                        c, "Детали" if c == "details" else c
                    ),
                    "id": c,
                    "type": "numeric" if c in numeric_columns else "text",
                    "presentation": "markdown" if c in markdown_columns else None,
                }
                for c in visible_columns
                if c in df.columns
            ]

            return df.to_dict("records"), columns

        except Exception as e:
            print(f"Error updating table: {e}")
            return [], [], []

    # Update the sort callback to use allow_duplicate
    @app.callback(
        Output("apartment-table", "data", allow_duplicate=True),
        [Input("apartment-table", "sort_by"), Input("filter-store", "data")],
        [State("apartment-data-store", "data")],
        prevent_initial_call=True,
    )
    def update_sort(sort_by, filters, data):
        """Handle table sorting from column headers."""
        if not data:
            return []

        df = pd.DataFrame(data)
        df = DataManager.filter_and_sort_data(df, filters, sort_by)
        return df.to_dict("records")
