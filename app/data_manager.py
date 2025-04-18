# app/data_manager.py
from collections import deque
import threading
import concurrent.futures

import logging
import base64
import requests
import os
import time
from app.app_config import AppConfig
from app.data_loader import DataLoader
from app.data_processor import DataProcessor

logger = logging.getLogger(__name__)


class ImageLoader:
    """Efficient apartment image processing with enhanced FIFO caching."""
    _image_cache = {}
    # ─── Use deque for FIFO ordering ───────────────────────────────────────
    _preloading_queue = deque()
    _currently_preloading = False

    @classmethod
    def preload_images_for_apartments(cls, apartment_ids, limit=10):
        """Preload images for multiple apartments in parallel, in FIFO order."""
        if not apartment_ids:
            return

        # Enqueue up to `limit` IDs in the order received
        for aid in apartment_ids[:limit]:
            if aid not in cls._preloading_queue:
                cls._preloading_queue.append(aid)

        # If already preloading, just return (new IDs remain in the deque)
        if cls._currently_preloading:
            logger.debug(f"Already preloading; queue length now {len(cls._preloading_queue)}")
            return

        cls._currently_preloading = True

        def preload_worker():
            start_time = time.time()
            total_loaded = 0
            apartments_processed = 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                while cls._preloading_queue:
                    try:
                        # Pop up to 3 oldest IDs for this batch
                        batch = []
                        for _ in range(3):
                            if not cls._preloading_queue:
                                break
                            offer_id = cls._preloading_queue.popleft()
                            if offer_id in cls._image_cache:
                                continue
                            batch.append(offer_id)

                        if not batch:
                            continue

                        futures = {
                            executor.submit(cls._preload_apartment_images, oid): oid
                            for oid in batch
                        }
                        for future in concurrent.futures.as_completed(futures):
                            oid = futures[future]
                            try:
                                result = future.result()
                                apartments_processed += 1
                                total_loaded += len(result)
                            except Exception as e:
                                logger.error(f"Error preloading images for {oid}: {e}")
                    except Exception as e:
                        logger.error(f"Error in preload worker: {e}")

            cls._currently_preloading = False
            elapsed = time.time() - start_time
            logger.info(f"Image preloading done in {elapsed:.2f}s: "
                        f"{apartments_processed} apartments, {total_loaded} images")

        thread = threading.Thread(target=preload_worker, daemon=True)
        thread.start()

    
    @classmethod
    def _preload_apartment_images(cls, offer_id):
        """
        Preload images for a single apartment, checking local assets first,
        then falling back to GitHub if none are found locally.
        """
        # 1) Try local assets directory first
        images = cls._get_images_from_local(offer_id)
        if images:
            cls._image_cache[offer_id] = images
            return images

        # 2) Fallback to GitHub if local assets are missing
        images = cls._get_images_from_github(offer_id)
        if images:
            cls._image_cache[offer_id] = images
            return images

        # 3) No images found anywhere
        return []
    
    @staticmethod
    def _get_images_from_local(offer_id):
        """Get images from local filesystem efficiently."""
        image_dir = AppConfig.get_images_path(str(offer_id))
        if not os.path.exists(image_dir):
            return []

        # Find and encode jpg files
        image_paths = []
        jpg_files = sorted(
            f for f in os.listdir(image_dir) if f.lower().endswith(".jpg")
        )

        for file in jpg_files:
            try:
                file_path = os.path.join(image_dir, file)
                # Only read if file exists and is not empty
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    with open(file_path, "rb") as image_file:
                        encoded = base64.b64encode(image_file.read()).decode()
                        image_paths.append(f"data:image/jpeg;base64,{encoded}")
            except Exception as e:
                logger.error(f"Error encoding image {file}: {e}")

        return image_paths

    @staticmethod
    def _get_images_from_github(offer_id):
        """Get images from GitHub repository with optimized requests."""
        image_paths = []

        # Use efficient parallel loading
        def fetch_image(idx):
            try:
                image_url = AppConfig.get_github_url("images", str(offer_id), f"{idx}.jpg")
                response = requests.get(image_url, timeout=5)
                if response.status_code == 200:
                    encoded = base64.b64encode(response.content).decode()
                    return f"data:image/jpeg;base64,{encoded}"
                return None
            except Exception:
                return None

        # Check first image to see if any exist
        first_image = fetch_image(1)
        if not first_image:
            return []
            
        # Add first image
        image_paths.append(first_image)
        
        # Load remaining images in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_image, i): i for i in range(2, 11)}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    image_paths.append(result)

        return image_paths
    
    @classmethod
    def get_apartment_images(cls, offer_id):
        """Get images for an apartment with efficient caching."""
        # Check cache first
        if offer_id in cls._image_cache:
            return cls._image_cache[offer_id]
            
        # Load images
        images = cls._preload_apartment_images(offer_id)
        return images


class DataManager:
    """Main interface for data operations with centralized processing."""
    
    # Cache of detail data
    _detail_cache = {}
    _main_data_fields = {}
    _preload_status = {"status": "not_started", "files_loaded": 0, "total_files": 6}
    
    @classmethod
    def load_and_process_data(cls):
        """Load, process, and prepare data for display."""
        # Load the data using centralized DataLoader
        df, update_time = DataLoader.load_main_apartment_data()
        
        if df.empty:
            return df, update_time
            
        # Process the data
        processed_df = DataProcessor.process_data(df)
        
        # Cache important fields for quick access
        if not processed_df.empty and "offer_id" in processed_df.columns:
            # Convert offer_id to string for consistent matching
            processed_df["offer_id"] = processed_df["offer_id"].astype(str)
            
            # Important fields to cache
            important_fields = [
                "offer_id", 
                "cian_estimation_value_formatted", 
                "price_value_formatted",
                "title", 
                "description", 
                "address_title",
                "metro_station",
                "distance"
            ]
            
            # Keep only available important fields
            available_fields = [f for f in important_fields if f in processed_df.columns]
            if available_fields:
                fields_df = processed_df[available_fields].copy()
                
                # Create a dictionary keyed by offer_id for fast lookup
                cls._main_data_fields = fields_df.set_index("offer_id").to_dict("index")
                
                logger.info(f"Cached main data fields for {len(cls._main_data_fields)} apartments")
        
        return processed_df, update_time
    
    @classmethod
    def get_apartment_images(cls, offer_id):
        """Get images for a specific apartment."""
        return ImageLoader.get_apartment_images(offer_id)
    
    @classmethod
    def get_apartment_details(cls, offer_id):
        """Get details for a specific apartment with caching."""
        # Check cache first
        str_offer_id = str(offer_id)
        if str_offer_id in cls._detail_cache:
            logger.debug(f"Using cached details for apartment {offer_id}")
            return cls._detail_cache[str_offer_id]
        
        # Create base data with offer ID
        apartment_data = {"offer_id": offer_id}
        
        # Add main data fields first if available
        if str_offer_id in cls._main_data_fields:
            # Add all preloaded main data fields
            apartment_data.update(cls._main_data_fields[str_offer_id])
            logger.debug(f"Added main data fields for apartment {offer_id}")
        
        # Load detailed data from centralized loader
        detailed_data = DataLoader.load_apartment_details(offer_id)
        
        # Merge the data
        apartment_data.update(detailed_data)
        
        # Cache for future use
        cls._detail_cache[str_offer_id] = apartment_data
        
        return apartment_data
    
    @classmethod
    def preload_detail_files(cls):
        """Preload all apartment detail files in background."""
        logger.info("Starting background preload of apartment detail files...")
        
        # Use thread to avoid blocking
        def background_loader():
            try:
                status = DataLoader.preload_detail_files()
                cls._preload_status = status
            except Exception as e:
                logger.error(f"Background loading error: {e}")
                cls._preload_status["status"] = "error"
                
        # Start background loading thread
        thread = threading.Thread(target=background_loader)
        thread.daemon = True
        thread.start()
        
        return {"status": "loading_started"}
    
    @classmethod
    def get_preload_status(cls):
        """Get current preload status."""
        return cls._preload_status