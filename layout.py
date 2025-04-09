# app.py
import os
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State

from config import BUTTON_STYLES
from config import PRICE_BUTTONS, DISTANCE_BUTTONS  # New imports
from config import CONFIG, STYLE, BUTTON_STYLES, COLUMN_STYLES, HEADER_STYLES


# Default values
default_price = next(
    (btn["value"] for btn in PRICE_BUTTONS if btn.get("default", False)), 80000
)
default_price_btn = next(
    (btn["id"] for btn in PRICE_BUTTONS if btn.get("default", False)), "btn-price-80k"
)
default_distance = next(
    (btn["value"] for btn in DISTANCE_BUTTONS if btn.get("default", False)), 3.0
)
default_distance_btn = next(
    (btn["id"] for btn in DISTANCE_BUTTONS if btn.get("default", False)), "btn-dist-3km"
)


def create_app_layout(app):
    # App layout
    app.layout = html.Div(
        [
            html.H2("", style=STYLE["header"]),
            html.Div(html.Span(id="last-update-time", style=STYLE["update_time"])),
            dcc.Interval(id="interval-component", interval=2 * 60 * 1000, n_intervals=0),
            # Filter store
            dcc.Store(
                id="filter-store",
                data={
                    "nearest": False,
                    "below_estimate": False,
                    "inactive": False,
                    "updated_today": False,
                    "price_value": default_price,
                    "distance_value": default_distance,
                    "active_price_btn": default_price_btn,
                    "active_dist_btn": default_distance_btn,
                },
            ),
            # Outer container for all button rows with fixed width of 375px
            html.Div(
                [
                    # Price buttons row - with label and buttons on the same row
                    html.Div(
                        [
                            # Label on the left
                            html.Label(
                                "Макс. цена (₽):",
                                className="dash-label",
                                style={
                                    "marginBottom": "2px", 
                                    "marginRight": "5px", 
                                    "minWidth": "110px",  # Fixed identical width using minWidth
                                    "width": "110px",     # Both width and minWidth for consistency
                                    "display": "inline-block",
                                    "whiteSpace": "nowrap"
                                },
                            ),
                            # Buttons on the right - completely joined
                            html.Div(
                                [
                                    html.Button(
                                        btn["label"],
                                        id=btn["id"],
                                        style={
                                            **BUTTON_STYLES["price"],
                                            "opacity": 1.0 if btn.get("default", False) else 0.6,
                                            "boxShadow": "0 0 5px #4682B4" if btn.get("default", False) else None,
                                            "flex": "1",  # Each button flex equally
                                            "margin": "0",  # Zero margin
                                            "padding": "2px 0",  # Reduced vertical padding for shorter height
                                            "fontSize": "10px",  # Smaller font size
                                            "lineHeight": "1",  # Tighter line height
                                            "borderRadius": "0",  # No rounded corners
                                            "borderLeft": "none" if i > 0 else "1px solid #ccc",  # Remove left border for all but first button
                                            "position": "relative",  # For z-index to work
                                            "zIndex": "1" if btn.get("default", False) else "0",  # Active button appears on top
                                        },
                                    )
                                    for i, btn in enumerate(PRICE_BUTTONS)
                                ],
                                style={
                                    "display": "flex",
                                    "flex": "1",  # Take all remaining space
                                    "width": "100%",
                                    "gap": "0",  # No gap between buttons
                                    "border-collapse": "collapse",  # Collapse borders
                                },
                            ),
                        ],
                        style={
                            "margin": "2px", 
                            "marginBottom": "6px",  # Add space between rows
                            "textAlign": "left", 
                            "width": "100%",
                            "display": "flex", 
                            "alignItems": "center"
                        },
                    ),
                    # Distance buttons row - with label and buttons on the same row
                    html.Div(
                        [
                            # Label on the left
                            html.Label(
                                "Макс. расстояние (км):",
                                className="dash-label",
                                style={
                                    "marginBottom": "2px", 
                                    "marginRight": "5px", 
                                    "minWidth": "110px",  # Fixed identical width using minWidth
                                    "width": "110px",     # Both width and minWidth for consistency
                                    "display": "inline-block",
                                    "whiteSpace": "nowrap"
                                },
                            ),
                            # Buttons on the right - completely joined
                            html.Div(
                                [
                                    html.Button(
                                        btn["label"],
                                        id=btn["id"],
                                        style={
                                            **BUTTON_STYLES["distance"],
                                            "opacity": 1.0 if btn.get("default", False) else 0.6,
                                            "boxShadow": "0 0 5px #4682B4" if btn.get("default", False) else None,
                                            "flex": "1",  # Each button flex equally
                                            "margin": "0",  # Zero margin
                                            "padding": "2px 0",  # Reduced vertical padding for shorter height
                                            "fontSize": "10px",  # Smaller font size
                                            "lineHeight": "1",  # Tighter line height
                                            "borderRadius": "0",  # No rounded corners
                                            "borderLeft": "none" if i > 0 else "1px solid #ccc",  # Remove left border for all but first button
                                            "position": "relative",  # For z-index to work
                                            "zIndex": "1" if btn.get("default", False) else "0",  # Active button appears on top
                                        },
                                    )
                                    for i, btn in enumerate(DISTANCE_BUTTONS)
                                ],
                                style={
                                    "display": "flex",
                                    "flex": "1",  # Take all remaining space
                                    "width": "100%",
                                    "gap": "0",  # No gap between buttons
                                    "border-collapse": "collapse",  # Collapse borders
                                },
                            ),
                        ],
                        style={
                            "margin": "2px", 
                            "marginBottom": "6px",  # Add space between rows
                            "textAlign": "left", 
                            "width": "100%",
                            "display": "flex", 
                            "alignItems": "center"
                        },
                    ),
                    # Filter buttons - label inside container with consistent alignment
                    html.Div(
                        [
                            html.Label(
                                "Быстрые фильтры:",
                                className="dash-label",
                                style={"marginBottom": "2px", "marginLeft": "4px", "textAlign": "left"},
                            ),
                        ],
                        style={
                            "margin": "2px", 
                            "marginTop": "5px",
                            "textAlign": "left", 
                            "width": "100%",
                        },
                    ),
                    # Filter buttons row 
                    html.Div(
                        [
                            html.Button(
                                "За сутки",
                                id="btn-updated-today",
                                style={**BUTTON_STYLES["updated_today"], "opacity": "0.6", "flex": "1"},
                            ),
                            html.Button(
                                "Рядом",
                                id="btn-nearest",
                                style={**BUTTON_STYLES["nearest"], "opacity": "0.6", "flex": "1"},
                            ),
                            html.Button(
                                "Выгодно",
                                id="btn-below-estimate",
                                style={**BUTTON_STYLES["below_estimate"], "opacity": "0.6", "flex": "1"},
                            ),
                            html.Button(
                                "Неактивные",
                                id="btn-inactive",
                                style={**BUTTON_STYLES["inactive"], "opacity": "0.6", "flex": "1"},
                            ),
                        ],
                        style={
                            "margin": "2px",
                            "display": "flex",
                            "width": "100%",
                            "gap": "0px",  # No gap between buttons
                        },
                    ),
                ],
                style={"textAlign": "left", "width": "355px", "padding": "0px"},  # Fixed width with no padding
            ),
            # Table container
            dcc.Loading(
                id="loading-main",
                children=[html.Div(id="table-container")],
                style={"margin": "5px"},
            ),
        ],
        style=STYLE["container"],
    )
    return app.layout