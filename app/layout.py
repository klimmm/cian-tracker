# app/layout.py
from dash import dcc, html
from app.config import BUTTON_STYLES, PRICE_BUTTONS, DISTANCE_BUTTONS, SORT_BUTTONS, STYLE

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


def create_button_group(buttons, label_text, active_button_id=None):
    """Create a consistent button group with label and joined buttons.
    
    Args:
        buttons: List of button config dictionaries
        label_text: Text label for the button group
        active_button_id: ID of the currently active button
        
    Returns:
        html.Div container with label and buttons
    """
    return html.Div(
        [
            # Label on the left
            html.Label(
                label_text,
                className="dash-label",
                style={
                    "marginBottom": "2px",
                    "marginRight": "5px",
                    "minWidth": "110px",
                    "width": "110px",
                    "display": "inline-block",
                    "whiteSpace": "nowrap",
                },
            ),
            # Buttons on the right - completely joined
            html.Div(
                [
                    html.Button(
                        btn["label"],
                        id=btn["id"],
                        style={
                            **BUTTON_STYLES.get(btn.get("type", "default"), {}),
                            "opacity": 1.0 if btn.get("default", False) or btn["id"] == active_button_id else 0.6,
                            "boxShadow": "0 0 5px #4682B4" if btn.get("default", False) or btn["id"] == active_button_id else None,
                            "flex": "1",
                            "margin": "0",
                            "padding": "2px 0",
                            "fontSize": "10px",
                            "lineHeight": "1",
                            "borderRadius": "0",
                            "borderLeft": "none" if i > 0 else "1px solid #ccc",
                            "position": "relative",
                            "zIndex": "1" if btn.get("default", False) or btn["id"] == active_button_id else "0",
                        },
                    )
                    for i, btn in enumerate(buttons)
                ],
                style={
                    "display": "flex",
                    "flex": "1",
                    "width": "100%",
                    "gap": "0",
                    "border-collapse": "collapse",
                },
            ),
        ],
        style={
            "margin": "2px",
            "marginBottom": "6px",
            "textAlign": "left",
            "width": "100%",
            "display": "flex",
            "alignItems": "center",
        },
    )


def create_filter_buttons():
    """Create the filter toggle buttons."""
    return html.Div(
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
                "Активные",
                id="btn-inactive",
                style={**BUTTON_STYLES["inactive"], "opacity": "0.6", "flex": "1"},
            ),
        ],
        style={
            "margin": "2px",
            "display": "none",
            "width": "100%",
            "gap": "0px",
        },
    )


def create_apartment_details_panel():
    """Create the overlay details panel."""
    return html.Div(
        id="apartment-details-panel",
        style={
            "display": "none",
            "position": "fixed",
            "top": "50%",
            "left": "50%",
            "transform": "translate(-50%, -50%)",
            "width": "345px",
            "minWidth": "345px",
            "maxWidth": "345px",
            "maxHeight": "100%",
            "zIndex": "1000",
            "backgroundColor": "#fff",
            "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.2)",
            "borderRadius": "8px",
            "padding": "15px",
            "overflow": "auto",
        },
        children=[
            # Top right close button
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "flex-end",
                    "padding": "0px",
                    "position": "absolute",
                    "top": "10px",
                    "right": "10px",
                    "zIndex": "1001",
                },
                children=[
                    html.Button(
                        "×",
                        id="close-details-button",
                        style={
                            "backgroundColor": "transparent",
                            "border": "none",
                            "color": "#4682B4",
                            "fontSize": "24px",
                            "fontWeight": "bold",
                            "cursor": "pointer",
                            "padding": "0",
                            "width": "24px",
                            "height": "24px",
                            "lineHeight": "20px",
                            "borderRadius": "50%",
                            "transition": "background-color 0.2s",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                    )
                ],
            ),
            # Navigation buttons
            html.Div(
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                    "marginBottom": "10px",
                    "marginTop": "30px",
                },
                children=[
                    html.Button(
                        "←",
                        id="prev-apartment-button",
                        style={
                            "backgroundColor": "#4682B4",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "4px",
                            "padding": "3px 8px",
                            "fontSize": "12px",
                            "fontWeight": "bold",
                            "cursor": "pointer",
                        },
                    ),
                    html.Button(
                        "→",
                        id="next-apartment-button",
                        style={
                            "backgroundColor": "#4682B4",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "4px",
                            "padding": "3px 8px",
                            "fontSize": "12px",
                            "fontWeight": "bold",
                            "cursor": "pointer",
                        },
                    ),
                ],
            ),
            # Dynamic content
            html.Div(id="apartment-details-card", style={"marginTop": "0px"}),
        ],
    )


def create_app_layout(app):
    """Create the application layout with components."""
    # Create a store for the selected apartment
    selected_apartment_store = dcc.Store(
        id="selected-apartment-store", data=None, storage_type="memory"
    )

    # Create apartment details panel
    apartment_details_panel = create_apartment_details_panel()

    # Base components for the layout
    header = html.H2("", style=STYLE["header"])
    update_time = html.Div(html.Span(id="last-update-time", style=STYLE["update_time"]))
    refresh_interval = dcc.Interval(id="interval-component", interval=2 * 60 * 1000, n_intervals=0)
    
    # Filter store with default values
    filter_store = dcc.Store(
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
            "sort_column": "distance_sort",
            "sort_direction": "asc",
            "active_sort_btn": "btn-sort-distance",
        },
    )
    
    # Create button groups for controls
    price_buttons = create_button_group(
        PRICE_BUTTONS, "Макс. цена (₽):", default_price_btn
    )
    
    distance_buttons = create_button_group(
        DISTANCE_BUTTONS, "Макс. расстояние (км):", default_distance_btn
    )
    
    sort_buttons = create_button_group(
        SORT_BUTTONS, "Сортировать:", "btn-sort-distance"
    )
    
    filter_buttons = create_filter_buttons()
    
    # Filter label
    filter_label = html.Div(
        [
            html.Label(
                "Быстрые фильтры:",
                className="dash-label",
                style={
                    "marginBottom": "2px",
                    "marginLeft": "4px",
                    "textAlign": "left",
                },
            ),
        ],
        style={
            "margin": "2px",
            "display": "none",
            "marginTop": "5px",
            "textAlign": "left",
            "width": "100%",
        },
    )
    
    # Combine all controls into a container
    controls_container = html.Div(
        [
            price_buttons,
            distance_buttons,
            filter_label,
            filter_buttons,
            sort_buttons,
        ],
        style={
            "textAlign": "left",
            "width": "355px",
            "padding": "0px",
        },
    )
    
    # Create main layout structure
    main_layout = [
        header,
        update_time,
        refresh_interval,
        filter_store,
        controls_container,
    ]
    
    # Set the app layout with all components
    app.layout = html.Div(
        main_layout + [
            # Table container with ID for toggling visibility
            html.Div(
                id="table-view-container",
                children=[
                    dcc.Loading(
                        id="loading-main",
                        children=[
                            html.Div(id="table-container"),
                            apartment_details_panel,
                        ],
                        style={"margin": "5px"},
                    )
                ],
            ),
            # Store for tracking the selected apartment
            selected_apartment_store,
            # Store for expanded row
            dcc.Store(id="expanded-row-store", data=None),
        ],
        style=STYLE["container"],
    )
    
    return app.layout