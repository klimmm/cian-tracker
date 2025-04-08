import re, os, json, time, logging, traceback
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import numpy as np
from distance import get_coordinates, calculate_distance

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("CianScraper")


def parse_updated_time(time_str):
    """Parse the update time string from Cian format to datetime"""
    if not time_str:
        return ""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    months = {
        "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "июн": 6,
        "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
    }
    try:
        if "сегодня" in time_str.lower():
            h, m = map(int, time_str.split(", ")[1].split(":"))
            return today.replace(hour=h, minute=m).strftime("%Y-%m-%d %H:%M:%S")
        elif "вчера" in time_str.lower() and ", " in time_str:
            h, m = map(int, time_str.split(", ")[1].split(":"))
            return (today - timedelta(days=1)).replace(hour=h, minute=m).strftime("%Y-%m-%d %H:%M:%S")
        elif any(x in time_str.lower() for x in ["минут", "секунд"]):
            now = datetime.now()
            if "минут" in time_str.lower():
                min = int(re.search(r"(\d+)\s+минут", time_str).group(1))
                return (now - timedelta(minutes=min)).strftime("%Y-%m-%d %H:%M:%S")
            else:
                sec = int(re.search(r"(\d+)\s+секунд", time_str).group(1))
                return (now - timedelta(seconds=sec)).strftime("%Y-%m-%d %H:%M:%S")
        elif ", " in time_str and any(m in time_str.lower() for m in months.keys()):
            date_part, time_part = time_str.split(", ")
            day = int(re.search(r"(\d+)", date_part).group(1))
            month = next((n for name, n in months.items() if name in date_part.lower()), None)
            if not month:
                return time_str
            h, m = map(int, time_part.split(":"))
            year = today.year
            dt = datetime(year, month, day, h, m)
            if dt > datetime.now() + timedelta(days=1):
                dt = dt.replace(year=year - 1)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return time_str


def extract_price_value(price_str):
    """Extract numeric value from price string"""
    if not price_str:
        return None
    if isinstance(price_str, (int, float)):
        return float(price_str)
    digits = re.sub(r"[^\d]", "", str(price_str))
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


class CianScraper:
    def __init__(self, headless=True, csv_filename="cian_apartments.csv", reference_address="Москва, переулок Большой Саввинский, 3"):
        # Initialize browser options
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        # Core attributes
        self.url_base = "https://www.cian.ru"
        self.driver = None
        self.apartments = []
        self.unpublished_data = []
        self.csv_filename = csv_filename
        self.reference_address = reference_address
        
        # Load existing data
        self.existing_data = {}
        self.existing_df = None
        self._load_existing_data()

    def __enter__(self):
        self.driver = webdriver.Chrome(options=self.chrome_options)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()

    def _load_existing_data(self):
        """Load existing data for comparison and merging"""
        if os.path.exists(self.csv_filename):
            try:
                self.existing_df = pd.read_csv(self.csv_filename, encoding="utf-8", comment="#")
                for _, row in self.existing_df.iterrows():
                    offer_id = str(row.get("offer_id", ""))
                    if offer_id:
                        self.existing_data[offer_id] = row.to_dict()
                
                logger.info(f"Loaded {len(self.existing_data)} existing entries")
            except Exception as e:
                logger.error(f"Error loading data: {e}")
                self.existing_data = {}
                self.existing_df = pd.DataFrame()

    def scrape(self, search_url, max_pages=5, max_distance_km=3, time_filter=None):
        """Main method to scrape and process apartments data from Cian"""
        logger.info(f"Starting scrape process with max_pages={max_pages}, max_distance={max_distance_km}km")
        
        # Apply time filter if provided
        url = search_url if time_filter is None else f"{search_url}&totime={time_filter * 60}"
        
        # Phase 1: Collect basic data from search pages
        all_apts = self._collect_listings(url, max_pages)
        collected_ids = {apt["offer_id"] for apt in all_apts if "offer_id" in apt}
        
        if not all_apts:
            logger.warning("No apartments found!")
            return []
            
        # Phase 2: Calculate distances for all apartments
        self._process_distances(all_apts)
        within_distance, outside_distance = self._filter_by_distance(all_apts, max_distance_km)
        
        # Phase 3: Determine update strategy and process updates
        full_updates, estimation_updates, keep_as_is = self._classify_updates(within_distance, outside_distance)
        self._process_updates(full_updates, estimation_updates, keep_as_is)
        
        # Phase 4: Check for unpublished listings
        self._check_for_unpublished_listings(collected_ids)
        
        # Phase 5: Final processing and saving
        self._finalize_data()
        
        return self.apartments

    def _collect_listings(self, url, max_pages=5):
        """Collect basic apartment data from search results pages"""
        all_apts = []
        seen_ids = set()
        
        with self:
            page = 1
            self.driver.get(url)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-name='CardComponent']"))
                )
            except Exception as e:
                logger.error(f"Timeout loading first page: {e}")
                return []
                
            logger.info("Starting collection of apartment listings")
            while True:
                logger.info(f"Parsing page {page}")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(1.5)
                
                # Parse current page
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                offers = soup.find("div", {"data-name": "Offers"})
                if not offers:
                    logger.warning("No offers container found")
                    break
                    
                cards = offers.find_all("article", {"data-name": "CardComponent"})
                if not cards:
                    logger.warning(f"No apartment cards on page {page}")
                    break
                    
                logger.info(f"Found {len(cards)} cards on page {page}")
                
                # Check for pagination issues
                current_page_ids = set()
                for card in cards:
                    if link := card.select_one("a[href*='/rent/flat/']"):
                        url = link.get("href")
                        if m := re.search(r"/rent/flat/(\d+)/", url):
                            current_page_ids.add(m.group(1))
                
                new_ids = current_page_ids - seen_ids
                if not new_ids and page > 1:
                    logger.warning("No new listings found. Possible pagination issue.")
                    break
                
                # Parse apartment cards
                for card in cards:
                    data = self._parse_card(card)
                    if not data or "offer_id" not in data or not data["offer_id"]:
                        continue
                        
                    id = data["offer_id"]
                    if id in seen_ids:
                        continue
                    
                    # Copy existing distance if available
                    if id in self.existing_data and "distance" in self.existing_data[id]:
                        data["distance"] = self.existing_data[id]["distance"]
                    
                    # Set default status as active
                    data["status"] = "active"
                    data["unpublished_date"] = "--"
                    
                    seen_ids.add(id)
                    all_apts.append(data)
                
                # Check if we should continue
                if max_pages and page >= max_pages:
                    logger.info(f"Reached max pages ({max_pages})")
                    break
                    
                # Navigate to next page with URL modification
                if not self._go_to_next_page(page):
                    break
                    
                page += 1
            
            logger.info(f"Collected {len(all_apts)} apartments from {page} pages")
            return all_apts

    def _parse_card(self, card):
        """Parse a single apartment card from search results"""
        try:
            data = {
                "offer_id": "", "offer_url": "", "updated_time": "", "title": "",
                "price": "", "cian_estimation": "", "price_info": "", "address": "",
                "metro_station": "", "neighborhood": "", "district": "",
                "description": "", "image_urls": [], "distance": None
            }
            
            # Extract URL and ID
            if link := card.select_one("a[href*='/rent/flat/']"):
                url = link.get("href")
                data["offer_url"] = self.url_base + url if url.startswith("/") else url
                if m := re.search(r"/rent/flat/(\d+)/", url):
                    data["offer_id"] = m.group(1)
            
            # Extract basic data
            if title := card.select_one("[data-mark='OfferTitle']"):
                data["title"] = title.get_text(strip=True)
            if price := card.select_one("[data-mark='MainPrice']"):
                data["price"] = price.get_text(strip=True)
            if price_info := card.select_one("[data-mark='PriceInfo']"):
                data["price_info"] = price_info.get_text(strip=True)
            
            # Extract location info
            if metro := card.select_one("div[data-name='SpecialGeo']"):
                text = metro.get_text(strip=True)
                data["metro_station"] = text.split("мин")[0].strip() if "мин" in text else text
                
            loc_elems = card.select("a[data-name='GeoLabel']")
            if len(loc_elems) > 3:
                data["metro_station"] = loc_elems[3].get_text(strip=True)
            if len(loc_elems) > 2:
                data["neighborhood"] = loc_elems[2].get_text(strip=True)
            if len(loc_elems) > 1:
                data["district"] = loc_elems[1].get_text(strip=True)
                
            street = loc_elems[4].get_text(strip=True) if len(loc_elems) > 4 else ""
            building = loc_elems[5].get_text(strip=True) if len(loc_elems) > 5 else ""
            data["address"] = f"{street}, {building}".strip(", ")
            
            # Extract description and time
            if desc := card.select_one("div[data-name='Description'] p"):
                data["description"] = desc.get_text(strip=True)
            if time_el := card.select_one("div[data-name='TimeLabel'] div._93444fe79c--absolute--yut0v span"):
                data["updated_time"] = parse_updated_time(time_el.get_text(strip=True))
                
            # Extract images
            data["image_urls"] = [
                img.get("src") for img in card.select("img._93444fe79c--container--KIwW4") if img.get("src")
            ]

            return data
        except Exception as e:
            logger.error(f"Error parsing card: {e}")
            return None

    def _go_to_next_page(self, current_page):
        """Navigate to the next page by modifying the URL parameter"""
        try:
            # Get current URL
            current_url = self.driver.current_url
            
            # Create URL for the next page
            next_page = current_page + 1
            if "p=" in current_url:
                # Replace existing page parameter
                next_url = re.sub(r'p=\d+', f'p={next_page}', current_url)
            else:
                # Add page parameter if it doesn't exist
                separator = "&" if "?" in current_url else "?"
                next_url = f"{current_url}{separator}p={next_page}"
            
            # Navigate to the new URL
            logger.info(f"Navigating to page {next_page}: {next_url}")
            self.driver.get(next_url)
            
            # Wait for page to load
            time.sleep(2)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-name='CardComponent']"))
            )
            
            # Check if we have results (to detect last page)
            cards = self.driver.find_elements(By.CSS_SELECTOR, "article[data-name='CardComponent']")
            if not cards:
                logger.info(f"No results on page {next_page}, reached end of listing")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error navigating to page {next_page}: {e}")
            return False

    def _process_distances(self, apartments):
        """Calculate distances for apartments with missing distance values"""
        logger.info("Processing distances...")
        
        try:
            ref_coords = get_coordinates(self.reference_address)
            
            # Track statistics
            preserved = 0
            calculated = 0
            failed = 0
            
            for apt in apartments:
                # Check if we have a valid distance already
                distance = apt.get("distance")
                if distance is not None and distance != "":
                    try:
                        distance_val = float(distance) if isinstance(distance, str) else distance
                        if not np.isnan(distance_val) and not np.isinf(distance_val):
                            apt["distance"] = distance_val
                            preserved += 1
                            continue
                    except (ValueError, TypeError):
                        pass
                
                # Calculate new distance
                try:
                    address = apt.get("address", "")
                    if not address:
                        failed += 1
                        continue
                        
                    full_address = f"Москва, {address}" if "Москва" not in address else address
                    distance_km = calculate_distance(from_point=ref_coords, to_address=full_address)
                    apt["distance"] = round(distance_km, 2)
                    calculated += 1
                    
                except Exception as e:
                    logger.error(f"Error calculating distance: {e}")
                    failed += 1
            
            logger.info(f"Distance processing: {preserved} preserved, {calculated} calculated, {failed} failed")
            
        except Exception as e:
            logger.error(f"Distance calculation error: {e}")

    def _filter_by_distance(self, apartments, max_distance_km):
        """
        Categorize apartments by distance - NOT for filtering them out
        All apartments are kept in the dataset, but those outside distance
        don't get cian_estimation fetched to save processing time
        """
        within = []
        outside = []
        
        for apt in apartments:
            try:
                distance = float(apt.get('distance', float('inf')))
                if distance <= max_distance_km:
                    within.append(apt)
                else:
                    outside.append(apt)
            except (ValueError, TypeError):
                outside.append(apt)
        
        logger.info(f"Distance categorization: {len(within)} within {max_distance_km}km, {len(outside)} outside limit")
        return within, outside

    def _classify_updates(self, within_distance, outside_distance):
        """Determine which apartments need full updates vs. estimation-only updates vs. no updates"""
        full_updates = []        # Apartments that need detail page fetch
        estimation_updates = []  # Apartments that only need estimation fetch
        keep_as_is = []          # Apartments outside distance to keep without fetching details
        
        # Process apartments within distance for full updates or estimation updates
        for apt in within_distance:
            id = apt["offer_id"]
            price = apt.get("price", "")
            
            if id in self.existing_data:
                ex_price = self.existing_data[id].get("price", "")
                ex_price_val = extract_price_value(ex_price)
                cur_price_val = extract_price_value(price)
                
                est = self.existing_data[id].get("cian_estimation", "")
                est_empty = (
                    est is None or est == "" or 
                    (isinstance(est, str) and (est.strip().lower() == "nan" or est.strip() == "")) or
                    (isinstance(est, float) and pd.isna(est))
                )
                
                if ex_price_val != cur_price_val:
                    # Price changed - do full update
                    price_diff = cur_price_val - ex_price_val if ex_price_val and cur_price_val else None
                    if price_diff is not None:
                        apt["price_change"] = f"From {ex_price_val} to {cur_price_val} ({price_diff:+.0f} ₽)"
                        apt["price_change_value"] = price_diff
                    full_updates.append(apt)
                else:
                    # No changes needed but keep the apartment
                    keep_as_is.append(apt)
            else:
                # New apartment - do full update
                apt["price_change_value"] = "new"
                full_updates.append(apt)
        
        # For apartments outside distance, just keep them without fetching details
        # Set a flag to indicate they're outside the distance filter
        for apt in outside_distance:
            apt["outside_distance"] = True
            keep_as_is.append(apt)
        
        logger.info(f"Update classification: {len(full_updates)} full updates, {len(estimation_updates)} estimation updates, {len(keep_as_is)} kept as-is")
        return full_updates, estimation_updates, keep_as_is

    def _process_updates(self, full_updates, estimation_updates, keep_as_is):
        """Process apartment updates based on classification"""
        results = []
        
        # Process full updates
        if full_updates:
            logger.info(f"Processing {len(full_updates)} full updates")
            with ThreadPoolExecutor(max_workers=4) as ex:
                updated_full = list(ex.map(self._fetch_details, full_updates))
            results.extend(updated_full)
            
        # Process estimation-only updates
        if estimation_updates:
            logger.info(f"Processing {len(estimation_updates)} estimation updates")
            with ThreadPoolExecutor(max_workers=4) as ex:
                updated_estimation = list(ex.map(self._fetch_details, estimation_updates))
            
            # For estimation-only updates, update the existing dict with estimation
            for apt in updated_estimation:
                if apt.get("offer_id") and apt.get("cian_estimation"):
                    # Find the original apartment in keep_as_is to update
                    orig_apt = next((a for a in keep_as_is if a.get("offer_id") == apt.get("offer_id")), None)
                    if orig_apt:
                        # Update the estimation in the original dict
                        orig_apt["cian_estimation"] = apt["cian_estimation"]
                        logger.debug(f"Updated estimation for {apt['offer_id']}")
                    else:
                        # If not found, add as minimal update
                        results.append({
                            "offer_id": apt["offer_id"],
                            "cian_estimation": apt["cian_estimation"]
                        })
                        logger.debug(f"Added minimal estimation for {apt['offer_id']}")
        
        # Add apartments that don't need any updates
        if keep_as_is:
            logger.info(f"Adding {len(keep_as_is)} apartments without fetching details")
            # Filter out apartments that were already processed for estimation
            processed_ids = {apt.get("offer_id") for apt in results if apt.get("offer_id")}
            keep_filtered = [apt for apt in keep_as_is if apt.get("offer_id") not in processed_ids]
            results.extend(keep_filtered)
        
        logger.info(f"Update processing complete: {len(results)} total apartments")
        self.apartments = results

    def _fetch_details(self, apt):
        """Fetch additional details for an apartment"""
        if "offer_url" not in apt:
            return apt
            
        url = apt["offer_url"]
        logger.info(f"Getting details: {url}")
        
        # Try to get estimation price
        for attempt in range(1, 4):
            driver = None
            try:
                driver = webdriver.Chrome(options=self.chrome_options)
                driver.get(url)
                time.sleep(1)
                
                positions = [0.5] if attempt == 1 else [0.2, 0.5, 0.8]
                for pos in positions:
                    driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight*{pos});")
                    time.sleep(1)
                    
                selector = "[data-testid='valuation_estimationPrice'] .a10a3f92e9--price--w7ha0 span"
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for el in elements:
                    text = el.text.strip()
                    if text:
                        apt["cian_estimation"] = text
                        return apt
                        
            except Exception as e:
                logger.error(f"Error on attempt {attempt}: {e}")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
        
        return apt

    def _check_for_unpublished_listings(self, collected_ids):
        """Check which existing listings are now unpublished"""
        if not self.existing_data:
            logger.info("No existing data to check for unpublished listings")
            return
            
        # Find IDs that were in existing data but not in current results
        existing_ids = set(self.existing_data.keys())
        missing_ids = existing_ids - collected_ids
        
        if not missing_ids:
            logger.info("No missing listings to check")
            return
            
        logger.info(f"Found {len(missing_ids)} previously listed but now missing IDs. Checking if unpublished...")
        self.unpublished_data = self._check_unpublished_listings(missing_ids)
        
        if self.unpublished_data:
            # Store unpublished IDs for reference during merging
            self.unpublished_ids = {item["offer_id"] for item in self.unpublished_data if "offer_id" in item}
            
            # Add unpublished data to self.apartments - this is the ONLY place we add them
            for item in self.unpublished_data:
                self.apartments.append(item)
                
            logger.info(f"Added {len(self.unpublished_data)} unpublished listings to results")

    def _check_unpublished_listings(self, missing_ids):
        """Check if missing listings have been unpublished"""
        unpublished_data = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            # Submit tasks for all missing IDs
            for id in missing_ids:
                if id not in self.existing_data or "offer_url" not in self.existing_data[id]:
                    continue
                url = self.existing_data[id]["offer_url"]
                futures[executor.submit(self._check_single_unpublished, id, url)] = id
                
            # Process results as they complete
            for future in futures:
                try:
                    result = future.result()
                    if result:
                        unpublished_data.append(result)
                except Exception as e:
                    logger.error(f"Error checking unpublished status: {e}")
                    
        logger.info(f"Found {len(unpublished_data)} unpublished listings out of {len(missing_ids)} missing IDs")
        return unpublished_data
        
    def _check_single_unpublished(self, id, url):
        """Check if a single listing has been unpublished with retry mechanism"""
        logger.info(f"Checking unpublished status for ID {id}: {url}")
        
        max_retries = 3
        base_delay = 2  # Base delay in seconds
        
        for attempt in range(1, max_retries + 1):
            driver = None
            try:
                driver = webdriver.Chrome(options=self.chrome_options)
                driver.get(url)
                time.sleep(1)
                
                # Check if listing is unpublished
                unpublished_divs = driver.find_elements(By.XPATH, 
                    "//div[@data-name='OfferUnpublished' and contains(text(), 'Объявление снято с публикации')]")
                
                if unpublished_divs:
                    # Get the update date
                    date_spans = driver.find_elements(
                        By.XPATH, 
                        "//span[contains(text(), 'Обновлено:')]"
                    )
                    
                    unpublished_date = "--"
                    if date_spans:
                        date_text = date_spans[0].text
                        if "Обновлено:" in date_text:
                            unpublished_date = date_text.replace("Обновлено:", "").strip()
                            # Convert to standard format
                            unpublished_date = parse_updated_time(unpublished_date)
                    
                    # Create data entry with unpublished status
                    data = self.existing_data[id].copy()
                    data["status"] = "non active"
                    data["unpublished_date"] = unpublished_date
                    
                    logger.info(f"Listing {id} is unpublished, date: {unpublished_date}")
                    return data
                else:
                    logger.info(f"Listing {id} is missing but not marked as unpublished")
                    return None
                    
            except Exception as e:
                if attempt < max_retries:
                    # Calculate delay with exponential backoff
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(f"Attempt {attempt}/{max_retries} failed for ID {id}: {e}")
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_retries} attempts failed for ID {id}: {e}")
                    # On final attempt failure, mark as non-active with a note about connection issues
                    if id in self.existing_data:
                        data = self.existing_data[id].copy()
                        data["status"] = "non active"
                        data["unpublished_date"] = f"-- (connection error on {datetime.now().strftime('%Y-%m-%d')})"
                        logger.info(f"Marking {id} as non-active due to persistent connection errors")
                        return data
                    return None
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
        
        return None

    def _finalize_data(self):
        """Perform final data processing and save results"""
        logger.info("Finalizing data...")
        
        # If we have no new data, return existing data
        if not self.apartments and self.existing_df is not None and not self.existing_df.empty:
            self.apartments = self.existing_df.to_dict("records")
            logger.info("No new data, using existing data")
            return self.apartments
            
        try:
            # Convert to DataFrame for easier processing
            if not self.apartments:
                logger.warning("No data to process")
                return []
                
            # Convert to DataFrame, handling serialization of complex objects
            apt_dicts = []
            for apt in self.apartments:
                # Ensure status field is set (default to "active" if not set or empty)
                if "status" not in apt or not apt["status"]:
                    apt["status"] = "active"
                    
                # Ensure unpublished_date is set (default to "--" if not set or empty)
                if "unpublished_date" not in apt or not apt["unpublished_date"]:
                    apt["unpublished_date"] = "--"
                    
                # Ensure price_change_formatted is set if price_change_value is present
                if "price_change_value" in apt and apt.get("price_change_value") not in ["", None]:
                    # If it's a new listing, set appropriate format
                    if apt.get("price_change_value") == "new":
                        apt["price_change_formatted"] = "new"
                        apt["price_change"] = ""
                    # If it's a numeric value, format it
                    elif isinstance(apt.get("price_change_value"), (int, float)) or str(apt.get("price_change_value")).replace(".", "", 1).isdigit():
                        try:
                            price_diff = float(apt.get("price_change_value"))
                            if not apt.get("price_change") or apt.get("price_change") == "nan":
                                # Format price change text if not already set
                                # We don't have original prices, so use a simpler format
                                apt["price_change"] = f"Изменение цены: {price_diff:+,.0f} ₽".replace(",", " ")
                                
                            if not apt.get("price_change_formatted") or apt.get("price_change_formatted") == "nan":
                                # Format the display value
                                if price_diff >= 0:
                                    apt["price_change_formatted"] = f"{int(price_diff):,}".replace(",", " ") + " ₽/мес."
                                else:
                                    apt["price_change_formatted"] = f"-{int(abs(price_diff)):,}".replace(",", " ") + " ₽/мес."
                        except:
                            # If conversion fails, set empty strings
                            if not apt.get("price_change") or apt.get("price_change") == "nan":
                                apt["price_change"] = ""
                            if not apt.get("price_change_formatted") or apt.get("price_change_formatted") == "nan":
                                apt["price_change_formatted"] = ""
                
                # Pre-process complex types before creating DataFrame
                apt_dict = {}
                for k, v in apt.items():
                    if isinstance(v, (list, dict, np.ndarray)):
                        try:
                            apt_dict[k] = json.dumps(v, ensure_ascii=False)
                        except:
                            apt_dict[k] = str(v)
                    else:
                        apt_dict[k] = v
                apt_dicts.append(apt_dict)
                
            current_df = pd.DataFrame(apt_dicts)
            logger.info(f"Created DataFrame with {len(current_df)} rows and {len(current_df.columns)} columns")
            
            # Ensure consistent ID format
            if "offer_id" in current_df.columns:
                current_df["offer_id"] = current_df["offer_id"].astype(str)
                
            # Merge with existing data
            if self.existing_df is not None and not self.existing_df.empty:
                merged_df = self._merge_dataframes(current_df, self.existing_df)
            else:
                merged_df = current_df
                
            # Perform calculations
            merged_df = self._calculate_fields(merged_df)
            
            # Final check to ensure all required fields have values
            for field in ["status", "unpublished_date"]:
                if field in merged_df.columns:
                    # Fill empty values with defaults
                    if field == "status":
                        merged_df[field] = merged_df[field].fillna("active").replace("", "active")
                    elif field == "unpublished_date":
                        merged_df[field] = merged_df[field].fillna("--").replace("", "--")
            
            # Sort by status (active first) and then by update time
            if "updated_time" in merged_df.columns:
                merged_df["updated_time"] = pd.to_datetime(
                    merged_df["updated_time"],
                    format="%Y-%m-%d %H:%M:%S",
                    errors="coerce"
                )
                # Create a sort key (1 for active, 2 for non-active)
                merged_df["sort_key"] = merged_df["status"].apply(
                    lambda x: 1 if x == "active" else 2
                )
                merged_df = merged_df.sort_values(["sort_key", "updated_time"], ascending=[True, False])
                merged_df = merged_df.drop(columns=["sort_key"])
                
            # Remove duplicates
            merged_df = merged_df.drop_duplicates(subset=["offer_id"], keep="first")
            
            # Save results
            self.apartments = merged_df.to_dict("records")
            self._save_data()
            
            return self.apartments
            
        except Exception as e:
            logger.error(f"Error in _finalize_data: {e}")
            logger.error(traceback.format_exc())
            # Return whatever we have so far
            return self.apartments or []

    def _merge_dataframes(self, current_df, existing_df):
        """Merge current and existing data, preserving existing values unless specific conditions are met"""
        logger.info("Merging with existing data...")
        
        # Ensure consistent ID format
        existing_df["offer_id"] = existing_df["offer_id"].astype(str)
        current_df["offer_id"] = current_df["offer_id"].astype(str)
        
        # Create output dataframe starting with existing data
        merged_df = existing_df.copy()
        
        # Ensure required columns exist with appropriate datatypes
        if "price_change" not in merged_df.columns:
            merged_df["price_change"] = ""
        if "price_change_formatted" not in merged_df.columns:
            merged_df["price_change_formatted"] = ""
        if "price_change_value" not in merged_df.columns:
            merged_df["price_change_value"] = ""
        
        # Convert price_change fields to object dtype to avoid compatibility issues
        merged_df["price_change"] = merged_df["price_change"].astype(object)
        merged_df["price_change_formatted"] = merged_df["price_change_formatted"].astype(object)
        
        # Stats for logging
        stats = {
            "total_ids": len(set(current_df["offer_id"])),
            "preserved": 0,
            "price_updated": 0,
            "estimation_updated": 0,
            "new_added": 0,
            "unpublished_preserved": 0
        }
        
        # Extract unpublished listings from current_df
        unpublished_entries = current_df[current_df["status"] == "non active"]
        unpublished_ids = set(unpublished_entries["offer_id"])
        
        if unpublished_ids:
            logger.info(f"Found {len(unpublished_ids)} unpublished listings in current data")
            
            # Update or add each unpublished listing to merged_df
            for _, unpub_row in unpublished_entries.iterrows():
                id = unpub_row["offer_id"]
                # Find if this ID exists in merged_df
                match_idx = merged_df[merged_df["offer_id"] == id].index
                
                if len(match_idx) > 0:
                    # Update existing entry with unpublished status
                    logger.info(f"Updating status for {id} to non active with date {unpub_row.get('unpublished_date', '--')}")
                    merged_df.loc[match_idx[0], "status"] = "non active"
                    merged_df.loc[match_idx[0], "unpublished_date"] = unpub_row.get("unpublished_date", "--")
                else:
                    # Add new entry
                    logger.info(f"Adding new unpublished listing {id}")
                    merged_df = pd.concat([merged_df, pd.DataFrame([unpub_row.to_dict()])], ignore_index=True)
                    
            stats["unpublished_preserved"] = len(unpublished_ids)
        
        # Process current data (excluding unpublished listings which we've already handled)
        for idx, row in current_df[~current_df["offer_id"].isin(unpublished_ids)].iterrows():
            try:
                id = str(row.get("offer_id", ""))
                if not id:
                    logger.warning(f"Row at index {idx} has no offer_id, skipping")
                    continue
                
                # Find matching record in merged_df
                match_idx = merged_df[merged_df["offer_id"] == id].index
                
                if len(match_idx) > 0:
                    match_row = merged_df.loc[match_idx[0]]
                    
                    # Compare prices
                    ex_price_val = extract_price_value(match_row.get("price", ""))
                    cur_price_val = extract_price_value(row.get("price", ""))
                    price_changed = False
                    
                    # Check price change only if both values are valid
                    if ex_price_val is not None and cur_price_val is not None:
                        price_changed = ex_price_val != cur_price_val
                        logger.info(f"Checking price change for {id}: {ex_price_val} -> {cur_price_val}, changed: {price_changed}")
                    
                    # Check if estimation was missing before and is now present
                    old_est = match_row.get("cian_estimation", "")
                    new_est = row.get("cian_estimation", "")
                    old_est_empty = (
                        old_est is None or old_est == "" or
                        (isinstance(old_est, str) and old_est.strip().lower() in ["", "nan"]) or
                        (isinstance(old_est, float) and pd.isna(old_est))
                    )
                    new_est_present = (
                        new_est and isinstance(new_est, str) and new_est.strip().lower() not in ["", "nan"]
                    )
                    estimation_filled = old_est_empty and new_est_present
                    
                    # Make decision about updating
                    if price_changed or estimation_filled:
                        update_msg = []
                        
                        # Create a list of fields to update
                        fields_to_update = []
                        
                        # Handle price change
                        if price_changed:
                            update_msg.append(f"price changed from {ex_price_val} to {cur_price_val}")
                            stats["price_updated"] += 1
                            
                            # Calculate price difference
                            price_diff = cur_price_val - ex_price_val
                            
                            # Format the price change values
                            price_change_text = f"From {ex_price_val:,.0f} to {cur_price_val:,.0f} ({price_diff:+,.0f} ₽)"
                            price_change_text = price_change_text.replace(",", " ")
                            
                            if price_diff >= 0:
                                formatted = f"{int(price_diff):,}".replace(",", " ") + " ₽/мес."
                            else:
                                formatted = f"-{int(abs(price_diff)):,}".replace(",", " ") + " ₽/мес."
                            
                            # Store these for later use
                            price_change_fields = {
                                "price_change": price_change_text,
                                "price_change_value": float(price_diff),
                                "price_change_formatted": formatted
                            }
                            
                            logger.info(f"  • Will update price_change to '{price_change_text}'")
                            logger.info(f"  • Will update price_change_value to {price_diff}")
                            logger.info(f"  • Will update price_change_formatted to '{formatted}'")
                        
                        # Handle estimation update
                        if estimation_filled:
                            update_msg.append(f"estimation added: {new_est}")
                            stats["estimation_updated"] += 1
                        
                        logger.info(f"Updating {id} — {', '.join(update_msg)}")
                        
                        # Update values in merged_df, excluding price_change fields which we'll handle separately
                        exclude_fields = {"price_change", "price_change_value", "price_change_formatted", "status", "unpublished_date"}
                        
                        for col in row.index:
                            if col in merged_df.columns and col not in exclude_fields:
                                old_val = merged_df.loc[match_idx[0], col]
                                new_val = row[col]
                                
                                # Skip empty values for numeric columns to avoid dtype warning
                                if isinstance(old_val, (int, float)) and (new_val == "" or pd.isna(new_val)):
                                    logger.debug(f"  • {id}: Skipping empty value for numeric column {col}")
                                    continue
                                    
                                if str(old_val) != str(new_val):  # Convert to string for comparison
                                    logger.info(f"  • {id}: Updated {col} from '{old_val}' to '{new_val}'")
                                    merged_df.loc[match_idx[0], col] = new_val
                        
                        # Now update price_change fields if there was a price change
                        if price_changed:
                            for field, value in price_change_fields.items():
                                merged_df.loc[match_idx[0], field] = value
                                logger.info(f"  • {id}: Finally set {field} to '{value}'")
                    else:
                        # No changes needed - preserve existing data
                        logger.debug(f"No update needed for {id} - preserving existing data")
                        stats["preserved"] += 1
                else:
                    # Add new record - make sure it has price_change fields
                    row_dict = row.to_dict()
                    
                    # Set price_change_value to "new" for new listings
                    if "price_change_value" not in row_dict or not row_dict["price_change_value"]:
                        row_dict["price_change_value"] = "new"
                    if "price_change_formatted" not in row_dict or not row_dict["price_change_formatted"]:
                        row_dict["price_change_formatted"] = "new"
                        
                    # Add new record
                    logger.info(f"Adding new record {id}")
                    merged_df = pd.concat([merged_df, pd.DataFrame([row_dict])], ignore_index=True)
                    stats["new_added"] += 1
                    
            except Exception as e:
                logger.error(f"Error merging row with id {row.get('offer_id', 'unknown')}: {e}")
                logger.error(traceback.format_exc())
        
        # Double-check all unpublished listings are correctly marked
        if unpublished_ids:
            for id in unpublished_ids:
                idx = merged_df[merged_df['offer_id'] == id].index
                if len(idx) > 0:
                    current_status = merged_df.loc[idx[0], 'status']
                    if current_status != 'non active':
                        logger.warning(f"Fixing status for {id}: was {current_status}, setting to non active")
                        
                        # Find the original unpublished entry to get the date
                        unpub_row = unpublished_entries[unpublished_entries['offer_id'] == id]
                        if len(unpub_row) > 0:
                            unpub_date = unpub_row.iloc[0].get('unpublished_date', '--')
                        else:
                            unpub_date = '--'
                            
                        merged_df.loc[idx[0], 'status'] = 'non active'
                        merged_df.loc[idx[0], 'unpublished_date'] = unpub_date
        
        # Remove duplicates
        pre_dedup_count = len(merged_df)
        merged_df = merged_df.drop_duplicates(subset=["offer_id"], keep="first")
        post_dedup_count = len(merged_df)
        if pre_dedup_count != post_dedup_count:
            logger.warning(f"Removed {pre_dedup_count - post_dedup_count} duplicate entries")
        
        # Log summary statistics
        logger.info("Merge statistics:")
        logger.info(f"  • Total IDs processed: {stats['total_ids']}")
        logger.info(f"  • Preserved without changes: {stats['preserved']}")
        logger.info(f"  • Updated due to price change: {stats['price_updated']}")
        logger.info(f"  • Updated with new estimation: {stats['estimation_updated']}")
        logger.info(f"  • New listings added: {stats['new_added']}")
        logger.info(f"  • Unpublished listings preserved: {stats['unpublished_preserved']}")
        logger.info(f"Merged data contains {len(merged_df)} apartments")
        
        return merged_df

    def _calculate_fields(self, df):
        """Calculate derived fields"""
        logger.info("Calculating derived fields...")
        
        # Calculate price difference only for apartments that have both price and estimation
        if all(col in df.columns for col in ["price", "cian_estimation"]):
            df["price_value"] = df["price"].apply(extract_price_value)
            df["estimation_value"] = df["cian_estimation"].apply(extract_price_value)
            
            # Calculate difference
            df["price_difference_value"] = df.apply(
                lambda x: x["estimation_value"] - x["price_value"] 
                if pd.notna(x["estimation_value"]) and pd.notna(x["price_value"]) 
                else None, 
                axis=1
            )
            
            # Format difference
            df["price_difference"] = df["price_difference_value"].apply(
                lambda x: f"{'{:,}'.format(int(x)).replace(',', ' ')} ₽/мес." if pd.notna(x) else ""
            )
            
            # Clean up temporary columns
            df = df.drop(columns=["price_value", "estimation_value"], errors="ignore")
        
        # Calculate days active
        if "updated_time" in df.columns:
            now = datetime.now()
            df["updated_time_dt"] = pd.to_datetime(df["updated_time"], errors="coerce")
            # Convert to Int64 dtype which supports both integers and NaN values
            df["days_active"] = pd.to_numeric(
                df["updated_time_dt"].apply(
                    lambda x: (now - x).days if pd.notna(x) else None
                ), 
                downcast='integer'
            )
            df = df.drop(columns=["updated_time_dt"], errors="ignore")
            logger.warning(f"days active unique values {df['days_active'].unique()}")

        # Ensure status columns are present
        if "status" not in df.columns:
            df["status"] = "active"
        if "unpublished_date" not in df.columns:
            df["unpublished_date"] = "--"
            
        # Add flag for apartments outside distance filter
        if "outside_distance" in df.columns:
            non_numeric = df[~df["outside_distance"].apply(lambda x: isinstance(x, (int, float)))]
            logger.warning(f"Non-numeric 'outside_distance' entries: {non_numeric[['offer_id', 'outside_distance']].to_dict('records')}")
            outside_count = pd.to_numeric(df["outside_distance"], errors="coerce").fillna(0).astype(int).sum()
            if outside_count > 0:
                logger.info(f"Dataset includes {outside_count} apartments outside distance filter")
        
        return df
                    
    def _save_data(self):
        """Save data to CSV and JSON files"""
        if not self.apartments:
            logger.warning("No data to save")
            return
            
        # Convert to DataFrame
        df = pd.DataFrame(self.apartments)
        
        # Determine columns to save
        priority_cols = [
            "offer_id", "offer_url", "title", "updated_time", "price_change",
            "days_active", "price", "cian_estimation", "price_difference",
            "price_difference_value", "price_info", "address", "metro_station",
            "neighborhood", "district", "description", "status", "unpublished_date"
        ]
        
        cols = [c for c in priority_cols if c in df.columns]
        for c in df.columns:
            if c not in cols and c != "image_urls":
                cols.append(c)
        
        df_save = df[cols].copy()
        
        # Handle special data types
        for c in df_save.columns:
            df_save[c] = df_save[c].apply(
                lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict, np.ndarray)) else
                x.strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, pd.Timestamp) else x
            )
        
        # Save to CSV with metadata
        try:
            with open(self.csv_filename + ".tmp", "w", encoding="utf-8") as f:
                update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"# last_updated={update_time},record_count={len(df_save)}\n")
                df_save.to_csv(f, index=False, encoding="utf-8")
            os.replace(self.csv_filename + ".tmp", self.csv_filename)
            logger.info(f"Saved to {self.csv_filename}: {len(df_save)} entries")
        except Exception as e:
            logger.error(f"CSV save error: {e}")
        
        # Save to JSON - convert Timestamp objects to strings
        try:
            json_filename = "cian_apartments.json"
            json_data = []
            
            for apt in self.apartments:
                apt_dict = {}
                for k, v in apt.items():
                    if isinstance(v, pd.Timestamp):
                        apt_dict[k] = v.strftime("%Y-%m-%d %H:%M:%S")
                    elif isinstance(v, (np.int64, np.float64)):
                        apt_dict[k] = float(v) if isinstance(v, np.float64) else int(v)
                    else:
                        apt_dict[k] = v
                json_data.append(apt_dict)
            
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            logger.info(f"Saved to {json_filename}")
        except Exception as e:
            logger.error(f"JSON save error: {e}")




if __name__ == "__main__":
    # Example usage
    csv_file = "cian_apartments.csv"
    base_url = "https://www.cian.ru/cat.php?currency=2&deal_type=rent&district%5B0%5D=13&district%5B1%5D=21&engine_version=2&maxprice=100000&metro%5B0%5D=4&metro%5B10%5D=86&metro%5B11%5D=115&metro%5B12%5D=118&metro%5B13%5D=120&metro%5B14%5D=134&metro%5B15%5D=143&metro%5B16%5D=151&metro%5B17%5D=159&metro%5B18%5D=310&metro%5B1%5D=8&metro%5B2%5D=12&metro%5B3%5D=18&metro%5B4%5D=20&metro%5B5%5D=33&metro%5B6%5D=46&metro%5B7%5D=56&metro%5B8%5D=63&metro%5B9%5D=80&offer_type=flat&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1&room9=1&type=4"
    
    # Create scraper and run full workflow with a single call
    scraper = CianScraper(headless=True, csv_filename=csv_file)
    apartments = scraper.scrape(
        search_url=base_url,
        max_pages=20,
        max_distance_km=5
    )
    
    print(f"Total apartments processed: {len(apartments)}")