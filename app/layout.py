# app/layout.py - Improved version

from dash import dcc, html
from app.button_factory import (
    DEFAULT_PRICE,
    DEFAULT_PRICE_BTN,
    DEFAULT_DISTANCE,
    DEFAULT_DISTANCE_BTN,
    price_buttons,
    distance_buttons,
    sort_buttons,
    filter_buttons,
)
from app.table_factory import TableFactory
from app.apartment_card_callbacks import create_apartment_details_panel


def create_app_layout(
    app,
    initial_records: list = None,
    initial_update_time: str = "",
):
    """
    Build the main dashboard layout with improved organization.
    """
    # ─── Data stores and interval ────────────────────────────────────────────
    apartment_data_store = dcc.Store(
        id="apartment-data-store",
        storage_type="memory",
        data=initial_records or [],
    )

    # Data check interval next to its associated store (semantically grouped)
    data_check_interval = dcc.Interval(
        id="data-check-interval",
        interval=1000,  # Check every second
        max_intervals=20,  # Reduced to 20 seconds maximum
        n_intervals=0,
        disabled=False,
    )

    # Other stores
    selected_apartment_store = dcc.Store(
        id="selected-apartment-store", storage_type="memory", data=None
    )
    expanded_row_store = dcc.Store(
        id="expanded-row-store", storage_type="memory", data=None
    )
    filter_store = dcc.Store(
        id="filter-store",
        storage_type="memory",
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
    preload_status_store = dcc.Store(
        id="preload-status-store", storage_type="memory", data={"status": "not_started"}
    )
    image_preload_trigger = dcc.Store(
        id="image-preload-trigger",
        storage_type="memory",
        data={"status": "not_started", "preloading_started": False},
    )

    # ─── Header with timestamp ──────────────────────────────────
    header = html.Div(
        [
            html.H2("Cian Apartment Dashboard", className="dashboard-header"),
            html.Div(
                html.Span(
                    initial_update_time,
                    id="last-update-time",
                    className="update-info-text",
                ),
                className="update-info",
            ),
        ],
        className="header-container",
    )

    # ─── Controls ───────────────────────────────────────────────
    controls = html.Div(
        [
            html.Div(price_buttons, className="controls-row"),
            html.Div(distance_buttons, className="controls-row"),
            html.Div(filter_buttons, className="controls-row"),
            html.Div(sort_buttons, className="controls-row"),
        ],
        className="controls-container",
    )

    # ─── Table + Details Panel with better loading ─────────────────────
    table = TableFactory.create_data_table()

    # Create details panel
    details = create_apartment_details_panel()

    # Use Dash's built-in loading component instead of custom CSS
    table_view = html.Div(
        id="table-view-container",
        className="content-container",
        children=[
            # Table with proper Dash loading
            dcc.Loading(
                id="loading-table",
                type="circle",
                children=html.Div(
                    id="table-container", className="table-responsive", children=[table]
                ),
            ),
            # Separate loading for details panel
            details,
        ],
    )

    return html.Div(
        [
            header,
            filter_store,
            controls,
            table_view,
            html.Div(
                [
                    # Data store with its interval grouped together
                    apartment_data_store,
                    data_check_interval,
                    # Other stores
                    selected_apartment_store,
                    expanded_row_store,
                    preload_status_store,
                    image_preload_trigger,
                ],
                style={"display": "none"},  # Hide div containing stores
            ),
        ],
        className="main-container",
    )
