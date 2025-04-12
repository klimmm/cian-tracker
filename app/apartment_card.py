# app/apartment_card.py
from dash import html, dcc
import logging
import re
import os
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from app.components import PillFactory, ContainerFactory, StyleManager
from app.formatters import FormatUtils
from app.app_config import AppConfig
from app.utils import ErrorHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


class ImageHandler:
    """Handle apartment image processing with robust error handling."""
    
    @staticmethod
    def get_apartment_images(offer_id: str) -> List[str]:
        """Get base64 encoded images for apartment with robust path handling."""
        return ErrorHandler.try_operation(
            logger,
            "get_apartment_images",
            ImageHandler._get_images,
            offer_id,
            default_return=[]
        )
    
    @staticmethod
    def _get_images(offer_id: str) -> List[str]:
        """Internal method to get images with error handling."""
        # Use AppConfig for consistent path handling
        image_dir = AppConfig.get_images_path(str(offer_id))
        logger.info(f"Looking for images in: {image_dir}")
        
        # Check if the directory exists
        if not os.path.exists(image_dir):
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
            image_path = os.path.join(image_dir, file)
            try:
                with open(image_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
                    # Format as data URL
                    image_paths.append(f"data:image/jpeg;base64,{encoded_string}")
                    logger.info(f"Successfully encoded image: {image_path}")
            except Exception as e:
                logger.error(f"Error encoding image {image_path}: {e}")

        return image_paths
    
    @staticmethod
    def create_slideshow(offer_id: str) -> Optional[html.Div]:
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
                            style=StyleManager.merge_styles(
                                {
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
                                }
                            ),
                        ),
                        html.Button(
                            "❯",
                            id={"type": "next-btn", "offer_id": offer_id},
                            style=StyleManager.merge_styles(
                                {
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
                                }
                            ),
                        ),
                        # Image counter
                        html.Div(
                            f"1/{len(image_paths)}",
                            id={"type": "counter", "offer_id": offer_id},
                            style=StyleManager.merge_styles(
                                {
                                    "position": "absolute",
                                    "bottom": "10px",
                                    "right": "10px",
                                    "backgroundColor": "rgba(0,0,0,0.5)",
                                    "color": "white",
                                    "padding": "3px 8px",
                                    "borderRadius": "12px",
                                    "fontSize": "10px",
                                }
                            ),
                        ),
                    ],
                    style=StyleManager.merge_styles(
                        {
                            "position": "relative",
                            "display": "flex",
                            "justifyContent": "center",
                            "alignItems": "center",
                            "height": "220px",
                            "backgroundColor": "#f5f5f5",
                            "borderRadius": "4px",
                            "overflow": "hidden",
                            "marginBottom": "5px",
                        }
                    ),
                ),
                # Hidden store for current index and image paths
                dcc.Store(
                    id={"type": "slideshow-data", "offer_id": offer_id},
                    data={"current_index": 0, "image_paths": image_paths},
                ),
                # Title showing total number of photos
                html.Div(
                    f"Фотографии ({len(image_paths)})",
                    style=StyleManager.merge_styles(
                        {
                            "fontSize": "11px",
                            "fontWeight": "bold",
                            "marginBottom": "10px",
                            "color": "#4682B4",
                            "textAlign": "center",
                        }
                    ),
                ),
            ],
            style=StyleManager.merge_styles(
                {
                    "marginBottom": "15px",
                    "borderBottom": "1px solid #eee",
                    "paddingBottom": "10px",
                }
            ),
        )

        return slideshow


class ApartmentCardBuilder:
    """Builder for creating apartment detail cards with modular sections."""
    
    @staticmethod
    def create_id_header(offer_id: str) -> html.Div:
        """Create a simple header with the apartment ID."""
        return html.Div(
            f"ID: {offer_id}",
            style=StyleManager.merge_styles(
                {
                    "fontSize": "10px",
                    "color": "#666",
                    "margin": "0 auto 10px auto",
                    "textAlign": "center",
                    "padding": "5px 0",
                    "borderBottom": "1px solid #eee",
                }
            ),
        )
    
    @staticmethod
    def create_address_section(address: str, metro: Optional[str], 
                              title: Optional[str], distance: Optional[str]) -> html.Div:
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
    def create_price_section(price: Optional[str], cian_est: Optional[str], 
                           price_history: Optional[List[Dict[str, Any]]] = None) -> html.Div:
        """Create the price information section."""
        price_value = re.sub(r"[^\d]", "", price) if price else None
        cian_est_value = re.sub(r"[^\d]", "", cian_est) if cian_est else None
        
        # Process price history for tags
        price_history_tags = []
        if price_history:
            # Add a more strict uniqueness check by including all fields
            seen_entries = set()
            
            # Sort history by date
            sorted_history = sorted(price_history, key=lambda x: x.get("date_iso", ""))
            
            # Create a pill for each unique price history entry
            for entry in sorted_history:
                if "date" in entry and "price" in entry:
                    # Create a unique key for this price history entry
                    price_clean = str(entry.get('price', '')).strip()
                    date_clean = str(entry.get('date', '')).strip()
                    
                    # Create a more robust key using cleaned values
                    entry_key = f"{date_clean}:{price_clean}"
                    
                    # Only add if we haven't seen this combination before
                    if entry_key not in seen_entries:
                        seen_entries.add(entry_key)
                        price_history_tags.append(
                            PillFactory.create(
                                f"{date_clean}: {price_clean}", "#f8f8f8", "#666"
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
    def create_terms_section(terms: Optional[Dict[str, Any]]) -> Optional[html.Div]:
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
    def create_property_features_section(apartment_data: Dict[str, Any]) -> Optional[html.Div]:
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


def create_apartment_details_card(apartment_data: Dict[str, Any], 
                                 table_row_data: Optional[Dict[str, Any]] = None, 
                                 row_idx: Optional[int] = None, 
                                 total_rows: Optional[int] = None) -> html.Div:
    """Render apartment data into a compact detail card with modern layout."""
    if not apartment_data:
        return html.Div("Нет данных для этой квартиры.", style={"fontSize": "12px"})

    # Extract basic apartment info
    offer_id = apartment_data.get("offer_id", "")

    # Extract address and other info from table_row_data if available
    address, distance, metro, title, cian_est, price, description = extract_row_data(table_row_data)

    # Build the card section by section
    slideshow = ImageHandler.create_slideshow(offer_id)
    id_header = ApartmentCardBuilder.create_id_header(offer_id)
    address_section = ApartmentCardBuilder.create_address_section(address, metro, title, distance)
    price_section = ApartmentCardBuilder.create_price_section(
        price, 
        cian_est, 
        apartment_data.get("price_history", [])
    )
    terms_section = ApartmentCardBuilder.create_terms_section(apartment_data.get("terms", {}))
    property_section = ApartmentCardBuilder.create_property_features_section(apartment_data)

    # Create external link button
    external_link = html.A(
        "Открыть на Циан ↗",
        href=f"https://www.cian.ru/rent/flat/{offer_id}/",
        target="_blank",
        style=StyleManager.merge_styles(
            {
                "backgroundColor": "#4682B4",
                "color": "white",
                "border": "none",
                "borderRadius": "4px",
                "padding": "5px 10px",
                "fontSize": "12px",
                "fontWeight": "bold",
                "textDecoration": "none",
                "display": "block",
                "textAlign": "center",
                "width": "fit-content",
                "margin": "10px auto",
            }
        ),
    )

    # Assemble all sections in the correct order (filtering out None sections)
    all_sections = [
        section for section in [
            id_header,
            slideshow,
            address_section,
            price_section,
            terms_section,
            property_section,
            html.Div(description, style={"fontSize": "11px", "lineHeight": "1.3", "marginBottom": "15px"}) 
            if description else None,
            external_link
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


def extract_row_data(table_row_data: Optional[Dict[str, Any]]) -> Tuple[str, str, str, str, str, str, str]:
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