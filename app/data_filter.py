# app/data_filter.py - Updated with enhanced logging
import pandas as pd
import logging
from app.config import CONFIG, MOSCOW_TZ

logger = logging.getLogger(__name__)


class DataFilterSorter:
    """Handles data filtering and sorting operations."""
    
    @staticmethod
    def apply_sorting(df):
        """Apply default sorting to the dataframe."""
        logger.info(f"apply_sorting called with dataframe of shape: {df.shape if not df.empty else 'EMPTY'}")
        
        if df.empty:
            logger.warning("apply_sorting received empty dataframe")
            return df
            
        # Create sorting key based on status
        if "status" in df.columns:
            logger.info(f"Creating sort key based on status column, unique values: {df['status'].unique()}")
            df["sort_key"] = df["status"].apply(lambda x: 1 if x == "active" else 2)
            
            # Sort by status first, then by distance
            if "distance_sort" in df.columns:
                logger.info("Sorting by status and distance")
                df = df.sort_values(["sort_key", "distance_sort"], ascending=[True, True])
            else:
                logger.info("Sorting by status only (distance_sort not available)")
                df = df.sort_values("sort_key", ascending=True)
                
            # Remove temporary sort key
            df = df.drop(columns="sort_key")
        else:
            logger.warning("Status column not found in dataframe")
            
        logger.info(f"apply_sorting returning dataframe of shape: {df.shape}")
        return df

    @staticmethod
    def filter_and_sort_data(df, filters=None, sort_by=None):
        """Filter and sort data based on provided criteria."""
        logger.info(f"filter_and_sort_data called with:")
        logger.info(f"  - dataframe shape: {df.shape if not df.empty else 'EMPTY'}")
        logger.info(f"  - filters: {filters}")
        logger.info(f"  - sort_by: {sort_by}")
        
        if df.empty:
            logger.warning("filter_and_sort_data received empty dataframe, returning early")
            return df
    
        # Log available columns
        logger.info(f"Available columns: {list(df.columns)}")
        
        # Add debug information about distance values
        if "distance_sort" in df.columns:
            logger.info(f"Distance stats: min={df['distance_sort'].min()}, max={df['distance_sort'].max()}, mean={df['distance_sort'].mean():.2f}")
            # Get unique values (sample if there are too many)
            unique_distances = sorted(df['distance_sort'].unique())
            sample_size = min(20, len(unique_distances))  # Show at most 20 unique values
            logger.info(f"Sample of {sample_size} unique distance values: {unique_distances[:sample_size]}")
            
            # Also show value counts for better understanding
            value_counts = df['distance_sort'].value_counts().sort_index()
            logger.info(f"Distance value distribution (first 10 entries):\n{value_counts.head(10)}")
        else:
            logger.warning("distance_sort column not found in dataframe")
        
        # If there's a human-readable distance column, check that too
        if "distance" in df.columns:
            logger.info(f"Human-readable distance sample (first 10): {df['distance'].head(10).tolist()}")
        
        df_size_before = len(df)
        
        # Apply filters if provided
        if filters:
            # Price filter
            if price_value := filters.get("price_value"):
                if price_value != float("inf") and "price_value" in df.columns:
                    logger.info(f"Applying price filter: <= {price_value}")
                    df = df[df["price_value"] <= price_value]
                    logger.info(f"After price filter: {len(df)}/{df_size_before} rows remaining")
                else:
                    logger.warning(f"Cannot apply price filter: price_value {'not in columns' if 'price_value' not in df.columns else 'is inf'}")
    
            # Distance filter
            if distance_value := filters.get("distance_value"):
                if distance_value != float("inf") and "distance_sort" in df.columns:
                    logger.info(f"Applying distance filter: <= {distance_value}")
                    # Log the number of rows that would pass the filter
                    passing_rows = (df["distance_sort"] <= distance_value).sum()
                    logger.info(f"Only {passing_rows} rows would pass distance filter <= {distance_value}")
                    df = df[df["distance_sort"] <= distance_value]
                    logger.info(f"After distance filter: {len(df)}/{df_size_before} rows remaining")
                else:
                    logger.warning(f"Cannot apply distance filter: distance_sort {'not in columns' if 'distance_sort' not in df.columns else 'is inf'}")
    
            # Rest of your code...
        
        if df.empty:
            logger.warning("filter_and_sort_data received empty dataframe, returning early")
            return df

        # Log available columns
        logger.info(f"Available columns: {list(df.columns)}")
        df_size_before = len(df)
        
        # Apply filters if provided
        if filters:
            # Price filter
            if price_value := filters.get("price_value"):
                if price_value != float("inf") and "price_value" in df.columns:
                    logger.info(f"Applying price filter: <= {price_value}")
                    df = df[df["price_value"] <= price_value]
                    logger.info(f"After price filter: {len(df)}/{df_size_before} rows remaining")
                else:
                    logger.warning(f"Cannot apply price filter: price_value {'not in columns' if 'price_value' not in df.columns else 'is inf'}")

            # Distance filter
            if distance_value := filters.get("distance_value"):
                if distance_value != float("inf") and "distance_sort" in df.columns:
                    logger.info(f"Applying distance filter: <= {distance_value}")
                    df = df[df["distance_sort"] <= distance_value]
                    logger.info(f"After distance filter: {len(df)}/{df_size_before} rows remaining")
                else:
                    logger.warning(f"Cannot apply distance filter: distance_sort {'not in columns' if 'distance_sort' not in df.columns else 'is inf'}")

            # Special filters
            if filters.get("nearest") and "distance_sort" in df.columns:
                logger.info("Applying nearest filter: < 1.5")
                df = df[df["distance_sort"] < 1.5]
                logger.info(f"After nearest filter: {len(df)}/{df_size_before} rows remaining")
            elif filters.get("nearest"):
                logger.warning("Cannot apply nearest filter: distance_sort not in columns")

            if filters.get("below_estimate") and "price_difference_value" in df.columns:
                logger.info("Applying below_estimate filter: >= 5000")
                df = df[df["price_difference_value"] >= 5000]
                logger.info(f"After below_estimate filter: {len(df)}/{df_size_before} rows remaining")
            elif filters.get("below_estimate"):
                logger.warning("Cannot apply below_estimate filter: price_difference_value not in columns")

            if filters.get("inactive") and "status" in df.columns:
                logger.info("Applying inactive filter: status == active")
                df = df[df["status"] == "active"]
                logger.info(f"After inactive filter: {len(df)}/{df_size_before} rows remaining")
            elif filters.get("inactive"):
                logger.warning("Cannot apply inactive filter: status not in columns")

            if filters.get("updated_today") and "updated_time_sort" in df.columns:
                logger.info("Applying updated_today filter")
                try:
                    df["updated_time_sort"] = pd.to_datetime(df["updated_time_sort"])
                    recent_time = pd.Timestamp.now(MOSCOW_TZ) - pd.Timedelta(hours=24)
                    df = df[df["updated_time_sort"] > recent_time]
                    logger.info(f"After updated_today filter: {len(df)}/{df_size_before} rows remaining")
                except Exception as e:
                    logger.error(f"Error applying updated_today filter: {e}")
            elif filters.get("updated_today"):
                logger.warning("Cannot apply updated_today filter: updated_time_sort not in columns")

            # Apply sorting from filters
            if "sort_column" in filters and "sort_direction" in filters:
                sort_column = filters["sort_column"]
                if sort_column in df.columns:
                    logger.info(f"Sorting by filter column: {sort_column} ({filters['sort_direction']})")
                    df = df.sort_values(
                        sort_column, ascending=filters["sort_direction"] == "asc"
                    )
                else:
                    logger.warning(f"Cannot sort by {sort_column}: column not in dataframe")

        # Apply sorting from sort_by parameter
        elif sort_by:
            for item in sort_by:
                col = CONFIG["columns"]["sort_map"].get(
                    item["column_id"], item["column_id"]
                )
                if col in df.columns:
                    logger.info(f"Sorting by sort_by column: {col} ({item['direction']})")
                    df = df.sort_values(col, ascending=item["direction"] == "asc")
                else:
                    logger.warning(f"Cannot sort by {col}: column not in dataframe")

        logger.info(f"filter_and_sort_data returning dataframe of shape: {df.shape} ({len(df)}/{df_size_before} rows)")
        return df