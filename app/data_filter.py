# app/data_manager.py
import pandas as pd
import logging
from app.config import CONFIG, MOSCOW_TZ

logger = logging.getLogger(__name__)


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
                df["updated_time_sort"] = pd.to_datetime(df["updated_time_sort"])

                
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