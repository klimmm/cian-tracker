# app/dashboard_callbacks.py
from dash import callback_context as ctx
from dash.dependencies import Input, Output, State, MATCH
import dash
import logging
from dash import ClientsideFunction
from app.button_factory import PRICE_BUTTONS, DISTANCE_BUTTONS, SORT_BUTTONS
from app.apartment_card_callbacks import register_apartment_card_callbacks
from app.table_callbacks import register_data_callbacks
from app.images_preload_callbacks import images_preload_callbacks
logger = logging.getLogger(__name__)


def register_all_callbacks(app):
    """Register all application callbacks in a structured manner."""
    register_data_callbacks(app)
    register_button_callbacks(app)
    register_apartment_card_callbacks(app)
    register_slideshow_callbacks(app)
    images_preload_callbacks(app)


def register_slideshow_callbacks(app):
    app.clientside_callback(
        ClientsideFunction(namespace='slideshow', function_name='nav'),
        [
            Output({'type': 'slideshow-data', 'offer_id': MATCH}, 'data'),
            Output({'type': 'slideshow-img', 'offer_id': MATCH}, 'src'),
            Output({'type': 'counter', 'offer_id': MATCH}, 'children'),
        ],
        [
            Input({'type': 'prev-btn', 'offer_id': MATCH}, 'n_clicks'),
            Input({'type': 'next-btn', 'offer_id': MATCH}, 'n_clicks'),
        ],
        [State({'type': 'slideshow-data', 'offer_id': MATCH}, 'data')],
        prevent_initial_call=True,
    )


def register_button_callbacks(app):
    """Register optional button-based callbacks (only used if table clicks don't work)."""

    @app.callback(
        [*[Output(f"{btn['id']}-text", "children") for btn in SORT_BUTTONS]],
        [Input("filter-store", "data")],
        prevent_initial_call=False,
    )
    def update_sort_button_text(filters):
        """Update sort button text with direction indicators."""
        if not filters:
            return [btn["label"] for btn in SORT_BUTTONS]

        active_btn = filters.get("active_sort_btn")
        sort_direction = filters.get("sort_direction", "asc")

        return [
            (
                f"{btn['label']} {'↑' if sort_direction == 'asc' else '↓'}"
                if btn["id"] == active_btn
                else btn["label"]
            )
            for btn in SORT_BUTTONS
        ]

    @app.callback(
        [Output("filter-store", "data")],
        [
            *[Input(btn["id"], "n_clicks") for btn in PRICE_BUTTONS],
            *[Input(btn["id"], "n_clicks") for btn in DISTANCE_BUTTONS],
            Input("btn-nearest", "n_clicks"),
            Input("btn-below-estimate", "n_clicks"),
            Input("btn-inactive", "n_clicks"),
            Input("btn-updated-today", "n_clicks"),
            *[Input(btn["id"], "n_clicks") for btn in SORT_BUTTONS],
        ],
        [State("filter-store", "data")],
        prevent_initial_call=True,
    )
    def update_filters(*args):
        """Update filters based on user interactions."""
        # Get triggered button
        if not (ctx_msg := ctx.triggered[0] if ctx.triggered else None):
            return [dash.no_update]

        trigger_id = ctx_msg["prop_id"].split(".")[0]
        current_filters = args[-1] or {}

        if trigger_id in [btn["id"] for btn in PRICE_BUTTONS]:
            current_filters["active_price_btn"] = trigger_id
            current_filters["price_value"] = next(
                (btn["value"] for btn in PRICE_BUTTONS if btn["id"] == trigger_id),
                current_filters.get("price_value", 80000),
            )

        elif trigger_id in [btn["id"] for btn in DISTANCE_BUTTONS]:
            current_filters["active_dist_btn"] = trigger_id
            current_filters["distance_value"] = next(
                (btn["value"] for btn in DISTANCE_BUTTONS if btn["id"] == trigger_id),
                current_filters.get("distance_value", 3.0),
            )

        elif trigger_id in [
            "btn-nearest",
            "btn-below-estimate",
            "btn-inactive",
            "btn-updated-today",
        ]:
            filter_key = {
                "btn-nearest": "nearest",
                "btn-below-estimate": "below_estimate",
                "btn-inactive": "inactive",
                "btn-updated-today": "updated_today",
            }[trigger_id]
            current_filters[filter_key] = not current_filters.get(filter_key, False)

        elif trigger_id in [btn["id"] for btn in SORT_BUTTONS]:
            button = next(
                (btn for btn in SORT_BUTTONS if btn["id"] == trigger_id), None
            )
            if button:
                if current_filters.get("active_sort_btn") == trigger_id:
                    current_filters["sort_direction"] = (
                        "desc"
                        if current_filters.get("sort_direction") == "asc"
                        else "asc"
                    )
                else:
                    current_filters["active_sort_btn"] = trigger_id
                    current_filters["sort_column"] = button["value"]
                    current_filters["sort_direction"] = button.get(
                        "default_direction", "asc"
                    )

        return [current_filters]

    @app.callback(
        [
            *[Output(btn["id"], "className") for btn in PRICE_BUTTONS],
            *[Output(btn["id"], "className") for btn in DISTANCE_BUTTONS],
            Output("btn-nearest", "className"),
            Output("btn-below-estimate", "className"),
            Output("btn-inactive", "className"),
            Output("btn-updated-today", "className"),
            *[Output(btn["id"], "className") for btn in SORT_BUTTONS],
        ],
        [Input("filter-store", "data")],
    )
    def update_button_styles(filters):
        """Update button classes based on active state."""
        if not filters:
            return dash.no_update

        classes = []

        def get_button_class(button_type, is_active=False):
            base_class = f"btn btn--{button_type}"
            if is_active:
                base_class += " btn--active"
            return base_class

        for btn in PRICE_BUTTONS:
            classes.append(
                get_button_class(
                    "default",
                    is_active=(btn["id"] == filters.get("active_price_btn")),
                )
            )

        for btn in DISTANCE_BUTTONS:
            classes.append(
                get_button_class(
                    "default",
                    is_active=(btn["id"] == filters.get("active_dist_btn")),
                )
            )

        filter_button_mapping = [
            ("btn-nearest", "default", "nearest"),
            ("btn-below-estimate", "default", "below_estimate"),
            ("btn-inactive", "default", "inactive"),
            ("btn-updated-today", "default", "updated_today"),
        ]

        for button_id, variant, filter_name in filter_button_mapping:
            classes.append(
                get_button_class(
                    variant,
                    is_active=filters.get(filter_name, False),
                )
            )

        # Sort buttons
        for btn in SORT_BUTTONS:
            classes.append(
                get_button_class(
                    "default",
                    is_active=(btn["id"] == filters.get("active_sort_btn")),
                )
            )

        return classes
