# app/apartment_card.py

from time import perf_counter
from dash import html, dcc
import logging
from app.apartment import ApartmentCard
from app.data_manager import DataManager
from app.components import ContainerFactory

logger = logging.getLogger(__name__)


def create_slideshow(offer_id):
    """Create responsive slideshow component for images with timing diagnostics."""
    t0 = perf_counter()
    image_paths = DataManager.get_apartment_images(offer_id)
    elapsed = perf_counter() - t0
    logger.info(f"[TIMER] get_apartment_images({offer_id}) → {elapsed:.3f}s")

    if not image_paths:
        return html.Div(
            [
                html.Div("No images available", className="no-photo-placeholder"),
                html.P("Фотографии недоступны"),
            ],
            className="slideshow-container no-photos",
        )

    total = len(image_paths)
    # Build slideshow container
    return ContainerFactory.create_section(
        [
            html.Div(
                [
                    html.Img(
                        id={"type": "slideshow-img", "offer_id": offer_id},
                        src=image_paths[0],
                        className="slideshow-img",
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
                ],
                className="slideshow-container",
                **{"data-total": str(total)},
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
    """Render apartment details with timing diagnostics around each stage."""
    start_total = perf_counter()

    if not apartment_data:
        return html.Div(
            [
                html.H3("Нет данных для этой квартиры"),
                html.P("Информация о квартире недоступна. Пожалуйста, выберите другую квартиру."),
            ],
            className="apartment-no-data",
        )

    # 1) extract_row_data
    t0 = perf_counter()
    offer_id = apartment_data.get("offer_id", "")
    address, distance, metro, title, cian_est, price, description = extract_row_data(table_row_data)
    logger.info(f"[TIMER] extract_row_data → {perf_counter() - t0:.3f}s")

    # Fallback for cian_est
    if not cian_est and apartment_data.get("cian_estimation_value_formatted"):
        cian_est = apartment_data["cian_estimation_value_formatted"]
        logger.info(f"Using fallback cian_est: '{cian_est}'")

    # 2) slideshow
    t1 = perf_counter()
    slideshow = create_slideshow(offer_id)
    logger.info(f"[TIMER] create_slideshow → {perf_counter() - t1:.3f}s")

    # 3) build components
    t2 = perf_counter()
    components = [
        ApartmentCard.create_id_header(offer_id),
        slideshow,
        ApartmentCard.create_address_section((address, metro, title, distance)),
        ApartmentCard.create_price_section(price, cian_est, apartment_data.get("price_history", [])),
        ApartmentCard.create_rental_terms_section(apartment_data.get("terms", {})),
        ApartmentCard.create_property_features_section(apartment_data),
        ApartmentCard.create_description_section(description),
        ApartmentCard.create_external_link(offer_id),
    ]
    # filter out any None
    components = [c for c in components if c is not None]
    logger.info(f"[TIMER] component assembly → {perf_counter() - t2:.3f}s")

    total_elapsed = perf_counter() - start_total
    logger.info(f"[TIMER] create_apartment_details_card total → {total_elapsed:.3f}s")

    return html.Div(
        components,
        className="apartment-card-content",
        **{"data-offer-id": offer_id},
    )



def extract_row_data(table_row_data):
    """Extract essential data from row with error handling."""
    if not table_row_data:
        return "", "", "", "", "", "", ""

    try:
        # Log all keys available for debugging
        logger.debug(f"Extract row data - table_row_data keys: {list(table_row_data.keys())}")
        
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