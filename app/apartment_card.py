# app/apartment_card.py
from dash import html
import logging
from app.apartment import ApartmentCard
from app.image_handler import ImageHandler

logger = logging.getLogger(__name__)


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

    # DEBUG: Print the cian estimation value
    print(f"Debug - Cian Estimation from extract_row_data: '{cian_est}'")
    
    # If cian_est is empty but exists in apartment_data, use that instead
    if not cian_est and apartment_data.get("cian_estimation_value_formatted"):
        cian_est = apartment_data.get("cian_estimation_value_formatted")
        print(f"Debug - Using cian_est from apartment_data: '{cian_est}'")
    
    # Create detailed components with improved responsive styling
    components = [
        # ID Header
        ApartmentCard.create_id_header(offer_id),
        # Slideshow - now with responsive capabilities
        ImageHandler.create_slideshow(offer_id),
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

    # Update position info in the navigation bar
    if row_idx is not None and total_rows is not None:
        # Position info is handled elsewhere via navigation bar
        pass

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

        # Extract other fields
        title = ""
        if "<br>" in address_title and len(address_title.split("<br>")) > 1:
            title = address_title.split("<br>")[1]
        else:
            title = table_row_data.get("title", "")
        cian_est = table_row_data.get("cian_estimation_value_formatted", "")


        
        return (
            address,
            table_row_data.get("distance", ""),
            table_row_data.get("metro_station", ""),
            title,
            table_row_data.get("cian_estimation_value_formatted", ""),
            table_row_data.get("price_value_formatted", ""),
            table_row_data.get("description", ""),
        )
    except Exception as e:
        logger.error(f"Error extracting row data: {e}")
        return "", "", "", "", "", "", ""
