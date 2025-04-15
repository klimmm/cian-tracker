# app/data_manager.py
import pandas as pd
import os
import logging
import traceback
import requests
from datetime import datetime
from app.formatters import DateFormatter, NumberFormatter
from app.config import CONFIG, MOSCOW_TZ
from app.app_config import AppConfig
from app.columns import ColumnFormatter
import re

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
    def process_data(df):
        """Process dataframe with all transformations."""
        if df.empty:
            return df

        df["offer_id"] = df["offer_id"].astype(str)

        # Apply all transformations
        base_url = CONFIG["base_url"]
        now = datetime.now(MOSCOW_TZ)
        df = ColumnFormatter.apply_transformations(df, base_url, now)

        # Sort by status and distance
        df["sort_key"] = df["status"].apply(lambda x: 1 if x == "active" else 2)
        df = df.sort_values(["sort_key", "distance_sort"], ascending=[True, True])

        if "sort_key" in df.columns:
            df = df.drop(columns="sort_key")

        return df

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
                df["updated_time_sort"] = pd.to_datetime(
                    df["updated_time_sort"], errors="coerce"
                )
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