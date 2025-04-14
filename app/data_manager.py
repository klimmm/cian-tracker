# data_manager.py
import pandas as pd
import os
import logging
import traceback
import requests
from datetime import datetime

# Import formatters from the other module
from formatters import (
    DateFormatter, NumberFormatter, 
    ColumnFormatter, 
    MOSCOW_TZ, CONFIG, 
    LINE_COLORS, METRO_TO_LINE
)

# You might want to relocate these constants to a common config module
# but I'm keeping them here for this example
from app.config import CONFIG, MOSCOW_TZ
from app.app_config import AppConfig
from app.metro import LINE_COLORS, METRO_TO_LINE

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Centralized error handling utilities."""

    @staticmethod
    def try_operation(
        logger, operation_name, func, *args, default_return=None, **kwargs
    ):
        """Execute operation with error handling."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {operation_name}: {str(e)}")
            return default_return


class DataManager:
    """Centralized data management."""

    @staticmethod
    def load_csv_safely(file_path):
        """Load CSV file safely with fallback to GitHub if needed."""
        try:
            # Try to load from local file first
            if os.path.exists(file_path):
                logger.info(f"Loading CSV from local file: {file_path}")
                return pd.read_csv(file_path, encoding="utf-8")

            # If local file doesn't exist and we're using hybrid mode for apartment details
            elif AppConfig.should_use_hybrid_for_apartment_details():
                # Extract filename from path
                file_name = os.path.basename(file_path)
                # Try to load from GitHub
                github_url = AppConfig.get_github_url("cian_data", file_name)
                logger.info(f"Local file not found, trying GitHub: {github_url}")
                return DataManager.load_csv_from_url(github_url)

            # If we're not using hybrid mode and file doesn't exist locally
            logger.warning(f"CSV file not found: {file_path} and not using hybrid mode")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    @staticmethod
    def load_csv_from_url(url):
        """Load CSV from URL."""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return pd.read_csv(
                    pd.io.common.StringIO(response.text), encoding="utf-8"
                )
            logger.error(f"Failed to fetch CSV: {url}, Status: {response.status_code}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading CSV from URL: {e}")
            return pd.DataFrame()

    @staticmethod
    def load_data():
        """Load main apartment data."""
        try:
            url = AppConfig.get_github_url("cian_data", "cian_apartments.csv")
            df = DataManager.load_csv_from_url(url)
            if df.empty:
                return pd.DataFrame(), "Data file not found"

            # Get update time
            update_time = DataManager._extract_update_time()

            return df, update_time
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return pd.DataFrame(), f"Error: {e}"

    @staticmethod
    def _extract_update_time():
        """Extract update time from metadata."""
        try:
            meta_url = AppConfig.get_github_url(
                "cian_data", "cian_apartments.meta.json"
            )
            response = requests.get(meta_url)

            if response.status_code == 200:
                metadata = response.json()
                update_time_str = metadata.get("last_updated", "Unknown")
                try:
                    dt = pd.to_datetime(update_time_str)
                    dt = dt.replace(tzinfo=MOSCOW_TZ)
                    return dt.strftime("%d.%m.%Y %H:%M:%S") + " (МСК)"
                except:
                    return update_time_str
            return "Unknown"
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return "Unknown"

    @staticmethod
    def process_data(df):
        """Process dataframe with all transformations."""
        if df.empty:
            return df

        df["offer_id"] = df["offer_id"].astype(str)

        # Apply all transformations
        DataManager._apply_transformations(df)

        # Sort by status and distance
        df["sort_key"] = df["status"].apply(lambda x: 1 if x == "active" else 2)
        df = df.sort_values(["sort_key", "distance_sort"], ascending=[True, True])

        if "sort_key" in df.columns:
            df = df.drop(columns="sort_key")

        return df

    @staticmethod
    def _apply_transformations(df):
        """Apply all data transformations."""
        # Process links
        base_url = CONFIG["base_url"]
        df["address"] = df.apply(
            lambda r: f"[{r['address']}]({base_url}{r['offer_id']}/)", axis=1
        )
        df["offer_link"] = df["offer_id"].apply(lambda x: f"[View]({base_url}{x}/)")
        df["address_title"] = df.apply(
            lambda r: f"[{r['address']}]({base_url}{r['offer_id']}/)<br>{r['title']}",
            axis=1,
        )

        # Process metrics
        df["distance_sort"] = pd.to_numeric(df["distance"], errors="coerce")
        df["distance"] = df["distance_sort"].apply(
            lambda x: f"{x:.2f} km" if pd.notnull(x) else ""
        )

        # Process dates
        now = datetime.now(MOSCOW_TZ)
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

        # Calculate days active
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

        # Combined date for sorting
        if "updated_time_sort" in df.columns:
            df["date_sort_combined"] = df["updated_time_sort"]

        # Format financial info
        DataManager._process_financial_info(df)

        # Create display columns
        DataManager._create_display_columns(df)

    @staticmethod
    def _process_financial_info(df):
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

        '''# Format price changes
        if "price_change_value" in df.columns:
            df["price_change_formatted"] = df["price_change_value"].apply(
                TagFormatter.format_price_change_tag
            )'''

    @staticmethod
    def _create_display_columns(df):
        """Create combined display columns."""
        # Use standardized column formatters
        if all(
            col in df.columns for col in ["price_value_formatted", "price_change_value"]
        ):
            df["price_text"] = df.apply(ColumnFormatter.format_price_column, axis=1)

        if "distance_sort" in df.columns:
            df["property_tags"] = df.apply(ColumnFormatter.format_property_tags, axis=1)

        if "price_change_formatted" in df.columns:
            df["price_change"] = df["price_change_formatted"]


        df["update_title"] = df.apply(ColumnFormatter.format_update_title, axis=1)


    @staticmethod
    def filter_and_sort_data(df, filters=None, sort_by=None):
        """Filter and sort data in a single function."""
        if df.empty:
            return df

        # Apply filters
        if filters:
            # Price filter
            if (
                (price_value := filters.get("price_value"))
                and price_value != float("inf")
                and "price_value" in df.columns
            ):
                df = df[df["price_value"] <= price_value]

            # Distance filter
            if (
                (distance_value := filters.get("distance_value"))
                and distance_value != float("inf")
                and "distance_sort" in df.columns
            ):
                df = df[df["distance_sort"] <= distance_value]

            # Special filters
            if filters.get("nearest") and "distance_sort" in df.columns:
                df = df[df["distance_sort"] < 1.5]

            if filters.get("below_estimate") and "price_difference_value" in df.columns:
                df = df[df["price_difference_value"] >= 5000]

            if filters.get("inactive") and "status" in df.columns:
                df = df[df["status"] == "active"]

            if filters.get("updated_today") and "updated_time_sort" in df.columns:
                recent_time = pd.Timestamp.now(MOSCOW_TZ) - pd.Timedelta(hours=24)
                df = df[df["updated_time_sort"] > recent_time]

            # Apply sorting from filters
            if "sort_column" in filters and "sort_direction" in filters:
                sort_column = filters["sort_column"]
                if sort_column in df.columns:
                    df = df.sort_values(
                        sort_column, ascending=filters["sort_direction"] == "asc"
                    )
                elif "price_value" in df.columns:
                    df = df.sort_values("price_value", ascending=True)

        # Apply sorting from sort_by parameter
        elif sort_by:
            for item in sort_by:
                col = CONFIG["columns"]["sort_map"].get(
                    item["column_id"], item["column_id"]
                )
                if col in df.columns:
                    df = df.sort_values(col, ascending=item["direction"] == "asc")

        return df

def load_apartment_details(offer_id):
    """Load details for a specific apartment."""
    data_dir = AppConfig.get_cian_data_path()
    apartment_data = {"offer_id": offer_id}

    # Define files to check
    files_to_check = [
        ("price_history.csv", "price_history"),
        ("stats.csv", "stats"),
        ("features.csv", "features"),
        ("rental_terms.csv", "terms"),
        ("apartment_details.csv", "apartment"),
        ("building_details.csv", "building"),
    ]

    for filename, group_name in files_to_check:
        try:
            filepath = os.path.join(data_dir, filename)
            df = DataManager.load_csv_safely(filepath)

            if not df.empty and "offer_id" in df.columns:
                df["offer_id"] = df["offer_id"].astype(str)
                filtered_df = df[df["offer_id"] == str(offer_id)]

                if not filtered_df.empty:
                    apartment_data[group_name] = (
                        filtered_df.to_dict("records")
                        if group_name == "price_history"
                        else filtered_df.iloc[0].to_dict()
                    )
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")

    return apartment_data