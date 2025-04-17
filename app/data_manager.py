# app/data_manager.py
import pandas as pd
import os
import logging
import traceback
import requests
import base64
from app.config import MOSCOW_TZ
from app.app_config import AppConfig
from app.data_processor import DataProcessor
logger = logging.getLogger(__name__)



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



class ImageLoader:
    """Efficient apartment image processing with enhanced presentation."""

    # Initialize class variables properly
    _image_cache = {}
    _preloading_queue = set()
    _currently_preloading = False
    
    @classmethod
    def preload_images_for_apartments(cls, apartment_ids, limit=10):
        """Preload images for multiple apartments in parallel."""
        if not apartment_ids:
            return
            
        # Limit the number of apartments to preload
        apartment_ids = apartment_ids[:limit]
        #logger.debug(f"🔄 IMAGE PRELOAD: Starting for {len(apartment_ids)} apartments: {apartment_ids}")
        
        # Add to preloading queue
        cls._preloading_queue.update(apartment_ids)
        
        # If already preloading, just return (the new IDs will be picked up)
        if cls._currently_preloading:
            logger.debug(f"🔄 IMAGE PRELOAD: Already in progress, added {len(apartment_ids)} to queue")
            return
            
        import concurrent.futures
        import time
        cls._currently_preloading = True
        
        # Use ThreadPoolExecutor for parallel loading
        def preload_worker():
            start_time = time.time()
            total_loaded = 0
            apartments_processed = 0
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                while cls._preloading_queue:
                    try:
                        # Get next batch of apartments to preload (up to 3)
                        batch = []
                        for _ in range(3):
                            if cls._preloading_queue:
                                batch.append(cls._preloading_queue.pop())
                            else:
                                break
                        
                        # Skip any that are already cached
                        cached_ids = [offer_id for offer_id in batch if offer_id in cls._image_cache]
                        if cached_ids:
                            logger.debug(f"🔄 IMAGE PRELOAD: Skipping already cached apartments: {cached_ids}")
                            
                        batch = [offer_id for offer_id in batch if offer_id not in cls._image_cache]
                        
                        if not batch:
                            continue
                            
                        #logger.info(f"🔄 IMAGE PRELOAD: Starting batch: {batch}")
                        
                        # Submit preload tasks
                        futures = {executor.submit(cls._preload_apartment_images, offer_id): offer_id for offer_id in batch}
                        
                        # Process as they complete
                        for future in concurrent.futures.as_completed(futures):
                            offer_id = futures[future]
                            try:
                                result = future.result()
                                apartments_processed += 1
                                total_loaded += len(result)
                                #logger.info(f"✅ IMAGE PRELOAD: Apartment {offer_id} - loaded {len(result)} images")
                            except Exception as e:
                                logger.error(f"❌ IMAGE PRELOAD: Error for {offer_id}: {e}")
                    except Exception as e:
                        logger.error(f"❌ IMAGE PRELOAD: Error in worker: {e}")
            
            elapsed = time.time() - start_time
            cls._currently_preloading = False
            #logger.info(f"🏁 IMAGE PRELOAD: Completed in {elapsed:.2f}s - {apartments_processed} apartments, {total_loaded} images")
        
        # Start in background thread
        import threading
        thread = threading.Thread(target=preload_worker)
        thread.daemon = True
        thread.start()
    
    @classmethod
    def _preload_apartment_images(cls, offer_id):
        """Preload images for a single apartment efficiently."""
        import time
        start_time = time.time()
        
        if offer_id in cls._image_cache:
            #logger.info(f"📋 IMAGE CACHE: Using cached images for {offer_id}")
            return cls._image_cache[offer_id]
            
        #logger.info(f"🔍 IMAGE LOAD: Starting for apartment {offer_id}")
        
        # We'll optimize the GitHub loading to be more efficient
        if AppConfig.is_using_github() or AppConfig.should_use_hybrid_for_images():
            #logger.info(f"🌐 IMAGE SOURCE: Trying GitHub for {offer_id}")
            images = cls._get_images_from_github_efficiently(offer_id)
            if images:
                elapsed = time.time() - start_time
                #logger.info(f"✅ IMAGE LOAD: Found {len(images)} images for {offer_id} on GitHub in {elapsed:.2f}s")
                cls._image_cache[offer_id] = images
                return images
                
        # Fall back to local if needed
        if not AppConfig.is_using_github() or AppConfig.should_use_hybrid_for_images():
            #logger.info(f"💻 IMAGE SOURCE: Trying local for {offer_id}")
            images = cls._get_images_from_local(offer_id)
            if images:
                elapsed = time.time() - start_time
                logger.info(f"✅ IMAGE LOAD: Found {len(images)} images for {offer_id} locally in {elapsed:.2f}s")
                cls._image_cache[offer_id] = images
                return images
        
        elapsed = time.time() - start_time        
        #logger.info(f"⚠️ IMAGE LOAD: No images found for {offer_id} in {elapsed:.2f}s")
        return []
    
    @classmethod
    def _get_images_from_github_efficiently(cls, offer_id):
        """Optimized version that loads images in parallel."""
        import time
        start_time = time.time()
        
        github_base = AppConfig.DATA_SOURCE["github"]["base_url"]
        image_dir_url = f"{github_base}images/{offer_id}/"
        image_paths = []
        
        try:
            # Try first image to check if directory exists
            first_image_url = f"{image_dir_url}1.jpg"
            #logger.info(f"🔍 IMAGE CHECK: Testing if images exist at {first_image_url}")
            
            response = requests.head(first_image_url)
            
            if response.status_code != 200:
                #logger.info(f"⚠️ IMAGE CHECK: No images found at {image_dir_url}")
                return []
                
            #logger.info(f"✅ IMAGE CHECK: Found images for {offer_id}, loading in parallel")
            
            # If first image exists, load up to 10 images in parallel
            import concurrent.futures
            urls = [f"{image_dir_url}{i}.jpg" for i in range(1, 11)]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_url = {executor.submit(cls._fetch_image, url, i): i 
                                for i, url in enumerate(urls, 1)}
                
                for future in concurrent.futures.as_completed(future_to_url):
                    idx = future_to_url[future]
                    try:
                        result = future.result()
                        if result:
                            image_paths.append(result)
                    except Exception as e:
                        logger.error(f"❌ IMAGE FETCH: Error with image {idx} for {offer_id}: {e}")
            
            elapsed = time.time() - start_time
            #logger.info(f"🏁 IMAGE GITHUB: Found {len(image_paths)}/10 for {offer_id} in {elapsed:.2f}s")
            return image_paths
        except Exception as e:
            elapsed = time.time() - start_time
            #logger.error(f"❌ IMAGE GITHUB: Error for {offer_id} in {elapsed:.2f}s: {e}")
            return []
    
    @staticmethod
    def _fetch_image(url, idx):
        """Helper method to fetch a single image."""
        import time
        start_time = time.time()
        
        try:
            logger.debug(f"🔄 IMAGE FETCH: Starting image {idx} from {url}")
            response = requests.get(url)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                size_kb = len(response.content) / 1024
                logger.debug(f"✅ IMAGE FETCH: Image {idx} ({size_kb:.1f} KB) loaded in {elapsed:.2f}s")
                encoded = base64.b64encode(response.content).decode()
                return f"data:image/jpeg;base64,{encoded}"
            
            logger.debug(f"⚠️ IMAGE FETCH: Image {idx} not found ({response.status_code}) in {elapsed:.2f}s")
            return None
        except Exception as e:
            elapsed = time.time() - start_time
            logger.debug(f"❌ IMAGE FETCH: Error with image {idx} in {elapsed:.2f}s: {e}")
            return None





    
    @staticmethod
    def get_apartment_images(offer_id):
        """Get images for apartment with optimized fallback strategies."""
        try:
            # Cache for found images
            image_cache = getattr(ImageLoader, "_image_cache", {})
            if offer_id in image_cache:
                return image_cache[offer_id]

            # Try local first in hybrid mode
            if AppConfig.should_use_hybrid_for_images():
                local_images = ImageLoader._get_images_from_local(offer_id)
                if local_images:
                    image_cache[offer_id] = local_images
                    return local_images

                github_images = ImageLoader._get_images_from_github(offer_id)
                if github_images:
                    image_cache[offer_id] = github_images
                    return github_images
                return []

            # Use configured source
            images = (
                ImageLoader._get_images_from_github(offer_id)
                if AppConfig.is_using_github()
                else ImageLoader._get_images_from_local(offer_id)
            )

            # Cache results
            if not hasattr(ImageLoader, "_image_cache"):
                ImageLoader._image_cache = {}
            image_cache[offer_id] = images
            return images
        except Exception as e:
            logger.error(f"Error getting images: {e}")
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
        github_base = AppConfig.DATA_SOURCE["github"]["base_url"]
        image_dir_url = f"{github_base}images/{offer_id}/"
        image_paths = []

        # Check for existence pattern first to reduce request overhead
        try:
            # Try first image to check if directory exists
            first_image_url = f"{image_dir_url}1.jpg"
            response = requests.head(first_image_url)

            if response.status_code != 200:
                return []

            # If first image exists, try the rest
            for i in range(1, 11):
                try:
                    image_url = f"{image_dir_url}{i}.jpg"
                    img_response = requests.get(image_url)
                    if img_response.status_code == 200:
                        encoded = base64.b64encode(img_response.content).decode()
                        image_paths.append(f"data:image/jpeg;base64,{encoded}")
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error fetching GitHub images: {e}")

        return image_paths


class DataManager:
    """Main interface for data operations, coordinating between other classes."""
    
    # Add class variables to store preloaded data and status
    _detail_dataframes = {}
    _preload_status = {"status": "not_started", "files_loaded": 0, "total_files": 6}
    
    @classmethod
    def preload_detail_files(cls):
        """Preload all apartment detail files in background."""
        logger.info("Starting background preload of apartment detail files...")
        data_dir = AppConfig.get_cian_data_path()
        
        # Define files to preload
        files_to_preload = [
            "price_history.csv",
            "stats.csv", 
            "features.csv", 
            "rental_terms.csv", 
            "apartment_details.csv", 
            "building_details.csv"
        ]
        
        cls._preload_status = {
            "status": "in_progress", 
            "files_loaded": 0, 
            "total_files": len(files_to_preload)
        }
        
        # Load all files
        for filename in files_to_preload:
            try:
                filepath = os.path.join(data_dir, filename)
                df = DataLoader.load_csv_safely(filepath)
                if not df.empty and "offer_id" in df.columns:
                    # Convert offer_id to string for consistent matching
                    df["offer_id"] = df["offer_id"].astype(str)
                    cls._detail_dataframes[filename] = df
                    logger.info(f"Preloaded {filename} with {len(df)} rows")
                else:
                    logger.warning(f"File {filename} empty or missing offer_id column")
            except Exception as e:
                logger.error(f"Error preloading {filename}: {e}")
            
            # Update status
            cls._preload_status["files_loaded"] += 1
        
        cls._preload_status["status"] = "completed"
        logger.info(f"Preloading complete. Loaded {len(cls._detail_dataframes)} files")
        return cls._preload_status
    
    @classmethod
    def get_preload_status(cls):
        """Get current preload status."""
        return cls._preload_status
    
    @staticmethod
    def load_and_process_data():
        """Load, process, and prepare data for display."""
        # Load the data
        df, update_time = DataLoader.load_data()
        
        if df.empty:
            return df, update_time
            
        # Process the data
        processed_df = DataProcessor.process_data(df)
        
        return processed_df, update_time
        
    @staticmethod
    def get_apartment_images(offer_id):
        """Get details for a specific apartment."""
        return ImageLoader.get_apartment_images(offer_id)    
        

    @classmethod
    def get_apartment_details(cls, offer_id):
        """Get details for a specific apartment using preloaded data if available."""
        apartment_data = {"offer_id": offer_id}
        
        # Map filenames to their group names in the result
        file_groups = {
            "price_history.csv": "price_history",
            "stats.csv": "stats",
            "features.csv": "features",
            "rental_terms.csv": "terms",
            "apartment_details.csv": "apartment",
            "building_details.csv": "building"
        }
        
        # Try to use preloaded dataframes first
        for filename, group_name in file_groups.items():
            try:
                if filename in cls._detail_dataframes:
                    # Use preloaded data
                    df = cls._detail_dataframes[filename]
                    filtered_df = df[df["offer_id"] == str(offer_id)]
                    
                    if not filtered_df.empty:
                        apartment_data[group_name] = (
                            filtered_df.to_dict("records")
                            if group_name == "price_history"
                            else filtered_df.iloc[0].to_dict()
                        )
                else:
                    # Fall back to loading from file if not preloaded
                    logger.info(f"Data for {filename} not preloaded, loading on demand")
                    data_dir = AppConfig.get_cian_data_path()
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
                            
                            # Cache for future use
                            cls._detail_dataframes[filename] = df
            except Exception as e:
                logger.error(f"Error processing {filename} for offer {offer_id}: {e}")
        
        return apartment_data      
