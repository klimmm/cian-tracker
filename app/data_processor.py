# app/data_processor.py
import pandas as pd
import logging
from datetime import datetime
import re
from app.formatters import DateFormatter, NumberFormatter
from app.config import CONFIG, MOSCOW_TZ
from app.columns import ColumnFormatter

logger = logging.getLogger(__name__)


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