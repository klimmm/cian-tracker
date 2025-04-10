# apartment_details_callbacks.py
import dash
from dash import html, dcc, callback_context as ctx
from dash.dependencies import Input, Output, State, MATCH, ALL
import logging
import re
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Helper functions for number formatting
def is_numeric(value):
    """Check if a value can be converted to a number"""
    if value is None:
        return False
    try:
        float(str(value).replace(' ', '').replace('₽', ''))
        return True
    except (ValueError, TypeError):
        return False
        
def format_number(value):
    """Format numbers with thousand separators and currency symbol"""
    if not is_numeric(value):
        return value
        
    # Remove non-numeric characters
    clean_value = re.sub(r'[^\d.]', '', str(value))
    try:
        num = int(float(clean_value))
        # Format with thousand separators
        formatted = '{:,}'.format(num).replace(',', ' ')
        return f"{formatted} ₽"
    except (ValueError, TypeError):
        return value

import base64
import os
import logging

def get_apartment_images(offer_id):
    """Get base64 encoded images for apartment with robust path handling"""
    logger = logging.getLogger(__name__)
    
    # Get the absolute path to the images directory relative to the current file
    # This ensures correct path resolution regardless of where the script is launched from
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    base_image_dir = os.path.join(current_file_dir, "images")
    image_dir = os.path.join(base_image_dir, str(offer_id))
    
    logger.info(f"Looking for images in: {image_dir}")
    
    # Check if the directory exists
    if not os.path.exists(image_dir):
        logger.warning(f"Image directory not found: {image_dir}")
        # Try an alternative path (relative to current working directory)
        alt_image_dir = os.path.join("images", str(offer_id))
        logger.info(f"Trying alternative path: {os.path.abspath(alt_image_dir)}")
        
        if os.path.exists(alt_image_dir):
            image_dir = alt_image_dir
            logger.info(f"Using alternative image path: {os.path.abspath(image_dir)}")
        else:
            logger.warning(f"Alternative image directory not found: {os.path.abspath(alt_image_dir)}")
            return []
    
    try:
        # List all jpg files in the directory
        image_files = [f for f in os.listdir(image_dir) if f.lower().endswith('.jpg')]
        logger.info(f"Found {len(image_files)} images for offer_id {offer_id}")
        
        if not image_files:
            logger.warning(f"No JPG images found in directory: {image_dir}")
            return []
        
        # Create list to store encoded images
        encoded_images = []
        
        # Encode each image as base64
        for file in sorted(image_files):
            image_path = os.path.join(image_dir, file)
            try:
                logger.info(f"Reading image file: {image_path}")
                with open(image_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
                    # Format as data URL
                    encoded_images.append(f"data:image/jpeg;base64,{encoded_string}")
                    logger.info(f"Successfully encoded image: {image_path}")
            except Exception as e:
                logger.error(f"Error encoding image {image_path}: {e}", exc_info=True)
        
        return encoded_images
    except Exception as e:
        logger.error(f"Error processing images for offer_id {offer_id}: {e}", exc_info=True)
        return []

def create_slideshow(offer_id):
    """Create a slideshow component for apartment images with fallback"""
    image_paths = get_apartment_images(offer_id)
    
    if not image_paths:
        # Create a fallback with a placeholder image
        return html.Div([
            # Placeholder image container
            html.Div([
                html.Div([
                    html.I(className="fas fa-image", style={
                        "fontSize": "48px",
                        "color": "#ccc",
                    }),
                    html.Div("Изображения недоступны", style={
                        "fontSize": "12px",
                        "color": "#888",
                        "marginTop": "10px"
                    })
                ], style={
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "height": "150px",
                    "backgroundColor": "#f5f5f5",
                    "borderRadius": "4px",
                })
            ], style={
                "position": "relative",
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
                "height": "150px",
                "backgroundColor": "#f5f5f5",
                "borderRadius": "4px",
                "marginBottom": "10px"
            }),
            
            # Title showing no photos available
            html.Div(
                "Фотографии недоступны", 
                style={
                    "fontSize": "11px", 
                    "fontWeight": "bold", 
                    "marginBottom": "10px",
                    "color": "#4682B4",
                    "textAlign": "center"
                }
            )
        ], style={
            "marginBottom": "15px",
            "borderBottom": "1px solid #eee",
            "paddingBottom": "10px"
        })
    
    # Rest of the function remains the same...
    slideshow_id = f"slideshow-{offer_id}"
    image_id = f"slideshow-img-{offer_id}"
    counter_id = f"counter-{offer_id}"
    
    # Create slideshow container
    slideshow = html.Div([
        # Image container with navigation arrows
        html.Div([
            # Main image
            html.Img(
                id={"type": "slideshow-img", "offer_id": offer_id},
                src=image_paths[0],
                style={
                    "maxWidth": "100%", 
                    "maxHeight": "220px", 
                    "objectFit": "contain",
                    "borderRadius": "4px"
                }
            ),
            
            # Left/right arrows
            html.Button(
                "❮", 
                id={"type": "prev-btn", "offer_id": offer_id},
                style={
                    "position": "absolute",
                    "top": "50%",
                    "left": "10px",
                    "transform": "translateY(-50%)",
                    "backgroundColor": "rgba(0,0,0,0.3)",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "50%",
                    "width": "30px",
                    "height": "30px",
                    "fontSize": "16px",
                    "cursor": "pointer",
                    "zIndex": "2",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center"
                }
            ),
            html.Button(
                "❯", 
                id={"type": "next-btn", "offer_id": offer_id},
                style={
                    "position": "absolute",
                    "top": "50%",
                    "right": "10px",
                    "transform": "translateY(-50%)",
                    "backgroundColor": "rgba(0,0,0,0.3)",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "50%",
                    "width": "30px",
                    "height": "30px",
                    "fontSize": "16px",
                    "cursor": "pointer",
                    "zIndex": "2",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center"
                }
            ),
            
            # Image counter
            html.Div(
                f"1/{len(image_paths)}", 
                id={"type": "counter", "offer_id": offer_id},
                style={
                    "position": "absolute",
                    "bottom": "10px",
                    "right": "10px",
                    "backgroundColor": "rgba(0,0,0,0.5)",
                    "color": "white",
                    "padding": "3px 8px",
                    "borderRadius": "12px",
                    "fontSize": "10px"
                }
            )
        ], style={
            "position": "relative",
            "display": "flex",
            "justifyContent": "center",
            "alignItems": "center",
            "height": "220px",
            "backgroundColor": "#f5f5f5",
            "borderRadius": "4px",
            "overflow": "hidden",
            "marginBottom": "5px"
        }),
        
        # Hidden store for current index and image paths
        dcc.Store(id={"type": "slideshow-data", "offer_id": offer_id}, data={
            "current_index": 0,
            "image_paths": image_paths
        }),
        
        # Title showing total number of photos
        html.Div(
            f"Фотографии ({len(image_paths)})", 
            style={
                "fontSize": "11px", 
                "fontWeight": "bold", 
                "marginBottom": "10px",
                "color": "#4682B4",
                "textAlign": "center"
            }
        )
    ], style={
        "marginBottom": "15px",
        "borderBottom": "1px solid #eee",
        "paddingBottom": "10px"
    })
    
    return slideshow
# Improved implementation for apartment_details_callbacks.py

def create_apartment_details_card(apartment_data, table_row_data=None):
    """Render all scraped apartment data into a compact detail card with header info."""
    if not apartment_data:
        return html.Div("Нет данных для этой квартиры.", style={"fontSize": "12px"})
    
    # Extract basic apartment info
    offer_id = apartment_data.get("offer_id", "")
    
    # Extract address and other info from table_row_data if available
    address = ""
    metro = ""
    title = ""
    cian_est = ""
    price = ""
    
    if table_row_data:
        address = table_row_data.get("address_title", "").split("<br>")[0].replace("[", "").split("](")[0] if "<br>" in table_row_data.get("address_title", "") else ""
        metro = table_row_data.get("metro_station", "")
        title = table_row_data.get("address_title", "").split("<br>")[1] if "<br>" in table_row_data.get("address_title", "") else table_row_data.get("title", "")
        cian_est = table_row_data.get("cian_estimation_formatted", "")
        price = table_row_data.get("price_value_formatted", "")
    
    # Process rental terms
    terms = apartment_data.get("terms", {})
    
    # Define mapping for terms display with proper formatting
    terms_mapping = {
        "utilities_payment": ("ЖКХ", lambda x: x),
        "security_deposit": ("Залог", lambda x: format_number(x) if is_numeric(x) else x),
        "commission": ("Комиссия", lambda x: x),
        "prepayment": ("Предоплата", lambda x: x),
        "rental_period": ("Срок аренды", lambda x: x),
        "living_conditions": ("Условия проживания", lambda x: x),
        "negotiable": ("Торг", lambda x: x)
    }
    
    # We'll build the terms directly in the layout later, not as a separate list
    
    # Create two-column header layout
    header = html.Div([
        # Top row with ID and Cian link - with justified alignment
        html.Div([
            html.Div(f"ID: {offer_id}", style={
                "fontSize": "10px", 
                "color": "#666",
                "display": "inline-block",
                "float": "left"
            }),
            html.A(
                "Открыть на Циан ↗", 
                href=f"https://www.cian.ru/rent/flat/{offer_id}/",
                target="_blank",
                style={
                    "fontSize": "10px", 
                    "color": "#4682B4", 
                    "textDecoration": "none",
                    "display": "inline-block",
                    "float": "right"
                }
            ),
            html.Div(style={"clear": "both"})
        ], style={"marginBottom": "6px", "width": "100%"}),
        
        # Two-column main header content
        html.Div([
            # Left column: Address, metro, title
            html.Div([
                html.Div(address, style={
                    "fontSize": "13px", 
                    "fontWeight": "bold", 
                    "marginBottom": "2px"
                }),
                html.Div(metro, style={
                    "fontSize": "11px", 
                    "color": "#4682B4", 
                    "marginBottom": "2px"
                }),
                html.Div(title, style={
                    "fontSize": "11px"
                }),
            ], style={"width": "60%", "display": "inline-block", "verticalAlign": "top"}),
            
            # Right column: Price, Cian estimation
            html.Div([
                html.Div([
                    html.Span("Цена: ", style={"fontWeight": "bold"}),
                    html.Span(price)
                ], style={
                    "fontSize": "11px", 
                    "marginBottom": "2px"
                }),
                html.Div([
                    html.Span("Оценка Циан: ", style={"fontWeight": "bold"}),
                    html.Span(cian_est)
                ], style={
                    "fontSize": "11px", 
                    "color": "#4682B4"
                })
            ], style={"width": "40%", "display": "inline-block", "verticalAlign": "top", "textAlign": "right"})
        ]),
        
        # Rental Terms section - grid layout for efficiency
        html.Div([
            html.Div("Условия:", style={
                "fontSize": "11px", 
                "fontWeight": "bold", 
                "color": "#4682B4",
                "marginBottom": "4px",
                "display": "block"
            }),
            # Create a grid layout for terms
            html.Div([
                # Replace terms_section with a custom grid layout
                html.Div([
                    html.Div([
                        html.Span(f"{label}: ", style={"fontWeight": "bold", "fontSize": "10px"}),
                        html.Span(formatter(terms.get(field)), style={"fontSize": "10px"})
                    ], style={
                        "display": "inline-block", 
                        "width": "48%", 
                        "marginRight": "2%",
                        "marginBottom": "3px",
                        "verticalAlign": "top"
                    })
                    for field, (label, formatter) in terms_mapping.items() if terms.get(field)
                ], style={"width": "100%"})
            ])
        ], style={
            "marginTop": "8px",
            "padding": "6px 8px",
            "backgroundColor": "#f7f9fc",
            "borderRadius": "4px"
        })
    ], style={
        "borderBottom": "1px solid #eee",
        "paddingBottom": "6px",
        "marginBottom": "6px"
    })

    def format_section(title, items, is_html_items=False):
        if not items:
            return None
            
        # Handle HTML items differently than string items
        content = items if is_html_items else html.Div(", ".join(items), style={"fontSize": "10px"})
            
        return html.Div([
            html.Div(title, style={"fontWeight": "bold", "fontSize": "11px", "color": "#4682B4", "marginBottom": "2px"}),
            content
        ], style={"marginBottom": "6px"})

    # === 1. Apartment info ===
    apartment_items = []
    apt = apartment_data.get("apartment", {})
    for field, label in {
        "apartment_type": "Тип жилья",
        "layout": "Планировка",
        "total_area": "Общая площадь",
        "living_area": "Жилая площадь",
        "kitchen_area": "Площадь кухни",
        "ceiling_height": "Высота потолков",
        "bathroom": "Санузел",
        "balcony": "Балкон/лоджия",
        "sleeping_places": "Спальных мест",
        "renovation": "Ремонт",
        "view": "Вид из окон"
    }.items():
        if apt.get(field):
            apartment_items.append(f"{label}: {apt[field]}")

    # === 2. Building info ===
    building_items = []
    bld = apartment_data.get("building", {})
    for field, label in {
        "year_built": "Год постройки",
        "building_series": "Серия",
        "garbage_chute": "Мусоропровод",
        "elevators": "Лифты",
        "building_type": "Тип дома",
        "ceiling_type": "Перекрытия",
        "parking": "Парковка",
        "entrances": "Подъезды",
        "heating": "Отопление",
        "emergency": "Аварийность",
        "gas_supply": "Газоснабжение"
    }.items():
        if bld.get(field):
            building_items.append(f"{label}: {bld[field]}")

    # === 3. Features ===
    features_items = []
    features = apartment_data.get("features", {})
    for field, label in {
        "has_refrigerator": "Холодильник",
        "has_dishwasher": "Посудомоечная машина",
        "has_washing_machine": "Стиральная машина",
        "has_air_conditioner": "Кондиционер",
        "has_tv": "Телевизор",
        "has_internet": "Интернет",
        "has_kitchen_furniture": "Мебель на кухне",
        "has_room_furniture": "Мебель в комнатах",
        "has_bathtub": "Ванна",
        "has_shower_cabin": "Душевая кабина"
    }.items():
        if str(features.get(field)).lower() == "true":
            features_items.append(label)

    # === 4. Price history with deduplication of same date/price entries ===
    price_items = []
    price_html_items = None
    
    if "price_history" in apartment_data and apartment_data["price_history"]:
        try:
            # Sort by date_iso in descending order (newest first)
            sorted_history = sorted(
                apartment_data["price_history"],
                key=lambda x: x.get("date_iso", ""),
                reverse=True
            )
            
            # Convert price_clean to numeric values and filter out invalid entries
            valid_entries = []
            for entry in sorted_history:
                try:
                    if "price_clean" in entry and entry["price_clean"]:
                        price_value = float(entry["price_clean"])
                        valid_entries.append({
                            "date": entry.get("date", ""),
                            "date_iso": entry.get("date_iso", ""),
                            "price": entry.get("price", ""),
                            "price_value": price_value
                        })
                except (ValueError, TypeError):
                    continue
            
            # Calculate price changes by comparing adjacent entries
            processed_entries = []
            seen_date_prices = set()  # To track unique date+price combinations
            
            for i, entry in enumerate(valid_entries):
                date = entry['date']
                price = entry['price']
                price_value = entry['price_value']
                
                # Create a unique key for this date+price combination
                key = f"{date}|{price_value}"
                
                # Skip if we've already seen this exact date and price
                if key in seen_date_prices:
                    continue
                    
                seen_date_prices.add(key)
                
                # Start with the basic display info
                display_entry = {
                    "date": date,
                    "price": price,
                    "has_change": False,
                    "change_text": "",
                    "price_value": price_value
                }
                
                # If not the last entry, calculate change from next (older) price
                if i < len(valid_entries) - 1:
                    current_price = price_value
                    previous_price = valid_entries[i+1]['price_value']
                    
                    if current_price != previous_price:
                        change_value = current_price - previous_price
                        change_abs = abs(change_value)
                        
                        # Format the change amount
                        if change_abs >= 1000:
                            change_formatted = f"{int(change_abs//1000)} 000 ₽"
                        else:
                            change_formatted = f"{int(change_abs)} ₽"
                        
                        # Add direction indicator based on actual calculation
                        if change_value > 0:
                            display_entry["change_text"] = f"↑ {change_formatted}"
                        else:
                            display_entry["change_text"] = f"↓ {change_formatted}"
                            
                        display_entry["has_change"] = True
                
                processed_entries.append(display_entry)
                
            # Format items for display
            for entry in processed_entries:
                line = f"{entry['date']}: {entry['price']}"
                
                if entry["has_change"]:
                    line += f" {entry['change_text']}"
                
                price_items.append(line)
            
            # Take only top 3 entries
            price_items = price_items[:3]
                
            # Create HTML formatted version with separators
            if price_items:
                price_html_items = html.Div([
                    html.Div(
                        item, 
                        style={
                            "fontSize": "10px",
                            "marginBottom": "2px",
                            "paddingBottom": "2px",
                            "borderBottom": "1px dotted #eee" if i < len(price_items)-1 else "none"
                        }
                    ) for i, item in enumerate(price_items)
                ])
                
        except Exception as e:
            print(f"Error processing price history: {e}")
            price_items = ["Ошибка обработки истории цен"]

    # === 5. Stats (optional) ===
    stats_items = []
    stats = apartment_data.get("stats", {})
    for field, label in {
        "creation_date": "Создано",
        "total_views": "Просмотров",
        "recent_views": "Недавних",
        "unique_views": "Уникальных"
    }.items():
        if stats.get(field):
            stats_items.append(f"{label}: {stats[field]}")

    # Create image slideshow
    slideshow = create_slideshow(offer_id)

    # Create two-column layout for info sections
    # First column: Apartment info and Building info
    # Second column: Features and Stats
    
    # Price history section
    price_history_section = format_section("История цен", price_html_items, is_html_items=True) if price_html_items else format_section("История цен", price_items)
    
    # Two-column layout for information sections
    info_sections = html.Div([
        # Left column
        html.Div([
            format_section("Основное", apartment_items),
            format_section("Дом", building_items),
        ], style={"width": "60%", "display": "inline-block", "verticalAlign": "top", "paddingRight": "8px"}),
        
        # Right column
        html.Div([
            format_section("Оснащение", features_items),
            format_section("Статистика", stats_items),
        ], style={"width": "40%", "display": "inline-block", "verticalAlign": "top"})
    ])
    
    # Main sections in compact layout
    main_sections = [
        header,
        slideshow,
        price_history_section,
        info_sections
    ]
    
    # Filter out None sections
    main_sections = [section for section in main_sections if section is not None]
    
    return html.Div(main_sections, style={
        "padding": "12px",
        "backgroundColor": "#fff",
        "fontFamily": "Arial, sans-serif",
        "fontSize": "10px",
        "borderRadius": "6px",
        "boxShadow": "0 2px 8px rgba(0, 0, 0, 0.1)",
        "width": "100%",
        "maxWidth": "500px",
        "margin": "0 auto",
        "lineHeight": "1.3"  # Slightly increase line height for better readability
    })
# Register callbacks with the app - this will be called from cian_dashboard.py
def register_callbacks(app):
    @app.callback(
        [
            Output("apartment-details-panel", "style"),
            Output("apartment-details-card", "children"),
            Output("selected-apartment-store", "data"),
            Output("apartment-table", "css")
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
            "maxHeight": "90vh",  # Use 90% of viewport height
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
        
        # ===== CASE 1: Close button was clicked =====
        if triggered_id == "close-details-button" and close_clicks:
            logger.info(f"CLOSING PANEL: close button clicked")
            # Clear the selected_apartment to allow clicking the same row again
            return panel_style, details_content, None, css_rules
            
        # ===== CASE 2: Table cell was clicked =====
        elif triggered_id == "apartment-table" and active_cell:
            column_id = active_cell.get("column_id")
            logger.info(f"Table cell clicked: column={column_id}, row={active_cell.get('row')}")
            
            # Only process clicks on the "details" column
            if column_id != "details":
                logger.info(f"Ignoring click on non-details column")
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
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
                # Pass table_row_data to the card creation function
                details_content = create_apartment_details_card(apartment_data, row_data)
                result_data = apartment_data
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
                "maxHeight": "90vh",  # Use 90% of viewport height
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
            
            logger.info(f"RETURNING: panel=visible, content=card, data=result, highlighting row {row_idx}")
            return panel_style, details_content, result_data, css_rules
        
        # Default case (should not normally happen)
        logger.warning(f"DEFAULT CASE REACHED - This should not normally happen")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    @app.callback(
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
    def navigate_slideshow(prev_clicks, next_clicks, slideshow_data):
        # Determine which button was clicked
        triggered_id = ctx.triggered_id
        
        # Get current state
        current_index = slideshow_data["current_index"]
        image_paths = slideshow_data["image_paths"]
        total_images = len(image_paths)
        
        # Update index based on which button was clicked
        if triggered_id and triggered_id["type"] == "prev-btn":
            # Go to previous image
            current_index = (current_index - 1) % total_images
        else:
            # Go to next image
            current_index = (current_index + 1) % total_images
        
        # Update the data
        slideshow_data["current_index"] = current_index
        
        # Return updated data and new image source
        return (
            slideshow_data, 
            image_paths[current_index],
            f"{current_index + 1}/{total_images}"
        )