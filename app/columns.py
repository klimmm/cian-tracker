# columns.py
import pandas as pd
import logging
import re
from app.pill_factory import PillFactory

logger = logging.getLogger(__name__)


class ColumnFormatter:
    """Centralized column formatting for consistent display using PillFactory."""

    @staticmethod
    def format_price_column(row):
        """Format price column with consistent pills."""
        pills = []

        # Main price pill
        price_formatted = row.get("price_value_formatted", "--")
        if price_formatted and price_formatted != "--":
            pills.append(PillFactory.create_price_pill(price_formatted))

        # Price change pill
        price_change = row.get("price_change_value", 0)
        if price_change:
            pills.append(PillFactory.create_price_change_pill(price_change))

        # Good price pill
        if (
            row.get("price_difference_value", 0) > 0
            and row.get("status") != "non active"
        ):
            pills.append(PillFactory.create_good_price_pill())

        # CIAN estimation pill
        cian_est = row.get("cian_estimation_formatted")
        if (
            pd.notnull(cian_est)
            and cian_est != "--"
            and cian_est != row.get("price_value_formatted")
        ):
            pills.append(PillFactory.create_cian_estimate_pill(cian_est))

        return PillFactory.create_pill_container(pills, wrap=True, return_as_html=True)

    @staticmethod
    def format_update_title(row):
        """Format update title column with activity date if available."""
        pills = []

        # Time string as a pill
        time_str = row.get("updated_time", "--")
        if time_str and time_str != "--":
            pills.append(PillFactory.create_time_pill(time_str))

        # Days active pill
        days_active = row.get("days_active")
        days_value = row.get("days_active_value", 0)
        if pd.notnull(days_active) and days_active != "--":
            pills.append(
                PillFactory.create_days_active_pill(
                    days_value, row.get("status", "active")
                )
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
                PillFactory.create_activity_date_pill(
                    activity_date, row.get("status", "active")
                )
            )

        return PillFactory.create_pill_container(pills, wrap=True, return_as_html=True)

    @staticmethod
    def format_property_tags(row):
        """Format property pills column consistently."""
        pills = []

        distance_value = row.get("distance_sort")
        if distance_value is not None and pd.notnull(distance_value):
            pills.append(PillFactory.create_walking_time_pill(distance_value))

        # Process neighborhood information
        neighborhood = str(row.get("neighborhood", ""))
        if neighborhood and neighborhood != "nan" and neighborhood != "None":
            pills.append(PillFactory.create_neighborhood_pill(neighborhood))

        # Add metro station pill
        if metro_station := row.get("metro_station"):
            pills.append(PillFactory.create_metro_pill(metro_station))

        return PillFactory.create_pill_container(pills, wrap=True, return_as_html=True)