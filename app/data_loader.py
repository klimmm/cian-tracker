# app/data_loader.py
import pandas as pd
import os
import json
import logging
import traceback
import requests
import time
from typing import Tuple, Optional, Dict, Any
from app.app_config import AppConfig
from app.config import MOSCOW_TZ

logger = logging.getLogger(__name__)


class DataLoader:
    """Centralized data loading with unified CSV handling and caching."""

    # Cached dataframes to avoid reloading
    _dataframe_cache: Dict[str, pd.DataFrame] = {}
    _metadata_cache: Dict[str, Any] = {}
    _last_load_time: Dict[str, float] = {}

    # Cache expiration in seconds (5 minutes)
    CACHE_EXPIRATION = 300

    @classmethod
    def load_csv(cls, filename: str, subdir: str = "cian_data") -> pd.DataFrame:
        """
        Unified method to load CSV with caching and proper source selection.

        Args:
            filename: Name of the CSV file
            subdir: Subdirectory within data_dir or GitHub repo

        Returns:
            DataFrame with the loaded data
        """
        cache_key = f"{subdir}/{filename}"

        # Check if we have a fresh cached version
        current_time = time.time()
        if (
            cache_key in cls._dataframe_cache
            and cache_key in cls._last_load_time
            and current_time - cls._last_load_time[cache_key] < cls.CACHE_EXPIRATION
        ):
            logger.debug(f"Using cached data for {cache_key}")
            return cls._dataframe_cache[cache_key]

        # Determine primary source based on configuration
        use_github_primary = AppConfig.should_use_github_for(filename)
        allow_fallback = AppConfig.should_use_fallback(filename)

        df = pd.DataFrame()
        error_message = None

        # Try primary source first
        if use_github_primary:
            # GitHub as primary
            df, error_message = cls._load_from_github(filename, subdir)
            if df.empty and allow_fallback:
                logger.info(f"Falling back to local for {filename}")
                df, fallback_error = cls._load_from_local(filename, subdir)
                if df.empty:
                    error_message = f"GitHub: {error_message}, Local: {fallback_error}"
        else:
            # Local as primary
            df, error_message = cls._load_from_local(filename, subdir)
            if df.empty and allow_fallback:
                logger.info(f"Falling back to GitHub for {filename}")
                df, fallback_error = cls._load_from_github(filename, subdir)
                if df.empty:
                    error_message = f"Local: {error_message}, GitHub: {fallback_error}"

        # Cache the result if successful
        if not df.empty:
            cls._dataframe_cache[cache_key] = df
            cls._last_load_time[cache_key] = current_time
            logger.info(f"Loaded and cached {cache_key}, {len(df)} rows")
        else:
            logger.warning(f"Failed to load {cache_key}: {error_message}")

        return df

    @classmethod
    def clear_cache(cls, filename: Optional[str] = None, subdir: Optional[str] = None):
        """
        Clear cache for a specific file or all files.

        Args:
            filename: Optional filename to clear
            subdir: Optional subdirectory to clear
        """
        if filename and subdir:
            cache_key = f"{subdir}/{filename}"
            if cache_key in cls._dataframe_cache:
                del cls._dataframe_cache[cache_key]
                logger.info(f"Cleared cache for {cache_key}")
        else:
            cls._dataframe_cache.clear()
            cls._last_load_time.clear()
            logger.info("Cleared all data cache")

    @staticmethod
    def _load_from_local(
        filename: str, subdir: str
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """Load CSV from local filesystem."""
        try:
            file_path = AppConfig.get_path(subdir, filename)
            if not os.path.exists(file_path):
                return pd.DataFrame(), f"File not found at {file_path}"

            logger.info(f"Loading {filename} from local file: {file_path}")
            return pd.read_csv(file_path, encoding="utf-8"), None
        except Exception as e:
            error = f"Error loading {filename} from local: {str(e)}"
            logger.error(error)
            logger.debug(traceback.format_exc())
            return pd.DataFrame(), error

    @staticmethod
    def _load_from_github(
        filename: str, subdir: str
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """Load CSV from GitHub repository."""
        try:
            github_url = AppConfig.get_github_url(subdir, filename)
            logger.info(f"Loading {filename} from GitHub: {github_url}")

            response = requests.get(github_url, timeout=10)
            if response.status_code != 200:
                return pd.DataFrame(), f"HTTP error: {response.status_code}"

            return (
                pd.read_csv(pd.io.common.StringIO(response.text), encoding="utf-8"),
                None,
            )
        except requests.RequestException as e:
            error = f"Request error for {filename} from GitHub: {str(e)}"
            logger.error(error)
            return pd.DataFrame(), error
        except Exception as e:
            error = f"Error loading {filename} from GitHub: {str(e)}"
            logger.error(error)
            logger.debug(traceback.format_exc())
            return pd.DataFrame(), error

    @classmethod
    def load_main_apartment_data(cls) -> Tuple[pd.DataFrame, str]:
        """
        Load main apartment data with update time information.

        Returns:
            Tuple of (DataFrame, update_time_string)
        """
        # Load the main apartments CSV
        df = cls.load_csv("cian_apartments.csv")
        if df.empty:
            return df, "Data file not found"

        # Get metadata for update time
        update_time = cls._get_update_time()

        return df, update_time

    @classmethod
    def _get_update_time(cls) -> str:
        """
        Get the last update time from metadata.

        Returns:
            Formatted update time string
        """
        try:

            github_url = AppConfig.get_github_url(
                "cian_data", "cian_apartments.meta.json"
            )
            logger.info(f"Loading metadata from GitHub: {github_url}")

            response = requests.get(github_url, timeout=10)
            if response.status_code != 200:
                return "Unknown"

            metadata = response.json()
            update_time_str = metadata.get("last_updated", "Unknown")

            # Format the date if possible
            try:
                dt = pd.to_datetime(update_time_str)
                dt = dt.replace(tzinfo=MOSCOW_TZ)
                formatted_time = dt.strftime("%d.%m.%Y %H:%M:%S") + " (МСК)"

                # Cache the result
                cls._metadata_cache["update_time"] = formatted_time
                return formatted_time
            except Exception:
                return update_time_str

        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return "Unknown"

    @classmethod
    def load_apartment_details(cls, offer_id: str) -> Dict[str, Any]:
        """
        Load all details for a specific apartment.

        Args:
            offer_id: The apartment offer ID

        Returns:
            Dictionary with all apartment details
        """
        # Base data structure with offer ID
        apartment_data = {"offer_id": offer_id}

        # Define detail files to load
        detail_files = [
            ("price_history.csv", "price_history"),
            ("stats.csv", "stats"),
            ("features.csv", "features"),
            ("rental_terms.csv", "terms"),
            ("apartment_details.csv", "apartment"),
            ("building_details.csv", "building"),
        ]

        # Load each file and extract relevant data
        for filename, group_name in detail_files:
            try:
                # Load the file
                df = cls.load_csv(filename)

                if not df.empty and "offer_id" in df.columns:
                    # Ensure offer_id is string for consistent comparison
                    df["offer_id"] = df["offer_id"].astype(str)

                    # Filter for this apartment
                    filtered_df = df[df["offer_id"] == str(offer_id)]

                    if not filtered_df.empty:
                        # For price history, keep all records; for others, just take first
                        apartment_data[group_name] = (
                            filtered_df.to_dict("records")
                            if group_name == "price_history"
                            else filtered_df.iloc[0].to_dict()
                        )
            except Exception as e:
                logger.error(f"Error processing {filename} for offer {offer_id}: {e}")

        return apartment_data

    @classmethod
    def preload_detail_files(cls) -> Dict[str, Any]:
        """
        Preload all detail files in the background.

        Returns:
            Status dictionary with loading progress
        """
        logger.info("Starting preload of apartment detail files...")

        # Define files to preload
        files_to_preload = [
            "price_history.csv",
            "stats.csv",
            "features.csv",
            "rental_terms.csv",
            "apartment_details.csv",
            "building_details.csv",
        ]

        status = {
            "status": "in_progress",
            "files_loaded": 0,
            "total_files": len(files_to_preload),
        }

        # Load all files
        for filename in files_to_preload:
            try:
                df = cls.load_csv(filename)
                if not df.empty and "offer_id" in df.columns:
                    # Convert offer_id to string for consistent matching
                    df["offer_id"] = df["offer_id"].astype(str)
                    logger.info(f"Preloaded {filename} with {len(df)} rows")
                else:
                    logger.warning(f"File {filename} empty or missing offer_id column")
            except Exception as e:
                logger.error(f"Error preloading {filename}: {e}")

            # Update status
            status["files_loaded"] += 1

        status["status"] = "completed"
        logger.info(f"Preloading complete. Loaded {status['files_loaded']} files")
        return status
