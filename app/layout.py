# app/layout.py
from dash import dcc, html
import dash
from app.config import PRICE_BUTTONS, DISTANCE_BUTTONS, SORT_BUTTONS, STYLE
from app.components import ButtonFactory, ContainerFactory

# Default values
default_price = next((btn["value"] for btn in PRICE_BUTTONS if btn.get("default", False)), 80000)
default_price_btn = next((btn["id"] for btn in PRICE_BUTTONS if btn.get("default", False)), "btn-price-80k")
default_distance = next((btn["value"] for btn in DISTANCE_BUTTONS if btn.get("default", False)), 3.0)
default_distance_btn = next((btn["id"] for btn in DISTANCE_BUTTONS if btn.get("default", False)), "btn-dist-3km")

def create_filter_buttons():
    """Create filter toggle buttons."""
    # Create buttons with a label
    return html.Div([
        # Label
        html.Label("Быстрые фильтры:", className="dash-label", style={
            "marginBottom": "2px", "marginRight": "5px", "minWidth": "110px",
            "width": "110px", "display": "inline-block", "whiteSpace": "nowrap", "fontSize": "10px"
        }),
        # Buttons row
        html.Div([
            html.Button(html.Span("Свежие", id="btn-updated-today-text"), id="btn-updated-today", 
                       style={"flex": "1", "margin": "0", "borderRadius": "0", "borderLeft": "1px solid #ccc" if i == 0 else "none"})
            if i == 0 else
            html.Button(html.Span("Рядом", id="btn-nearest-text"), id="btn-nearest", 
                       style={"flex": "1", "margin": "0", "borderRadius": "0", "borderLeft": "none"})
            if i == 1 else
            html.Button(html.Span("Выгодно", id="btn-below-estimate-text"), id="btn-below-estimate", 
                       style={"flex": "1", "margin": "0", "borderRadius": "0", "borderLeft": "none"})
            if i == 2 else
            html.Button(html.Span("Активные", id="btn-inactive-text"), id="btn-inactive", 
                       style={"flex": "1", "margin": "0", "borderRadius": "0", "borderLeft": "none"})
            for i in range(4)
        ], style={"display": "flex", "flex": "1", "width": "100%", "gap": "0", "border-collapse": "collapse"}),
    ], style={
        "margin": "2px", "marginBottom": "6px", "textAlign": "left",
        "width": "100%", "display": "flex", "alignItems": "center"
    })

def create_apartment_details_panel():
    """Create the overlay details panel."""
    return html.Div(
        id="apartment-details-panel",
        style={"display": "none", "position": "fixed", "top": "50%", "left": "50%", 
              "transform": "translate(-50%, -50%)", "width": "345px", "minWidth": "345px", 
              "maxWidth": "345px", "maxHeight": "100%", "zIndex": "1000", "padding": "15px", 
              "overflow": "auto", "backgroundColor": "#fff", "borderRadius": "6px", 
              "boxShadow": "0 2px 8px rgba(0, 0, 0, 0.1)"},
        children=[
            # Close button
            html.Div(
                style={"display": "flex", "justifyContent": "flex-end", "padding": "0px", 
                      "position": "absolute", "top": "10px", "right": "10px", "zIndex": "1001"},
                children=[
                    html.Button("×", id="close-details-button", style={
                        "backgroundColor": "transparent", "border": "none", "color": "#4682B4",
                        "fontSize": "24px", "fontWeight": "bold", "cursor": "pointer",
                        "padding": "0", "width": "24px", "height": "24px", "lineHeight": "20px",
                        "borderRadius": "50%", "transition": "background-color 0.2s",
                        "display": "flex", "alignItems": "center", "justifyContent": "center"
                    })
                ],
            ),
            # Navigation
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", 
                      "alignItems": "center", "marginBottom": "10px", "marginTop": "30px"},
                children=[
                    html.Button("←", id="prev-apartment-button", style={
                        "backgroundColor": "#4682B4", "color": "white", "border": "none",
                        "borderRadius": "4px", "padding": "3px 8px", "fontSize": "12px",
                        "fontWeight": "bold", "cursor": "pointer"
                    }),
                    html.Button("→", id="next-apartment-button", style={
                        "backgroundColor": "#4682B4", "color": "white", "border": "none",
                        "borderRadius": "4px", "padding": "3px 8px", "fontSize": "12px",
                        "fontWeight": "bold", "cursor": "pointer"
                    }),
                ],
            ),
            # Content
            html.Div(id="apartment-details-card", style={"marginTop": "0px"}),
        ],
    )

def create_app_layout(app):
    """Create the application layout."""
    # Create stores
    selected_apartment_store = dcc.Store(id="selected-apartment-store", data=None, storage_type="memory")
    
    # Create detail panel
    apartment_details_panel = create_apartment_details_panel()

    # Base layout components
    header = html.H2("Cian Apartment Dashboard", style=STYLE["header"])
    update_time = html.Div(html.Span(id="last-update-time", style=STYLE["update_time"]))
    refresh_interval = dcc.Interval(id="interval-component", interval=2 * 60 * 1000, n_intervals=0)
    
    # Filter store with defaults
    filter_store = dcc.Store(
        id="filter-store",
        data={
            "nearest": False, "below_estimate": False, "inactive": False, "updated_today": False,
            "price_value": default_price, "distance_value": default_distance,
            "active_price_btn": default_price_btn, "active_dist_btn": default_distance_btn,
            "sort_column": "date_sort_combined", "sort_direction": "desc",
            "active_sort_btn": "btn-sort-time"
        }
    )
    
    # Create button groups
    price_buttons = ButtonFactory.create_button_group(PRICE_BUTTONS, "Макс. цена (₽):", default_price_btn)
    distance_buttons = ButtonFactory.create_button_group(DISTANCE_BUTTONS, "Макс. расстояние (км):", default_distance_btn)
    sort_buttons = ButtonFactory.create_button_group(SORT_BUTTONS, "Сортировать:", "btn-sort-time")
    filter_buttons = create_filter_buttons()
    
    # Controls container
    controls_container = html.Div(
        [price_buttons, distance_buttons, filter_buttons, sort_buttons],
        style={"textAlign": "left", "width": "355px", "padding": "0px", "margin": "0", "alignSelf": "flex-start"}
    )
    
    # Main layout structure
    return html.Div(
        [
            header,
            update_time,
            refresh_interval,
            filter_store,
            controls_container,
            # Table container
            html.Div(
                id="table-view-container",
                children=[
                    dcc.Loading(
                        id="loading-main",
                        children=[
                            html.Div(id="table-container"),
                            apartment_details_panel,
                        ],
                        style={"margin": "5px"}
                    )
                ]
            ),
            # Data stores
            selected_apartment_store,
            dcc.Store(id="expanded-row-store", data=None),
            # Important! This critical store was missing in the optimized code
            dcc.Store(id="apartment-data-store", storage_type="memory", data=[])
        ],
        style=STYLE["container"]
    )