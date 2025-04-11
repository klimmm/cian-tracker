# Optimized cian_dashboard.py

import re
import os
import json
import dash
from dash import dash_table, html, dcc, callback, callback_context as ctx
from dash.dependencies import Input, Output, State, MATCH, ALL
from config import CONFIG, STYLE, COLUMN_STYLES, HEADER_STYLES
from utils import load_and_process_data, filter_and_sort_data
from layout import create_app_layout
import logging
from config import BUTTON_STYLES, PRICE_BUTTONS, DISTANCE_BUTTONS
from layout import default_price, default_price_btn, default_distance, default_distance_btn
from apartment_card import create_apartment_details_card
from utils import load_apartment_details

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Get current directory to set up assets properly
current_dir = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(current_dir, 'assets')

# Initialize the app with proper assets configuration
app = dash.Dash(
    __name__,
    title="",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
    assets_folder=assets_path,
)

# Create assets directory structure if it doesn't exist
if not os.path.exists(assets_path):
    os.makedirs(assets_path)

# Create a symlink from images to assets/images if it doesn't exist already
images_dir = os.path.join(current_dir, 'images')
assets_images_dir = os.path.join(assets_path, 'images')

if os.path.exists(images_dir) and not os.path.exists(assets_images_dir):
    # On Windows, we might need different commands or directory junction
    if os.name == 'nt':  # Windows
        try:
            # Try directory junction on Windows
            import subprocess
            subprocess.run(['mklink', '/J', assets_images_dir, images_dir], shell=True, check=False)
        except Exception as e:
            print(f"Warning: Could not create directory junction: {e}")
            # Fall back to copying if junctions don't work
            import shutil
            if not os.path.exists(assets_images_dir):
                os.makedirs(assets_images_dir)
    else:  # Unix-like
        try:
            # Create a symbolic link
            os.symlink(images_dir, assets_images_dir)
        except Exception as e:
            print(f"Warning: Could not create symlink: {e}")
            
server = app.server

# Add custom CSS for styling
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

# Create additional data store components for caching
apartment_data_store = dcc.Store(id="apartment-data-store", storage_type="memory", data=[])

# Get base layout from layout module
base_layout = create_app_layout(app)

# Add our new data store to the layout
if isinstance(base_layout, html.Div) and hasattr(base_layout, 'children'):
    if isinstance(base_layout.children, list):
        base_layout.children.append(apartment_data_store)
    else:
        base_layout.children = [base_layout.children, apartment_data_store]

# Set the app layout
app.layout = base_layout

# =====================================================================
# OPTIMIZED DATA LOADING 
# =====================================================================

# Main callback for loading data - now only runs on interval or initial load
@app.callback(
    [
        Output("apartment-data-store", "data"),
        Output("last-update-time", "children"),
    ],
    [Input("interval-component", "n_intervals")],
    prevent_initial_call=False
)
def load_apartment_data(_):
    """Callback to load data from disk and store in dcc.Store component"""
    try:
        # Load data only once
        df, update_time = load_and_process_data()
        if "details" not in df.columns:
            df["details"] = "🔍"

        # Convert to dict for storage
        df_dict = df[CONFIG["columns"]["display"] + ["details", "offer_id"]].to_dict("records") if not df.empty else []
        
        # Return data for storage and update time display
        return df_dict, f"Актуально на: {update_time}"
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return [], f"Ошибка загрузки данных: {str(e)}"

# =====================================================================
# UNIFIED FILTER MANAGEMENT
# =====================================================================

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
    ],
    [State("filter-store", "data")],
    prevent_initial_call=True
)
def unified_filter_update(*args):
    """Consolidated callback that handles all filter button clicks"""
    # Get the triggered input
    ctx_msg = ctx.triggered[0] if ctx.triggered else None
    if not ctx_msg:
        return [dash.no_update]
    
    # Extract button ID from the trigger
    trigger_id = ctx_msg["prop_id"].split(".")[0]
    
    # Get current filter state
    current_filters = args[-1]  # Last argument is the filter-store State
    
    # Handle price buttons
    price_button_ids = [btn["id"] for btn in PRICE_BUTTONS]
    if trigger_id in price_button_ids:
        # Set the active price button and corresponding value
        current_filters["active_price_btn"] = trigger_id
        current_filters["price_value"] = next(
            (btn["value"] for btn in PRICE_BUTTONS if btn["id"] == trigger_id),
            default_price
        )
    
    # Handle distance buttons
    distance_button_ids = [btn["id"] for btn in DISTANCE_BUTTONS]
    if trigger_id in distance_button_ids:
        # Set the active distance button and corresponding value
        current_filters["active_dist_btn"] = trigger_id
        current_filters["distance_value"] = next(
            (btn["value"] for btn in DISTANCE_BUTTONS if btn["id"] == trigger_id),
            default_distance
        )
    
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
    
    return [current_filters]

# =====================================================================
# BUTTON STYLES UPDATE
# =====================================================================

@app.callback(
    [
        *[Output(btn["id"], "style") for btn in PRICE_BUTTONS],
        *[Output(btn["id"], "style") for btn in DISTANCE_BUTTONS],
        Output("btn-nearest", "style"),
        Output("btn-below-estimate", "style"),
        Output("btn-inactive", "style"),
        Output("btn-updated-today", "style"),
    ],
    [Input("filter-store", "data")],
)
def update_button_styles(filters):
    """Update button styles based on filter store state"""
    if not filters:
        return dash.no_update
    
    styles = []
    
    # Price button styles
    for i, btn in enumerate(PRICE_BUTTONS):
        # Base style 
        base_style = {
            **BUTTON_STYLES["price"],
            "flex": "1",
            "margin": "0",
            "padding": "2px 0",
            "fontSize": "10px",
            "lineHeight": "1",
            "borderRadius": "0",
            "borderLeft": "none" if i > 0 else "1px solid #ccc",
            "position": "relative",
        }
        
        # Apply active styling if this is the active button
        if btn["id"] == filters.get("active_price_btn"):
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
            
        styles.append(base_style)
    
    # Distance button styles
    for i, btn in enumerate(DISTANCE_BUTTONS):
        # Base style
        base_style = {
            **BUTTON_STYLES["distance"],
            "flex": "1",
            "margin": "0",
            "padding": "2px 0",
            "fontSize": "10px",
            "lineHeight": "1",
            "borderRadius": "0",
            "borderLeft": "none" if i > 0 else "1px solid #ccc",
            "position": "relative",
        }
        
        # Apply active styling if this is the active button
        if btn["id"] == filters.get("active_dist_btn"):
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
            
        styles.append(base_style)
    
    # Filter toggle button styles
    for filter_name, button_id in [
        ("nearest", "btn-nearest"),
        ("below_estimate", "btn-below-estimate"),
        ("inactive", "btn-inactive"),
        ("updated_today", "btn-updated-today"),
    ]:
        button_type = button_id.split("-")[1]
        if button_type == "below":
            button_type = "below_estimate"
        elif button_type == "updated":
            button_type = "updated_today"
            
        base_style = {
            **BUTTON_STYLES[button_type], 
            "flex": "1"
        }
        
        if filters.get(filter_name):
            base_style.update({
                "opacity": 1.0,
                "boxShadow": "0 0 5px #4682B4"
            })
        else:
            base_style.update({
                "opacity": 0.6
            })
            
        styles.append(base_style)
    
    return styles

# =====================================================================
# TABLE FILTERING AND DISPLAY
# =====================================================================

@app.callback(
    Output("table-container", "children"),
    [Input("filter-store", "data"), Input("apartment-data-store", "data")],
)
def update_table_content(filters, data):
    """Update table based on filters, using cached data"""
    if not data:
        return html.Div("Нет данных")
    
    # Convert list of records back to DataFrame for filtering
    import pandas as pd
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
    markdown_cols = {"price_change_formatted", "address_title", "offer_link", 'price_info', 'update_title'}
    
    columns = [
        {
            "name": CONFIG["columns"]["headers"].get(c, "Детали" if c == "details" else c),
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
    
    # Create the DataTable
    table = dash_table.DataTable(
        id="apartment-table",
        columns=columns,
        data=df.to_dict("records") if not df.empty else [],
        sort_action="custom",
        sort_mode="multi",
        sort_by=[],
        hidden_columns=CONFIG["hidden_cols"] + ["offer_id"],
        style_table=STYLE["table"],
        style_cell=STYLE["cell"],
        style_cell_conditional=STYLE.get("cell_conditional", []) + [
            {"if": {"column_id": c["id"]}, "width": "auto"} for c in columns
        ] + [details_style],
        style_header=STYLE["header_cell"],
        style_header_conditional=HEADER_STYLES,
        style_data=STYLE["data"],
        style_filter=STYLE["filter"],
        style_data_conditional=COLUMN_STYLES + [
            {
                "if": {"column_id": "details"},
                "fontWeight": "normal",
                "backgroundColor": "transparent",
                "cursor": "pointer !important"
            }
        ],
        page_size=1000,
        page_action="native",
        markdown_options={"html": True},
        cell_selectable=True,
        css=[
            {
                "selector": ".dash-cell:nth-child(n+1):nth-child(-n+15)",
                "rule": "padding: 5px !important;"
            },
            {
                "selector": "td.details-column",
                "rule": "background-color: transparent !important; text-align: center !important; padding: 3px 5px !important;"
            },
            {
                "selector": "td.details-column .dash-cell-value",
                "rule": """
                    background-color: #4682B4 !important; 
                    color: white !important;
                    border-radius: 4px !important;
                    padding: 3px 8px !important;
                    display: inline-block !important;
                    font-size: 11px !important;
                    cursor: pointer !important;
                    transition: background-color 0.2s !important;
                    font-weight: normal !important;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
                """
            },
            {
                "selector": "td.details-column .dash-cell-value:hover",
                "rule": "background-color: #365F8A !important;"
            },
            {
                "selector": ".dash-spreadsheet td.cell-clickable",
                "rule": "cursor: pointer !important;"
            }
        ]
    )
    
    return table

# Simplified callback for table sorting
@app.callback(
    Output("apartment-table", "data"),
    [Input("apartment-table", "sort_by"), Input("filter-store", "data")],
    [State("apartment-data-store", "data")]
)
def update_sort(sort_by, filters, data):
    """Handle table sorting using cached data"""
    if not data:
        return []
        
    # Convert to DataFrame for sorting
    import pandas as pd
    df = pd.DataFrame(data)
    
    # Apply filters and sorting
    df = filter_and_sort_data(df, filters, sort_by)
    
    # Return data for table
    return df.to_dict("records")

# =====================================================================
# DETAILS PANEL MANAGEMENT
# =====================================================================

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
    prevent_initial_call=True
)
def handle_apartment_panel(active_cell, prev_clicks, next_clicks, close_clicks, table_data, selected_data):
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
        "animation": "fadeIn 0.3s ease-in-out"
    }

    # Handle close
    if triggered_id == "close-details-button":
        return hidden_style, dash.no_update, None

    # Handle clicking a table row
    if triggered_id == "apartment-table" and active_cell and active_cell.get("column_id") == "details":
        row_idx = active_cell["row"]
        row_data = table_data[row_idx]
        offer_id = row_data.get("offer_id")

        try:
            apartment_data = load_apartment_details(offer_id)
            details_card = create_apartment_details_card(apartment_data, row_data, row_idx, len(table_data))

            selected = {
                "apartment_data": apartment_data,
                "row_data": row_data,
                "row_idx": row_idx,
                "total_rows": len(table_data),
                "offer_id": offer_id,
                "table_data": table_data
            }

            return visible_style, details_card, selected

        except Exception as e:
            logger.error(f"Error loading apartment details: {e}")
            return visible_style, html.Div(f"Ошибка загрузки: {e}", style={"color": "red"}), None

    # Handle prev/next navigation
    if triggered_id in ["prev-apartment-button", "next-apartment-button"] and selected_data:
        current_idx = selected_data["row_idx"]
        table_data = selected_data["table_data"]
        total_rows = len(table_data)

        new_idx = current_idx
        if triggered_id == "prev-apartment-button" and current_idx > 0:
            new_idx -= 1
        elif triggered_id == "next-apartment-button" and current_idx < total_rows - 1:
            new_idx += 1

        if new_idx == current_idx:
            return dash.no_update, dash.no_update, dash.no_update

        new_row = table_data[new_idx]
        offer_id = new_row.get("offer_id")

        try:
            apartment_data = load_apartment_details(offer_id)
            details_card = create_apartment_details_card(apartment_data, new_row, new_idx, total_rows)

            selected = {
                "apartment_data": apartment_data,
                "row_data": new_row,
                "row_idx": new_idx,
                "total_rows": total_rows,
                "offer_id": offer_id,
                "table_data": table_data
            }

            return dash.no_update, details_card, selected

        except Exception as e:
            logger.error(f"Error loading apartment details: {e}")
            return dash.no_update, html.Div(f"Ошибка загрузки: {e}", style={"color": "red"}), selected_data

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
        Output({"type": "counter", "offer_id": MATCH}, "children")
    ],
    [
        Input({"type": "prev-btn", "offer_id": MATCH}, "n_clicks"),
        Input({"type": "next-btn", "offer_id": MATCH}, "n_clicks")
    ],
    [
        State({"type": "slideshow-data", "offer_id": MATCH}, "data")
    ],
    prevent_initial_call=True
)

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
