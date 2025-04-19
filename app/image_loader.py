import threading
import time
import logging
from collections import deque
import concurrent.futures

import base64
import requests
import os
from app.app_config import AppConfig

logger = logging.getLogger(__name__)


class ImageLoader:
    _image_cache = {}
    _preloading_queue = deque()
    _currently_preloading = False

    @classmethod
    def preload_images_for_apartments(cls, apartment_ids, limit=10):
        if not apartment_ids:
            logger.debug("No apartments to preload.")
            return

        # Enqueue or skip each ID
        for aid in apartment_ids[:limit]:
            if aid in cls._image_cache:
                count = len(cls._image_cache[aid])
                logger.debug(f"Skipping {aid!r}: already in cache ({count} images)")
            elif aid not in cls._preloading_queue:
                logger.debug(f"Enqueueing {aid!r} for preload")
                cls._preloading_queue.append(aid)

        if cls._currently_preloading:
            logger.debug(f"Already preloading; queue length now {len(cls._preloading_queue)}")
            return

        cls._currently_preloading = True

        def preload_worker():
            start_time = time.time()
            apartments_processed = 0
            skip_count = 0
            total_loaded = 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                while cls._preloading_queue:
                    batch = []
                    for _ in range(3):
                        if not cls._preloading_queue:
                            break
                        aid = cls._preloading_queue.popleft()
                        if aid in cls._image_cache:
                            skip_count += 1
                            logger.debug(f"Worker skipping cached {aid!r} ({len(cls._image_cache[aid])} images)")
                            continue
                        batch.append(aid)

                    if not batch:
                        break

                    futures = {executor.submit(cls._preload_apartment_images, aid): aid for aid in batch}
                    for future in concurrent.futures.as_completed(futures):
                        aid = futures[future]
                        try:
                            imgs = future.result()
                            apartments_processed += 1
                            total_loaded += len(imgs)
                        except Exception as e:
                            logger.error(f"Error preloading images for {aid}: {e}")

            cls._currently_preloading = False
            elapsed = time.time() - start_time
            logger.debug(
                f"Image preloading done in {elapsed:.2f}s: "
                f"{apartments_processed} processed, {skip_count} skipped, {total_loaded} new images"
            )

        thread = threading.Thread(target=preload_worker, daemon=True)
        thread.start()

    @classmethod
    def preload_visible_apartments(cls, table_data, page_current=None, page_size=None):
        """
        Preload images for apartments that are visible in the table, with pagination support.
        
        Args:
            table_data (list): List of apartment data rows from the table
            page_current (int, optional): Current page number for pagination
            page_size (int, optional): Page size for pagination
        
        Returns:
            bool: True if preloading was initiated, False otherwise
        """
        # Skip if no data
        if not table_data or len(table_data) == 0:
            logger.debug("No table data available for image preloading")
            return False
        
        # Calculate visible page if pagination is active
        start_idx = 0
        end_idx = 10  # Default to first 10 if pagination not set
        if page_current is not None and page_size is not None:
            start_idx = page_current * page_size
            end_idx = start_idx + page_size
        
        # Ensure end_idx is within bounds
        end_idx = min(end_idx, len(table_data))
        
        # Extract offer_ids from the visible apartments
        visible_apartments = table_data[start_idx:end_idx]
        offer_ids = [
            row.get("offer_id")
            for row in visible_apartments
            if row.get("offer_id")
        ]
        
        if not offer_ids:
            logger.debug("No valid offer IDs found for preloading")
            return False
            
        # Start background thread for preloading in batches
        def background_image_loader():
            try:
                logger.debug(
                    f"🚀 IMAGE PRELOAD: Starting preload of {min(3, len(offer_ids))} visible apartments: {offer_ids[:3]}"
                )
                # Start with just the first 3 for immediate response
                first_batch = offer_ids[:3]
                cls.preload_images_for_apartments(first_batch, limit=3)
                
                # After a brief delay, load the rest
                time.sleep(1)
                
                # Load the next batch
                next_batch = offer_ids[3:]
                if next_batch:
                    logger.debug(
                        f"🚀 IMAGE PRELOAD: Starting second batch of {len(next_batch)} more visible apartments"
                    )
                    cls.preload_images_for_apartments(
                        next_batch, limit=len(next_batch)
                    )
            except Exception as e:
                logger.error(f"❌ IMAGE PRELOAD: Error in background preloader: {e}")
        
        # Start background thread
        logger.debug(
            f"🚀 IMAGE PRELOAD: Initializing preloader for page {page_current}, size {page_size}"
        )
        thread = threading.Thread(target=background_image_loader)
        thread.daemon = True
        thread.start()
        
        return True

    @classmethod
    def _preload_apartment_images(cls, offer_id):
        logger.debug(f"▶ Processing {offer_id!r} (cache miss)")

        # 1) Local
        images = cls._get_images_from_local(offer_id)
        if images:
            logger.debug(f"   ✓ Found {len(images)} LOCAL images for {offer_id!r}")
            cls._image_cache[offer_id] = images
            return images

        logger.debug("   – no local images, falling back to GitHub")
        images = cls._get_images_from_github(offer_id, max_images=5)
        if images:
            logger.debug(f"   ✓ Found {len(images)} GITHUB images for {offer_id!r}")
            cls._image_cache[offer_id] = images
            return images

        logger.debug(f"   ✗ No images found for {offer_id!r}")
        cls._image_cache[offer_id] = []
        return []

    @staticmethod
    def _get_images_from_local(offer_id):
        image_dir = AppConfig.get_images_path(str(offer_id))
        logger.debug(f"Checking local dir: {image_dir}")
        if not os.path.isdir(image_dir):
            logger.debug("   → directory does not exist")
            return []

        valid_ext = (".jpg", ".jpeg", ".png")
        files = sorted(f for f in os.listdir(image_dir) if f.lower().endswith(valid_ext))
        logger.debug(f"   → files found: {files}")
        images = []
        for fname in files:
            path = os.path.join(image_dir, fname)
            try:
                with open(path, "rb") as f:
                    data = base64.b64encode(f.read()).decode()
                images.append(f"data:image/jpeg;base64,{data}")
            except Exception as e:
                logger.error(f"Error encoding {path}: {e}")
        return images

    @staticmethod
    def _get_images_from_github(offer_id, max_images=5):
        images = []
        for idx in range(1, max_images + 1):
            for ext in ("jpg", "jpeg"):
                url = AppConfig.get_github_url("images", str(offer_id), f"{idx}.{ext}")
                logger.debug(f"Trying GitHub URL: {url}")
                try:
                    resp = requests.get(url, timeout=4)
                    logger.debug(f"   → status {resp.status_code}")
                    if resp.status_code == 200:
                        data = base64.b64encode(resp.content).decode()
                        images.append(f"data:image/jpeg;base64,{data}")
                        break
                except Exception as e:
                    logger.error(f"   GitHub fetch error for {url}: {e}")
        return images

    @classmethod
    def get_apartment_images(cls, offer_id):
        if offer_id in cls._image_cache:
            return cls._image_cache[offer_id]
        return cls._preload_apartment_images(offer_id)