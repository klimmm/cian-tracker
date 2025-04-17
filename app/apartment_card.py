# app/apartment_card.py
from dash import html
import logging
from app.apartment import ApartmentCard
from app.data_manager import DataManager
from app.components import ContainerFactory
from dash import dcc
logger = logging.getLogger(__name__)


def create_slideshow(offer_id):
    """Create responsive slideshow component for images with improved styling."""
    image_paths = DataManager.get_apartment_images(offer_id)
    if not image_paths:
        return html.Div(
            [
                html.Div("No images available", className="no-photo-placeholder"),
                html.P("Фотографии недоступны"),
            ],
            className="slideshow-container no-photos",
        )

    # Create slideshow with improved responsive design
    return ContainerFactory.create_section(
        [
            # Image container with nav arrows and touch support
            html.Div(
                [
                    html.Img(
                        id={"type": "slideshow-img", "offer_id": offer_id},
                        src=image_paths[0],
                        className="slideshow-img",
                        # Specifically avoid using loading="lazy" which can cause issues
                    ),
                    html.Button(
                        "❮",
                        id={"type": "prev-btn", "offer_id": offer_id},
                        className="slideshow-nav-btn slideshow-nav-btn--prev",
                        # Add aria-label for accessibility
                        **{"aria-label": "Previous image"},
                    ),
                    html.Button(
                        "❯",
                        id={"type": "next-btn", "offer_id": offer_id},
                        className="slideshow-nav-btn slideshow-nav-btn--next",
                        **{"aria-label": "Next image"},
                    ),
                    html.Div(
                        f"1/{len(image_paths)}",
                        id={"type": "counter", "offer_id": offer_id},
                        className="slideshow-counter",
                    ),
                ],
                className="slideshow-container",
                # Add data attribute for identifying total images
                **{"data-total": str(len(image_paths))},
            ),
            dcc.Store(
                id={"type": "slideshow-data", "offer_id": offer_id},
                data={"current_index": 0, "image_paths": image_paths},
            ),
        ],
        divider=True,
    )


def create_apartment_details_card(
    apartment_data, table_row_data=None, row_idx=None, total_rows=None
):
    """Render apartment data into a detailed card with responsive design."""
    if not apartment_data:
        return html.Div(
            [
                html.H3("Нет данных для этой квартиры"),
                html.P(
                    "Информация о квартире недоступна. Пожалуйста, выберите другую квартиру."
                ),
            ],
            className="apartment-no-data",
        )

    # Extract basic data
    offer_id = apartment_data.get("offer_id", "")
    address, distance, metro, title, cian_est, price, description = extract_row_data(
        table_row_data
    )

    # DEBUG: Log data sources for debugging
    logger.info(f"Debug - Cian Estimation from extract_row_data: '{cian_est}'")
    logger.info(f"Debug - Apartment data keys: {list(apartment_data.keys())}")
    
    # Enhanced fallback mechanism - check multiple places for the field
    if not cian_est:
        # 1. Check if directly in apartment_data (added by callback)
        if apartment_data.get("cian_estimation_value_formatted"):
            cian_est = apartment_data.get("cian_estimation_value_formatted")
            logger.info(f"Debug - Using cian_est from apartment_data root: '{cian_est}'")
        # 2. Check apartment subdict if it exists
        elif apartment_data.get("apartment", {}).get("cian_estimation_value_formatted"):
            cian_est = apartment_data["apartment"]["cian_estimation_value_formatted"]
            logger.info(f"Debug - Using cian_est from apartment_data.apartment: '{cian_est}'")
        # 3. Check stats subdict if it exists
        elif apartment_data.get("stats", {}).get("cian_estimation_value_formatted"):
            cian_est = apartment_data["stats"]["cian_estimation_value_formatted"]
            logger.info(f"Debug - Using cian_est from apartment_data.stats: '{cian_est}'")
        # 4. Try alternative field names
        elif apartment_data.get("cian_estimation"):
            cian_est = apartment_data.get("cian_estimation")
            logger.info(f"Debug - Using alternative field cian_estimation: '{cian_est}'")
    
    # Create detailed components with improved responsive styling
    components = [
        # ID Header
        ApartmentCard.create_id_header(offer_id),
        # Slideshow - now with responsive capabilities
        create_slideshow(offer_id),
        # Address section
        ApartmentCard.create_address_section((address, metro, title, distance)),
        ApartmentCard.create_price_section(
            price, cian_est, apartment_data.get("price_history", [])
        ),
        ApartmentCard.create_rental_terms_section(apartment_data.get("terms", {})),
        # Property features section
        ApartmentCard.create_property_features_section(apartment_data),
        # Description section with responsive typography
        ApartmentCard.create_description_section(description),
        # External link
        ApartmentCard.create_external_link(offer_id),
    ]

    # Filter out None values
    components = [component for component in components if component is not None]

    # Create the main card container with responsive styling
    return html.Div(
        components,
        className="apartment-card-content",
        # Add data attribute for potential JS manipulation
        **{"data-offer-id": offer_id},
    )


def extract_row_data(table_row_data):
    """Extract essential data from row with error handling."""
    if not table_row_data:
        return "", "", "", "", "", "", ""

    try:
        # Log all keys available for debugging
        logger.info(f"Extract row data - table_row_data keys: {list(table_row_data.keys())}")
        
        # Extract address from address_title
        address_title = table_row_data.get("address_title", "")
        address = ""
        if "<br>" in address_title:
            address_parts = address_title.split("<br>")
            if address_parts and len(address_parts) > 0:
                address_text = address_parts[0]
                # Extract from markdown link if present
                if "[" in address_text and "](" in address_text:
                    address = address_text.split("[")[1].split("](")[0]
                else:
                    address = address_text
        address = table_row_data.get("address", "")
        # Extract other fields
        title = ""
        if "<br>" in address_title and len(address_title.split("<br>")) > 1:
            title = address_title.split("<br>")[1]
        else:
            title = table_row_data.get("title", "")
            
        # Try multiple possible field names for Cian estimation
        cian_est = table_row_data.get("cian_estimation_value_formatted", "")
        logger.info(f"Extract row data - cian_est initial value: {cian_est}")
        
        # Try alternative field names if needed
        if not cian_est:
            cian_est = table_row_data.get("cian_estimate", "")
            if not cian_est:
                cian_est = table_row_data.get("estimation_value", "")
                if not cian_est:
                    cian_est = table_row_data.get("cian_estimation", "")
        
        return (
            address,
            table_row_data.get("distance", ""),
            table_row_data.get("metro_station", ""),
            title,
            cian_est,
            table_row_data.get("price_value_formatted", ""),
            table_row_data.get("description", ""),
        )
    except Exception as e:
        logger.error(f"Error extracting row data: {e}")
        return "", "", "", "", "", "", ""