# app/layout.py
from dash import dcc, html
from app.button_factory import (
    DEFAULT_PRICE,
    DEFAULT_PRICE_BTN,
    DEFAULT_DISTANCE,
    DEFAULT_DISTANCE_BTN,
)
from app.button_factory import (
    price_buttons,
    distance_buttons,
    sort_buttons,
    filter_buttons,
)
from app.table_factory import TableFactory


# Update this function in layout.py to move navigation panel to the top
def create_apartment_details_panel():
    """Create the improved overlay details panel with navigation at the top."""
    return html.Div(
        [
            # Background overlay - ensure it starts hidden
            html.Div(
                id="details-overlay",
                className="details-overlay details-panel--hidden",
            ),
            # Main panel - ensure it starts hidden
            html.Div(
                id="apartment-details-panel",
                className="details-panel details-panel--hidden",
                children=[
                    # Header with title, navigation, and close button
                    html.Div(
                        className="details-panel-header",
                        children=[
                            # Left side - back button
                            html.Button(
                                "← Пред.",
                                id="prev-apartment-button",
                                className="details-nav-button details-nav-button--prev",
                                n_clicks=0,
                            ),
                            # Center - title
                            html.H3(
                                "Информация о квартире", className="details-panel-title"
                            ),
                            # Right side - next button and close button
                            html.Div(
                                className="details-header-right",
                                children=[
                                    html.Button(
                                        "След. →",
                                        id="next-apartment-button",
                                        className="details-nav-button details-nav-button--next",
                                        n_clicks=0,
                                    ),
                                    html.Button(
                                        "×",
                                        id="close-details-button",
                                        className="details-close-x",
                                        n_clicks=0,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    # Scrollable content area - start with empty div to prevent errors
                    html.Div(
                        id="apartment-details-card",
                        className="details-panel-content",
                        children=[],  # Start with empty array
                    ),
                ],
            ),
        ],
        id="details-panel-container",  # Add container ID for easier targeting
    )


def create_app_layout(app):
    """Create the improved application layout structure with inline button labels and buttons."""
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
            "inactive": True,
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
                className="update-info",
            ),
        ],
        className="header-container",
    )

    refresh_interval = dcc.Interval(
        id="interval-component", interval=2 * 60 * 1000, n_intervals=0
    )

    # Reorganize controls to have two button groups per row with responsive behavior
    controls_container = html.Div(
        [
            # 1st line: price
            html.Div(price_buttons, className="controls-row"),
            # 2nd line: distance
            html.Div(distance_buttons, className="controls-row"),
            # 3rd line: filters
            html.Div(filter_buttons,   className="controls-row"),
            # 4th line: sorting
            html.Div(sort_buttons,     className="controls-row"),
        ],
        className="controls-container",
    )


    # Detail panel for apartment information with improved design
    apartment_details_panel = create_apartment_details_panel()

    # Initialize empty data table to ensure it exists in the layout
    empty_data_table = TableFactory.create_data_table()

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
                            html.Div(
                                id="table-container",
                                className="table-responsive",
                                children=[
                                    empty_data_table
                                ],  # Include empty table in initial layout
                            ),
                            apartment_details_panel,
                        ],
                        type="circle",
                    )
                ],
                className="content-container",
            ),
            # Data stores
            selected_apartment_store,
            expanded_row_store,
            apartment_data_store,
        ],
        className="main-container",
    )
