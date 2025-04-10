# In cian_dashboard.py

import os
import dash
from dash import dash_table, html, dcc
from dash.dependencies import Input, Output, State
from config import CONFIG, STYLE, COLUMN_STYLES, HEADER_STYLES
from utils import load_and_process_data, filter_and_sort_data
from layout import create_app_layout
import callbacks
import apartment_details_callbacks


# Get current directory to set up assets properly
current_dir = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(current_dir, 'assets')

# Initialize the app with proper assets configuration
app = dash.Dash(
    __name__,
    title="",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
    assets_folder=assets_path,  # Set the assets folder
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
            
apartment_details_callbacks.register_callbacks(app)
# Add this to cian_dashboard.py right after the app initialization
server = app.server

# Add custom CSS to remove paragraph margins and add animations
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* Animation keyframes */
            @keyframes fadeIn {
                from { opacity: 0; transform: translate(-50%, -50%) scale(0.95); }
                to { opacity: 1; transform: translate(-50%, -50%) scale(1); }
            }
            
            /* Dash container */
            .dash-container {
              position: relative;
              overflow-x: hidden; /* Prevent horizontal scrolling during animations */
            }
            
            /* Remove margins from paragraph elements */
            .dash-cell-value p {
                margin: 0 !important;
                padding: 0 !important;
            }
            
            # Details button styling - more prominent */
            td.details-column .dash-cell-value {
                display: inline-block !important;
                background-color: #4682B4 !important;
                color: white !important;
                border: none !important;
                padding: 3px 10px !important;
                border-radius: 4px !important;
                font-size: 11px !important;
                cursor: pointer !important;
                transition: background-color 0.2s !important;
                text-align: center !important;
                font-weight: normal !important;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
                position: relative !important;
                min-width: 80px !important;
            }
            
            /* Add button-like appearance */
            td.details-column .dash-cell-value:before {
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: rgba(255,255,255,0.3);
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            
            td.details-column .dash-cell-value:after {
                content: "";
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: rgba(0,0,0,0.1);
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            
            td.details-column .dash-cell-value:hover {
                background-color: #365F8A !important;
                transform: translateY(-1px) !important;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
            }
            
            /* Fix cursor for clickable cells */
            .dash-spreadsheet td.cell-clickable,
            td.details-column, 
            td[data-dash-column="details"] {
                cursor: pointer !important;
            }
            
            /* Apartment details panel */
            #apartment-details-panel {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                z-index: 1000;
                background-color: #fff;
                box-shadow: 0 4px 16px rgba(0,0,0,0.2);
                border-radius: 8px;
                padding: 15px;
                overflow: auto;
                width: 90%;
                max-width: 500px;
                max-height: 100%;
                
                /* Animation settings */
                transform-origin: center;
                will-change: opacity, visibility, transform;
                transition: opacity 0.25s ease, visibility 0.25s ease;
                
                /* Initial state - hidden */
                opacity: 0;
                visibility: hidden;
                pointer-events: none;
            }
            
            /* When panel is visible */
            #apartment-details-panel[style*="visibility: visible"] {
                opacity: 1;
                visibility: visible;
                pointer-events: auto;
                animation: fadeIn 0.3s ease-in-out;
            }
            
            /* Highlighted row */
            .highlighted-row td {
                background-color: #e6f3ff !important;
                border-bottom: 2px solid #4682B4 !important;
                transition: background-color 0.3s ease;
            }
            
            /* Make details column transparent */
            .details-column {
                background-color: transparent !important;
                padding: 3px 5px !important;
            }
        </style>
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
# App layout
app.layout = create_app_layout(app)

# Combined callback for updating table and time
@app.callback(
    [Output("table-container", "children"), Output("last-update-time", "children")],
    [Input("filter-store", "data"), Input("interval-component", "n_intervals")],
)
def update_table_and_time(filters, _):
    df, update_time = load_and_process_data()
    df = filter_and_sort_data(df, filters)
    
    # Use a button-like HTML for the details column
    df['details'] = "Подробнее"
    
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
    
    # Custom styling for the details column that will be consistent
    details_style = {
        "if": {"column_id": "details"},
        "className": "details-column",  # Use CSS class for consistent styling
    }
    
    # Create the DataTable with improved styling
    table = dash_table.DataTable(
        id="apartment-table",
        columns=columns,
        data=df[CONFIG["columns"]["display"] + ["details", "offer_id"]].to_dict("records") if not df.empty else [],
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
            # Format the details column with consistent button styling
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
        cell_selectable=True,  # Important for handling clicks on cells
        css=[
            # Add CSS rules for consistent detail button styling
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
            # Fix for cursor on details cells
            {
                "selector": ".dash-spreadsheet td.cell-clickable",
                "rule": "cursor: pointer !important;"
            }
        ]
    )
    
    # Wrap the table in a div
    table_container = html.Div(
        style={"position": "relative"},  # Helps with details panel positioning
        children=[table]
    )
    
    return table_container, f"Актуально на: {update_time}"
    
# Callback for sorting - kept in app.py
@app.callback(
    Output("apartment-table", "data"),
    [Input("apartment-table", "sort_by"), Input("filter-store", "data")],
)
def update_sort(sort_by, filters):
    df, _ = load_and_process_data()
    df = filter_and_sort_data(df, filters, sort_by)
    
    # Add the 'details' column - this was missing
    df['details'] = "Подробнее"
    
    return df[CONFIG["columns"]["display"] + ["details", "offer_id"]].to_dict("records") if not df.empty else []

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))