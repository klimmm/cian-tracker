# app/layout.py
from dash import dcc, html
import dash
from typing import Dict, Any, List, Optional
from app.config import PRICE_BUTTONS, DISTANCE_BUTTONS, SORT_BUTTONS, STYLE, BUTTON_STYLES
from app.components import ButtonFactory, ContainerFactory, StyleManager

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


def create_filter_buttons() -> html.Div:
    """Create the filter toggle buttons with consistent styling."""
    # Create filter buttons with a label - similar to other button groups
    return html.Div(
        [
            # Label on the left
            html.Label(
                "Быстрые фильтры:",
                className="dash-label",
                style={
                    "marginBottom": "2px",
                    "marginRight": "5px",
                    "minWidth": "110px",
                    "width": "110px",
                    "display": "inline-block",
                    "whiteSpace": "nowrap",
                    "fontSize": "10px",
                },
            ),
            # Buttons in a row - consistent with other button groups
            html.Div(
                [
                    html.Button(
                        html.Span("Свежие", id="btn-updated-today-text"),
                        id="btn-updated-today",
                        style=StyleManager.create_button_style("updated_today", False, i, True)
                    ) if i == 0 else
                    html.Button(
                        html.Span("Рядом", id="btn-nearest-text"),
                        id="btn-nearest",
                        style=StyleManager.create_button_style("nearest", False, i, True)
                    ) if i == 1 else
                    html.Button(
                        html.Span("Выгодно", id="btn-below-estimate-text"),
                        id="btn-below-estimate",
                        style=StyleManager.create_button_style("below_estimate", False, i, True)
                    ) if i == 2 else
                    html.Button(
                        html.Span("Активные", id="btn-inactive-text"),
                        id="btn-inactive",
                        style=StyleManager.create_button_style("inactive", False, i, True)
                    )
                    for i in range(4)
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


def create_apartment_details_panel() -> html.Div:
    """Create the overlay details panel."""
    return html.Div(
        id="apartment-details-panel",
        style=StyleManager.create_container_style("card", {
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
            "padding": "15px",
            "overflow": "auto",
        }),
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


def create_app_layout(app: dash.Dash) -> html.Div:
    """Create the application layout with components."""
    # Create a store for the selected apartment
    selected_apartment_store = dcc.Store(
        id="selected-apartment-store", data=None, storage_type="memory"
    )

    # Create apartment details panel
    apartment_details_panel = create_apartment_details_panel()

    # Base components for the layout
    header = html.H2("Cian Apartment Dashboard", style=STYLE["header"])
    update_time = html.Div(
        html.Span(id="last-update-time", style=STYLE["update_time"])
    )
    refresh_interval = dcc.Interval(
        id="interval-component", interval=2 * 60 * 1000, n_intervals=0
    )
    
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
            "sort_column": "date_sort_combined",
            "sort_direction": "desc",
            "active_sort_btn": "btn-sort-time",
        },
    )
    
    # Create button groups for controls using ButtonFactory
    price_buttons = ButtonFactory.create_button_group(
        PRICE_BUTTONS, "Макс. цена (₽):", default_price_btn
    )
    
    distance_buttons = ButtonFactory.create_button_group(
        DISTANCE_BUTTONS, "Макс. расстояние (км):", default_distance_btn
    )
    
    sort_buttons = ButtonFactory.create_button_group(
        SORT_BUTTONS, "Сортировать:", "btn-sort-time"  # Updated default
    )
    
    filter_buttons = create_filter_buttons()
    
    # Combine all controls into a container with left alignment
    controls_container = html.Div(
        [
            price_buttons,
            distance_buttons,
            filter_buttons,  # Now includes label
            sort_buttons,
        ],
        style={
            "textAlign": "left",
            "width": "355px",
            "padding": "0px",
            "margin": "0",
            "alignSelf": "flex-start",
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
    
    # Return the layout with all components
    return html.Div(
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