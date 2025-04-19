from dataclasses import dataclass, field
from typing import List, Dict, Any
from time import perf_counter
from dash import html, dcc
import logging
from app.image_loader import ImageLoader

from app.pill_factory import PillFactory
from app.formatters import NumberFormatter

logger = logging.getLogger(__name__)

# Combined field labels dictionary
FIELD_LABELS = {
    "terms": {
        "security_deposit": "Залог",
        "commission": "Комиссия",
        "prepayment": "Предоплата",
        "utilities_payment": "ЖКХ",
    },
    "apartment": {
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
    },
    "building": {
        "year_built": "Год",
        "building_series": "Серия",
        "building_type": "Тип дома",
        "ceiling_type": "Перекрытия",
        "parking": "Парковка",
        "elevators": "Лифты",
        "garbage_chute": "Мусоропровод",
    },
    "amenities": {
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
    },
}


@dataclass
class PriceHistory:
    date: str
    date_iso: str = ""
    price: str = ""


@dataclass
class RentalTerms:
    security_deposit: str = ""
    commission: str = ""
    prepayment: str = ""
    utilities_payment: str = ""


@dataclass
class ApartmentDetails:
    floor: str = ""
    total_floors: str = ""
    layout: str = ""
    apartment_type: str = ""
    total_area: str = ""
    living_area: str = ""
    kitchen_area: str = ""
    renovation: str = ""
    bathroom: str = ""
    balcony: str = ""
    ceiling_height: str = ""
    view: str = ""


@dataclass
class BuildingDetails:
    year_built: str = ""
    building_series: str = ""
    building_type: str = ""
    ceiling_type: str = ""
    parking: str = ""
    elevators: str = ""
    garbage_chute: str = ""


@dataclass
class ApartmentFeatures:
    has_refrigerator: bool = False
    has_dishwasher: bool = False
    has_washing_machine: bool = False
    has_air_conditioner: bool = False
    has_tv: bool = False
    has_internet: bool = False
    has_kitchen_furniture: bool = False
    has_room_furniture: bool = False
    has_bathtub: bool = False
    has_shower_cabin: bool = False


@dataclass
class Apartment:
    offer_id: str = ""
    address: str = ""
    title: str = ""
    address_title: str = ""
    metro_station: str = ""
    distance: str = ""
    price_value_formatted: str = ""
    cian_estimation_value_formatted: str = ""
    description: str = ""
    price_history: List[PriceHistory] = field(default_factory=list)
    terms: RentalTerms = field(default_factory=RentalTerms)
    apartment: ApartmentDetails = field(default_factory=ApartmentDetails)
    building: BuildingDetails = field(default_factory=BuildingDetails)
    features: ApartmentFeatures = field(default_factory=ApartmentFeatures)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Apartment':
        """Convert a dictionary to an Apartment object"""
        if not data:
            return cls()
            
        # Create the base apartment
        apartment = cls(
            offer_id=data.get("offer_id", ""),
            address=data.get("address", ""),
            title=data.get("title", ""),
            address_title=data.get("address_title", ""),
            metro_station=data.get("metro_station", ""),
            distance=data.get("distance", ""),
            price_value_formatted=data.get("price_value_formatted", ""),
            cian_estimation_value_formatted=data.get("cian_estimation_value_formatted", ""),
            description=data.get("description", "")
        )
        
        # Process price history
        price_history = []
        for item in data.get("price_history", []):
            price_history.append(PriceHistory(
                date=item.get("date", ""),
                date_iso=item.get("date_iso", ""),
                price=item.get("price", "")
            ))
        apartment.price_history = price_history
        
        # Process rental terms
        terms_data = data.get("terms", {})
        apartment.terms = RentalTerms(
            security_deposit=terms_data.get("security_deposit", ""),
            commission=terms_data.get("commission", ""),
            prepayment=terms_data.get("prepayment", ""),
            utilities_payment=terms_data.get("utilities_payment", "")
        )
        
        # Process apartment details
        apt_data = data.get("apartment", {})
        apartment.apartment = ApartmentDetails(
            floor=apt_data.get("floor", ""),
            total_floors=apt_data.get("total_floors", ""),
            layout=apt_data.get("layout", ""),
            apartment_type=apt_data.get("apartment_type", ""),
            total_area=apt_data.get("total_area", ""),
            living_area=apt_data.get("living_area", ""),
            kitchen_area=apt_data.get("kitchen_area", ""),
            renovation=apt_data.get("renovation", ""),
            bathroom=apt_data.get("bathroom", ""),
            balcony=apt_data.get("balcony", ""),
            ceiling_height=apt_data.get("ceiling_height", ""),
            view=apt_data.get("view", "")
        )
        
        # Process building details
        bld_data = data.get("building", {})
        apartment.building = BuildingDetails(
            year_built=bld_data.get("year_built", ""),
            building_series=bld_data.get("building_series", ""),
            building_type=bld_data.get("building_type", ""),
            ceiling_type=bld_data.get("ceiling_type", ""),
            parking=bld_data.get("parking", ""),
            elevators=bld_data.get("elevators", ""),
            garbage_chute=bld_data.get("garbage_chute", "")
        )
        
        # Process features
        features_data = data.get("features", {})
        apartment.features = ApartmentFeatures(
            has_refrigerator=str(features_data.get("has_refrigerator", "")).lower() == "true",
            has_dishwasher=str(features_data.get("has_dishwasher", "")).lower() == "true",
            has_washing_machine=str(features_data.get("has_washing_machine", "")).lower() == "true",
            has_air_conditioner=str(features_data.get("has_air_conditioner", "")).lower() == "true",
            has_tv=str(features_data.get("has_tv", "")).lower() == "true",
            has_internet=str(features_data.get("has_internet", "")).lower() == "true",
            has_kitchen_furniture=str(features_data.get("has_kitchen_furniture", "")).lower() == "true",
            has_room_furniture=str(features_data.get("has_room_furniture", "")).lower() == "true",
            has_bathtub=str(features_data.get("has_bathtub", "")).lower() == "true",
            has_shower_cabin=str(features_data.get("has_shower_cabin", "")).lower() == "true"
        )
        
        return apartment


class ContainerFactory:
    """Factory for creating consistent container components"""

    @classmethod
    def create_section(
        cls, children, title=None, divider=True, spacing="sm", custom_style=None
    ):
        """Create a section container with optional title and divider"""
        # Quick early return if no children
        if not children or (isinstance(children, list) and not any(children)):
            return None

        # Build elements list and class name
        elements = [html.H4(title, className="section-title")] if title else []
        elements.extend(children if isinstance(children, list) else [children])
        class_name = f"section"
        if divider:
            class_name += " section--divider"
        
        # Apply compact styling - ensure no margins
        style = custom_style or {}
        style["marginBottom"] = "0"
        style["marginTop"] = "0"
        style["paddingBottom"] = "var(--space-xs)"
        
        return html.Div(elements, style=style, className=class_name)


def _nav_button(label, btn_id, extra_classes=""):
    return html.Button(
        label,
        id=btn_id,
        className=f"details-nav-button {extra_classes}".strip(),
        n_clicks=0,
    )

def create_apartment_details_panel():
    return html.Div(
        [
            html.Div(id="details-overlay", className="details-overlay details-panel--hidden"),
            html.Div(
                id="apartment-details-panel",
                className="details-panel details-panel--hidden",
                children=[
                    html.Div(
                        className="details-panel-header",
                        children=[
                            _nav_button(
                                "←",
                                "prev-apartment-button",
                                "details-nav-button--prev",
                            ),
                            html.A(
                                "Циан",
                                id="cian-link-header",
                                href="#",  # This will be updated dynamically
                                target="_blank",
                                className="details-panel-title cian-link-header",
                            ),
                            html.Div(
                                className="details-header-right",
                                children=[
                                    _nav_button(
                                        "→",
                                        "next-apartment-button",
                                        "details-nav-button--next",
                                    ),
                                    html.Button(
                                        "×", 
                                        id="close-details-button", 
                                        className="details-close-x",
                                        n_clicks=0
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


def HeroSlideshow(apartment: Apartment) -> html.Div:
    """Create responsive slideshow component with overlaid address and badges"""
    offer_id = apartment.offer_id
    
    t0 = perf_counter()
    image_paths = ImageLoader.get_apartment_images(offer_id)
    logger.info(
        f"[TIMER] get_apartment_images({offer_id}) → {perf_counter() - t0:.3f}s"
    )

    if not image_paths:
        return html.Div(
            [
                html.Div("No images available", className="no-photo-placeholder"),
                html.P("Фотографии недоступны"),
            ],
            className="card-hero card-hero--empty",
        )

    total = len(image_paths)
    address_overlay = None

    if apartment.address:
        title_element = html.Div(apartment.title, className="apartment-title") if apartment.title else None
        metro_badge = PillFactory.create_metro_pill(apartment.metro_station, custom_class="card-pill") if apartment.metro_station else None
        distance_badge = PillFactory.create_distance_pill(apartment.distance, custom_class="card-pill") if apartment.distance else None
        
        badges = []
        if metro_badge:
            badges.append(metro_badge)
        if distance_badge:
            badges.append(distance_badge)
            
        badge_container = PillFactory.create_pill_container(badges, align="center") if badges else None
        
        overlay_elements = []
        if apartment.address:
            overlay_elements.append(html.H3(apartment.address, className="hero-address"))
        # Add title element to overlay (new)
        if title_element:
            overlay_elements.append(title_element)
        if badge_container:
            overlay_elements.append(badge_container)
            
        if overlay_elements:
            address_overlay = html.Div(overlay_elements, className="card-hero__overlay")

    # Create slideshow
    slideshow = html.Div(
        [
            html.Img(
                id={"type": "slideshow-img", "offer_id": offer_id},
                src=image_paths[0],
                className="slideshow-img",
                alt=f"Apartment {offer_id} - Image 1 of {total}",
            ),
            html.Button(
                "❮",
                id={"type": "prev-btn", "offer_id": offer_id},
                className="slideshow-nav-btn slideshow-nav-btn--prev",
                **{"aria-label": "Previous image"},
            ),
            html.Button(
                "❯",
                id={"type": "next-btn", "offer_id": offer_id},
                className="slideshow-nav-btn slideshow-nav-btn--next",
                **{"aria-label": "Next image"},
            ),
            html.Div(
                f"1/{total}",
                id={"type": "counter", "offer_id": offer_id},
                className="slideshow-counter",
            ),
            dcc.Store(
                id={"type": "slideshow-data", "offer_id": offer_id},
                data={"current_index": 0, "image_paths": image_paths},
            ),
        ],
        className="card-hero__slideshow",
        **{"data-total": str(total)},
    )
    
    # Combine slideshow and overlay
    hero_elements = [slideshow]
    if address_overlay:
        hero_elements.append(address_overlay)
        
    return html.Div(hero_elements, className="card-hero")


def PriceRow(apartment: Apartment) -> html.Div:
    """Create a row with price, CIAN estimate, and price history"""
    price = apartment.price_value_formatted
    cian_est = apartment.cian_estimation_value_formatted
    price_history = apartment.price_history
    
    if not price:
        return None
        
    price_elements = [PillFactory.create_price_pill(price, custom_class="card-pill--price")]
    if cian_est:
        price_elements.append(PillFactory.create_cian_estimate_pill(cian_est, custom_class="card-pill"))

    if price_history:
        seen_entries = set()

        for entry in sorted(price_history, key=lambda x: x.date_iso or ""):
            if entry.date and entry.price and str(entry.date).lower() not in ['nan', 'none', ''] and str(entry.price).lower() not in ['nan', 'none', '']:
                entry_key = f"{entry.date.strip()}:{entry.price.strip()}"
                if entry_key not in seen_entries:
                    seen_entries.add(entry_key)
                    price_elements.append(
                        PillFactory.create_price_history_pill(
                            entry.date, entry.price, custom_class="card-pill"
                        )
                    )
    
    pills_container = PillFactory.create_pill_container(price_elements, wrap=True)

    return html.Div(
        pills_container, 
        className="card-specs section section--divider"
    )


def CombinedSpecsRow(apartment: Apartment) -> html.Div:
    """Create a combined row with apartment, building, and amenities specs as pills in one flex container"""
    if not apartment:
        return None
        
    apt = apartment.apartment
    bld = apartment.building
    features = apartment.features
    terms = apartment.terms
    if not terms:
        return None
        
    terms_items = []
    for field, label in FIELD_LABELS["terms"].items():
        value = getattr(terms, field, "")
        if value and str(value).lower() not in ['nan', 'none', '']:
            if field == "security_deposit" and NumberFormatter.is_numeric(value):
                value = NumberFormatter.format_number(value)
            terms_items.append(
                PillFactory.create_pill(f"{label}: {value}", "neutral", custom_class="card-pill")
            )

    apartment_pills = []
    
    # Add floor information as the first pill
    floor, total_floors = apt.floor, apt.total_floors
    if floor and str(floor).lower() not in ['nan', 'none', '']:
        floor_value = f"{floor}/{total_floors}" if total_floors else floor
        apartment_pills.append(
            PillFactory.create_pill(f"Этаж: {floor_value}", "apartment", custom_class="card-pill")
        )
    
    # Add apartment specs as pills
    for field, label in FIELD_LABELS["apartment"].items():
        if field not in ["floor", "total_floors"]:
            value = getattr(apt, field, "")
            if value and str(value).lower() not in ['nan', 'none', '']:
                apartment_pills.append(
                    PillFactory.create_pill(f"{label}: {value}", "apartment", custom_class="card-pill")
                )
    
    # Create building features pills
    building_pills = []
    for field, label in FIELD_LABELS["building"].items():
        value = getattr(bld, field, "")
        if value and str(value).lower() not in ['nan', 'none', '']:
            building_pills.append(
                PillFactory.create_pill(f"{label}: {value}", "building", custom_class="card-pill")
            )
    
    # Create amenities pills
    amenities_pills = []
    for field, label in FIELD_LABELS["amenities"].items():
        if getattr(features, field, False):
            amenities_pills.append(PillFactory.create_amenity_pill(label, custom_class="card-pill"))
    
    # Combine all pills
    all_pills = terms_items + apartment_pills + building_pills + amenities_pills
    
    if not all_pills:
        return None
    
    # Create a single container with all pills
    pills_container = PillFactory.create_pill_container(all_pills, wrap=True)
    
    return html.Div(
        pills_container,
        className="card-specs section section--divider"
    )


def DescriptionSection(apartment: Apartment) -> html.Div:
    """Create a description section"""
    if not apartment.description:
        return None
        
    return html.Div(
        html.Div(
            apartment.description,
            className="apartment-description"
        ),
        className="card-description section"  # Removed divider to reduce spacing
    )
    
def create_apartment_details_card(data: Dict[str, Any]):
    """Render apartment details using component-based architecture."""
    start_total = perf_counter()

    # 1) No data? show error placeholder
    if not data:
        return html.Div(
            [
                html.H3("Нет данных для этой квартиры"),
                html.P("Пожалуйста, выберите другую квартиру."),
            ],
            className="apartment-no-data",
        )

    # Convert dictionary to Apartment object
    t0 = perf_counter()
    apt = Apartment.from_dict(data)
    logger.info(f"[TIMER] create_apartment_object → {perf_counter() - t0:.3f}s")

    # Assemble all sections in a clear, explicit order
    t1 = perf_counter()
    sections = [
        HeroSlideshow(apt),
        PriceRow(apt),
        CombinedSpecsRow(apt),
        DescriptionSection(apt)
    ]
    
    # Filter out None components
    components = [sect for sect in sections if sect is not None]
    logger.info(f"[TIMER] assemble_components → {perf_counter() - t1:.3f}s")

    total = perf_counter() - start_total
    logger.info(f"[TIMER] create_apartment_details_card total → {total:.3f}s")

    return html.Div(
        components,
        className="apartment-card apartment-card-content",
        style={"gap": "0"}, # Remove gap between sections
        **{"data-offer-id": apt.offer_id},
    )