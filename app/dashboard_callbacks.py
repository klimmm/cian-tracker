# app/dashboard_callbacks.py - Refactored to use CSS classes
from dash import callback_context as ctx
from dash.dependencies import Input, Output, State, MATCH
import dash
import logging
import pandas as pd
from app.data_manager import DataManager, load_apartment_details
from app.apartment_card import create_apartment_details_card
from app.button_factory import PRICE_BUTTONS, DISTANCE_BUTTONS, SORT_BUTTONS
from dash import dash_table, html
from app.config import CONFIG, COLUMN_STYLES, HEADER_STYLES
from app.components import TableFactory

logger = logging.getLogger(__name__)


def register_all_callbacks(app):
    """Register all application callbacks in a structured manner."""
    register_data_callbacks(app)
    register_filter_callbacks(app)
    register_style_callbacks(app)
    register_details_callbacks(app)


def register_data_callbacks(app):
    """Register data loading and processing callbacks."""

    @app.callback(
        [
            Output("apartment-data-store", "data"),
            Output("last-update-time", "children"),
        ],
        [Input("interval-component", "n_intervals")],
        prevent_initial_call=False,
    )
    def load_apartment_data(_):
        """Load and process apartment data for display."""
        try:
            # Load data from source
            df, update_time = DataManager.load_data()
            if df.empty:
                return [], "Error: No data loaded"

            # Process the data
            df = DataManager.process_data(df)

            # Add details indicator
            if "details" not in df.columns:
                df["details"] = "🔍"

            # Get required columns
            required_cols = CONFIG["columns"]["display"] + [
                "details",
                "offer_id",
                "date_sort_combined",
            ]
            available_cols = [col for col in required_cols if col in df.columns]

            # Convert to dictionary for storage
            df_dict = df[available_cols].to_dict("records") if not df.empty else []

            return df_dict, f"Актуально на: {update_time}"

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return [], f"Ошибка загрузки данных: {str(e)}"


def register_filter_callbacks(app):
    """Register filter and sorting callbacks."""

    @app.callback(
        [Output("filter-store", "data")],
        [
            *[Input(btn["id"], "n_clicks") for btn in PRICE_BUTTONS],
            *[Input(btn["id"], "n_clicks") for btn in DISTANCE_BUTTONS],
            Input("btn-nearest", "n_clicks"),
            Input("btn-below-estimate", "n_clicks"),
            Input("btn-inactive", "n_clicks"),
            Input("btn-updated-today", "n_clicks"),
            *[Input(btn["id"], "n_clicks") for btn in SORT_BUTTONS],
        ],
        [State("filter-store", "data")],
        prevent_initial_call=True,
    )
    def update_filters(*args):
        """Update filters based on user interactions."""
        # Get triggered button
        if not (ctx_msg := ctx.triggered[0] if ctx.triggered else None):
            return [dash.no_update]

        trigger_id = ctx_msg["prop_id"].split(".")[0]
        current_filters = args[-1] or {}

        # Handle price button clicks
        if trigger_id in [btn["id"] for btn in PRICE_BUTTONS]:
            current_filters["active_price_btn"] = trigger_id
            current_filters["price_value"] = next(
                (btn["value"] for btn in PRICE_BUTTONS if btn["id"] == trigger_id),
                current_filters.get("price_value", 80000),
            )

        # Handle distance button clicks
        elif trigger_id in [btn["id"] for btn in DISTANCE_BUTTONS]:
            current_filters["active_dist_btn"] = trigger_id
            current_filters["distance_value"] = next(
                (btn["value"] for btn in DISTANCE_BUTTONS if btn["id"] == trigger_id),
                current_filters.get("distance_value", 3.0),
            )

        # Handle toggle filters
        elif trigger_id in [
            "btn-nearest",
            "btn-below-estimate",
            "btn-inactive",
            "btn-updated-today",
        ]:
            filter_key = {
                "btn-nearest": "nearest",
                "btn-below-estimate": "below_estimate",
                "btn-inactive": "inactive",
                "btn-updated-today": "updated_today",
            }[trigger_id]
            current_filters[filter_key] = not current_filters.get(filter_key, False)

        # Handle sort buttons
        elif trigger_id in [btn["id"] for btn in SORT_BUTTONS]:
            button = next(
                (btn for btn in SORT_BUTTONS if btn["id"] == trigger_id), None
            )
            if button:
                # Toggle direction if same button clicked again
                if current_filters.get("active_sort_btn") == trigger_id:
                    current_filters["sort_direction"] = (
                        "desc"
                        if current_filters.get("sort_direction") == "asc"
                        else "asc"
                    )
                else:
                    current_filters["active_sort_btn"] = trigger_id
                    current_filters["sort_column"] = button["value"]
                    current_filters["sort_direction"] = button.get(
                        "default_direction", "asc"
                    )

        return [current_filters]

    @app.callback(
        [Output("table-container", "children")],
        [Input("filter-store", "data"), Input("apartment-data-store", "data")],
    )
    def update_table_content(filters, data):
        """Update table based on filters and data."""
        if not data:
            return [html.Div("Нет данных")]

        # Convert to DataFrame for processing
        df = pd.DataFrame(data)

        # Apply filtering and sorting
        df = DataManager.filter_and_sort_data(df, filters)

        # Create and return data table
        return [create_data_table(df)]

    @app.callback(
        Output("apartment-table", "data"),
        [Input("apartment-table", "sort_by"), Input("filter-store", "data")],
        [State("apartment-data-store", "data")],
    )
    def update_sort(sort_by, filters, data):
        """Handle table sorting from column headers."""
        if not data:
            return []

        df = pd.DataFrame(data)
        df = DataManager.filter_and_sort_data(df, filters, sort_by)
        return df.to_dict("records")

    @app.callback(
        [*[Output(f"{btn['id']}-text", "children") for btn in SORT_BUTTONS]],
        [Input("filter-store", "data")],
        prevent_initial_call=False,
    )
    def update_sort_button_text(filters):
        """Update sort button text with direction indicators."""
        if not filters:
            return [btn["label"] for btn in SORT_BUTTONS]

        active_btn = filters.get("active_sort_btn")
        sort_direction = filters.get("sort_direction", "asc")

        return [
            (
                f"{btn['label']} {'↑' if sort_direction == 'asc' else '↓'}"
                if btn["id"] == active_btn
                else btn["label"]
            )
            for btn in SORT_BUTTONS
        ]


def register_style_callbacks(app):
    """Register styling callbacks for UI elements."""

    @app.callback(
        [
            *[Output(btn["id"], "className") for btn in PRICE_BUTTONS],
            *[Output(btn["id"], "className") for btn in DISTANCE_BUTTONS],
            Output("btn-nearest", "className"),
            Output("btn-below-estimate", "className"),
            Output("btn-inactive", "className"),
            Output("btn-updated-today", "className"),
            *[Output(btn["id"], "className") for btn in SORT_BUTTONS],
        ],
        [Input("filter-store", "data")],
    )
    def update_button_styles(filters):
        """Update button classes based on active state."""
        if not filters:
            return dash.no_update

        classes = []

        # Helper function for creating button classes
        def get_button_class(button_type, is_active=False):
            base_class = f"btn btn--{button_type}"
            if is_active:
                base_class += " btn--active"
            return base_class

        # Price buttons
        for btn in PRICE_BUTTONS:
            classes.append(
                get_button_class(
                    "default",
                    is_active=(btn["id"] == filters.get("active_price_btn")),
                )
            )

        # Distance buttons
        for btn in DISTANCE_BUTTONS:
            classes.append(
                get_button_class(
                    "default",
                    is_active=(btn["id"] == filters.get("active_dist_btn")),
                )
            )

        # Filter toggle buttons
        filter_button_mapping = [
            ("btn-nearest", "primary", "nearest"),
            ("btn-below-estimate", "warning", "below_estimate"),
            ("btn-inactive", "default", "inactive"),
            ("btn-updated-today", "success", "updated_today"),
        ]
        
        for button_id, variant, filter_name in filter_button_mapping:
            classes.append(
                get_button_class(
                    variant,
                    is_active=filters.get(filter_name, False),
                )
            )

        # Sort buttons
        for btn in SORT_BUTTONS:
            classes.append(
                get_button_class(
                    "default",
                    is_active=(btn["id"] == filters.get("active_sort_btn")),
                )
            )

        return classes


def register_details_callbacks(app):
    """Register callbacks for apartment details panel."""

    @app.callback(
        [
            Output("apartment-details-panel", "className"),
            Output("apartment-details-card", "children"),
            Output("selected-apartment-store", "data"),
        ],
        [
            Input("apartment-table", "active_cell"),
            Input("prev-apartment-button", "n_clicks"),
            Input("next-apartment-button", "n_clicks"),
            Input("close-details-button", "n_clicks"),
        ],
        [
            State("apartment-table", "data"),
            State("selected-apartment-store", "data"),
            State("apartment-details-panel", "className"),
        ],
        prevent_initial_call=True,
    )
    def handle_apartment_panel(
        active_cell,
        prev_clicks,
        next_clicks,
        close_clicks,
        table_data,
        selected_data,
        current_class,
    ):
        """Handle apartment details panel interactions."""
        triggered_id = ctx.triggered_id

        # Setup panel classes
        hidden_class = "details-panel details-panel--hidden"
        visible_class = "details-panel details-panel--visible"

        # Handle close action
        if triggered_id == "close-details-button":
            return hidden_class, dash.no_update, None

        # Handle table cell click
        if (
            triggered_id == "apartment-table"
            and active_cell
            and active_cell.get("column_id") == "details"
        ):
            row_idx = active_cell["row"]
            if row_idx >= len(table_data):
                logger.error(
                    f"Row index {row_idx} out of bounds for table data length {len(table_data)}"
                )
                return (
                    visible_class,
                    html.Div(
                        "Ошибка: индекс строки вне диапазона.", 
                        className="apartment-no-data"
                    ),
                    None,
                )

            row_data = table_data[row_idx]
            offer_id = row_data.get("offer_id")

            try:
                apartment_data = load_apartment_details(offer_id)
                details_card = create_apartment_details_card(
                    apartment_data, row_data, row_idx, len(table_data)
                )

                selected = {
                    "apartment_data": apartment_data,
                    "row_data": row_data,
                    "row_idx": row_idx,
                    "total_rows": len(table_data),
                    "offer_id": offer_id,
                    "table_data": table_data,
                }

                return visible_class, details_card, selected
            except Exception as e:
                logger.error(f"Error loading details: {e}")
                return (
                    visible_class,
                    html.Div(
                        f"Ошибка загрузки: {e}", 
                        className="apartment-no-data error"
                    ),
                    None,
                )

        # Handle navigation
        if (
            triggered_id in ["prev-apartment-button", "next-apartment-button"]
            and selected_data
        ):
            current_idx = selected_data["row_idx"]
            table_data = selected_data["table_data"]
            total_rows = len(table_data)

            # Calculate new index
            new_idx = current_idx
            if triggered_id == "prev-apartment-button" and current_idx > 0:
                new_idx -= 1
            elif (
                triggered_id == "next-apartment-button" and current_idx < total_rows - 1
            ):
                new_idx += 1

            if new_idx == current_idx:
                return dash.no_update, dash.no_update, dash.no_update

            # Load new data
            new_row = table_data[new_idx]
            offer_id = new_row.get("offer_id")

            try:
                apartment_data = load_apartment_details(offer_id)
                details_card = create_apartment_details_card(
                    apartment_data, new_row, new_idx, total_rows
                )

                selected = {
                    "apartment_data": apartment_data,
                    "row_data": new_row,
                    "row_idx": new_idx,
                    "total_rows": total_rows,
                    "offer_id": offer_id,
                    "table_data": table_data,
                }

                return dash.no_update, details_card, selected
            except Exception as e:
                logger.error(f"Error loading details: {e}")
                return (
                    dash.no_update,
                    html.Div(
                        f"Ошибка загрузки: {e}", 
                        className="apartment-no-data error"
                    ),
                    selected_data,
                )

        return dash.no_update, dash.no_update, dash.no_update

    # Slideshow navigation (client-side)
    app.clientside_callback(
        """
        function(prev_clicks, next_clicks, slideshow_data) {
            if (!slideshow_data || !slideshow_data.image_paths || !slideshow_data.image_paths.length) {
                return [slideshow_data, "", ""];
            }
            
            let currentIndex = slideshow_data.current_index || 0;
            const imagePaths = slideshow_data.image_paths;
            const totalImages = imagePaths.length;
            
            const prevTriggered = prev_clicks && prev_clicks > 0;
            const nextTriggered = next_clicks && next_clicks > 0;
            
            if (prevTriggered && !nextTriggered) {
                currentIndex = (currentIndex - 1 + totalImages) % totalImages;
            } else if (!prevTriggered && nextTriggered) {
                currentIndex = (currentIndex + 1) % totalImages;
            }
            
            return [
                {current_index: currentIndex, image_paths: imagePaths}, 
                imagePaths[currentIndex],
                `${currentIndex + 1}/${totalImages}`
            ];
        }
        """,
        [
            Output({"type": "slideshow-data", "offer_id": MATCH}, "data"),
            Output({"type": "slideshow-img", "offer_id": MATCH}, "src"),
            Output({"type": "counter", "offer_id": MATCH}, "children"),
        ],
        [
            Input({"type": "prev-btn", "offer_id": MATCH}, "n_clicks"),
            Input({"type": "next-btn", "offer_id": MATCH}, "n_clicks"),
        ],
        [State({"type": "slideshow-data", "offer_id": MATCH}, "data")],
        prevent_initial_call=True,
    )


def create_data_table(df):
    """Create a DataTable for apartment data with styling fully regulated by CSS."""
    from dash import html

    if df.empty:
        return html.Div("Нет данных", className="no-data-message")

    # Define which columns to display.
    visible_columns = CONFIG["columns"]["visible"] + ["details"]
    numeric_columns = {
        "distance", "price_value_formatted", "cian_estimation_formatted", 
        "price_difference_formatted", "monthly_burden_formatted"
    }
    markdown_columns = {
        "price_change_formatted", "address_title", "offer_link", "price_info",
        "update_title", "property_tags", "price_change", "walking_time",
        "price_text", "days_active", "activity_date"
    }

    # Build the column definitions.
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

    # Create and return the DataTable using the TableFactory.
    # Note: Instead of using a className property, you can target the table via its ID ("apartment-table") 
    # or through other selectors in your external CSS.
    return TableFactory.create_data_table(
        id="apartment-table",
        columns=columns,
        data=df.to_dict("records"),
        sort_action="custom",
        sort_mode="multi",
        sort_by=[],
        hidden_columns=CONFIG["hidden_cols"] + ["offer_id"],
        page_size=100,
        page_action="native",
        markdown_options={"html": True},
        cell_selectable=True
    )
