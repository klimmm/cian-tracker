# apartment_details_callbacks.py
import dash
from dash import html, dcc, callback_context as ctx
from dash.dependencies import Input, Output, State, MATCH, ALL
import logging
import re
import os
from apartment_card import create_apartment_details_card
from utils import load_apartment_details

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)




def register_callbacks(app):
    app.clientside_callback(
        """
        function(prev_clicks, next_clicks, slideshow_data) {
            // Ensure slideshow_data exists and has the expected structure
            if (!slideshow_data || !slideshow_data.image_paths || !slideshow_data.image_paths.length) {
                return [slideshow_data, "", ""];
            }
            
            // Get current state
            let currentIndex = slideshow_data.current_index || 0;
            const imagePaths = slideshow_data.image_paths;
            const totalImages = imagePaths.length;
            
            // Track which button increased its clicks
            // We use this approach instead of callback_context since it's more reliable
            const prevTriggered = prev_clicks && prev_clicks > 0;
            const nextTriggered = next_clicks && next_clicks > 0;
            
            // Simple logic - if both changed or neither, don't move
            // If prev changed, go back; if next changed, go forward
            if (prevTriggered && !nextTriggered) {
                // Go to previous image
                currentIndex = (currentIndex - 1 + totalImages) % totalImages;
            } else if (!prevTriggered && nextTriggered) {
                // Go to next image
                currentIndex = (currentIndex + 1) % totalImages;
            }
            
            // Update the data
            const newData = {
                current_index: currentIndex,
                image_paths: imagePaths
            };
            
            // Return updated data and new image source
            return [
                newData, 
                imagePaths[currentIndex],
                `${currentIndex + 1}/${totalImages}`
            ];
        }
        """,
        [
            Output({"type": "slideshow-data", "offer_id": MATCH}, "data"),
            Output({"type": "slideshow-img", "offer_id": MATCH}, "src"),
            Output({"type": "counter", "offer_id": MATCH}, "children")
        ],
        [
            Input({"type": "prev-btn", "offer_id": MATCH}, "n_clicks"),
            Input({"type": "next-btn", "offer_id": MATCH}, "n_clicks")
        ],
        [
            State({"type": "slideshow-data", "offer_id": MATCH}, "data")
        ],
        prevent_initial_call=True
    )
        
    @app.callback(
        [
            Output("apartment-details-panel", "style"),
            Output("apartment-details-card", "children"),
            Output("selected-apartment-store", "data"),
            Output("apartment-table", "css"),
            Output("table-container", "style")  # Added output for table visibility
        ],
        [
            Input("apartment-table", "active_cell"), 
            Input("close-details-button", "n_clicks")
        ],
        [
            State("apartment-table", "data"), 
            State("selected-apartment-store", "data")
        ],
        prevent_initial_call=True
    )
    def handle_apartment_details(active_cell, close_clicks, table_data, selected_apartment):
        # Determine which input triggered the callback
        triggered_id = ctx.triggered_id if ctx.triggered_id else None
        logger.info(f"CALLBACK TRIGGERED by {triggered_id}")
        
        # Default panel style (hidden)
        panel_style = {
            "opacity": "0",
            "visibility": "hidden",
            "pointer-events": "none",
            "display": "block",  # Always set display:block and control visibility with CSS properties
            "position": "fixed",  # Fixed position instead of absolute
            "top": "50%",
            "left": "50%",
            "transform": "translate(-50%, -50%)",  # Center in viewport
            "width": "90%",  # Take 90% of viewport width
            "maxWidth": "500px",  # Limit to 500px
            "maxHeight": "100%",  # Use 90% of viewport height
            "zIndex": "1000",
            "backgroundColor": "#fff",
            "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.2)",
            "borderRadius": "8px",
            "padding": "15px",
            "overflow": "auto",
            "transformOrigin": "center",  # Add animation origin
            "willChange": "opacity, visibility",  # Performance optimization
        }
        details_content = []
        result_data = None
        
        # Default CSS with no row highlighting and proper cursor for details cells
        css_rules = [
            {"selector": ".highlighted-row td", 
             "rule": "background-color: #e6f3ff !important; border-bottom: 2px solid #4682B4 !important;"},
            {"selector": "td.details-column .dash-cell-value", 
             "rule": "cursor: pointer !important;"}
        ]
        
        # Default table container style (visible)
        table_container_style = {"position": "relative", "display": "block"}
        
        # ===== CASE 1: Close button was clicked =====
        if triggered_id == "close-details-button" and close_clicks:
            logger.info(f"CLOSING PANEL: close button clicked")
            # Clear the selected_apartment to allow clicking the same row again
            # Make table visible when panel is closed
            return panel_style, details_content, None, css_rules, table_container_style
            
        # ===== CASE 2: Table cell was clicked =====
        elif triggered_id == "apartment-table" and active_cell:
            column_id = active_cell.get("column_id")
            logger.info(f"Table cell clicked: column={column_id}, row={active_cell.get('row')}")
            
            # Only process clicks on the "details" column
            if column_id != "details":
                logger.info(f"Ignoring click on non-details column")
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            # Get the clicked row data
            row_idx = active_cell["row"]
            row_data = table_data[row_idx]
            offer_id = row_data.get("offer_id")
            logger.info(f"Details requested for offer_id: {offer_id}")
            
            # Load apartment details and create the card
            logger.info(f"Loading apartment details for offer_id: {offer_id}")
            from utils import load_apartment_details
            try:
                apartment_data = load_apartment_details(offer_id)
                logger.info(f"Successfully loaded data for offer_id: {offer_id}")
                
                # Pass row_idx and total_rows to the card creation function
                details_content = create_apartment_details_card(
                    apartment_data, 
                    row_data,
                    row_idx=row_idx,
                    total_rows=len(table_data)
                )
                
                # Store row_idx and total_rows in the result data
                result_data = {
                    "apartment_data": apartment_data,
                    "row_data": row_data,
                    "row_idx": row_idx,
                    "total_rows": len(table_data),
                    "offer_id": offer_id
                }
                
            except Exception as e:
                logger.error(f"Error loading apartment details: {str(e)}")
                details_content = html.Div(f"Error loading details: {str(e)}", style={"color": "red"})
                result_data = {"offer_id": offer_id, "error": str(e)}
            
            # Show panel with improved style
            panel_style = {
                "opacity": "1",
                "visibility": "visible",
                "pointer-events": "auto",
                "display": "block",
                "position": "fixed",  # Fixed position for better centering
                "top": "50%",
                "left": "50%",
                "transform": "translate(-50%, -50%)",  # Center in viewport
                "width": "90%",  # Take 90% of viewport width
                "maxWidth": "500px",  # Limit to 500px
                "maxHeight": "100%",  # Use 90% of viewport height
                "zIndex": "1000",
                "backgroundColor": "#fff",
                "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.2)",
                "borderRadius": "8px",
                "padding": "15px",
                "overflow": "auto",
                "transformOrigin": "center",
                "willChange": "opacity, visibility",
                "animation": "fadeIn 0.3s ease-in-out"  # Add animation
            }
            
            # Add CSS rule for highlighting the selected row
            css_rules.append({
                "selector": f'tr[data-dash-row-id="{row_idx}"]', 
                "rule": "background-color: #e6f3ff !important; border-bottom: 2px solid #4682B4 !important;"
            })
            
            # Hide table when details panel is visible
            table_container_style = {"position": "relative", "display": "none"}
            
            logger.info(f"RETURNING: panel=visible, content=card, data=result, highlighting row {row_idx}, table hidden")
            return panel_style, details_content, result_data, css_rules, table_container_style
        
        # Default case (should not normally happen)
        logger.warning(f"DEFAULT CASE REACHED - This should not normally happen")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update



    @app.callback(
        [
            Output("apartment-details-card", "children", allow_duplicate=True),
            Output("selected-apartment-store", "data", allow_duplicate=True)
        ],
        [
            Input("prev-apartment-button", "n_clicks"),
            Input("next-apartment-button", "n_clicks")
        ],
        [
            State("selected-apartment-store", "data"),
            State("apartment-table", "data")
        ],
        prevent_initial_call=True
    )
    def navigate_apartments(prev_clicks, next_clicks, selected_data, table_data):
        # Determine which button was clicked
        triggered_id = ctx.triggered_id
        
        # Get current apartment index
        if not selected_data or "row_idx" not in selected_data:
            return dash.no_update, dash.no_update
            
        current_idx = selected_data["row_idx"]
        total_rows = len(table_data)
        
        # Calculate new index based on which button was clicked
        new_idx = current_idx
        if triggered_id == "prev-apartment-button" and current_idx > 0:
            new_idx = current_idx - 1
        elif triggered_id == "next-apartment-button" and current_idx < total_rows - 1:
            new_idx = current_idx + 1
        
        # Don't update if index didn't change
        if new_idx == current_idx:
            return dash.no_update, dash.no_update
        
        # Get the data for the new apartment
        new_row_data = table_data[new_idx]
        offer_id = new_row_data.get("offer_id")
        
        try:
            # Load new apartment details
            apartment_data = load_apartment_details(offer_id)
            
            # Create new card content
            details_content = create_apartment_details_card(
                apartment_data, 
                new_row_data,
                row_idx=new_idx,
                total_rows=total_rows
            )
            
            # Update selected apartment data
            new_selected_data = {
                "apartment_data": apartment_data,
                "row_idx": new_idx,
                "total_rows": total_rows
            }
            
            return details_content, new_selected_data
            
        except Exception as e:
            logger.error(f"Error loadi'ng apartment details: {str(e)}")
            error_content = html.Div(f"Error loading details: {str(e)}", style={"color": "red"})
            return error_content, selected_data


    '''app.clientside_callback(
        """
        function(n_clicks, url) {
            if (n_clicks) {
                window.open(url, '_blank');
            }
            return '';
        }
        """,
        Output("cian-link-button", "children"),
        Input("cian-link-button", "n_clicks"),
        State("cian-link-button", "data-url")
    )'''