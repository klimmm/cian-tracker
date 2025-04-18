# Updated imports for apartment.py
from dash import html
import logging
import re
from app.pill_factory import PillFactory
from app.formatters import NumberFormatter

logger = logging.getLogger(__name__)


class ContainerFactory:
    """Factory for creating consistent container components"""

    @classmethod
    def create_section(
        cls, children, title=None, divider=True, spacing="md", custom_style=None
    ):
        """Create a section container with optional title and divider"""
        # Filter out None values
        if isinstance(children, list):
            children = [child for child in children if child is not None]
            if not children:
                return None
        elif children is None:
            return None

        # Build class name
        class_name = f"section section--spacing-{spacing}"
        if divider:
            class_name += " section--divider"

        # Build section elements
        elements = []

        # Add title if provided
        if title:
            elements.append(html.H4(title, className="section-title"))

        # Add children
        if isinstance(children, list):
            elements.extend(children)
        else:
            elements.append(children)

        # Keep only truly dynamic styles, if any
        dynamic_style = {}
        if custom_style:
            dynamic_style = custom_style

        return html.Div(elements, style=dynamic_style, className=class_name)


class ApartmentCard:
    """Improved apartment card implementation with enhanced visuals."""

    @staticmethod
    def create_price_section(price, cian_est, price_history=None):
        """Create price section with semantic styling."""
        if not price:
            return None

        price_value = re.sub(r"[^\d]", "", price) if price else None
        cian_est_value = re.sub(r"[^\d]", "", cian_est) if cian_est else None

        # Price elements
        price_elements = []

        # Main price tag with prominent styling
        price_elements.append(PillFactory.create_price_pill(price))

        # Price comparison if available
        """if price_value and cian_est_value:
            price_elements.append(
                PillFactory.create_price_comparison(price_value, cian_est_value)
            )"""

        # if cian_est and cian_est != "--":
        price_elements.append(PillFactory.create_cian_estimate_pill(cian_est))

        # Process price history with styling
        price_history_elements = []
        if price_history:
            seen_entries = set()
            for entry in sorted(price_history, key=lambda x: x.get("date_iso", "")):
                if "date" in entry and "price" in entry:
                    entry_key = f"{entry.get('date', '').strip()}:{entry.get('price', '').strip()}"
                    if entry_key not in seen_entries:
                        seen_entries.add(entry_key)
                        price_history_elements.append(
                            PillFactory.create_price_history_pill(
                                entry.get("date", ""), entry.get("price", "")
                            )
                        )

        # Create main price container
        price_container = PillFactory.create_pill_container(
            price_elements, align="center"
        )

        # Add price history if available
        elements = [price_container]
        if price_history_elements:
            history_container = PillFactory.create_pill_container(
                price_history_elements, wrap=True
            )
            elements.append(history_container)

        return ContainerFactory.create_section(elements, divider=False)

    @staticmethod
    def create_rental_terms_section(terms):
        """Create rental terms section with improved pill styling."""
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
                if field == "security_deposit" and NumberFormatter.is_numeric(value):
                    value = NumberFormatter.format_number(value)
                terms_items.append(
                    PillFactory.create_pill(f"{label}: {value}", "neutral")
                )

        if not terms_items:
            return None

        return PillFactory.create_pill_container(terms_items, wrap=True)

    @staticmethod
    def create_property_features_section(apartment_data):
        """Create property features section with semantic grouping."""
        if not apartment_data:
            return None

        apt = apartment_data.get("apartment", {})
        bld = apartment_data.get("building", {})
        features = apartment_data.get("features", {})

        # Create apartment features pills
        apartment_features = []

        # Floor information
        floor = apt.get("floor", "")
        total_floors = apt.get("total_floors", "")
        if floor and total_floors:
            apartment_features.append(
                PillFactory.create_floor_pill(floor, total_floors)
            )
        elif floor:
            apartment_features.append(PillFactory.create_floor_pill(floor))

        # Property mappings with semantic grouping
        apartment_properties = {
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
        }

        building_properties = {
            "year_built": "Год",
            "building_series": "Серия",
            "building_type": "Тип дома",
            "ceiling_type": "Перекрытия",
            "parking": "Парковка",
            "elevators": "Лифты",
            "garbage_chute": "Мусоропровод",
        }

        # Process apartment properties
        for field, label in apartment_properties.items():
            if (
                field in apt
                and apt.get(field)
                and field not in ["floor", "total_floors"]
            ):
                apartment_features.append(
                    PillFactory.create_property_feature_pill(
                        label, apt.get(field), "apartment"
                    )
                )

        # Process building properties
        building_features = []
        for field, label in building_properties.items():
            if field in bld and bld.get(field):
                building_features.append(
                    PillFactory.create_property_feature_pill(
                        label, bld.get(field), "building"
                    )
                )

        # Process amenities with success styling
        amenities_features = []
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
            if str(features.get(field, "")).lower() == "true":
                amenities_features.append(PillFactory.create_amenity_pill(label))

        # Create section content for each feature group
        section_content = []

        # Apartment features
        if apartment_features:
            section_content.append(
                PillFactory.create_pill_container(apartment_features, wrap=True)
            )

        # Building features
        if building_features:
            section_content.append(
                PillFactory.create_pill_container(building_features, wrap=True)
            )

        # Amenities
        if amenities_features:
            section_content.append(
                PillFactory.create_pill_container(amenities_features, wrap=True)
            )

        # Return only if we have content
        if section_content:
            return ContainerFactory.create_section(section_content, divider=True)
        return None

    @staticmethod
    def create_address_section(address_data):
        """Create address section with improved typography and layout."""
        if not address_data:
            return None

        address, metro, title, distance = address_data

        # Address content creation
        address_elements = []

        # Main address with bold styling
        if address:
            address_elements.append(html.H3(address, className="apartment-address"))

        # Secondary info items with pills
        info_elements = []

        if metro:
            info_elements.append(PillFactory.create_metro_pill(metro))

        if distance:
            info_elements.append(PillFactory.create_distance_pill(distance))

        if title:
            info_elements.append(html.Div(title, className="apartment-title"))

        if info_elements:
            address_elements.append(
                PillFactory.create_pill_container(
                    info_elements, align="center", wrap=True
                )
            )

        return ContainerFactory.create_section(
            address_elements, title=None, divider=True
        )

    @staticmethod
    def create_id_header(offer_id):
        """Create ID header with improved badge styling."""
        if not offer_id:
            return None

        return html.Div(
            [html.Span(f"ID: {offer_id}", className="apartment-id")],
            className="apartment-header",
        )

    @staticmethod
    def create_description_section(description):
        """Create description section with improved typography."""
        if not description:
            return None

        return ContainerFactory.create_section(
            html.Div(description, className="apartment-description"),
            title="Описание",
            divider=True,
        )

    @staticmethod
    def create_external_link(offer_id):
        """Create enhanced styled external link button."""
        if not offer_id:
            return None

        return html.A(
            "Открыть на Циан",
            href=f"https://www.cian.ru/rent/flat/{offer_id}/",
            target="_blank",
            className="apartment-external-link",
        )