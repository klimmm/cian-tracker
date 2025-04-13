# app/dashboard_callbacks.py - Optimized
from dash import callback_context as ctx
from dash.dependencies import Input, Output, State, MATCH
import dash
import logging
import pandas as pd
from app.utils import DataManager, load_apartment_details
from app.apartment_card import create_apartment_details_card
from app.config import PRICE_BUTTONS, DISTANCE_BUTTONS, SORT_BUTTONS, BUTTON_STYLES
from dash import dash_table, html
from app.config import CONFIG, STYLE, COLUMN_STYLES, HEADER_STYLES
from app.components import StyleManager

logger = logging.getLogger(__name__)


def register_all_callbacks(app):
    """Register all callbacks."""
    register_data_callbacks(app)
    register_filter_callbacks(app)
    register_style_callbacks(app)
    register_details_callbacks(app)


def register_data_callbacks(app):
    """Register data-related callbacks."""

    @app.callback(
        [
            Output("apartment-data-store", "data"),
            Output("last-update-time", "children"),
        ],
        [Input("interval-component", "n_intervals")],
        prevent_initial_call=False,
    )
    def load_apartment_data(_):
        """Load apartment data and update store."""
        try:
            df, update_time = DataManager.load_data()
            if df.empty:
                return [], "Error: No data loaded"

            # Process the data
            df = DataManager.process_data(df)

            # Add details indicator
            if "details" not in df.columns:
                df["details"] = "🔍"

            # Get required columns
            required_cols = CONFIG["columns"]["display"] + [
                "details",
                "offer_id",
                "date_sort_combined",
            ]
            available_cols = [col for col in required_cols if col in df.columns]

            # Convert to dict
            df_dict = df[available_cols].to_dict("records") if not df.empty else []

            return df_dict, f"Актуально на: {update_time}"

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return [], f"Ошибка загрузки данных: {str(e)}"


def register_filter_callbacks(app):
    """Register filter-related callbacks."""

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
        """Update filters based on button clicks."""
        # Get triggered button
        if not (ctx_msg := ctx.triggered[0] if ctx.triggered else None):
            return [dash.no_update]

        trigger_id = ctx_msg["prop_id"].split(".")[0]
        current_filters = args[-1] or {}

        # Handle filter updates based on button type
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

        # Toggle filters
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

        # Handle sort buttons
        elif trigger_id in [btn["id"] for btn in SORT_BUTTONS]:
            button = next(
                (btn for btn in SORT_BUTTONS if btn["id"] == trigger_id), None
            )
            if button:
                # Toggle direction if same button clicked again
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
        [Output("table-container", "children")],
        [Input("filter-store", "data"), Input("apartment-data-store", "data")],
    )
    def update_table_content(filters, data):
        """Update table based on filters."""
        if not data:
            return [html.Div("Нет данных")]

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Apply filtering and sorting
        df = DataManager.filter_and_sort_data(df, filters)

        # Create table
        return [create_data_table(df)]

    @app.callback(
        Output("apartment-table", "data"),
        [Input("apartment-table", "sort_by"), Input("filter-store", "data")],
        [State("apartment-data-store", "data")],
    )
    def update_sort(sort_by, filters, data):
        """Handle table sorting."""
        if not data:
            return []

        df = pd.DataFrame(data)
        df = DataManager.filter_and_sort_data(df, filters, sort_by)
        return df.to_dict("records")

    @app.callback(
        [*[Output(f"{btn['id']}-text", "children") for btn in SORT_BUTTONS]],
        [Input("filter-store", "data")],
        prevent_initial_call=False,
    )
    def update_sort_button_text(filters):
        """Update sort button text with indicators."""
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


def register_style_callbacks(app):
    """Register style-related callbacks."""

    @app.callback(
        [
            *[Output(btn["id"], "style") for btn in PRICE_BUTTONS],
            *[Output(btn["id"], "style") for btn in DISTANCE_BUTTONS],
            Output("btn-nearest", "style"),
            Output("btn-below-estimate", "style"),
            Output("btn-inactive", "style"),
            Output("btn-updated-today", "style"),
            *[Output(btn["id"], "style") for btn in SORT_BUTTONS],
        ],
        [Input("filter-store", "data")],
    )
    def update_button_styles(filters):
        """Update button styles based on filter state."""
        if not filters:
            return dash.no_update

        styles = []

        # Create button styles function
        def get_button_style(button, index, type_name, is_active=False):
            base_style = StyleManager.merge_styles(
                BUTTON_STYLES.get(type_name, {}), {"flex": "1"}
            )

            if is_active:
                base_style.update({"opacity": 1.0, "boxShadow": "0 0 5px #4682B4"})
            else:
                base_style.update({"opacity": 0.6})

            return base_style

        # Price buttons
        for i, btn in enumerate(PRICE_BUTTONS):
            styles.append(
                get_button_style(
                    btn,
                    i,
                    "price",
                    is_active=(btn["id"] == filters.get("active_price_btn")),
                )
            )

        # Distance buttons
        for i, btn in enumerate(DISTANCE_BUTTONS):
            styles.append(
                get_button_style(
                    btn,
                    i,
                    "distance",
                    is_active=(btn["id"] == filters.get("active_dist_btn")),
                )
            )

        # Filter toggle buttons
        for filter_name, button_id in [
            ("nearest", "btn-nearest"),
            ("below_estimate", "btn-below-estimate"),
            ("inactive", "btn-inactive"),
            ("updated_today", "btn-updated-today"),
        ]:
            base_style = StyleManager.merge_styles(
                BUTTON_STYLES.get(filter_name, {}), {"flex": "1"}
            )

            if filters.get(filter_name):
                base_style.update({"opacity": 1.0, "boxShadow": "0 0 5px #4682B4"})
            else:
                base_style.update({"opacity": 0.6})

            styles.append(base_style)

        # Sort buttons
        for i, btn in enumerate(SORT_BUTTONS):
            styles.append(
                get_button_style(
                    btn,
                    i,
                    "sort",
                    is_active=(btn["id"] == filters.get("active_sort_btn")),
                )
            )

        return styles


def register_details_callbacks(app):
    """Register apartment details callbacks."""

    @app.callback(
        [
            Output("apartment-details-panel", "style"),
            Output("apartment-details-card", "children"),
            Output("selected-apartment-store", "data"),
        ],
        [
            Input("apartment-table", "active_cell"),
            Input("prev-apartment-button", "n_clicks"),
            Input("next-apartment-button", "n_clicks"),
            Input("close-details-button", "n_clicks"),
        ],
        [
            State("apartment-table", "data"),
            State("selected-apartment-store", "data"),
            State("apartment-details-panel", "style"),
        ],
        prevent_initial_call=True,
    )
    def handle_apartment_panel(
        active_cell,
        prev_clicks,
        next_clicks,
        close_clicks,
        table_data,
        selected_data,
        current_style,
    ):
        """Handle apartment details panel interactions."""
        triggered_id = ctx.triggered_id

        # Setup panel styles
        current_style = current_style or {}
        hidden_style = {
            **current_style,
            "opacity": "0",
            "visibility": "hidden",
            "pointer-events": "none",
            "display": "none",
        }
        visible_style = {
            **current_style,
            "opacity": "1",
            "visibility": "visible",
            "pointer-events": "auto",
            "display": "block",
        }

        # Handle close action
        if triggered_id == "close-details-button":
            return hidden_style, dash.no_update, None

        # Handle table cell click
        if (
            triggered_id == "apartment-table"
            and active_cell
            and active_cell.get("column_id") == "details"
        ):
            row_idx = active_cell["row"]
            row_data = table_data[row_idx]
            offer_id = row_data.get("offer_id")

            try:
                apartment_data = load_apartment_details(offer_id)
                details_card = create_apartment_details_card(
                    apartment_data, row_data, row_idx, len(table_data)
                )

                selected = {
                    "apartment_data": apartment_data,
                    "row_data": row_data,
                    "row_idx": row_idx,
                    "total_rows": len(table_data),
                    "offer_id": offer_id,
                    "table_data": table_data,
                }

                return visible_style, details_card, selected
            except Exception as e:
                logger.error(f"Error loading details: {e}")
                return (
                    visible_style,
                    html.Div(f"Ошибка загрузки: {e}", style={"color": "red"}),
                    None,
                )

        # Handle navigation
        if (
            triggered_id in ["prev-apartment-button", "next-apartment-button"]
            and selected_data
        ):
            current_idx = selected_data["row_idx"]
            table_data = selected_data["table_data"]
            total_rows = len(table_data)

            # Calculate new index
            new_idx = current_idx
            if triggered_id == "prev-apartment-button" and current_idx > 0:
                new_idx -= 1
            elif (
                triggered_id == "next-apartment-button" and current_idx < total_rows - 1
            ):
                new_idx += 1

            if new_idx == current_idx:
                return dash.no_update, dash.no_update, dash.no_update

            # Load new data
            new_row = table_data[new_idx]
            offer_id = new_row.get("offer_id")

            try:
                apartment_data = load_apartment_details(offer_id)
                details_card = create_apartment_details_card(
                    apartment_data, new_row, new_idx, total_rows
                )

                selected = {
                    "apartment_data": apartment_data,
                    "row_data": new_row,
                    "row_idx": new_idx,
                    "total_rows": total_rows,
                    "offer_id": offer_id,
                    "table_data": table_data,
                }

                return dash.no_update, details_card, selected
            except Exception as e:
                logger.error(f"Error loading details: {e}")
                return (
                    dash.no_update,
                    html.Div(f"Ошибка загрузки: {e}", style={"color": "red"}),
                    selected_data,
                )

        return dash.no_update, dash.no_update, dash.no_update

    # Slideshow navigation (client-side)
    app.clientside_callback(
        """
        function(prev_clicks, next_clicks, slideshow_data) {
            if (!slideshow_data || !slideshow_data.image_paths || !slideshow_data.image_paths.length) {
                return [slideshow_data, "", ""];
            }
            
            let currentIndex = slideshow_data.current_index || 0;
            const imagePaths = slideshow_data.image_paths;
            const totalImages = imagePaths.length;
            
            const prevTriggered = prev_clicks && prev_clicks > 0;
            const nextTriggered = next_clicks && next_clicks > 0;
            
            if (prevTriggered && !nextTriggered) {
                currentIndex = (currentIndex - 1 + totalImages) % totalImages;
            } else if (!prevTriggered && nextTriggered) {
                currentIndex = (currentIndex + 1) % totalImages;
            }
            
            return [
                {current_index: currentIndex, image_paths: imagePaths}, 
                imagePaths[currentIndex],
                `${currentIndex + 1}/${totalImages}`
            ];
        }
        """,
        [
            Output({"type": "slideshow-data", "offer_id": MATCH}, "data"),
            Output({"type": "slideshow-img", "offer_id": MATCH}, "src"),
            Output({"type": "counter", "offer_id": MATCH}, "children"),
        ],
        [
            Input({"type": "prev-btn", "offer_id": MATCH}, "n_clicks"),
            Input({"type": "next-btn", "offer_id": MATCH}, "n_clicks"),
        ],
        [State({"type": "slideshow-data", "offer_id": MATCH}, "data")],
        prevent_initial_call=True,
    )


def create_data_table(df):
    """Create a DataTable with consistent configuration."""
    if df.empty:
        return html.Div("Нет данных")

    # Define columns
    visible = CONFIG["columns"]["visible"] + ["details"]
    numeric_cols = {
        "distance",
        "price_value_formatted",
        "cian_estimation_formatted",
        "price_difference_formatted",
        "monthly_burden_formatted",
    }
    markdown_cols = {
        "price_change_formatted",
        "address_title",
        "offer_link",
        "price_info",
        "update_title",
        "property_tags",
        "price_change",
        "walking_time",
        "price_text",
        "days_active",
        "activity_date"
    }

    columns = [
        {
            "name": CONFIG["columns"]["headers"].get(
                c, "Детали" if c == "details" else c
            ),
            "id": c,
            "type": "numeric" if c in numeric_cols else "text",
            "presentation": "markdown" if c in markdown_cols else None,
        }
        for c in visible
    ]

    # Special styling
    details_style = {"if": {"column_id": "details"}, "className": "details-column"}
    markdown_style = [
        {"if": {"column_id": col}, "textAlign": "center"} for col in markdown_cols
    ]

    # Create DataTable
    return dash_table.DataTable(
        id="apartment-table",
        columns=columns,
        data=df.to_dict("records") if not df.empty else [],
        sort_action="custom",
        sort_mode="multi",
        sort_by=[],
        hidden_columns=CONFIG["hidden_cols"] + ["offer_id"],
        style_table={
            "overflowX": "auto",
            "maxWidth": "1200px",
            "width": "100%",
            "margin": "0 auto",
        },
        style_cell=STYLE["cell"],
        style_cell_conditional=STYLE.get("cell_conditional", [])
        + [details_style]
        + markdown_style,
        style_header=STYLE["header_cell"],
        style_header_conditional=HEADER_STYLES,
        style_data=STYLE["data"],
        style_filter=STYLE["filter"],
        style_data_conditional=COLUMN_STYLES
        + [
            {
                "if": {"column_id": "details"},
                "fontWeight": "normal",
                "cursor": "pointer !important",
            }
        ],
        page_size=100,
        page_action="native",
        markdown_options={"html": True},
        cell_selectable=True,
        css=[
            {
                "selector": ".dash-cell:nth-child(n+1):nth-child(-n+15)",
                "rule": "padding: 5px !important;",
            },
            {
                "selector": "td.details-column",
                "rule": "background-color: transparent !important; text-align: center !important; padding: 3px 5px !important;",
            },
        ],
    )
