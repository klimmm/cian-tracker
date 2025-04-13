# app/apartment_card.py - Optimized
from dash import html, dcc
import logging
import re
import os
import base64
from typing import Dict, List, Any, Optional, Tuple
import requests
from app.components import PillFactory, ContainerFactory, StyleManager
from app.app_config import AppConfig
from app.utils import is_numeric, format_number

logger = logging.getLogger(__name__)


class ImageHandler:
    """Handle apartment image processing."""

    @staticmethod
    def get_apartment_images(offer_id):
        """Get images for apartment with fallback strategies."""
        try:
            # Try local first in hybrid mode
            if AppConfig.should_use_hybrid_for_images():
                local_images = ImageHandler._get_images_from_local(offer_id)
                if local_images:
                    return local_images
                return ImageHandler._get_images_from_github(offer_id)

            # Use configured source
            return (
                ImageHandler._get_images_from_github(offer_id)
                if AppConfig.is_using_github()
                else ImageHandler._get_images_from_local(offer_id)
            )
        except Exception as e:
            logger.error(f"Error getting images: {e}")
            return []

    @staticmethod
    def _get_images_from_local(offer_id):
        """Get images from local filesystem."""
        image_dir = AppConfig.get_images_path(str(offer_id))
        if not os.path.exists(image_dir):
            return []

        # Find and encode jpg files
        image_paths = []
        for file in sorted(
            f for f in os.listdir(image_dir) if f.lower().endswith(".jpg")
        ):
            try:
                with open(os.path.join(image_dir, file), "rb") as image_file:
                    encoded = base64.b64encode(image_file.read()).decode()
                    image_paths.append(f"data:image/jpeg;base64,{encoded}")
            except Exception as e:
                logger.error(f"Error encoding image: {e}")
        return image_paths

    @staticmethod
    def _get_images_from_github(offer_id):
        """Get images from GitHub repository."""
        github_base = AppConfig.DATA_SOURCE["github"]["base_url"]
        image_dir_url = f"{github_base}images/{offer_id}/"
        image_paths = []

        # Try standard image names
        for i in range(1, 11):
            try:
                image_url = f"{image_dir_url}{i}.jpg"
                response = requests.head(image_url)
                if response.status_code == 200:
                    img_response = requests.get(image_url)
                    if img_response.status_code == 200:
                        encoded = base64.b64encode(img_response.content).decode()
                        image_paths.append(f"data:image/jpeg;base64,{encoded}")
            except Exception:
                pass
        return image_paths

    @staticmethod
    def create_slideshow(offer_id):
        """Create slideshow component for images."""
        image_paths = ImageHandler.get_apartment_images(offer_id)
        if not image_paths:
            return None

        # Styles
        img_style = {
            "maxWidth": "100%",
            "maxHeight": "220px",
            "objectFit": "contain",
            "borderRadius": "4px",
        }
        nav_btn_style = {
            "position": "absolute",
            "top": "50%",
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

        # Create slideshow with navigation
        return html.Div(
            [
                # Image container with nav arrows
                html.Div(
                    [
                        html.Img(
                            id={"type": "slideshow-img", "offer_id": offer_id},
                            src=image_paths[0],
                            style=img_style,
                        ),
                        html.Button(
                            "❮",
                            id={"type": "prev-btn", "offer_id": offer_id},
                            style={**nav_btn_style, "left": "10px"},
                        ),
                        html.Button(
                            "❯",
                            id={"type": "next-btn", "offer_id": offer_id},
                            style={**nav_btn_style, "right": "10px"},
                        ),
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
                dcc.Store(
                    id={"type": "slideshow-data", "offer_id": offer_id},
                    data={"current_index": 0, "image_paths": image_paths},
                ),
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


class ApartmentCardBuilder:
    """Builder for apartment detail cards."""

    @staticmethod
    def create_card_component(component_type, data, custom_style=None):
        """Factory method for card components."""
        components = {
            "id_header": lambda: html.Div(
                f"ID: {data}",
                style={
                    "fontSize": "10px",
                    "color": "#666",
                    "margin": "0 auto 10px auto",
                    "textAlign": "center",
                    "padding": "5px 0",
                    "borderBottom": "1px solid #eee",
                },
            ),
            "address": lambda: html.Div(
                [
                    html.Div(
                        data[0],
                        style={
                            "fontSize": "13px",
                            "fontWeight": "bold",
                            "marginBottom": "2px",
                        },
                    ),
                    html.Div(
                        [
                            (
                                html.Span(
                                    data[1],
                                    style={
                                        "fontSize": "11px",
                                        "color": "#4682B4",
                                        "marginRight": "8px",
                                    },
                                )
                                if data[1]
                                else None
                            ),
                            (
                                html.Span(
                                    data[2],
                                    style={"fontSize": "11px", "marginRight": "8px"},
                                )
                                if data[2]
                                else None
                            ),
                            (
                                html.Span(
                                    data[3],
                                    style={"fontSize": "11px", "fontWeight": "bold"},
                                )
                                if data[3]
                                else None
                            ),
                        ],
                        style={"marginBottom": "5px"},
                    ),
                ]
            ),
            "external_link": lambda: html.A(
                "Открыть на Циан ↗",
                href=f"https://www.cian.ru/rent/flat/{data}/",
                target="_blank",
                style={
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
                },
            ),
            "description": lambda: (
                html.Div(
                    data,
                    style={
                        "fontSize": "11px",
                        "lineHeight": "1.3",
                        "marginBottom": "15px",
                    },
                )
                if data
                else None
            ),
        }

        if component_type not in components:
            return None

        component = components[component_type]()
        if component and custom_style:
            component.style.update(custom_style)

        return component

    @staticmethod
    def create_price_section(price, cian_est, price_history=None):
        """Create price information section."""
        price_value = re.sub(r"[^\d]", "", price) if price else None
        cian_est_value = re.sub(r"[^\d]", "", cian_est) if cian_est else None

        # Process price history
        price_history_tags = []
        if price_history:
            seen_entries = set()
            for entry in sorted(price_history, key=lambda x: x.get("date_iso", "")):
                if "date" in entry and "price" in entry:
                    entry_key = f"{entry.get('date', '').strip()}:{entry.get('price', '').strip()}"
                    if entry_key not in seen_entries:
                        seen_entries.add(entry_key)
                        price_history_tags.append(
                            PillFactory.create(
                                f"{entry.get('date', '')}: {entry.get('price', '')}",
                                "#f8f8f8",
                                "#666",
                            )
                        )

        return html.Div(
            [
                html.Div(
                    "",
                    style={
                        "fontSize": "12px",
                        "fontWeight": "bold",
                        "marginBottom": "5px",
                        "color": "#4682B4",
                    },
                ),
                html.Div(
                    [
                        html.Span(
                            price, style={"fontSize": "14px", "fontWeight": "bold"}
                        ),
                        (
                            PillFactory.create_price_comparison(
                                price_value, cian_est_value
                            )
                            if price_value and cian_est_value
                            else None
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "10px",
                        "marginBottom": "6px",
                    },
                ),
                (
                    ContainerFactory.create_flex_container(
                        price_history_tags,
                        gap="3px",
                        custom_style={"marginBottom": "10px"},
                    )
                    if price_history_tags
                    else None
                ),
            ]
        )

    @staticmethod
    def create_terms_section(terms):
        """Create rental terms section."""
        if not terms:
            return None

        term_mappings = {
            "security_deposit": "Залог",
            "commission": "Комиссия",
            "prepayment": "Предоплата",
            "utilities_payment": "ЖКХ",
        }

        terms_items = []
        for field, label in term_mappings.items():
            if terms.get(field):
                value = terms.get(field)
                if field == "security_deposit" and is_numeric(value):
                    value = format_number(value)
                terms_items.append(
                    PillFactory.create(f"{label}: {value}", "#f0f0f0", "#333")
                )

        return (
            ContainerFactory.create_flex_container(
                terms_items, gap="3px", custom_style={"marginBottom": "10px"}
            )
            if terms_items
            else None
        )

    @staticmethod
    def create_property_features_section(apartment_data):
        """Create properties and features section."""
        apt = apartment_data.get("apartment", {})
        bld = apartment_data.get("building", {})
        features = apartment_data.get("features", {})

        all_properties = []

        # Floor information
        floor = apt.get("floor", "")
        total_floors = apt.get("total_floors", "")
        if floor and total_floors:
            all_properties.append(
                PillFactory.create(
                    f"Этаж: {floor}/{total_floors}", "#f0f8ff", "#4682B4"
                )
            )
        elif floor:
            all_properties.append(
                PillFactory.create(f"Этаж: {floor}", "#f0f8ff", "#4682B4")
            )

        # Property mappings for apartment and building
        property_mapping = {
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
            "year_built": "Год",
            "building_series": "Серия",
            "building_type": "Тип дома",
            "ceiling_type": "Перекрытия",
            "parking": "Парковка",
            "elevators": "Лифты",
            "garbage_chute": "Мусоропровод",
        }

        # Process properties
        for field, label in property_mapping.items():
            value = None
            in_apt = (
                field in apt
                and apt.get(field)
                and field not in ["floor", "total_floors"]
            )
            in_bld = field in bld and bld.get(field)

            if in_apt:
                value = apt.get(field)
                bg_color, text_color = "#f0f8ff", "#4682B4"  # Apartment properties
            elif in_bld:
                value = bld.get(field)
                bg_color, text_color = "#f5f5f5", "#555555"  # Building properties

            if value:
                all_properties.append(
                    PillFactory.create(f"{label}: {value}", bg_color, text_color)
                )

        # Features as pills
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

        return (
            ContainerFactory.create_flex_container(
                all_properties, gap="3px", custom_style={"marginBottom": "10px"}
            )
            if all_properties
            else None
        )


def extract_row_data(table_row_data):
    """Extract essential data from row."""
    if not table_row_data:
        return "", "", "", "", "", "", ""

    # Extract address from address_title
    address_title = table_row_data.get("address_title", "")
    address = (
        address_title.split("<br>")[0].replace("[", "").split("](")[0]
        if "<br>" in address_title
        else ""
    )

    # Extract other fields
    title = (
        address_title.split("<br>")[1]
        if "<br>" in address_title
        else table_row_data.get("title", "")
    )

    return (
        address,
        table_row_data.get("distance", ""),
        table_row_data.get("metro_station", ""),
        title,
        table_row_data.get("cian_estimation_formatted", ""),
        table_row_data.get("price_value_formatted", ""),
        table_row_data.get("description", ""),
    )


def create_apartment_details_card(
    apartment_data, table_row_data=None, row_idx=None, total_rows=None
):
    """Render apartment data into a compact detail card."""
    if not apartment_data:
        return html.Div("Нет данных для этой квартиры.", style={"fontSize": "12px"})

    # Extract basic data
    offer_id = apartment_data.get("offer_id", "")
    address, distance, metro, title, cian_est, price, description = extract_row_data(
        table_row_data
    )

    # Build card components
    card_sections = [
        ApartmentCardBuilder.create_card_component("id_header", offer_id),
        ImageHandler.create_slideshow(offer_id),
        ApartmentCardBuilder.create_card_component(
            "address", (address, metro, title, distance)
        ),
        ApartmentCardBuilder.create_price_section(
            price, cian_est, apartment_data.get("price_history", [])
        ),
        ApartmentCardBuilder.create_terms_section(apartment_data.get("terms", {})),
        ApartmentCardBuilder.create_property_features_section(apartment_data),
        ApartmentCardBuilder.create_card_component("description", description),
        ApartmentCardBuilder.create_card_component("external_link", offer_id),
    ]

    # Create the card container (filtering out None sections)
    return ContainerFactory.create_card(
        [section for section in card_sections if section is not None],
        custom_style={
            "fontFamily": "Arial, sans-serif",
            "fontSize": "10px",
            "lineHeight": "1.2",
            "maxWidth": "500px",
        },
    )
