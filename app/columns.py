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


        # Price change pill
        price_change = row.get("price_change_value", 0)
        if price_change:
            pills.append(
                PillFactory.create_price_change_pill(price_change, status=status)
            )


        
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
        time_str = row.get("updated_time_display", "--")
        if time_str and time_str != "--":
            pills.append(PillFactory.create_time_pill(time_str, status=status))


        # Activity date formatting
        should_add_activity_date = "activity_date_display" in row and pd.notnull(
            row["activity_date_display"]
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
            activity_date = row["activity_date_display"]
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
    
    @staticmethod
    def format_distance(distance_value):
        """Format distance value for display."""
        return f"{distance_value:.2f} km" if pd.notnull(distance_value) else ""
    
    @staticmethod
    def format_active_time(days_value, hours_value):
        """Format active time for display (days or hours)."""
        # Show hours for recent listings (less than a day old)
        if pd.notnull(days_value) and days_value == 0 and pd.notnull(hours_value):
            return f"{int(hours_value)} ч."
            
        # Show days for older listings
        if pd.notnull(days_value) and days_value >= 0:
            return f"{int(days_value)} дн."
            
        # Default case
        return "--"
        
    @staticmethod
    def apply_display_formatting(df, base_url):
        """Apply display formatting to dataframe columns."""
        # Format address_title column
        df["address_title"] = df.apply(
            lambda r: ColumnFormatter.format_address_title(r, base_url), axis=1
        )
        
        # Create combined display columns
        if all(
            col in df.columns for col in ["price_value_formatted", "price_change_value"]
        ):
            df["price_text"] = df.apply(ColumnFormatter.format_price_column, axis=1)

        df["property_tags"] = df.apply(ColumnFormatter.format_property_tags, axis=1)

        if "price_change_formatted" in df.columns:
            df["price_change"] = df["price_change_formatted"]

        df["update_title"] = df.apply(ColumnFormatter.format_update_title, axis=1)
        
        return df