
from dash import callback_context as ctx
from dash.dependencies import Input, Output, State, MATCH
import dash
from app.data_manager import load_apartment_details
from app.apartment_card import create_apartment_details_card
from dash import html


def register_apartment_card_callbacks(app):
    """Register callbacks for apartment details panel."""

    @app.callback(
        [
            Output("apartment-details-panel", "className"),
            Output("apartment-details-card", "children"),
            Output("selected-apartment-store", "data"),
            Output("details-overlay", "className"),
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
            State("apartment-details-panel", "className"),
            State("details-overlay", "className"),
        ],
    )
    def handle_apartment_panel(
        active_cell,
        prev_clicks,
        next_clicks,
        close_clicks,
        table_data,
        selected_data,
        current_class,
        overlay_class,
    ):
        """Handle apartment details panel interactions."""
        # Setup panel classes
        hidden_panel_class = "details-panel details-panel--hidden"
        visible_panel_class = "details-panel details-panel--visible"
        hidden_overlay_class = "details-overlay details-panel--hidden"
        visible_overlay_class = "details-overlay details-panel--visible"

        # Get the triggered component
        ctx_triggered = ctx.triggered if ctx.triggered else []
        trigger_id = (
            ctx_triggered[0]["prop_id"].split(".")[0] if ctx_triggered else None
        )

        # For initial load, ensure the panel is hidden
        if not ctx_triggered or trigger_id is None:
            return hidden_panel_class, [], None, hidden_overlay_class

        # Handle close action
        if trigger_id == "close-details-button" and close_clicks and close_clicks > 0:
            return hidden_panel_class, dash.no_update, None, hidden_overlay_class

        # Handle table cell click
        if trigger_id == "apartment-table" and active_cell:
            # Only accept clicks on the details column
            if active_cell.get("column_id") != "details":
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update

            row_idx = active_cell["row"]
            if not table_data or row_idx >= len(table_data):
                logger.error(
                    f"Row index {row_idx} out of bounds for table data length {len(table_data) if table_data else 0}"
                )
                return (
                    visible_panel_class,
                    html.Div(
                        "Ошибка: индекс строки вне диапазона или нет данных.",
                        className="apartment-no-data",
                    ),
                    None,
                    visible_overlay_class,
                )

            row_data = table_data[row_idx]
            offer_id = row_data.get("offer_id")
            if not offer_id:
                logger.error(f"No offer_id found in row data")
                return (
                    visible_panel_class,
                    html.Div(
                        "Ошибка: не найден ID квартиры.", className="apartment-no-data"
                    ),
                    None,
                    visible_overlay_class,
                )

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

                logger.info(f"Loaded details for offer_id {offer_id}, showing panel")
                return (
                    visible_panel_class,
                    details_card,
                    selected,
                    visible_overlay_class,
                )
            except Exception as e:
                logger.error(f"Error loading details: {e}")
                return (
                    visible_panel_class,
                    html.Div(
                        f"Ошибка загрузки: {e}", className="apartment-no-data error"
                    ),
                    None,
                    visible_overlay_class,
                )

        # Handle navigation
        if (
            trigger_id in ["prev-apartment-button", "next-apartment-button"]
            and selected_data
            and table_data
        ):
            current_idx = selected_data["row_idx"]
            table_data = selected_data.get("table_data", table_data)
            total_rows = len(table_data)

            # Calculate new index
            new_idx = current_idx
            if trigger_id == "prev-apartment-button" and current_idx > 0:
                new_idx -= 1
            elif trigger_id == "next-apartment-button" and current_idx < total_rows - 1:
                new_idx += 1

            if new_idx == current_idx:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update

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

                return dash.no_update, details_card, selected, dash.no_update
            except Exception as e:
                logger.error(f"Error loading details: {e}")
                return (
                    dash.no_update,
                    html.Div(
                        f"Ошибка загрузки: {e}", className="apartment-no-data error"
                    ),
                    selected_data,
                    dash.no_update,
                )

        # For any other case, don't update
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    app.clientside_callback(
        """
        function(prev_clicks, next_clicks, slideshow_data) {
            // Make sure data exists
            if (!slideshow_data || !slideshow_data.image_paths || slideshow_data.image_paths.length === 0) {
                return [slideshow_data, "", ""];
            }
            
            // Get current state
            let currentIndex = slideshow_data.current_index || 0;
            const imagePaths = slideshow_data.image_paths;
            const totalImages = imagePaths.length;
            
            // Get offer ID for tracking
            const ctx = dash_clientside.callback_context;
            const triggerId = ctx.triggered[0].prop_id;
            const matches = triggerId.match(/{[^}]*"offer_id"[^}]*:([^}]*)}/);
            const offerId = matches ? matches[1].trim() : 'unknown';
            
            // Create button click trackers specific to this slideshow
            const stateKey = `slideshow_${offerId}`;
            if (typeof window[stateKey] === 'undefined') {
                window[stateKey] = {
                    prevClicks: prev_clicks || 0,
                    nextClicks: next_clicks || 0
                };
            }
            
            // Determine which button was clicked by comparing with stored values
            if (prev_clicks > window[stateKey].prevClicks) {
                // Move to previous image with wrap-around
                currentIndex = (currentIndex - 1 + totalImages) % totalImages;
                window[stateKey].prevClicks = prev_clicks;
            } 
            else if (next_clicks > window[stateKey].nextClicks) {
                // Move to next image with wrap-around
                currentIndex = (currentIndex + 1) % totalImages;
                window[stateKey].nextClicks = next_clicks;
            }
            
            // Return updated values
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
