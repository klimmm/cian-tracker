from dash import callback_context as ctx, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from app.data_manager import DataManager, ImageLoader
from app.apartment_card import create_apartment_details_card
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# CSS class constants
PANEL_HIDDEN = "details-panel details-panel--hidden"
PANEL_VISIBLE = "details-panel details-panel--visible"
OVERLAY_HIDDEN = "details-overlay details-panel--hidden"
OVERLAY_VISIBLE = "details-overlay details-panel--visible"


def _nav_button(label, btn_id, extra_classes=""):
    return html.Button(
        label,
        id=btn_id,
        className=f"details-nav-button {extra_classes}".strip(),
        n_clicks=0,
    )


@lru_cache(maxsize=1)
def create_apartment_details_panel():
    return html.Div(
        [
            html.Div(id="details-overlay", className=OVERLAY_HIDDEN),
            html.Div(
                id="apartment-details-panel",
                className=PANEL_HIDDEN,
                children=[
                    html.Div(
                        className="details-panel-header",
                        children=[
                            _nav_button(
                                "← Пред.",
                                "prev-apartment-button",
                                "details-nav-button--prev",
                            ),
                            html.H3(
                                "Информация о квартире", className="details-panel-title"
                            ),
                            html.Div(
                                className="details-header-right",
                                children=[
                                    _nav_button(
                                        "След. →",
                                        "next-apartment-button",
                                        "details-nav-button--next",
                                    ),
                                    _nav_button(
                                        "×", "close-details-button", "details-close-x"
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        id="apartment-details-card", className="details-panel-content"
                    ),
                ],
            ),
        ],
        id="details-panel-container",
    )


def register_apartment_card_callbacks(app):
    """Register separate callbacks for toggling panel and updating details."""

    @app.callback(
        [
            Output("apartment-details-panel", "className"),
            Output("details-overlay", "className"),
        ],
        [
            Input("apartment-table", "active_cell"),
            Input("close-details-button", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def toggle_panel(active_cell, close_clicks):
        trigger = ctx.triggered_id
        if trigger == "close-details-button":
            return PANEL_HIDDEN, OVERLAY_HIDDEN
        if trigger == "apartment-table" and active_cell:
            return PANEL_VISIBLE, OVERLAY_VISIBLE
        return PANEL_HIDDEN, OVERLAY_HIDDEN

    @app.callback(
        [
            Output("apartment-details-card", "children"),
            Output("selected-apartment-store", "data"),
        ],
        [
            Input("apartment-table", "active_cell"),
            Input("prev-apartment-button", "n_clicks"),
            Input("next-apartment-button", "n_clicks"),
        ],
        [State("apartment-table", "data"), State("selected-apartment-store", "data")],
        prevent_initial_call=True,
    )
    def update_details(active_cell, prev_clicks, next_clicks, table_data, selected):
        trigger = ctx.triggered_id

        # Determine the new index
        if trigger == "apartment-table" and active_cell:
            idx = active_cell["row"]
        elif trigger in ("prev-apartment-button", "next-apartment-button"):
            if not selected or "row_idx" not in selected:
                raise PreventUpdate
            idx = selected["row_idx"]
            total = len(table_data or [])
            if trigger == "prev-apartment-button":
                idx = max(0, idx - 1)
            else:
                idx = min(total - 1, idx + 1)
            if idx == selected["row_idx"]:
                raise PreventUpdate
        else:
            raise PreventUpdate

        # Validate row index
        if not table_data or idx < 0 or idx >= len(table_data):
            card = html.Div(
                "Ошибка: индекс строки вне диапазона или нет данных.",
                className="apartment-no-data",
            )
            return card, None

        row_data = table_data[idx]
        offer_id = row_data.get("offer_id")
        if not offer_id:
            card = html.Div(
                "Ошибка: не найден ID квартиры.",
                className="apartment-no-data",
            )
            return card, None

        # Preload neighbor images on initial open
        if trigger == "apartment-table":
            neighbor_indices = list(
                range(max(0, idx - 5), min(len(table_data), idx + 6))
            )
            neighbor_indices = [i for i in neighbor_indices if i != idx]
            neighbor_ids = [
                table_data[i].get("offer_id")
                for i in neighbor_indices
                if i < len(table_data)
            ]
            neighbor_ids = [nid for nid in neighbor_ids if nid]
            if neighbor_ids:
                ImageLoader.preload_images_for_apartments(neighbor_ids)

        try:
            apartment_data = DataManager.get_apartment_details(offer_id)
            card = create_apartment_details_card(
                apartment_data, row_data, idx, len(table_data)
            )
            selected_data = {"row_idx": idx, "offer_id": offer_id}
            logger.info(f"Selected apartment idx={idx}, offer_id={offer_id}")
            return card, selected_data
        except Exception as e:
            logger.error(f"Error loading details for offer {offer_id}: {e}")
            card = html.Div(
                f"Ошибка загрузки: {e}",
                className="apartment-no-data error",
            )
            return card, None
