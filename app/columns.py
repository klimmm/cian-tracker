# app/columns.py
import pandas as pd
import logging
import re
from app.pill_factory import PillFactory
from app.formatters import DateFormatter, NumberFormatter
from datetime import datetime

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
            
    @staticmethod
    def extract_title_data(df):
        """Extract room count, area, and floor information from titles into new columns."""
        if "title" not in df.columns:
            return df

        # Process each title row by row to avoid creating temporary columns
        room_counts = []
        areas = []
        floors = []
        total_floors_list = []

        for title in df["title"]:
            # Ensure title is a string
            title = str(title) if title is not None else ""
            if not title or title == "nan":
                room_counts.append(None)
                areas.append(None)
                floors.append(None)
                total_floors_list.append(None)
                continue

            # Extract room count
            room_count = None
            if "Студия" in title:
                room_count = 0  # 0 represents studio
            elif "Апартаменты-студия" in title:
                room_count = 0  # 0 represents studio
            else:
                room_match = re.search(r"(\d+)-комн", title)
                if room_match:
                    try:
                        room_count = int(room_match.group(1))
                    except (ValueError, TypeError):
                        room_count = None
            room_counts.append(room_count)

            # Extract area
            area = None
            area_match = re.search(r"(\d+[,.]?\d*)\s*м[г²²]?", title)
            if area_match:
                try:
                    area_str = area_match.group(1).replace(",", ".")
                    area = float(area_str)
                except (ValueError, TypeError):
                    area = None
            areas.append(area)

            # Extract floor info
            floor = None
            total_floors = None
            floor_match = re.search(r"(\d+)/(\d+)\s*этаж", title)
            if floor_match:
                try:
                    floor = int(floor_match.group(1))
                    total_floors = int(floor_match.group(2))
                except (ValueError, TypeError):
                    floor = None
                    total_floors = None
            floors.append(floor)
            total_floors_list.append(total_floors)

        # Add extracted columns to dataframe
        df["room_count"] = room_counts
        df["area"] = areas
        df["floor"] = floors
        df["total_floors"] = total_floors_list

        return df
        
    @staticmethod
    def process_metrics(df):
        """Process metrics data."""
        df["distance_sort"] = pd.to_numeric(df["distance"], errors="coerce")
        df["distance"] = df["distance_sort"].apply(
            lambda x: f"{x:.2f} km" if pd.notnull(x) else ""
        )
        return df

    @staticmethod
    def process_dates(df, now):
        """Process date columns."""
        for col in ["updated_time", "unpublished_date", "activity_date"]:
            if col in df.columns:
                df[f"{col}_sort"] = pd.to_datetime(df[col], errors="coerce")
                df[f"{col}_sort"] = df[f"{col}_sort"].apply(
                    lambda x: (
                        DateFormatter.ensure_timezone(x) if pd.notnull(x) else None
                    )
                )

                df[col] = df[f"{col}_sort"].apply(
                    lambda x: DateFormatter.format_date(x) if pd.notnull(x) else "--"
                )
        
        return df

    @staticmethod
    def calculate_active_time(df, now):
        """Calculate how long listings have been active."""
        if all(col in df.columns for col in ["updated_time_sort", "status"]):
            df["days_active_value"] = df.apply(
                lambda r: (
                    (now - DateFormatter.ensure_timezone(r["updated_time_sort"])).days
                    if r["status"] == "active" and pd.notnull(r["updated_time_sort"])
                    else (
                        (
                            DateFormatter.ensure_timezone(r["unpublished_date_sort"])
                            - DateFormatter.ensure_timezone(r["updated_time_sort"])
                        ).days
                        if r["status"] == "non active"
                        and pd.notnull(r["unpublished_date_sort"])
                        and pd.notnull(r["updated_time_sort"])
                        else None
                    )
                ),
                axis=1,
            )

            # Hours for entries where days = 0
            df["hours_active_value"] = df.apply(
                lambda r: (
                    int(
                        (
                            now - DateFormatter.ensure_timezone(r["updated_time_sort"])
                        ).total_seconds()
                        // 3600
                    )
                    if r["status"] == "active"
                    and pd.notnull(r["updated_time_sort"])
                    and (
                        now - DateFormatter.ensure_timezone(r["updated_time_sort"])
                    ).days
                    == 0
                    else (
                        int(
                            (
                                DateFormatter.ensure_timezone(
                                    r["unpublished_date_sort"]
                                )
                                - DateFormatter.ensure_timezone(r["updated_time_sort"])
                            ).total_seconds()
                            // 3600
                        )
                        if r["status"] == "non active"
                        and pd.notnull(r["unpublished_date_sort"])
                        and pd.notnull(r["updated_time_sort"])
                        and (
                            DateFormatter.ensure_timezone(r["unpublished_date_sort"])
                            - DateFormatter.ensure_timezone(r["updated_time_sort"])
                        ).days
                        == 0
                        else None
                    )
                ),
                axis=1,
            )

            # Format days active
            df["days_active"] = df.apply(
                lambda r: (
                    f"{int(r['hours_active_value'])} ч."
                    if pd.notnull(r["days_active_value"])
                    and r["days_active_value"] == 0
                    and pd.notnull(r["hours_active_value"])
                    else (
                        f"{int(r['days_active_value'])} дн."
                        if pd.notnull(r["days_active_value"])
                        and r["days_active_value"] >= 0
                        else "--"
                    )
                ),
                axis=1,
            )
        
        return df

    @staticmethod
    def process_financial_info(df):
        """Process financial information."""
        # Format price columns
        for col in ["price_value", "cian_estimation_value"]:
            if col in df.columns:
                df[f"{col}_formatted"] = df[col].apply(
                    lambda x: (
                        NumberFormatter.format_number(x)
                        if NumberFormatter.is_numeric(x)
                        else "--"
                    )
                )

        # Calculate price difference
        if all(col in df.columns for col in ["price_value", "cian_estimation_value"]):
            df["price_difference_value"] = df.apply(
                lambda r: (
                    int(r["cian_estimation_value"]) - int(r["price_value"])
                    if (
                        NumberFormatter.is_numeric(r["price_value"])
                        and NumberFormatter.is_numeric(r["cian_estimation_value"])
                        and not pd.isna(r["price_value"])
                        and not pd.isna(r["cian_estimation_value"])
                    )
                    else 0
                ),
                axis=1,
            )
        
        return df

    @staticmethod
    def create_display_columns(df):
        """Create combined display columns."""
        # Use standardized column formatters
        if all(
            col in df.columns for col in ["price_value_formatted", "price_change_value"]
        ):
            df["price_text"] = df.apply(ColumnFormatter.format_price_column, axis=1)

        df["property_tags"] = df.apply(ColumnFormatter.format_property_tags, axis=1)

        if "price_change_formatted" in df.columns:
            df["price_change"] = df["price_change_formatted"]

        df["update_title"] = df.apply(ColumnFormatter.format_update_title, axis=1)
        
        return df

    @staticmethod
    def apply_transformations(df, base_url, now):
        """Apply all data transformations."""
        # Extract structured data from title
        if "title" in df.columns:
            df = ColumnFormatter.extract_title_data(df)

        # Process metrics
        df = ColumnFormatter.process_metrics(df)

        # Format address_title column
        df["address_title"] = df.apply(
            lambda r: ColumnFormatter.format_address_title(r, base_url), axis=1
        )
        
        # Process dates
        df = ColumnFormatter.process_dates(df, now)

        # Calculate days active
        df = ColumnFormatter.calculate_active_time(df, now)

        # Combined date for sorting
        if "updated_time_sort" in df.columns:
            df["date_sort_combined"] = df["updated_time_sort"]

        # Format financial info
        df = ColumnFormatter.process_financial_info(df)

        # Create display columns
        df = ColumnFormatter.create_display_columns(df)
        
        return df