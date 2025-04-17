from dash.dependencies import Input, Output, State
import logging
import pandas as pd
from app.data_filter import DataFilterSorter
from app.data_manager import DataManager, ImageLoader
from app.config import CONFIG
import dash
logger = logging.getLogger(__name__)



def register_data_callbacks(app):
    """Register data loading and processing callbacks."""
    @app.callback(
        Output("preload-status-store", "data"),
        Input("apartment-data-store", "data"),
        prevent_initial_call=False
    )
    def preload_details_in_background(main_data):
        """Start background preloading after table is rendered"""
        # First return immediately to not block rendering
        if not main_data:
            return {"status": "waiting_for_data"}
            
        # Use a separate thread to load detail files
        import threading
        
        def background_loader():
            try:
                DataManager.preload_detail_files()
            except Exception as e:
                logger.error(f"Background loading error: {e}")
                
        # Start background loading thread
        thread = threading.Thread(target=background_loader)
        thread.daemon = True  # Don't block app shutdown
        thread.start()
        
        return {"status": "loading_started"}


    
    @app.callback(
        Output("image-preload-trigger", "data"),
        # Change input to use the actual table data!
        Input("apartment-table", "data"),
        prevent_initial_call=False
    )
    def start_image_preloading(table_data):
        """Begin preloading images for apartments that are actually visible in the table."""
        if not table_data or len(table_data) == 0:
            logger.info("⚠️ IMAGE PRELOAD TRIGGER: No table data available for preloading")
            return {"status": "no_data"}
        
        # Start a background thread to preload images
        import threading
        
        def background_image_loader():
            try:
                # Extract offer_ids from the first 20 apartments ACTUALLY VISIBLE in the table
                offer_ids = [row.get("offer_id") for row in table_data[:20] 
                            if row.get("offer_id")]
                
                if offer_ids:
                    logger.info(f"🚀 IMAGE PRELOAD TRIGGER: Starting first batch of {min(5, len(offer_ids))} visible apartments: {offer_ids[:5]}")
                    # Start with the first 5 for immediate response
                    first_batch = offer_ids[:5]
                    ImageLoader.preload_images_for_apartments(first_batch, limit=5)
                    
                    # After 3 seconds, start loading more
                    import time
                    time.sleep(3)
                    
                    # Load the next batch
                    next_batch = offer_ids[5:20]
                    if next_batch:
                        logger.info(f"🚀 IMAGE PRELOAD TRIGGER: Starting second batch of {len(next_batch)} more visible apartments")
                        ImageLoader.preload_images_for_apartments(next_batch, limit=15)
            except Exception as e:
                logger.error(f"❌ IMAGE PRELOAD TRIGGER: Error in background preloader: {e}")
        
        # Start background thread
        logger.info(f"🚀 IMAGE PRELOAD TRIGGER: Initializing background preloader for {len(table_data)} table rows")
        thread = threading.Thread(target=background_image_loader)
        thread.daemon = True
        thread.start()
        
        return {"status": "preloading_started"}


    @app.callback(
        [
            Output("apartment-data-store", "data"),
            Output("last-update-time", "children"),
        ],
        [Input("dummy-load", "children")],
        prevent_initial_call=False,
    )
    def load_apartment_data(_):
        """Load and process apartment data for display."""
        try:
            # Load data from source
            df, update_time = DataManager.load_and_process_data()
            if df.empty:
                return [], "Error: No data loaded"

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

            # Convert to dictionary for storage
            df_dict = df[available_cols].to_dict("records") if not df.empty else []

            return df_dict, f"Обновлено: {update_time}"

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return [], f"Ошибка загрузки данных: {str(e)}"


def register_table_callbacks(app):
    @app.callback(
        [
            Output("apartment-table", "data"),
            Output("apartment-table", "columns"),
        ],
        [
            Input("filter-store", "data"),
            Input("apartment-data-store", "data"),
            Input("apartment-table", "sort_by")
        ]
    )
    def update_table_content(filters, data, sort_by):
        """Update table based on filters, data and sorting in a single callback."""
        import dash
        ctx = dash.callback_context
        
        if not data:
            return [], []
            
        try:
            # Convert to DataFrame for processing
            df = pd.DataFrame(data)
            
            # Log which input triggered the callback
            trigger = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
            logger.info(f"Table update triggered by: {trigger} with sort_by: {sort_by}")
            
            # Apply filtering and sorting
            df = DataFilterSorter.filter_and_sort_data(df, filters or {}, sort_by)
            
            # Define which columns to display
            visible_columns = ["update_title", "property_tags", "address_title", "price_text"]
            numeric_columns = {
                "distance",
                "price_value_formatted",
                "cian_estimation_formatted",
                "price_difference_formatted",
                "monthly_burden_formatted",
            }
            markdown_columns = {
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
                "activity_date",
            }
            
            # Build the column definitions
            columns = [
                {
                    "name": CONFIG["columns"]["headers"].get(c, c),
                    "id": c,
                    "type": "numeric" if c in numeric_columns else "text",
                    "presentation": "markdown" if c in markdown_columns else None,
                }
                for c in visible_columns
                if c in df.columns
            ]
            
            return df.to_dict("records"), columns
            
        except Exception as e:
            logger.error(f"Error updating table: {e}")
            return [], []