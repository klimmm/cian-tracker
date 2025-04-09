# callbacks.py
import dash
from dash.dependencies import Input, Output, State
from dash import callback

from config import BUTTON_STYLES, PRICE_BUTTONS, DISTANCE_BUTTONS
from layout import default_price, default_price_btn, default_distance, default_distance_btn

# Base layout styles for buttons that should be preserved
PRICE_BUTTON_LAYOUT = {
    "flex": "1",  # Take full width
    "margin": "0",  # No margin
    "padding": "2px 0",  # Reduced vertical padding
    "fontSize": "10px",  # Smaller font size
    "lineHeight": "1",  # Tighter line height
    "borderRadius": "0",  # No rounded corners
}

DISTANCE_BUTTON_LAYOUT = {
    "flex": "1",  # Take full width
    "margin": "0",  # No margin
    "padding": "2px 0",  # Reduced vertical padding
    "fontSize": "10px",  # Smaller font size
    "lineHeight": "1",  # Tighter line height
    "borderRadius": "0",  # No rounded corners
}

# Callback to handle price button clicks
@callback(
    [Output(btn["id"], "style") for btn in PRICE_BUTTONS]
    + [Output("filter-store", "data", allow_duplicate=True)],
    [Input(btn["id"], "n_clicks") for btn in PRICE_BUTTONS],
    [State("filter-store", "data")],
    prevent_initial_call=True,
)
def update_price_buttons(*args):
    n_buttons = len(PRICE_BUTTONS)
    clicks = args[:n_buttons]
    current_filters = args[n_buttons]

    ctx = dash.callback_context
    if not ctx.triggered:
        # Default button
        button_id = default_price_btn
        price_value = default_price
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        price_value = next(
            (btn["value"] for btn in PRICE_BUTTONS if btn["id"] == button_id),
            default_price,
        )

    # Update the filter store
    current_filters["price_value"] = price_value
    current_filters["active_price_btn"] = button_id

    # Create button styles
    styles = []
    for i, btn in enumerate(PRICE_BUTTONS):
        # Base style with layout preserved
        base_style = {
            **BUTTON_STYLES["price"],
            **PRICE_BUTTON_LAYOUT,
        }
        
        # Add buttongroup-specific styling
        if i > 0:
            base_style["borderLeft"] = "none"
        
        # Add active/inactive styling
        if btn["id"] == button_id:
            base_style.update({
                "opacity": 1.0,
                "boxShadow": "0 0 5px #4682B4",
                "position": "relative",
                "zIndex": "1",
            })
        else:
            base_style.update({
                "opacity": 0.6,
                "position": "relative",
                "zIndex": "0",
            })
            
        styles.append(base_style)

    return *styles, current_filters


# Callback to handle distance button clicks
@callback(
    [Output(btn["id"], "style") for btn in DISTANCE_BUTTONS]
    + [Output("filter-store", "data", allow_duplicate=True)],
    [Input(btn["id"], "n_clicks") for btn in DISTANCE_BUTTONS],
    [State("filter-store", "data")],
    prevent_initial_call=True,
)
def update_distance_buttons(*args):
    n_buttons = len(DISTANCE_BUTTONS)
    clicks = args[:n_buttons]
    current_filters = args[n_buttons]

    ctx = dash.callback_context
    if not ctx.triggered:
        # Default button
        button_id = default_distance_btn
        distance_value = default_distance
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        distance_value = next(
            (btn["value"] for btn in DISTANCE_BUTTONS if btn["id"] == button_id),
            default_distance,
        )

    # Update the filter store
    current_filters["distance_value"] = distance_value
    current_filters["active_dist_btn"] = button_id

    # Create button styles
    styles = []
    for i, btn in enumerate(DISTANCE_BUTTONS):
        # Base style with layout preserved
        base_style = {
            **BUTTON_STYLES["distance"],
            **DISTANCE_BUTTON_LAYOUT,
        }
        
        # Add buttongroup-specific styling
        if i > 0:
            base_style["borderLeft"] = "none"
            
        # Add active/inactive styling
        if btn["id"] == button_id:
            base_style.update({
                "opacity": 1.0,
                "boxShadow": "0 0 5px #4682B4",
                "position": "relative",
                "zIndex": "1",
            })
        else:
            base_style.update({
                "opacity": 0.6,
                "position": "relative",
                "zIndex": "0",
            })
            
        styles.append(base_style)

    return *styles, current_filters


# Callback to handle filter button clicks
@callback(
    [
        Output("btn-nearest", "style"),
        Output("btn-below-estimate", "style"),
        Output("btn-inactive", "style"),
        Output("btn-updated-today", "style"),
        Output("filter-store", "data", allow_duplicate=True),
    ],
    [
        Input("btn-nearest", "n_clicks"),
        Input("btn-below-estimate", "n_clicks"),
        Input("btn-inactive", "n_clicks"),
        Input("btn-updated-today", "n_clicks"),
    ],
    [State("filter-store", "data")],
    prevent_initial_call=True,
)
def update_filters(
    nearest_clicks,
    below_est_clicks,
    inactive_clicks,
    updated_today_clicks,
    current_filters,
):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [
            {**BUTTON_STYLES["nearest"], "opacity": 0.6},
            {**BUTTON_STYLES["below_estimate"], "opacity": 0.6},
            {**BUTTON_STYLES["inactive"], "opacity": 0.6},
            {**BUTTON_STYLES["updated_today"], "opacity": 0.6},
            current_filters,
        ]

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    filter_map = {
        "btn-nearest": "nearest",
        "btn-below-estimate": "below_estimate",
        "btn-inactive": "inactive",
        "btn-updated-today": "updated_today",
    }

    if button_id in filter_map:
        current_filters[filter_map[button_id]] = not current_filters[
            filter_map[button_id]
        ]

    # Create button styles
    styles = []
    for key in ["nearest", "below_estimate", "inactive", "updated_today"]:
        filter_style = {**BUTTON_STYLES[key], "flex": "1"}  # Add flex for full width
        
        if current_filters[key]:
            filter_style.update({"opacity": 1.0, "boxShadow": "0 0 5px #4682B4"})
        else:
            filter_style.update({"opacity": 0.6})
            
        styles.append(filter_style)

    return *styles, current_filters