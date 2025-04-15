# app/dashboard_callbacks.py - Fixed version with resolved callback conflicts
from dash import callback_context as ctx
from dash.dependencies import Input, Output, State, MATCH, ALL
import dash
import logging
import pandas as pd
import json  # Added import for JSON parsing
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
    register_table_buttons(app)

    
# Update the register_table_buttons function to use allow_duplicate
def register_table_buttons(app):
    """Register optional button-based callbacks (only used if table clicks don't work)."""
    
    @app.callback(
        Output("apartment-table", "data", allow_duplicate=True),
        [Input("filter-store", "data"), Input("apartment-data-store", "data")],
        prevent_initial_call=True
    )
    def add_button_to_table(filters, data):
        """Update table data when filters change."""
        if not data:
            return dash.no_update
            
        # Convert to DataFrame for processing
        df = pd.DataFrame(data)
        
        # Apply filtering and sorting
        df = DataManager.filter_and_sort_data(df, filters or {})
        
        # Return the filtered data
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

    # Update the update_table_content function to include more debugging info
    

    @app.callback(
        [
            Output("apartment-table", "data"),
            Output("apartment-table", "columns"),
            Output("apartment-table", "style_cell_conditional"),
            Output("apartment-table", "style_data_conditional"),
            
        ],
        [Input("filter-store", "data"), Input("apartment-data-store", "data")],
    )
    def update_table_content(filters, data):
        """Update table based on filters and data with added debugging."""
        if not data:
            return [], [], []
    
        try:
            # Convert to DataFrame for processing
            df = pd.DataFrame(data)
    
            # Apply filtering and sorting
            df = DataManager.filter_and_sort_data(df, filters or {})
    
            # Define which columns to display
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
    
            # Define style_cell_conditional
            style_cell_conditional = [
                {
                    'if': {'column_id': 'details'},
                    'textAlign': 'center',
                    'cursor': 'pointer',
                    'width': '80px'
                },

                
            ]

            COLUMN_STYLES = [
                {
                    "if": {"filter_query": '{status} contains "non active"'},
                    "backgroundColor": "#f4f4f4",
                    "color": "#888",
                }                        
            ]       
            # Return updated table properties
            return df.to_dict("records"), columns, style_cell_conditional, COLUMN_STYLES
    
        except Exception as e:
            print(f"Error updating table: {e}")
            return [], [], []
    
    # Update the sort callback to use allow_duplicate
    @app.callback(
        Output("apartment-table", "data", allow_duplicate=True),
        [Input("apartment-table", "sort_by"), Input("filter-store", "data")],
        [State("apartment-data-store", "data")],
        prevent_initial_call=True
    )
    def update_sort(sort_by, filters, data):
        """Handle table sorting from column headers."""
        if not data:
            return []
    
        df = pd.DataFrame(data)
        df = DataManager.filter_and_sort_data(df, filters, sort_by)
        return df.to_dict("records")



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
            Output("details-overlay", "className"),
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
            State("details-overlay", "className"),
        ],
    )
    def handle_apartment_panel(
        active_cell,
        prev_clicks,
        next_clicks,
        close_clicks,
        table_data,
        selected_data,
        current_class,
        overlay_class,
    ):
        """Handle apartment details panel interactions."""
        # Setup panel classes
        hidden_panel_class = "details-panel details-panel--hidden"
        visible_panel_class = "details-panel details-panel--visible" 
        hidden_overlay_class = "details-overlay details-panel--hidden"
        visible_overlay_class = "details-overlay details-panel--visible"
        
        # Get the triggered component
        ctx_triggered = ctx.triggered if ctx.triggered else []
        trigger_id = ctx_triggered[0]['prop_id'].split('.')[0] if ctx_triggered else None
        
        # For initial load, ensure the panel is hidden
        if not ctx_triggered or trigger_id is None:
            return hidden_panel_class, [], None, hidden_overlay_class
            
        # Handle close action
        if trigger_id == "close-details-button" and close_clicks and close_clicks > 0:
            return hidden_panel_class, dash.no_update, None, hidden_overlay_class

        # Handle table cell click
        if trigger_id == "apartment-table" and active_cell:
            # Only accept clicks on the details column
            if active_cell.get("column_id") != "details":
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
                
            row_idx = active_cell["row"]
            if not table_data or row_idx >= len(table_data):
                logger.error(f"Row index {row_idx} out of bounds for table data length {len(table_data) if table_data else 0}")
                return (
                    visible_panel_class,
                    html.Div(
                        "Ошибка: индекс строки вне диапазона или нет данных.", 
                        className="apartment-no-data"
                    ),
                    None,
                    visible_overlay_class,
                )

            row_data = table_data[row_idx]
            offer_id = row_data.get("offer_id")
            if not offer_id:
                logger.error(f"No offer_id found in row data")
                return (
                    visible_panel_class,
                    html.Div(
                        "Ошибка: не найден ID квартиры.", 
                        className="apartment-no-data"
                    ),
                    None,
                    visible_overlay_class,
                )

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
                
                logger.info(f"Loaded details for offer_id {offer_id}, showing panel")
                return visible_panel_class, details_card, selected, visible_overlay_class
            except Exception as e:
                logger.error(f"Error loading details: {e}")
                return (
                    visible_panel_class,
                    html.Div(
                        f"Ошибка загрузки: {e}", 
                        className="apartment-no-data error"
                    ),
                    None,
                    visible_overlay_class,
                )

        # Handle navigation
        if (
            trigger_id in ["prev-apartment-button", "next-apartment-button"]
            and selected_data
            and table_data
        ):
            current_idx = selected_data["row_idx"]
            table_data = selected_data.get("table_data", table_data)
            total_rows = len(table_data)

            # Calculate new index
            new_idx = current_idx
            if trigger_id == "prev-apartment-button" and current_idx > 0:
                new_idx -= 1
            elif (
                trigger_id == "next-apartment-button" and current_idx < total_rows - 1
            ):
                new_idx += 1

            if new_idx == current_idx:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update

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

                return dash.no_update, details_card, selected, dash.no_update
            except Exception as e:
                logger.error(f"Error loading details: {e}")
                return (
                    dash.no_update,
                    html.Div(
                        f"Ошибка загрузки: {e}", 
                        className="apartment-no-data error"
                    ),
                    selected_data,
                    dash.no_update,
                )

        # For any other case, don't update
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update





    app.clientside_callback(
        """
        function(prev_clicks, next_clicks, slideshow_data) {
            // Make sure data exists
            if (!slideshow_data || !slideshow_data.image_paths || slideshow_data.image_paths.length === 0) {
                return [slideshow_data, "", ""];
            }
            
            // Get current state
            let currentIndex = slideshow_data.current_index || 0;
            const imagePaths = slideshow_data.image_paths;
            const totalImages = imagePaths.length;
            
            // Get offer ID for tracking
            const ctx = dash_clientside.callback_context;
            const triggerId = ctx.triggered[0].prop_id;
            const matches = triggerId.match(/{[^}]*"offer_id"[^}]*:([^}]*)}/);
            const offerId = matches ? matches[1].trim() : 'unknown';
            
            // Create button click trackers specific to this slideshow
            const stateKey = `slideshow_${offerId}`;
            if (typeof window[stateKey] === 'undefined') {
                window[stateKey] = {
                    prevClicks: prev_clicks || 0,
                    nextClicks: next_clicks || 0
                };
            }
            
            // Determine which button was clicked by comparing with stored values
            if (prev_clicks > window[stateKey].prevClicks) {
                // Move to previous image with wrap-around
                currentIndex = (currentIndex - 1 + totalImages) % totalImages;
                window[stateKey].prevClicks = prev_clicks;
            } 
            else if (next_clicks > window[stateKey].nextClicks) {
                // Move to next image with wrap-around
                currentIndex = (currentIndex + 1) % totalImages;
                window[stateKey].nextClicks = next_clicks;
            }
            
            // Return updated values
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
    """Create a DataTable for apartment data with forced ID."""
    from dash import dash_table, html
    import pandas as pd

    if df.empty:
        return html.Div("Нет данных", className="no-data-message")

    # Define which columns to display
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

    # Create the DataTable directly with explicit ID
    table = TableFactory.create_data_table(
        id="apartment-table", 
        data=df.to_dict("records"),
        columns=columns,
        conditional_styles=COLUMN_STYLES,
        sort_action="custom",
        sort_mode="multi",
        sort_by=[],
        page_size=100,
        page_action="native",
        hidden_columns=CONFIG["hidden_cols"] + ["offer_id"],
        style_header={
            'backgroundColor': 'var(--color-primary)',
            'color': 'white',
            'fontWeight': 'bold',
        },
        style_cell={
            'textAlign': 'left',
            'padding': '8px',
            'fontFamily': 'var(--font-family)',
            'fontSize': 'var(--font-sm)',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis'
        },
        style_cell_conditional=[
            {
                'if': {'column_id': 'details'},
                'textAlign': 'center',
                'cursor': 'pointer',
                'width': '80px'
            }
        ],
        markdown_options={"html": True},
        cell_selectable=True
    )
    
    # Print for debugging
    print(f"Created table with ID: {table.id}")
    return table


def check_table_factory():
    # Create a sample table and check its ID
    table = TableFactory.create_data_table(...)
    print("Table ID:", table.id)
    return table