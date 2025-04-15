# app/layout.py - Corrected and improved
from dash import dcc, html
from app.config import PRICE_BUTTONS, DISTANCE_BUTTONS, SORT_BUTTONS, STYLE
from app.components import ButtonFactory

# Default configuration values
DEFAULT_PRICE = next(
    (btn["value"] for btn in PRICE_BUTTONS if btn.get("default", False)), 80000
)
DEFAULT_PRICE_BTN = next(
    (btn["id"] for btn in PRICE_BUTTONS if btn.get("default", False)), "btn-price-80k"
)
DEFAULT_DISTANCE = next(
    (btn["value"] for btn in DISTANCE_BUTTONS if btn.get("default", False)), 3.0
)
DEFAULT_DISTANCE_BTN = next(
    (btn["id"] for btn in DISTANCE_BUTTONS if btn.get("default", False)), "btn-dist-3km"
)


def create_apartment_details_panel():
    """Create the improved overlay details panel for apartment information."""
    return html.Div([
        # Background overlay
        html.Div(
            id="details-overlay",
            className="details-overlay details-panel--hidden",
        ),
        # Main panel
        html.Div(
            id="apartment-details-panel",
            className="details-panel details-panel--hidden",
            children=[
                # Header with title and close button
                html.Div(
                    className="details-panel-header",
                    children=[
                        html.H3("Информация о квартире", className="details-panel-title"),
                        html.Div(
                            className="details-close-button",
                            children=[
                                html.Button("×", id="close-details-button", className="details-close-x")
                            ],
                        ),
                    ],
                ),
                # Scrollable content area
                html.Div(
                    id="apartment-details-card", 
                    className="details-panel-content"
                ),
                # Improved navigation footer
                html.Div(
                    className="details-nav",
                    children=[
                        html.Button(
                            "← Предыдущая",
                            id="prev-apartment-button", 
                            className="details-nav-button"
                        ),
                        html.Div(
                            id="apartment-position-info",
                            className="details-nav-info",
                            children=["Квартира"]
                        ),
                        html.Button(
                            "Следующая →",
                            id="next-apartment-button", 
                            className="details-nav-button"
                        ),
                    ],
                ),
            ],
        )
    ])


def create_filter_buttons():
    """Create improved quick filter toggle buttons with modern styling."""
    filter_buttons = [
        {
            "id": "btn-updated-today",
            "label": "Свежие",
            "variant": "success"
        },
        {
            "id": "btn-nearest",
            "label": "Рядом",
            "variant": "primary"
        },
        {
            "id": "btn-below-estimate",
            "label": "Ниже оценки",
            "variant": "warning"
        },
        {
            "id": "btn-inactive",
            "label": "Только активные",
            "variant": "default"
        }
    ]
    
    # Create button group using modernized components
    return ButtonFactory.create_button_group(
        filter_buttons, 
        label_text="Фильтры", 
        direction="horizontal"
    )


def create_app_layout(app):
    """Create the improved application layout structure."""
    # Create stores for application state
    apartment_data_store = dcc.Store(
        id="apartment-data-store", storage_type="memory", data=[]
    )
    selected_apartment_store = dcc.Store(
        id="selected-apartment-store", data=None, storage_type="memory"
    )
    expanded_row_store = dcc.Store(id="expanded-row-store", data=None)

    # Initialize filter store with default values
    filter_store = dcc.Store(
        id="filter-store",
        data={
            "nearest": False,
            "below_estimate": False,
            "inactive": False,
            "updated_today": False,
            "price_value": DEFAULT_PRICE,
            "distance_value": DEFAULT_DISTANCE,
            "active_price_btn": DEFAULT_PRICE_BTN,
            "active_dist_btn": DEFAULT_DISTANCE_BTN,
            "sort_column": "date_sort_combined",
            "sort_direction": "desc",
            "active_sort_btn": "btn-sort-time",
        },
    )

    # Create header components with improved styling
    header = html.Div(
        [
            html.H2("Cian Apartment Dashboard", className="dashboard-header"),
            html.Div(
                html.Span(id="last-update-time", className="update-time"),
                className="update-info"
            )
        ],
        className="header-container"
    )
    
    refresh_interval = dcc.Interval(
        id="interval-component", interval=2 * 60 * 1000, n_intervals=0
    )

    # Create button groups for filters with improved classes
    price_buttons = ButtonFactory.create_button_group(
        PRICE_BUTTONS, "Максимальная цена (₽):", DEFAULT_PRICE_BTN
    )
    distance_buttons = ButtonFactory.create_button_group(
        DISTANCE_BUTTONS, "Максимальное расстояние (км):", DEFAULT_DISTANCE_BTN
    )
    sort_buttons = ButtonFactory.create_button_group(
        SORT_BUTTONS, "Сортировать:", "btn-sort-time"
    )
    filter_buttons = create_filter_buttons()

    # Controls container with grouping
    controls_container = html.Div(
        [
            html.Div([price_buttons, distance_buttons], className="controls-row"),
            html.Div([filter_buttons, sort_buttons], className="controls-row"),
        ],
        className="controls-container"
    )

    # Detail panel for apartment information with improved design
    apartment_details_panel = create_apartment_details_panel()

    # Main layout structure
    return html.Div(
        [
            # Header section
            header,
            refresh_interval,
            filter_store,
            # Controls section with improved styling
            controls_container,
            # Table view container
            html.Div(
                id="table-view-container",
                children=[
                    dcc.Loading(
                        id="loading-main",
                        children=[
                            html.Div(id="table-container", className="table-responsive"),
                            apartment_details_panel,
                        ],
                        type="circle",
                    )
                ],
                className="content-container"
            ),
            # Data stores
            selected_apartment_store,
            expanded_row_store,
            apartment_data_store,
        ],
        className="main-container"
    )