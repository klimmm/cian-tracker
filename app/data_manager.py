import os
import io
import threading
import logging
import requests
import pandas as pd

from typing import Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
from cachetools import TTLCache
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.app_config import AppConfig
from app.data_processor import DataProcessor
from app.config import MOSCOW_TZ

logger = logging.getLogger(__name__)

# ─── CACHES ──────────────────────────────────────────────────────────────
_success_cache = TTLCache(maxsize=50, ttl=300)  # 5 min for good loads
_failure_cache = TTLCache(maxsize=50, ttl=30)  # 30 s for failures
_cache_lock = threading.RLock()

_detail_cache = TTLCache(maxsize=100, ttl=300)
_detail_cache_lock = threading.RLock()

_metadata_cache = TTLCache(maxsize=10, ttl=600)
_metadata_cache_lock = threading.RLock()


class CSVLoader:
    """Loads CSVs with local↔GitHub fallback and per‑outcome caching."""

    def load(self, filename: str, subdir: str = "cian_data") -> pd.DataFrame:
        key = f"{subdir}/{filename}"
        # 1) fast‐path caches
        with _cache_lock:
            if key in _success_cache:
                return _success_cache[key]
            if key in _failure_cache:
                return _failure_cache[key]

        # 2) actual load
        try:
            df = self._load_primary_then_fallback(filename, subdir)
            # success → cache long‑TTL
            with _cache_lock:
                _success_cache[key] = df
            return df

        except Exception as e:
            logger.warning(f"Failed to load {filename}: {e}")
            # build appropriate empty DataFrame
            if filename == "cian_apartments.csv":
                df = pd.DataFrame(
                    columns=["offer_id", "title", "price", "location", "url"]
                )
            else:
                df = pd.DataFrame()
            # failure → cache short‑TTL
            with _cache_lock:
                _failure_cache[key] = df
            return df

    def _load_primary_then_fallback(self, filename: str, subdir: str) -> pd.DataFrame:
        use_github = AppConfig.should_use_github_for(filename)
        if use_github:
            try:
                return self._load_from_github(filename, subdir)
            except Exception:
                return self._load_from_local(filename, subdir)
        else:
            try:
                return self._load_from_local(filename, subdir)
            except Exception:
                return self._load_from_github(filename, subdir)

    def _load_from_local(self, filename: str, subdir: str) -> pd.DataFrame:
        path = AppConfig.get_path(subdir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        if os.path.getsize(path) == 0 or not os.access(path, os.R_OK):
            raise ValueError(f"Bad local file: {path}")
        df = pd.read_csv(path, encoding="utf-8")
        if df.empty:
            raise ValueError(f"No rows in {path}")
        logger.info(f"Loaded {filename} locally ({len(df)} rows)")
        return df

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.RequestException, IOError)),
    )
    def _load_from_github(self, filename: str, subdir: str) -> pd.DataFrame:
        url = AppConfig.get_github_url(subdir, filename)
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text), encoding="utf-8")
        if df.empty:
            raise ValueError(f"No rows in GitHub file {filename}")
        logger.info(f"Loaded {filename} from GitHub ({len(df)} rows)")
        return df

    def clear_cache(self):
        with _cache_lock:
            _success_cache.clear()
            _failure_cache.clear()
        logger.debug("Cleared CSV caches")


class DetailAssembler:
    DETAIL_FILES = {
        "price_history": ("price_history.csv", True),
        "stats": ("stats.csv", False),
        "features": ("features.csv", False),
        "terms": ("rental_terms.csv", False),
        "apartment": ("apartment_details.csv", False),
        "building": ("building_details.csv", False),
    }

    def __init__(self, csv_loader: CSVLoader, main_fields: Dict[str, Dict] = None):
        self.csv_loader = csv_loader
        self.main_fields = main_fields or {}

    def assemble(self, offer_id: str) -> Dict[str, Any]:
        key = f"detail_{offer_id}"
        with _detail_cache_lock:
            if key in _detail_cache:
                return _detail_cache[key]

        data = {"offer_id": offer_id}
        if offer_id in self.main_fields:
            data.update(self.main_fields[offer_id])

        for group, (fname, is_list) in self.DETAIL_FILES.items():
            try:
                df = self.csv_loader.load(fname, "cian_data")
                if "offer_id" in df:
                    df = df[df["offer_id"].astype(str) == offer_id]
                    if not df.empty:
                        data[group] = (
                            df.to_dict("records") if is_list else df.iloc[0].to_dict()
                        )
            except Exception as e:
                logger.warning(f"{group} load error for {offer_id}: {e}")

        with _detail_cache_lock:
            _detail_cache[key] = data
        return data

    def preload_all(self):
        files = [fname for fname, _ in self.DETAIL_FILES.values()]
        with ThreadPoolExecutor(max_workers=4) as exec:
            for fname in files:
                exec.submit(self.csv_loader.load, fname, "cian_data")
        logger.info("Preloaded all detail files")


class DataManager:
    def __init__(self):
        self.csv_loader = CSVLoader()
        self.processor = DataProcessor()
        self.main_fields = {}
        self.detail_assembler = None


    def get_update_time(self) -> str:
        with _metadata_cache_lock:
            if "update_time" in _metadata_cache:
                return _metadata_cache["update_time"]

        try:
            url = AppConfig.get_github_url("cian_data", "cian_apartments.meta.json")
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            raw = resp.json().get("last_updated", "")
            dt = pd.to_datetime(raw).tz_localize(MOSCOW_TZ)
            val = dt.strftime("%d.%m.%Y %H:%M:%S") + " (МСК)"
        except Exception as e:
            logger.error(f"Metadata load error: {e}")
            val = "Unknown"

        with _metadata_cache_lock:
            _metadata_cache["update_time"] = val
        return val
    # Add to DataManager class
    def update_main_fields_from_df(self, df):
        """Update main_fields from a DataFrame, regardless of source."""
        if "offer_id" in df.columns:
            df = df.copy()  # Avoid modifying the original
            df["offer_id"] = df["offer_id"].astype(str)
            self.main_fields = df.set_index("offer_id").to_dict("index")
            logger.info(f"Updated main_fields with {len(self.main_fields)} entries from {len(df)} rows")
            
            # Clear detail cache and update assembler
            with _detail_cache_lock:
                _detail_cache.clear()
                
            if self.detail_assembler:
                self.detail_assembler.main_fields = self.main_fields
        else:
            logger.warning("No offer_id column in DataFrame, main_fields not updated")
    
    def preload_detail_files(self):
        if not self.detail_assembler:
            self.detail_assembler = DetailAssembler(self.csv_loader, self.main_fields)
            logger.info("Created new detail_assembler with current main_fields")
        else:
            # Ensure it has the latest main_fields reference
            self.detail_assembler.main_fields = self.main_fields
            logger.info("Updated detail_assembler.main_fields reference in preload")
        
        # Start preloading files
        threading.Thread(target=self.detail_assembler.preload_all, daemon=True).start()
    
    def load_and_process_data(self) -> Tuple[pd.DataFrame, str]:
        df = self.csv_loader.load("cian_apartments.csv", "cian_data")
        if df.empty:
            return df, "Data file not found"
    
        processed = self.processor.process_data(df)
        if "offer_id" in processed:
            processed["offer_id"] = processed["offer_id"].astype(str)
            self.main_fields = processed.set_index("offer_id").to_dict("index")
            
            # Update assembler if it exists
            if self.detail_assembler:
                # Clear detail cache before updating the reference
                with _detail_cache_lock:
                    _detail_cache.clear()
                    logger.info("Cleared detail cache for main_fields update")
                
                self.detail_assembler.main_fields = self.main_fields
                logger.info(f"Updated detail_assembler with fresh main_fields containing {len(self.main_fields)} entries")
        else:
            self.main_fields = {}
            
        return processed, self.get_update_time()
    
    def get_apartment_details(self, offer_id: str) -> Dict[str, Any]:
        # Final safety check 
        if not self.detail_assembler:
            logger.warning("detail_assembler was None when get_apartment_details called")
            self.detail_assembler = DetailAssembler(self.csv_loader, self.main_fields)
        elif id(self.detail_assembler.main_fields) != id(self.main_fields):
            # References don't match, update AND clear cache
            logger.warning("detail_assembler.main_fields reference was stale, updating")
            
            # Clear the detail cache to force regeneration with new main_fields
            with _detail_cache_lock:
                _detail_cache.clear()
                logger.info("Cleared detail cache due to stale reference")
                
            self.detail_assembler.main_fields = self.main_fields
            
        # Debug info
        if str(offer_id) in self.main_fields:
            logger.info(f"Main fields for {offer_id} contain {len(self.main_fields[str(offer_id)])} entries")
        else:
            logger.warning(f"Offer ID {offer_id} not found in main_fields dictionary")
            
        return self.detail_assembler.assemble(str(offer_id))
    def clear_cache(self):
        self.csv_loader.clear_cache()
        with _detail_cache_lock:
            _detail_cache.clear()
        with _metadata_cache_lock:
            _metadata_cache.clear()
        logger.debug("Cleared all caches")


data_manager = DataManager()
