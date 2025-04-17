# app/data_manager.py
import pandas as pd
import os
import logging
import traceback
import requests
from datetime import datetime
import re
from app.formatters import DateFormatter, NumberFormatter
from app.config import CONFIG, MOSCOW_TZ
from app.app_config import AppConfig
from app.columns import ColumnFormatter

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


class DataLoader:
    """Handles loading data from various sources."""

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
                return DataLoader.load_csv_from_url(github_url)

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
            df = DataLoader.load_csv_from_url(url)
            if df.empty:
                return pd.DataFrame(), "Data file not found"

            # Get update time
            update_time = DataLoader._extract_update_time()

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
                df = DataLoader.load_csv_safely(filepath)

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


class DataValidator:
    """Centralizes all data validation operations."""
    
    @staticmethod
    def prepare_data(df):
        """Comprehensive preparation of the dataframe.
        This handles all validation, type conversion, and preparation
        before any actual data processing."""
        if df.empty:
            return df
            
        # Convert types
        df = DataValidator.convert_types(df)
        
        # Ensure dates have proper timezones
        df = DataValidator.ensure_date_timezones(df)
        
        # Create validation maps directly
        df = DataValidator.create_validation_maps(df)
        
        return df
        
    @staticmethod
    def convert_types(df):
        """Convert columns to proper data types."""
        # Convert IDs to string
        if "offer_id" in df.columns:
            df["offer_id"] = df["offer_id"].astype(str)
            
        # Convert numeric fields
        numeric_columns = ["distance", "price_value", "cian_estimation_value", "price_change_value"]
        for col in numeric_columns:
            if col in df.columns:
                df[f"{col}_sort"] = pd.to_numeric(df[col], errors="coerce")
                
        # Convert date fields
        date_columns = ["updated_time", "unpublished_date", "activity_date"]
        for col in date_columns:
            if col in df.columns:
                df[f"{col}_sort"] = pd.to_datetime(df[col], errors="coerce")
                
        return df
        
    @staticmethod
    def ensure_date_timezones(df):
        """Ensure all date columns have proper timezone information."""
        date_columns = [col for col in df.columns if col.endswith('_sort') and pd.api.types.is_datetime64_any_dtype(df[col])]
        
        for col in date_columns:
            df[col] = df[col].apply(
                lambda x: DateFormatter.ensure_timezone(x) if pd.notnull(x) else None
            )
            
        return df
        
    @staticmethod
    def create_validation_maps(df):
        """Create validation maps for columns that need validation.
        This creates reusable validation masks to avoid repeating validation logic.
        """
        # Validate numeric columns
        numeric_columns = [
            "price_value", 
            "cian_estimation_value", 
            "distance",
            "area",
            "room_count",
            "floor",
            "total_floors",
            "price_change_value"
        ]
        
        # Create validation maps for numeric columns
        for col in numeric_columns:
            if col in df.columns:
                df[f"{col}_valid"] = df[col].apply(NumberFormatter.is_numeric)
                
        # Create combined validation for price calculations
        if all(col in df.columns for col in ["price_value_valid", "cian_estimation_value_valid"]):
            df["price_estimation_valid"] = df["price_value_valid"] & df["cian_estimation_value_valid"]
            
        # Create active status masks
        if "status" in df.columns:
            df["is_active"] = df["status"] == "active"
            df["is_non_active"] = df["status"] == "non active"
            
        return df


class DataProcessor:
    """Handles data processing, transformation, and feature extraction."""
    
    @staticmethod
    def process_data(df):
        """Process dataframe with all transformations."""
        if df.empty:
            return df

        # Get configuration
        base_url = CONFIG["base_url"]
        now = datetime.now(MOSCOW_TZ)
        
        # Prepare and validate the dataframe
        df = DataValidator.prepare_data(df)
        
        # Extract structured data from title
        df = DataProcessor.extract_title_data(df)
            
        # Format metrics for display
        df = DataProcessor.format_metrics(df)
            
        # Format dates for display
        df = DataProcessor.format_dates_for_display(df)
        
        # Calculate activity time
        df = DataProcessor.calculate_days_active(df, now)
        df = DataProcessor.calculate_hours_active(df, now)
        df = DataProcessor.apply_active_time_formatting(df)
        
        # Combined date for sorting
        if "updated_time_sort" in df.columns:
            df["date_sort_combined"] = df["updated_time_sort"]
            
        # Process financial info
        df = DataProcessor.process_financial_info(df)
        
        # Apply formatting for display
        df = ColumnFormatter.apply_display_formatting(df, base_url)

        return df
    
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
    def format_metrics(df):
        """Format metrics for display."""
        # Format distance
        if "distance_sort" in df.columns:
            df["distance"] = df["distance_sort"].apply(
                lambda x: f"{x:.2f} km" if pd.notnull(x) else ""
            )
            
        return df
        
    @staticmethod
    def format_dates_for_display(df):
        """Format dates for display."""
        for col_base in ["updated_time", "unpublished_date", "activity_date"]:
            col_sort = f"{col_base}_sort"
            if col_base in df.columns and col_sort in df.columns:
                df[col_base] = df[col_sort].apply(
                    lambda x: DateFormatter.format_date(x) if pd.notnull(x) else "--"
                )
        
        return df
        
    @staticmethod
    def calculate_days_active(df, now):
        """Calculate days active for listings."""
        if not all(col in df.columns for col in ["updated_time_sort", "status"]):
            return df
            
        # Initialize days_active_value column with NaN
        df["days_active_value"] = pd.NA
            
        # Calculate days for active listings
        active_mask = (df["status"] == "active") & df["updated_time_sort"].notna()
        if active_mask.any():
            df.loc[active_mask, "days_active_value"] = df.loc[active_mask, "updated_time_sort"].apply(
                lambda dt: (now - dt).days
            )
            
        # Calculate days for non-active listings
        non_active_mask = (
            (df["status"] == "non active") & 
            df["updated_time_sort"].notna() & 
            df["unpublished_date_sort"].notna()
        )
        if non_active_mask.any():
            df.loc[non_active_mask, "days_active_value"] = df.loc[non_active_mask].apply(
                lambda r: (r["unpublished_date_sort"] - r["updated_time_sort"]).days,
                axis=1
            )
            
        return df
        
    @staticmethod
    def calculate_hours_active(df, now):
        """Calculate hours active for listings with less than 1 day active."""
        if not all(col in df.columns for col in ["updated_time_sort", "status", "days_active_value"]):
            return df
            
        # Initialize hours_active_value column with NaN
        df["hours_active_value"] = pd.NA
            
        # Only calculate hours for entries with 0 days
        zero_days_mask = df["days_active_value"] == 0
        
        # Calculate hours for active listings with 0 days
        active_zero_days = zero_days_mask & (df["status"] == "active") & df["updated_time_sort"].notna()
        if active_zero_days.any():
            df.loc[active_zero_days, "hours_active_value"] = df.loc[active_zero_days, "updated_time_sort"].apply(
                lambda dt: int((now - dt).total_seconds() // 3600)
            )
            
        # Calculate hours for non-active listings with 0 days
        non_active_zero_days = (
            zero_days_mask & 
            (df["status"] == "non active") & 
            df["updated_time_sort"].notna() &
            df["unpublished_date_sort"].notna()
        )
        if non_active_zero_days.any():
            df.loc[non_active_zero_days, "hours_active_value"] = df.loc[non_active_zero_days].apply(
                lambda r: int((r["unpublished_date_sort"] - r["updated_time_sort"]).total_seconds() // 3600),
                axis=1
            )
            
        return df
    
    @staticmethod
    def apply_active_time_formatting(df):
        """Apply formatting to active time values using ColumnFormatter."""
        if "days_active_value" not in df.columns:
            return df
            
        # Use the formatter from ColumnFormatter
        df["days_active"] = df.apply(
            lambda r: ColumnFormatter.format_active_time(
                r["days_active_value"], r.get("hours_active_value")
            ), 
            axis=1
        )
        
        return df
    
    @staticmethod
    def process_financial_info(df):
        """Process financial information."""
        # Format price columns
        price_cols = ["price_value", "cian_estimation_value"]
        for col in price_cols:
            if col not in df.columns:
                continue
                
            # Initialize with default value
            df[f"{col}_formatted"] = "--"
            
            # Get valid mask for this column
            valid_mask = f"{col}_valid"
            
            if valid_mask in df.columns and df[valid_mask].any():
                df.loc[df[valid_mask], f"{col}_formatted"] = df.loc[df[valid_mask], col].apply(
                    NumberFormatter.format_number
                )

        # Calculate price difference
        if not all(col in df.columns for col in price_cols):
            return df
            
        # Initialize with default value
        df["price_difference_value"] = 0
        
        # Use the valid masks for both price and estimation
        if "price_estimation_valid" in df.columns and df["price_estimation_valid"].any():
            valid_mask = df["price_estimation_valid"]
            df.loc[valid_mask, "price_difference_value"] = (
                df.loc[valid_mask, "cian_estimation_value"].astype(int) - 
                df.loc[valid_mask, "price_value"].astype(int)
            )
        
        return df


class DataFilterSorter:
    """Handles data filtering and sorting operations."""
    
    @staticmethod
    def apply_sorting(df):
        """Apply default sorting to the dataframe."""
        if df.empty:
            return df
            
        # Create sorting key based on status
        if "status" in df.columns:
            df["sort_key"] = df["status"].apply(lambda x: 1 if x == "active" else 2)
            
            # Sort by status first, then by distance
            if "distance_sort" in df.columns:
                df = df.sort_values(["sort_key", "distance_sort"], ascending=[True, True])
            else:
                df = df.sort_values("sort_key", ascending=True)
                
            # Remove temporary sort key
            df = df.drop(columns="sort_key")
            
        return df

    @staticmethod
    def filter_and_sort_data(df, filters=None, sort_by=None):
        """Filter and sort data based on provided criteria."""
        if df.empty:
            return df

        # Apply filters if provided
        if filters:
            # Price filter
            if price_value := filters.get("price_value"):
                if price_value != float("inf") and "price_value" in df.columns:
                    df = df[df["price_value"] <= price_value]

            # Distance filter
            if distance_value := filters.get("distance_value"):
                if distance_value != float("inf") and "distance_sort" in df.columns:
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
                df = df.sort_values(
                    sort_column, ascending=filters["sort_direction"] == "asc"
                )

        # Apply sorting from sort_by parameter
        elif sort_by:
            for item in sort_by:
                col = CONFIG["columns"]["sort_map"].get(
                    item["column_id"], item["column_id"]
                )
                df = df.sort_values(col, ascending=item["direction"] == "asc")

        return df


class DataManager:
    """Main interface for data operations, coordinating between other classes."""
    
    @staticmethod
    def load_and_process_data():
        """Load, process, and prepare data for display."""
        # Load the data
        df, update_time = DataLoader.load_data()
        
        if df.empty:
            return df, update_time
            
        # Process the data
        processed_df = DataProcessor.process_data(df)
        
        # Apply default sorting
        sorted_df = DataFilterSorter.apply_sorting(processed_df)
        
        return sorted_df, update_time
        
    @staticmethod
    def filter_data(df, filters=None, sort_by=None):
        """Apply filters and sorting to the data."""
        return DataFilterSorter.filter_and_sort_data(df, filters, sort_by)
        
    @staticmethod
    def get_apartment_details(offer_id):
        """Get details for a specific apartment."""
        return DataLoader.load_apartment_details(offer_id)
        
        
def load_apartment_details(offer_id):
    """Legacy function for backward compatibility."""
    return DataManager.get_apartment_details(offer_id)