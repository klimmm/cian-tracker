# app/dashboard_callbacks.py
from dash import callback_context as ctx
from dash.dependencies import Input, Output, State, MATCH
import dash
import logging
import pandas as pd
from app.utils import load_and_process_data, filter_and_sort_data, load_apartment_details
from app.apartment_card import create_apartment_details_card
from app.config import PRICE_BUTTONS, DISTANCE_BUTTONS, SORT_BUTTONS
from dash import dash_table, html
from app.config import CONFIG, STYLE, COLUMN_STYLES, HEADER_STYLES
from app.config import BUTTON_STYLES

logger = logging.getLogger(__name__)


def register_data_callbacks(app):
    """Register callbacks for data loading and management."""
    
    # In app/dashboard_callbacks.py, update the load_apartment_data function
    @app.callback(
        [
            Output("apartment-data-store", "data"),
            Output("last-update-time", "children"),
        ],
        [Input("interval-component", "n_intervals")],
        prevent_initial_call=False,
    )
    def load_apartment_data(_):
        """Load apartment data and update the data store."""
        try:
            # Load data from files
            logger.info("Callback triggered: Loading apartment data")
            df, update_time = load_and_process_data()
            
            if df.empty:
                logger.error("Loaded DataFrame is empty!")
                return [], f"Error: No data loaded"
                
            logger.info(f"Successfully loaded {len(df)} rows of data")
            
            # Add details indicator column if not present
            if "details" not in df.columns:
                df["details"] = "🔍"
    
            # Make sure all required columns are included
            required_columns = CONFIG["columns"]["display"] + [
                "details",
                "offer_id",
                "date_sort_combined",
            ]
    
            # Get columns that exist in the dataframe
            available_columns = [col for col in required_columns if col in df.columns]
            logger.info(f"Available columns: {len(available_columns)} of {len(required_columns)} required")
    
            # Convert to dict for storage
            df_dict = df[available_columns].to_dict("records") if not df.empty else []
            logger.info(f"Prepared {len(df_dict)} records for data store")
    
            # Return data for storage and update time display
            return df_dict, f"Актуально на: {update_time}"
            
        except Exception as e:
            import traceback
            logger.error(f"Error loading data: {e}")
            logger.error(traceback.format_exc())
            return [], f"Ошибка загрузки данных: {str(e)}"


def register_filter_callbacks(app):
    """Register callbacks for filter management."""
    
    # Unified filter button callback
    @app.callback(
        [Output("filter-store", "data")],
        [
            # All buttons as inputs
            *[Input(btn["id"], "n_clicks") for btn in PRICE_BUTTONS],
            *[Input(btn["id"], "n_clicks") for btn in DISTANCE_BUTTONS],
            Input("btn-nearest", "n_clicks"),
            Input("btn-below-estimate", "n_clicks"),
            Input("btn-inactive", "n_clicks"),
            Input("btn-updated-today", "n_clicks"),
            # Add sort buttons
            *[Input(btn["id"], "n_clicks") for btn in SORT_BUTTONS],
        ],
        [State("filter-store", "data")],
        prevent_initial_call=True,
    )
    def unified_filter_update(*args):
        """Update filter store based on button clicks."""
        # Get the triggered input
        ctx_msg = ctx.triggered[0] if ctx.triggered else None
        if not ctx_msg:
            return [dash.no_update]

        # Extract button ID from the trigger
        trigger_id = ctx_msg["prop_id"].split(".")[0]

        # Get current filter state
        current_filters = args[-1]  # Last argument is the filter-store State
        
        # Handle button clicks based on type
        filter_updated = handle_button_click(trigger_id, current_filters)
        
        # Return updated filters if changes were made
        return [current_filters] if filter_updated else [dash.no_update]
    
    
    @app.callback(
        [Output("table-container", "children")],
        [Input("filter-store", "data"), Input("apartment-data-store", "data")],
    )
    def update_table_content(filters, data):
        """Update table based on filters, using cached data."""
        if not data:
            return [html.Div("Нет данных")]

        # Convert list of records back to DataFrame for filtering


        df = pd.DataFrame(data)

        # Apply filtering
        df = filter_and_sort_data(df, filters)

        # Define column properties
        visible = CONFIG["columns"]["visible"] + ["details"]
        numeric_cols = {
            "distance",
            "price_value_formatted",
            "cian_estimation_formatted",
            "price_difference_formatted",
            "monthly_burden_formatted",
        }
        markdown_cols = {
            "price_change_formatted",
            "address_title",
            "offer_link",
            "price_info",
            "update_title",
            "property_tags",
            "price_change",
            "walking_time",
            "price_text",
        }

        columns = [
            {
                "name": CONFIG["columns"]["headers"].get(
                    c, "Детали" if c == "details" else c
                ),
                "id": c,
                "type": "numeric" if c in numeric_cols else "text",
                "presentation": "markdown" if c in markdown_cols else None,
            }
            for c in visible
        ]

        # Details column styling
        details_style = {
            "if": {"column_id": "details"},
            "className": "details-column",
        }
        markdown_style = [
            {"if": {"column_id": col}, "textAlign": "center"} for col in markdown_cols
        ]

        # Create the DataTable
        table = dash_table.DataTable(
            id="apartment-table",
            columns=columns,
            data=df.to_dict("records") if not df.empty else [],
            sort_action="custom",
            sort_mode="multi",
            sort_by=[],
            hidden_columns=CONFIG["hidden_cols"] + ["offer_id"],
            # Responsive styling
            style_table={
                "overflowX": "auto",
                "maxWidth": "1200px",
                "width": "100%",
                "margin": "0 auto",
            },
            style_cell=STYLE["cell"],
            style_cell_conditional=STYLE.get("cell_conditional", [])
            + [details_style]
            + markdown_style,
            style_header=STYLE["header_cell"],
            style_header_conditional=HEADER_STYLES,
            style_data=STYLE["data"],
            style_filter=STYLE["filter"],
            style_data_conditional=COLUMN_STYLES
            + [
                {
                    "if": {"column_id": "details"},
                    "fontWeight": "normal",
                    "cursor": "pointer !important",
                }
            ],
            page_size=100,
            page_action="native",
            markdown_options={"html": True},
            cell_selectable=True,
            # CSS snippets
            css=[
                {
                    "selector": ".dash-cell:nth-child(n+1):nth-child(-n+15)",
                    "rule": "padding: 5px !important;",
                },
                {
                    "selector": "td.details-column",
                    "rule": "background-color: transparent !important; text-align: center !important; padding: 3px 5px !important;",
                },
            ],
        )
        return [table]
    
    
    @app.callback(
        Output("apartment-table", "data"),
        [Input("apartment-table", "sort_by"), Input("filter-store", "data")],
        [State("apartment-data-store", "data")],
    )
    def update_sort(sort_by, filters, data):
        """Handle table sorting using cached data."""
        if not data:
            return []

        # Convert to DataFrame for sorting
        df = pd.DataFrame(data)

        # Apply filters and sorting
        df = filter_and_sort_data(df, filters, sort_by)

        # Return data for table
        return df.to_dict("records")
    
    
    @app.callback(
        [*[Output(f"{btn['id']}-text", "children") for btn in SORT_BUTTONS]],
        [Input("filter-store", "data")],
        prevent_initial_call=True,
    )
    def update_sort_button_text(filters):
        """Update sort button text with direction indicators."""
        if not filters:
            return [btn["label"] for btn in SORT_BUTTONS]

        button_texts = []
        active_btn = filters.get("active_sort_btn")
        sort_direction = filters.get("sort_direction", "asc")

        for btn in SORT_BUTTONS:
            if btn["id"] == active_btn:
                arrow = "↑" if sort_direction == "asc" else "↓"
                button_texts.append(f"{btn['label']} {arrow}")
            else:
                button_texts.append(btn["label"])

        return button_texts


def register_style_callbacks(app):
    """Register callbacks for styling updates."""
    
    @app.callback(
        [
            *[Output(btn["id"], "style") for btn in PRICE_BUTTONS],
            *[Output(btn["id"], "style") for btn in DISTANCE_BUTTONS],
            Output("btn-nearest", "style"),
            Output("btn-below-estimate", "style"),
            Output("btn-inactive", "style"),
            Output("btn-updated-today", "style"),
            *[Output(btn["id"], "style") for btn in SORT_BUTTONS],
        ],
        [Input("filter-store", "data")],
    )
    def update_button_styles(filters):
        """Update button styles based on filter store state."""
        
        if not filters:
            return dash.no_update

        styles = []

        # Price button styles
        for i, btn in enumerate(PRICE_BUTTONS):
            base_style = create_button_style(
                btn, 
                i, 
                "price", 
                is_active=(btn["id"] == filters.get("active_price_btn"))
            )
            styles.append(base_style)

        # Distance button styles
        for i, btn in enumerate(DISTANCE_BUTTONS):
            base_style = create_button_style(
                btn, 
                i, 
                "distance", 
                is_active=(btn["id"] == filters.get("active_dist_btn"))
            )
            styles.append(base_style)

        # Filter toggle button styles
        for filter_name, button_id in [
            ("nearest", "btn-nearest"),
            ("below_estimate", "btn-below-estimate"),
            ("inactive", "btn-inactive"),
            ("updated_today", "btn-updated-today"),
        ]:
            button_type = filter_name
            if button_type == "below_estimate":
                button_type = "below_estimate"
            elif button_type == "updated_today":
                button_type = "updated_today"

            base_style = {**BUTTON_STYLES[button_type], "flex": "1"}

            if filters.get(filter_name):
                base_style.update({"opacity": 1.0, "boxShadow": "0 0 5px #4682B4"})
            else:
                base_style.update({"opacity": 0.6})

            styles.append(base_style)

        # Sort button styles
        for i, btn in enumerate(SORT_BUTTONS):
            base_style = create_button_style(
                btn, 
                i, 
                "sort", 
                is_active=(btn["id"] == filters.get("active_sort_btn"))
            )
            
            # Add direction indicator to active button
            if btn["id"] == filters.get("active_sort_btn"):
                direction = filters.get("sort_direction", btn.get("default_direction", "asc"))
                arrow = "↑" if direction == "asc" else "↓"
                base_style["label"] = f"{btn['label']} {arrow}"
                
            styles.append(base_style)

        return styles


def register_details_callbacks(app):
    """Register callbacks for apartment details panel."""
    
    @app.callback(
        [
            Output("apartment-details-panel", "style"),
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
        ],
        prevent_initial_call=True,
    )
    def handle_apartment_panel(
        active_cell, prev_clicks, next_clicks, close_clicks, table_data, selected_data
    ):
        """Handle the apartment details panel interactions."""
        
        triggered_id = ctx.triggered_id
        
        # Panel style presets
        hidden_style = {
            "opacity": "0",
            "visibility": "hidden",
            "pointer-events": "none",
            "display": "none",
        }
        visible_style = {
            "opacity": "1",
            "visibility": "visible",
            "pointer-events": "auto",
            "display": "block",
            "position": "fixed",
            "top": "50%",
            "left": "50%",
            "transform": "translate(-50%, -50%)",
            "width": "90%",
            "maxWidth": "500px",
            "maxHeight": "100%",
            "zIndex": "1000",
            "backgroundColor": "#fff",
            "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.2)",
            "borderRadius": "8px",
            "padding": "15px",
            "overflow": "auto",
            "transformOrigin": "center",
            "willChange": "opacity, visibility",
            "animation": "fadeIn 0.3s ease-in-out",
        }

        # Handle close
        if triggered_id == "close-details-button":
            return hidden_style, dash.no_update, None

        # Handle clicking a table row
        if (
            triggered_id == "apartment-table"
            and active_cell
            and active_cell.get("column_id") == "details"
        ):
            return handle_apartment_selection(
                active_cell["row"], table_data, visible_style
            )

        # Handle prev/next navigation
        if (
            triggered_id in ["prev-apartment-button", "next-apartment-button"]
            and selected_data
        ):
            return handle_apartment_navigation(
                triggered_id, selected_data, visible_style
            )

        # Fallback
        return dash.no_update, dash.no_update, dash.no_update
    
    
    # Slideshow navigation - client-side callback for performance
    app.clientside_callback(
        """
        function(prev_clicks, next_clicks, slideshow_data) {
            // Ensure slideshow_data exists and has the expected structure
            if (!slideshow_data || !slideshow_data.image_paths || !slideshow_data.image_paths.length) {
                return [slideshow_data, "", ""];
            }
            
            // Get current state
            let currentIndex = slideshow_data.current_index || 0;
            const imagePaths = slideshow_data.image_paths;
            const totalImages = imagePaths.length;
            
            // Track which button increased its clicks
            const prevTriggered = prev_clicks && prev_clicks > 0;
            const nextTriggered = next_clicks && next_clicks > 0;
            
            // Simple logic - if both changed or neither, don't move
            // If prev changed, go back; if next changed, go forward
            if (prevTriggered && !nextTriggered) {
                // Go to previous image
                currentIndex = (currentIndex - 1 + totalImages) % totalImages;
            } else if (!prevTriggered && nextTriggered) {
                // Go to next image
                currentIndex = (currentIndex + 1) % totalImages;
            }
            
            // Update the data
            const newData = {
                current_index: currentIndex,
                image_paths: imagePaths
            };
            
            // Return updated data and new image source
            return [
                newData, 
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


# ==================== HELPER FUNCTIONS ====================

def handle_button_click(trigger_id, current_filters):
    """Handle a button click based on the button type.
    
    Args:
        trigger_id: The ID of the clicked button
        current_filters: Current filter state dictionary
        
    Returns:
        bool: Whether filters were updated
    """
    # Handle price buttons
    price_button_ids = [btn["id"] for btn in PRICE_BUTTONS]
    if trigger_id in price_button_ids:
        # Set the active price button and corresponding value
        current_filters["active_price_btn"] = trigger_id
        current_filters["price_value"] = next(
            (btn["value"] for btn in PRICE_BUTTONS if btn["id"] == trigger_id),
            current_filters.get("price_value", 80000),
        )
        return True

    # Handle distance buttons
    distance_button_ids = [btn["id"] for btn in DISTANCE_BUTTONS]
    if trigger_id in distance_button_ids:
        # Set the active distance button and corresponding value
        current_filters["active_dist_btn"] = trigger_id
        current_filters["distance_value"] = next(
            (btn["value"] for btn in DISTANCE_BUTTONS if btn["id"] == trigger_id),
            current_filters.get("distance_value", 3.0),
        )
        return True

    # Handle filter toggle buttons
    filter_toggle_map = {
        "btn-nearest": "nearest",
        "btn-below-estimate": "below_estimate",
        "btn-inactive": "inactive",
        "btn-updated-today": "updated_today",
    }

    if trigger_id in filter_toggle_map:
        # Toggle the filter state
        filter_key = filter_toggle_map[trigger_id]
        current_filters[filter_key] = not current_filters[filter_key]
        return True

    # Handle sort buttons
    sort_button_ids = [btn["id"] for btn in SORT_BUTTONS]
    if trigger_id in sort_button_ids:
        # Get the selected sort column
        active_sort_btn = trigger_id
        sort_button = next(
            (btn for btn in SORT_BUTTONS if btn["id"] == trigger_id), None
        )

        if sort_button:
            sort_column = sort_button["value"]

            # If the same button is clicked again, toggle the direction
            if current_filters.get("active_sort_btn") == active_sort_btn:
                # Toggle sort direction
                current_filters["sort_direction"] = (
                    "desc" if current_filters.get("sort_direction") == "asc" else "asc"
                )
            else:
                # New sort button, set as active and use its default direction
                current_filters["active_sort_btn"] = active_sort_btn
                current_filters["sort_column"] = sort_column
                current_filters["sort_direction"] = sort_button.get(
                    "default_direction", "asc"
                )
            return True
    
    return False


def create_button_style(btn, index, button_type, is_active=False):
    """Create a consistent button style.
    
    Args:
        btn: Button configuration dictionary
        index: Button index in its group
        button_type: Type of button (price, distance, etc.)
        is_active: Whether the button is active
        
    Returns:
        dict: Style dictionary for the button
    """
    
    # Base style
    base_style = {
        **BUTTON_STYLES.get(button_type, {}),
        "flex": "1",
        "margin": "0",
        "padding": "2px 0",
        "fontSize": "10px",
        "lineHeight": "1",
        "borderRadius": "0",
        "borderLeft": "none" if index > 0 else "1px solid #ccc",
        "position": "relative",
    }

    # Apply active styling if this is the active button
    if is_active:
        base_style.update({
            "opacity": 1.0,
            "boxShadow": "0 0 5px #4682B4",
            "zIndex": "1",
        })
    else:
        base_style.update({
            "opacity": 0.6,
            "zIndex": "0",
        })
        
    return base_style


def handle_apartment_selection(row_idx, table_data, visible_style):
    """Handle selection of an apartment from the table.
    
    Args:
        row_idx: Index of the selected row
        table_data: Table data as list of dictionaries
        visible_style: Style dictionary for the visible panel
        
    Returns:
        tuple: (panel_style, panel_content, selected_data)
    """
    
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

        return visible_style, details_card, selected

    except Exception as e:
        logger.error(f"Error loading apartment details: {e}")
        return (
            visible_style,
            html.Div(f"Ошибка загрузки: {e}", style={"color": "red"}),
            None,
        )


def handle_apartment_navigation(trigger_id, selected_data, visible_style):
    """Handle navigation between apartments.
    
    Args:
        trigger_id: ID of the triggered button (prev/next)
        selected_data: Currently selected apartment data
        visible_style: Style dictionary for the visible panel
        
    Returns:
        tuple: (panel_style, panel_content, selected_data)
    """
    
    current_idx = selected_data["row_idx"]
    table_data = selected_data["table_data"]
    total_rows = len(table_data)

    new_idx = current_idx
    if trigger_id == "prev-apartment-button" and current_idx > 0:
        new_idx -= 1
    elif trigger_id == "next-apartment-button" and current_idx < total_rows - 1:
        new_idx += 1

    if new_idx == current_idx:
        return dash.no_update, dash.no_update, dash.no_update

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
        logger.error(f"Error loading apartment details: {e}")
        return (
            dash.no_update,
            html.Div(f"Ошибка загрузки: {e}", style={"color": "red"}),
            selected_data,
        )


def register_all_callbacks(app):
    """Register all callbacks for the application."""
    register_data_callbacks(app)
    register_filter_callbacks(app)
    register_style_callbacks(app)
    register_details_callbacks(app)