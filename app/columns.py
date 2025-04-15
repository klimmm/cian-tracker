# app/columns.py
import pandas as pd
import logging
from app.pill_factory import PillFactory

logger = logging.getLogger(__name__)


class ColumnFormatter:
    """Centralized column formatting for consistent display using PillFactory."""

    @staticmethod
    def format_price_column(row):
        """Format price column with consistent pills."""
        pills = []

        # Get status from row
        status = row.get("status", "active")

        price_formatted = row.get("price_value_formatted", "--")

        # Determine if it's a 'good price'
        is_good_price = (
            row.get("price_difference_value", 0) > 0 and status != "non active"
        )

        if price_formatted and price_formatted != "--":
            # Use centralized PillFactory logic for styling
            pills.append(
                PillFactory.create_price_pill(
                    price_formatted, is_good_price=is_good_price, status=status
                )
            )

        # CIAN estimation pill
        cian_est = row.get("cian_estimation_formatted")
        if (
            pd.notnull(cian_est)
            and cian_est != "--"
            and cian_est != row.get("price_value_formatted")
        ):
            pills.append(PillFactory.create_cian_estimate_pill(cian_est, status=status))

        return PillFactory.create_pill_container(
            pills, wrap=True, return_as_html=True, status=status
        )

    @staticmethod
    def format_update_title(row):
        """Format update title column with activity date if available."""
        pills = []

        # Get status from row
        status = row.get("status", "active")

        # Time string as a pill
        time_str = row.get("updated_time", "--")
        if time_str and time_str != "--":
            pills.append(PillFactory.create_time_pill(time_str, status=status))

        # Price change pill
        price_change = row.get("price_change_value", 0)
        if price_change:
            pills.append(
                PillFactory.create_price_change_pill(price_change, status=status)
            )

        # Activity date formatting
        should_add_activity_date = "activity_date" in row and pd.notnull(
            row["activity_date"]
        )

        # Skip if same as updated time
        if (
            should_add_activity_date
            and pd.notnull(row.get("updated_time_sort"))
            and pd.notnull(row.get("activity_date_sort"))
        ):
            time_diff = abs(
                (row["activity_date_sort"] - row["updated_time_sort"]).total_seconds()
            )
            if time_diff < 60:
                should_add_activity_date = False

        if should_add_activity_date:
            activity_date = row["activity_date"]
            pills.append(
                PillFactory.create_activity_date_pill(activity_date, status=status)
            )

        return PillFactory.create_pill_container(
            pills, wrap=True, return_as_html=True, status=status
        )

    @staticmethod
    def format_property_tags(row):
        """Format property pills column consistently."""
        pills = []

        # Get status from row
        status = row.get("status", "active")

        # Room count pill
        room_count = row.get("room_count")
        if pd.notnull(room_count):
            pill = PillFactory.create_room_pill(room_count, status=status)
            if pill:
                pills.append(pill)

        # Area pill
        area = row.get("area")
        if pd.notnull(area):
            pill = PillFactory.create_area_pill(area, status=status)
            if pill:
                pills.append(pill)

        # Floor pill
        floor = row.get("floor")
        total_floors = row.get("total_floors")
        if pd.notnull(floor) and pd.notnull(total_floors):
            pill = PillFactory.create_floor_pill(floor, total_floors, status=status)
            if pill:
                pills.append(pill)

        return PillFactory.create_pill_container(
            pills, wrap=True, return_as_html=True, status=status
        )

    @staticmethod
    def format_address_title(row, base_url):
        """Format address with distance, neighborhood, and metro station information."""
        # First create all pills EXCEPT address as normal pills
        pills = []

        # Get status from row
        status = row.get("status", "active")

        # Distance value pill
        distance_value = row.get("distance_sort")
        if distance_value is not None and pd.notnull(distance_value):
            pills.append(
                PillFactory.create_walking_time_pill(distance_value, status=status)
            )

        # Neighborhood pill
        neighborhood = str(row.get("neighborhood", ""))
        if neighborhood and neighborhood != "nan" and neighborhood != "None":
            pills.append(
                PillFactory.create_neighborhood_pill(neighborhood, status=status)
            )

        # Create the pill container with proper spacing
        pills_html = (
            PillFactory.create_pill_container(
                pills, wrap=True, return_as_html=True, status=status
            )
            if pills
            else ""
        )

        # Create the address link separately to maintain clickability
        address = row.get("address", "")
        offer_id = row.get("offer_id", "")

        # Apply inactive styling to the address pill if status is non active
        address_class = "pill pill--default address-pill"
        address_style = ""
        if status == "non active":
            address_class += " pill--inactive"
            address_style = 'style="background-color: #e0e0e0; color: #757575; border-color: #bdbdbd"'

        address_html = f'<div class="{address_class}" {address_style}><a href="{base_url}{offer_id}/" class="address-link">{address}</a></div>'

        # Combine all elements
        if pills_html:
            return f"{address_html} {pills_html}"
        else:
            return address_html
