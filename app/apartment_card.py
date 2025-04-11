# app/apartment_card.py
from dash import html, dcc
import logging
import re
import os
import base64
from pathlib import Path
from app.components import PillFactory, ContainerFactory
from app.formatters import FormatUtils
from app.app_config import AppConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


class ImageHandler:
    """Handle apartment image processing with robust error handling."""
    
    @staticmethod
    def get_apartment_images(offer_id):
        """Get base64 encoded images for apartment with robust path handling."""
        try:
            # Use AppConfig for consistent path handling
            image_dir = AppConfig.get_images_path(str(offer_id))
            logger.info(f"Looking for images in: {image_dir}")
            
            # Check if the directory exists
            if not image_dir.exists():
                logger.warning(f"Image directory not found: {image_dir}")
                return []

            # List all jpg files in the directory
            image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(".jpg")]
            logger.info(f"Found {len(image_files)} images for offer_id {offer_id}")

            if not image_files:
                logger.warning(f"No JPG images found in directory: {image_dir}")
                return []

            # Encode each image as base64
            image_paths = []
            for file in sorted(image_files):
                image_path = image_dir / file
                try:
                    with open(image_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode()
                        # Format as data URL
                        image_paths.append(f"data:image/jpeg;base64,{encoded_string}")
                        logger.info(f"Successfully encoded image: {image_path}")
                except Exception as e:
                    logger.error(f"Error encoding image {image_path}: {e}", exc_info=True)

            return image_paths
            
        except Exception as e:
            logger.error(f"Error processing images for offer_id {offer_id}: {e}", exc_info=True)
            return []
    
    @staticmethod
    def create_slideshow(offer_id):
        """Create a slideshow component for apartment images."""
        image_paths = ImageHandler.get_apartment_images(offer_id)

        if not image_paths:
            return None

        # Create slideshow container
        slideshow = html.Div(
            [
                # Image container with navigation arrows
                html.Div(
                    [
                        # Main image
                        html.Img(
                            id={"type": "slideshow-img", "offer_id": offer_id},
                            src=image_paths[0],
                            style={
                                "maxWidth": "100%",
                                "maxHeight": "220px",
                                "objectFit": "contain",
                                "borderRadius": "4px",
                            },
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
                                "justifyContent": "center",
                            },
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
                                "justifyContent": "center",
                            },
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
                                "fontSize": "10px",
                            },
                        ),
                    ],
                    style={
                        "position": "relative",
                        "display": "flex",
                        "justifyContent": "center",
                        "alignItems": "center",
                        "height": "220px",
                        "backgroundColor": "#f5f5f5",
                        "borderRadius": "4px",
                        "overflow": "hidden",
                        "marginBottom": "5px",
                    },
                ),
                # Hidden store for current index and image paths
                dcc.Store(
                    id={"type": "slideshow-data", "offer_id": offer_id},
                    data={"current_index": 0, "image_paths": image_paths},
                ),
                # Title showing total number of photos
                html.Div(
                    f"Фотографии ({len(image_paths)})",
                    style={
                        "fontSize": "11px",
                        "fontWeight": "bold",
                        "marginBottom": "10px",
                        "color": "#4682B4",
                        "textAlign": "center",
                    },
                ),
            ],
            style={
                "marginBottom": "15px",
                "borderBottom": "1px solid #eee",
                "paddingBottom": "10px",
            },
        )

        return slideshow


class ApartmentCardBuilder:
    """Builder for creating apartment detail cards with modular sections."""
    
    @staticmethod
    def create_navigation_header(offer_id, row_idx=None, total_rows=None):
        """Create the navigation header with controls."""
        return html.Div(
            [
                # Left: Navigation buttons with counter
                html.Div(
                    [
                        html.Button(
                            "←",
                            id="prev-apartment-button",
                            disabled=row_idx == 0,
                            style={
                                "backgroundColor": "#4682B4" if row_idx > 0 else "#cccccc",
                                "color": "white",
                                "border": "none",
                                "borderRadius": "4px",
                                "padding": "3px 8px",
                                "marginRight": "8px",
                                "cursor": "pointer" if row_idx > 0 else "not-allowed",
                                "fontSize": "12px",
                                "fontWeight": "bold",
                            },
                        ),
                        html.Span(
                            f"{row_idx + 1}/{total_rows}" if row_idx is not None and total_rows else "",
                            style={"fontSize": "10px", "margin": "0 8px", "color": "#666"},
                        ),
                        html.Button(
                            "→",
                            id="next-apartment-button",
                            disabled=row_idx >= total_rows - 1 if total_rows else True,
                            style={
                                "backgroundColor": "#4682B4" if row_idx < total_rows - 1 else "#cccccc",
                                "color": "white",
                                "border": "none",
                                "borderRadius": "4px",
                                "padding": "3px 8px",
                                "cursor": "pointer" if row_idx < total_rows - 1 else "not-allowed",
                                "fontSize": "12px",
                                "fontWeight": "bold",
                            },
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "flexShrink": "0"},
                ),
                # Center: ID
                html.Div(
                    f"ID: {offer_id}",
                    style={
                        "fontSize": "10px",
                        "color": "#666",
                        "margin": "0 auto",
                        "textAlign": "center",
                    },
                ),
                # Right: External link styled like navigation buttons
                html.A(
                    "Циан ↗",
                    href=f"https://www.cian.ru/rent/flat/{offer_id}/",
                    target="_blank",
                    style={
                        "backgroundColor": "#4682B4",
                        "color": "white",
                        "border": "none",
                        "borderRadius": "4px",
                        "padding": "3px 8px",
                        "fontSize": "12px",
                        "fontWeight": "bold",
                        "textDecoration": "none",
                        "display": "inline-block",
                        "textAlign": "center",
                        "flexShrink": "0",
                    },
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "marginBottom": "10px",
                "padding": "5px 0",
                "borderBottom": "1px solid #eee",
            },
        )
    
    @staticmethod
    def create_address_section(address, metro, title, distance):
        """Create the address section with location details."""
        return html.Div(
            [
                html.Div(
                    address,
                    style={"fontSize": "13px", "fontWeight": "bold", "marginBottom": "2px"},
                ),
                html.Div(
                    [
                        html.Span(
                            metro,
                            style={"fontSize": "11px", "color": "#4682B4", "marginRight": "8px"}
                        ) if metro else None,
                        html.Span(
                            title, 
                            style={"fontSize": "11px", "marginRight": "8px"}
                        ) if title else None,
                        html.Span(
                            distance, 
                            style={"fontSize": "11px", "fontWeight": "bold"}
                        ) if distance else None,
                    ],
                    style={"marginBottom": "5px"},
                ),
            ]
        )
    
    @staticmethod
    def create_price_section(price, cian_est, price_history=None):
        """Create the price information section."""
        price_value = re.sub(r"[^\d]", "", price) if price else None
        cian_est_value = re.sub(r"[^\d]", "", cian_est) if cian_est else None
        
        # Process price history for tags
        price_history_tags = []
        if price_history:
            # Track unique date+price combinations to avoid duplicates
            seen_entries = set()
            
            # Sort history by date
            sorted_history = sorted(price_history, key=lambda x: x.get("date_iso", ""))
            
            # Create a pill for each unique price history entry
            for entry in sorted_history:
                if "date" in entry and "price" in entry:
                    # Create a unique key for this date+price combination
                    entry_key = f"{entry['date']}:{entry['price']}"
                    
                    # Only add if we haven't seen this combination before
                    if entry_key not in seen_entries:
                        seen_entries.add(entry_key)
                        price_history_tags.append(
                            PillFactory.create(
                                f"{entry['date']}: {entry['price']}", "#f8f8f8", "#666"
                            )
                        )
        
        return html.Div(
            [
                # Price header
                html.Div(
                    "",
                    style={
                        "fontSize": "12px",
                        "fontWeight": "bold",
                        "marginBottom": "5px",
                        "color": "#4682B4",
                    },
                ),
                # Current price with formatted difference vs Cian estimation
                html.Div(
                    [
                        html.Span(price, style={"fontSize": "14px", "fontWeight": "bold"}),
                        PillFactory.create_price_comparison(price_value, cian_est_value)
                        if price_value and cian_est_value else None,
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "10px",
                        "marginBottom": "6px",
                    },
                ),
                # Price history as tags
                ContainerFactory.create_flex_container(
                    price_history_tags,
                    gap="3px",
                    custom_style={"marginBottom": "10px"}
                ) if price_history_tags else None,
            ]
        )
    
    @staticmethod
    def create_terms_section(terms):
        """Create the rental terms section with formatting."""
        if not terms:
            return None
            
        terms_items = []
        
        # Create pill/tag for each term
        for field, label in {
            "security_deposit": "Залог",
            "commission": "Комиссия",
            "prepayment": "Предоплата",
            "utilities_payment": "ЖКХ",
        }.items():
            if terms.get(field):
                value = terms.get(field)
                if field == "security_deposit" and FormatUtils.is_numeric(value):
                    value = FormatUtils.format_number(value)
                
                terms_items.append(PillFactory.create(f"{label}: {value}", "#f0f0f0", "#333"))
        
        # Create terms container if we have terms
        return ContainerFactory.create_flex_container(
            terms_items,
            gap="3px",
            custom_style={"marginBottom": "10px"}
        ) if terms_items else None
    
    @staticmethod
    def create_property_features_section(apartment_data):
        """Create a combined properties and features section."""
        apt = apartment_data.get("apartment", {})
        bld = apartment_data.get("building", {})
        features = apartment_data.get("features", {})
        
        # Combine all properties
        all_properties = []
        
        # Special handling for floor and total_floors
        floor = apt.get("floor", "")
        total_floors = apt.get("total_floors", "")
        if floor and total_floors:
            all_properties.append(
                PillFactory.create(f"Этаж: {floor}/{total_floors}", "#f0f8ff", "#4682B4")
            )
        elif floor:
            all_properties.append(
                PillFactory.create(f"Этаж: {floor}", "#f0f8ff", "#4682B4")
            )
        
        # Main property mappings
        property_mapping = {
            # Apartment properties
            "layout": "Тип",
            "apartment_type": "Тип",
            "total_area": "Площадь",
            "living_area": "Жилая",
            "kitchen_area": "Кухня",
            "renovation": "Ремонт",
            "bathroom": "Санузел",
            "balcony": "Балкон",
            "ceiling_height": "Потолки",
            "view": "Вид",
            # Building properties
            "year_built": "Год",
            "building_series": "Серия",
            "building_type": "Тип дома",
            "ceiling_type": "Перекрытия",
            "parking": "Парковка",
            "elevators": "Лифты",
            "garbage_chute": "Мусоропровод",
        }
        
        # Process other apartment properties
        for field, label in property_mapping.items():
            value = None
            if field in apt and apt.get(field) and field not in ["floor", "total_floors"]:
                value = apt.get(field)
            elif field in bld and bld.get(field):
                value = bld.get(field)
            
            if value:
                # Use different colors for different property types
                bg_color = "#f0f8ff"  # Light blue for apartment properties
                text_color = "#4682B4"
                
                if field in bld:
                    bg_color = "#f5f5f5"  # Light gray for building properties
                    text_color = "#555555"
                
                all_properties.append(
                    PillFactory.create(f"{label}: {value}", bg_color, text_color)
                )
        
        # Add features as pills with their special color
        feature_mapping = {
            "has_refrigerator": "Холодильник",
            "has_dishwasher": "Посудомоечная машина",
            "has_washing_machine": "Стиральная машина",
            "has_air_conditioner": "Кондиционер",
            "has_tv": "Телевизор",
            "has_internet": "Интернет",
            "has_kitchen_furniture": "Мебель на кухне",
            "has_room_furniture": "Мебель в комнатах",
            "has_bathtub": "Ванна",
            "has_shower_cabin": "Душевая кабина",
        }
        
        for field, label in feature_mapping.items():
            if str(features.get(field)).lower() == "true":
                all_properties.append(PillFactory.create(label, "#e8f2e8", "#2e7d32"))
        
        # Create combined properties container
        return ContainerFactory.create_flex_container(
            all_properties,
            gap="3px",
            custom_style={"marginBottom": "10px"}
        ) if all_properties else None


def create_apartment_details_card(apartment_data, table_row_data=None, row_idx=None, total_rows=None):
    """Render apartment data into a compact detail card with modern layout."""
    if not apartment_data:
        return html.Div("Нет данных для этой квартиры.", style={"fontSize": "12px"})

    # Extract basic apartment info
    offer_id = apartment_data.get("offer_id", "")

    # Extract address and other info from table_row_data if available
    address, distance, metro, title, cian_est, price, description = extract_row_data(table_row_data)

    # Create navigation header
    nav_header = ApartmentCardBuilder.create_navigation_header(
        offer_id, row_idx, total_rows
    )

    # Build the card section by section
    slideshow = ImageHandler.create_slideshow(offer_id)
    address_section = ApartmentCardBuilder.create_address_section(address, metro, title, distance)
    price_section = ApartmentCardBuilder.create_price_section(
        price, 
        cian_est, 
        apartment_data.get("price_history", [])
    )
    terms_section = ApartmentCardBuilder.create_terms_section(apartment_data.get("terms", {}))
    property_section = ApartmentCardBuilder.create_property_features_section(apartment_data)

    # Assemble all sections in the correct order (filtering out None sections)
    all_sections = [
        section for section in [
            nav_header,
            slideshow,
            address_section,
            price_section,
            terms_section,
            property_section,
            html.Div(description, style={"fontSize": "11px", "lineHeight": "1.3"}) if description else None,
        ] if section is not None
    ]

    # Create the card container
    return ContainerFactory.create_card(
        all_sections,
        custom_style={
            "fontFamily": "Arial, sans-serif",
            "fontSize": "10px",
            "lineHeight": "1.2",
            "maxWidth": "500px"
        }
    )


def extract_row_data(table_row_data):
    """Extract and format address and other data from table_row_data."""
    if not table_row_data:
        return "", "", "", "", "", "", ""
        
    # Extract address from address_title
    address = (
        table_row_data.get("address_title", "")
        .split("<br>")[0]
        .replace("[", "")
        .split("](")[0]
        if "<br>" in table_row_data.get("address_title", "")
        else ""
    )
    
    # Extract other fields
    distance = table_row_data.get("distance", "")
    metro = table_row_data.get("metro_station", "")
    
    # Extract title from address_title or use title field
    title = (
        table_row_data.get("address_title", "").split("<br>")[1]
        if "<br>" in table_row_data.get("address_title", "")
        else table_row_data.get("title", "")
    )
    
    # Extract remaining fields
    cian_est = table_row_data.get("cian_estimation_formatted", "")
    price = table_row_data.get("price_value_formatted", "")
    description = table_row_data.get("description", "")
    
    return address, distance, metro, title, cian_est, price, description