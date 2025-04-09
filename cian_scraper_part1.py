import os, re, json, time, logging, random, traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from distance import get_coordinates, calculate_distance
from utils import parse_updated_time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CianScraper')

class CianScraper:
    def __init__(self, headless=True, csv_filename='cian_apartments.csv', 
                 reference_address='Москва, переулок Большой Саввинский, 3',
                 user_agent=None):
        self.chrome_options = Options()
        
        # Always use headless mode by default to prevent browser windows
        # The 'headless' parameter is kept for backward compatibility
        if headless:
            # Use both legacy and new headless mode for maximum compatibility
            self.chrome_options.add_argument('--headless')
            self.chrome_options.add_argument('--headless=new')
        
        # Common Chrome options for stability and invisibility
        for arg in ['--disable-gpu', '--window-size=1920,1080', '--disable-extensions', 
                    '--no-sandbox', '--disable-dev-shm-usage', '--disable-infobars',
                    '--disable-notifications', '--ignore-certificate-errors',
                    '--disable-popup-blocking']:
            self.chrome_options.add_argument(arg)
        
        # Use provided user agent or default one with randomized version
        if not user_agent:
            chrome_version = f"Chrome/{121 + random.randint(0, 5)}.0.{random.randint(7000, 7200)}.{random.randint(40, 99)}"
            user_agent = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) {chrome_version} Safari/537.36'
        
        self.chrome_options.add_argument(f'user-agent={user_agent}')
        
        # Add experimental options to avoid detection
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)

        self.url_base = 'https://www.cian.ru'
        self.csv_filename = csv_filename
        self.reference_address = reference_address
        self.new = self.removed = self.price_changes = 0
        self.existing_data = self._load_existing_data()
        self.session_listings = set()  # Keep track of listings seen in this session

    def _load_existing_data(self):
        if not os.path.exists(self.csv_filename):
            return {}
        try:
            df = pd.read_csv(self.csv_filename, encoding='utf-8', comment='#')
            result = {}
            for _, row in df.iterrows():
                if 'offer_id' in row:
                    entry = row.to_dict()

                    # Initialize new fields if they don't exist
                    if 'price_info' in entry and ('rental_period' not in entry or self._is_empty(entry.get('rental_period'))):
                        price_info = entry.get('price_info', '')
                        parts = [p.strip() for p in str(price_info).split(',')]
                        
                        entry['rental_period'] = '--'
                        entry['utilities_type'] = '--'
                        entry['commission_info'] = '--'
                        entry['deposit_info'] = '--'
                        
                        for p in parts:
                            if p in ['От года', 'На несколько месяцев']: 
                                entry['rental_period'] = p
                            elif 'комм. платежи' in p: 
                                entry['utilities_type'] = p
                            elif 'комиссия' in p or 'без комиссии' in p: 
                                entry['commission_info'] = p
                            elif 'залог' in p or 'без залога' in p: 
                                entry['deposit_info'] = p
                        
                    result[str(row['offer_id'])] = entry
            logger.info(f"Loaded {len(result)} existing listings from {self.csv_filename}")
            return result
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
            return {}

    def _extract_price(self, price):
        if not price:
            return None
        if isinstance(price, (int, float)):
            return float(price)
        try:
            return float(re.sub(r'[^\d]', '', str(price)) or 0)
        except:
            return None

    def _is_empty(self, val):
        return (val is None or val == '' or val == '--' or
                (isinstance(val, str) and (val.strip().lower() in ['nan', 'n/a'] or val.strip() == '')) or
                (isinstance(val, float) and pd.isna(val)))
    
    def _initialize_driver(self, max_retries=3, retry_delay=5):
        """Initialize the Chrome webdriver with retries"""
        for attempt in range(max_retries):
            try:
                # Ensure headless mode is properly enforced
                if self.chrome_options._arguments and '--headless' not in self.chrome_options._arguments:
                    logger.info("Enforcing headless mode to prevent browser window display")
                    self.chrome_options.add_argument('--headless')
                    
                # Additional options to ensure no window appears
                self.chrome_options.add_argument('--headless=new')  # New headless implementation in Chrome
                self.chrome_options.add_argument('--disable-dev-shm-usage')
                self.chrome_options.add_argument('--disable-gpu')
                
                driver = webdriver.Chrome(options=self.chrome_options)
                
                # Execute stealth JS to avoid detection
                driver.execute_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                
                return driver
            except Exception as e:
                logger.error(f"Failed to initialize webdriver (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to initialize webdriver after {max_retries} attempts")
    
    def _load_page(self, driver, url, max_retries=3, retry_delay=5):
        """Load a page with retry mechanism"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Loading URL: {url}")
                driver.get(url)
                
                # Wait for the main content to load
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-name='CardComponent']"))
                )
                return True
            except TimeoutException:
                logger.warning(f"Timeout waiting for page to load (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay * (attempt + 1))  # Increasing backoff
                else:
                    logger.error(f"Failed to load page after {max_retries} attempts")
                    return False
            except WebDriverException as e:
                logger.error(f"WebDriver error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"Failed to load page after {max_retries} attempts")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error loading page (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"Failed to load page after {max_retries} attempts")
                    return False
    
    def _scroll_page(self, driver):
        """Scroll the page to load all content"""
        try:
            # Get the page height
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            # Scroll in increments
            for i in range(5):  # Divide into 5 scrolls
                target_height = last_height * (i + 1) // 5
                driver.execute_script(f"window.scrollTo(0, {target_height});")
                time.sleep(0.5 + random.random())  # Random delay between 0.5-1.5 seconds
            
            # Scroll back to top (sometimes helps with loading)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
            
            return True
        except Exception as e:
            logger.error(f"Error scrolling page: {e}")
            return False
    
    def collect_listings(self, url, max_pages=5, max_retries=3, retry_delay=5):
        all_apts, seen_ids = [], set()
        driver = None
        
        try:
            driver = self._initialize_driver(max_retries, retry_delay)
            page = 1
            pagination_error_count = 0
            max_pagination_errors = 3  # Max consecutive pagination errors before giving up
            duplicate_page_count = 0   # Counter for pages with all duplicate listings
            max_duplicate_pages = 2    # Max number of consecutive pages with all duplicates
            previous_page_ids = set()  # IDs from the previous page
            
            # Track content hash from previous pages to detect repeating content
            last_content_hashes = []
            
            while page <= max_pages:
                logger.info(f'Processing page {page} of {max_pages}')
                
                # Construct the URL for the current page
                current_url = url
                if page > 1:
                    if 'p=' in url:
                        current_url = re.sub(r'p=\d+', f'p={page}', url)
                    else:
                        current_url = f"{url}{'&' if '?' in url else '?'}p={page}"
                
                # Try to load the page
                if not self._load_page(driver, current_url, max_retries, retry_delay):
                    pagination_error_count += 1
                    if pagination_error_count >= max_pagination_errors:
                        logger.error(f"Too many consecutive pagination errors ({pagination_error_count}). Stopping.")
                        break
                    page += 1
                    continue
                
                # Check if we were redirected to a different page number
                try:
                    current_page_url = driver.current_url
                    page_match = re.search(r'[?&]p=(\d+)', current_page_url)
                    if page_match:
                        actual_page = int(page_match.group(1))
                        if actual_page != page:
                            logger.warning(f"Redirected from page {page} to page {actual_page}. This may indicate we've reached the end.")
                            # If we've been redirected to a previous page, we've likely hit the end
                            if actual_page < page:
                                logger.info("Redirected to an earlier page. End of results reached.")
                                break
                except Exception as e:
                    logger.warning(f"Error checking for page redirect: {e}")
                
                # Reset the pagination error count on successful page load
                pagination_error_count = 0
                
                # Scroll to load all content
                self._scroll_page(driver)
                
                # Generate a content hash to detect duplicate pages
                page_content = driver.page_source
                content_hash = hash(page_content)
                
                # Check if this page has the same content as recent pages
                if content_hash in last_content_hashes:
                    logger.warning(f"Page {page} has identical content to a recent page. Possible end of results.")
                    duplicate_page_count += 1
                    if duplicate_page_count >= max_duplicate_pages:
                        logger.info(f"Found {duplicate_page_count} consecutive duplicate pages. End of results reached.")
                        break
                else:
                    duplicate_page_count = 0  # Reset if we found new content
                    
                # Keep track of the last few page hashes
                last_content_hashes.append(content_hash)
                if len(last_content_hashes) > 3:  # Only keep the last 3 hashes
                    last_content_hashes.pop(0)
                
                # Parse the page with BeautifulSoup
                try:
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    cards = soup.select("article[data-name='CardComponent']")
                    
                    if not cards:
                        logger.warning(f"No cards found on page {page}. This might be the last page or a parsing issue.")
                        # Try an alternative selector or check if we're on a no-results page
                        if soup.select_one('.no-results-found') or soup.select_one('.error-page') or soup.select_one('[data-name="EmptyMessage"]'):
                            logger.info("Reached end of results or error page. Stopping.")
                            break
                        
                        # Check if we're on a captcha page
                        if "captcha" in page_content.lower() or "подтвердите" in page_content.lower():
                            logger.error("Detected a CAPTCHA page. The site may have blocked the scraper.")
                            break
                    
                    logger.info(f"Found {len(cards)} cards on page {page}")
                    
                    # Track IDs found on this page
                    current_page_ids = set()
                    new_ids_found = 0
                    
                    # Process each card
                    for card in cards:
                        try:
                            data = self._parse_card(card)
                            if not data or 'offer_id' not in data or not data['offer_id']:
                                continue
                            
                            offer_id = data['offer_id']
                            current_page_ids.add(offer_id)
                            
                            # Skip if we've already seen this ID in this session
                            if offer_id in seen_ids:
                                continue
                            
                            # Count new IDs
                            new_ids_found += 1
                            
                            # Update data from existing records if available
                            if offer_id in self.existing_data and 'distance' in self.existing_data[offer_id]:
                                data['distance'] = self.existing_data[offer_id]['distance']
                            
                            data['status'] = 'active'
                            data['unpublished_date'] = '--'
                            data['price_value'] = self._extract_price(data.get('price'))
                            
                            seen_ids.add(offer_id)
                            self.session_listings.add(offer_id)
                            all_apts.append(data)
                        except Exception as e:
                            logger.error(f"Error processing card: {e}")
                            continue
                    
                    logger.info(f"Extracted {len(current_page_ids)} unique listings from page {page}")
                    
                    # Check if all listings on this page are duplicates (already seen)
                    if new_ids_found == 0 and current_page_ids:
                        logger.warning("All listings on this page have been seen before.")
                        duplicate_page_count += 1
                        if duplicate_page_count >= max_duplicate_pages:
                            logger.info(f"Found {duplicate_page_count} consecutive pages with only duplicate listings. End of results reached.")
                            break
                    else:
                        duplicate_page_count = 0
                    
                    # Check if page has exactly the same listings as the previous page
                    if current_page_ids == previous_page_ids and current_page_ids:
                        logger.warning("This page has exactly the same listings as the previous page.")
                        logger.info("Likely reached the end of results. Stopping.")
                        break
                    
                    # Update previous page IDs
                    previous_page_ids = current_page_ids
                    
                    # Check if we found no new listings on this page
                    if not current_page_ids:
                        logger.info("No listings found on this page. Might have reached the end.")
                        break
                    
                    # Randomized delay before next page (2-4 seconds)
                    delay = 2 + random.uniform(0, 2)
                    logger.info(f"Waiting {delay:.2f} seconds before fetching next page...")
                    time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Error parsing page {page}: {e}")
                    logger.error(traceback.format_exc())
                    pagination_error_count += 1
                    if pagination_error_count >= max_pagination_errors:
                        logger.error(f"Too many consecutive errors ({pagination_error_count}). Stopping.")
                        break
                
                page += 1
                if page > max_pages:
                    logger.info(f"Reached max pages limit ({max_pages})")
                    break
                
        except Exception as e:
            logger.error(f"Unexpected error during collection: {e}")
            logger.error(traceback.format_exc())
        finally:
            if driver:
                try:
                    driver.quit()
                    logger.info("Browser closed properly")
                except:
                    logger.warning("Failed to close browser properly")
        
        logger.info(f"Collection completed: {len(all_apts)} listings collected across {page-1} pages")
        return all_apts

    def _parse_card(self, card):
        try:
            data = {
                'offer_id': '', 'offer_url': '', 'updated_time': '', 'title': '',
                'price': '', 'price_info': '', 'address': '', 'metro_station': '', 
                'neighborhood': '', 'district': '', 'description': '', 'image_urls': [], 
                'distance': None, 'cian_estimation': '',
                'rental_period': '--', 'utilities_type': '--', 
                'commission_info': '--', 'deposit_info': '--',
                'commission_value': None, 'deposit_value': None
            }

            # Extract offer URL and ID
            if link := card.select_one("a[href*='/rent/flat/']"):
                url = link.get('href')
                data['offer_url'] = self.url_base + url if url.startswith('/') else url
                if m := re.search(r'/rent/flat/(\d+)/', url):
                    data['offer_id'] = m.group(1)
            
            # Check for valid offer_id
            if not data['offer_id']:
                return None
                
            # Extract title
            if title := card.select_one('[data-mark="OfferTitle"]'):
                data['title'] = title.get_text(strip=True)
            
            # Extract price
            if price := card.select_one('[data-mark="MainPrice"]'):
                data['price'] = price.get_text(strip=True)

            # Extract price info and parse components
            if price_info := card.select_one('[data-mark="PriceInfo"]'):
                price_info_text = price_info.get_text(strip=True)
                data['price_info'] = price_info_text
                
                # Parse price info components
                parts = [p.strip() for p in price_info_text.split(',')]
                for p in parts:
                    if p in ['От года', 'На несколько месяцев']: 
                        data['rental_period'] = p
                    elif 'комм. платежи' in p: 
                        data['utilities_type'] = p
                    elif 'комиссия' in p or 'без комиссии' in p: 
                        data['commission_info'] = p
                        # Extract commission as numeric value
                        if 'без комиссии' in p:
                            data['commission_value'] = 0
                        elif 'комиссия' in p:
                            commission_match = re.search(r'комиссия\s+(\d+)%', p)
                            if commission_match:
                                data['commission_value'] = float(commission_match.group(1))
                    elif 'залог' in p or 'без залога' in p: 
                        data['deposit_info'] = p
                        # Extract deposit as numeric value
                        if 'без залога' in p:
                            data['deposit_value'] = 0
                        elif 'залог' in p:
                            deposit_match = re.search(r'залог\s+([\d\s\xa0]+)\s*₽', p)
                            if deposit_match:
                                amount_str = deposit_match.group(1)
                                # Remove all whitespace including non-breaking spaces
                                clean_amount = re.sub(r'\s', '', amount_str)
                                try:
                                    data['deposit_value'] = int(clean_amount)
                                except ValueError:
                                    pass  # Keep as None if conversion fails
            
            # Extract metro station
            if metro := card.select_one('div[data-name="SpecialGeo"]'):
                text = metro.get_text(strip=True)
                data['metro_station'] = text.split('мин')[0].strip() if 'мин' in text else text
            
            # Extract location details
            loc_elems = card.select('a[data-name="GeoLabel"]')
            if len(loc_elems) > 3:
                data['metro_station'] = loc_elems[3].get_text(strip=True)
            if len(loc_elems) > 2:
                data['neighborhood'] = loc_elems[2].get_text(strip=True)
            if len(loc_elems) > 1:
                data['district'] = loc_elems[1].get_text(strip=True)
            
            street = loc_elems[4].get_text(strip=True) if len(loc_elems) > 4 else ''
            building = loc_elems[5].get_text(strip=True) if len(loc_elems) > 5 else ''
            data['address'] = f"{street}, {building}".strip(', ')
            
            # Extract description
            if desc := card.select_one('div[data-name="Description"] p'):
                data['description'] = desc.get_text(strip=True)
            
            # Extract updated time
            if time_el := card.select_one('div[data-name="TimeLabel"] div._93444fe79c--absolute--yut0v span'):
                data['updated_time'] = parse_updated_time(time_el.get_text(strip=True))
            
            # Extract image URLs
            data['image_urls'] = [img.get('src') for img in card.select('img._93444fe79c--container--KIwW4') if img.get('src')]
            
            return data
        except Exception as e:
            logger.error(f'Error parsing card: {e}')
            return None

    def _combine_with_existing(self, new_apts):
        combined_apts = []
        new_ids = set(apt['offer_id'] for apt in new_apts if 'offer_id' in apt)
        
        # Process new apartments
        for apt in new_apts:
            if 'offer_id' not in apt:
                continue
                
            offer_id = str(apt['offer_id'])
            if offer_id in self.existing_data:
                existing = self.existing_data[offer_id]
                new_price = self._extract_price(apt.get('price'))
                old_price = self._extract_price(existing.get('price'))
                
                if new_price != old_price and new_price is not None:
                    # Price changed
                    merged = apt.copy()
                    # Store the price change information
                    merged['price_change'] = f"Changed from {old_price} to {new_price}"
                    combined_apts.append(merged)
                    self.price_changes += 1
                else:
                    # No price change, keep existing data but mark as active
                    merged = existing.copy()
                    merged['status'] = 'active'
                    merged['unpublished_date'] = '--'
                    combined_apts.append(merged)
            else:
                # New listing
                combined_apts.append(apt)
                self.new += 1
        
        # Add missing apartments (no longer available)
        for missing_id in set(self.existing_data.keys()) - new_ids:
            if existing := self.existing_data.get(missing_id):
                if existing.get('status') != 'non active':  # Only count if not already marked as inactive
                    existing = existing.copy()
                    existing['status'] = 'non active'
                    existing['unpublished_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    combined_apts.append(existing)
                    self.removed += 1
                else:
                    # Already inactive, just add to the combined list
                    combined_apts.append(existing.copy())
        
        return combined_apts

    def _process_distances(self, apartments):
        try:
            # Get reference coordinates only once
            ref_coords = get_coordinates(self.reference_address)
            
            # Process each apartment
            for apt in apartments:
                # Skip if already has valid distance
                distance = apt.get('distance')
                if distance and not (isinstance(distance, float) and (np.isnan(distance) or np.isinf(distance))):
                    apt['distance'] = float(distance) if isinstance(distance, str) else distance
                    continue
                
                # Calculate distance if address is available
                address = apt.get('address', '')
                if address:
                    try:
                        full_address = f"Москва, {address}" if 'Москва' not in address else address
                        apt['distance'] = round(calculate_distance(from_point=ref_coords, to_address=full_address), 2)
                    except Exception as e:
                        logger.warning(f"Error calculating distance for {address}: {e}")
                        apt['distance'] = None
        except Exception as e:
            logger.error(f"Error in distance processing: {e}")

    def _save_data(self, apartments):
        if not apartments:
            return []
        try:
            # Define file paths
            base_filename = self.csv_filename.replace('.csv', '')
            current_csv = f"{base_filename}.csv"
            current_json = f"{base_filename}.json"
            backup_csv = f"{base_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup.csv"
            
            # Create backup of existing file
            if os.path.exists(current_csv):
                try:
                    import shutil
                    shutil.copy2(current_csv, backup_csv)
                    logger.info(f"Created backup at {backup_csv}")
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")
            
            # Prepare data for saving
            processed_apts = []
            for apt in apartments:
                # Convert complex types to strings
                processed_apt = {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict, np.ndarray)) 
                    else v for k, v in apt.items()
                }
                processed_apts.append(processed_apt)
            
            # Convert to DataFrame
            df = pd.DataFrame(processed_apts)
            
            # Make sure offer_id is string
            if 'offer_id' in df.columns:
                df['offer_id'] = df['offer_id'].astype(str)
            
            # Remove unwanted columns
            for col in ['price_change', 'cian_estimation']:
                if col in df.columns:
                    df.drop(columns=col, inplace=True)
            
            # Drop duplicates and convert to records
            result = df.drop_duplicates('offer_id', keep='first').to_dict('records')
            
            if result:
                # Define column order
                priority_cols = [
                    'offer_id', 'offer_url', 'title', 'updated_time',
                    'address', 'metro_station', 'neighborhood', 'district', 'description',
                    'status', 'unpublished_date'
                ]
                
                # Create DataFrame for saving
                save_df = pd.DataFrame(result)
                cols = [c for c in priority_cols if c in save_df.columns] + \
                       [c for c in save_df.columns if c not in priority_cols and c != 'image_urls']
                
                if cols:  # Make sure we have columns
                    save_df = save_df[cols]
                    
                    # Format values for saving
                    for col in save_df.columns:
                        save_df[col] = save_df[col].map(lambda x: (
                            json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict, np.ndarray)) 
                            else x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) 
                            else x
                        ))
                    
                    # Save using a temporary file
                    tmp_csv = current_csv + '.tmp'
                    with open(tmp_csv, 'w', encoding='utf-8') as f:
                        save_df.to_csv(f, index=False, encoding='utf-8')
                    
                    # Replace the original file
                    os.replace(tmp_csv, current_csv)
                    logger.info(f"Saved {len(save_df)} records to {current_csv}")
                    
                    # Save metadata
                    metadata = {
                        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "record_count": len(save_df),
                        "new_records": self.new,
                        "removed_records": self.removed,
                        "price_changes": self.price_changes
                    }
                    
                    with open(base_filename + '.meta.json', 'w', encoding='utf-8') as meta_f:
                        json.dump(metadata, meta_f, ensure_ascii=False, indent=2)
                    
                    # Save JSON version with all records
                    with open(current_json, 'w', encoding='utf-8') as f:
                        json.dump([{
                            k: (v.strftime('%Y-%m-%d %H:%M:%S') if isinstance(v, pd.Timestamp) 
                               else float(v) if isinstance(v, np.float64) 
                               else int(v) if isinstance(v, np.int64) 
                               else v) 
                            for k, v in apt.items()
                        } for apt in result], f, ensure_ascii=False, indent=4)
            
            return result
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            logger.error(traceback.format_exc())
            return apartments

    def scrape(self, search_url, max_pages=5, max_retries=3, retry_delay=5, max_distance_km=None, time_filter=None, auto_detect_pages=True):
        """
        Main scraping method that coordinates the entire process
        
        Args:
            search_url: The base search URL
            max_pages: Maximum number of pages to scrape
            max_retries: Number of retry attempts for failed operations
            retry_delay: Delay between retries in seconds
            max_distance_km: Filter by maximum distance (optional)
            time_filter: Time filter in minutes (optional)
            auto_detect_pages: Try to automatically detect the total number of pages (default: True)
            
        Returns:
            List of processed apartments
        """
        # Reset session stats
        self.new = self.removed = self.price_changes = 0
        self.session_listings = set()
        
        # Add time filter if specified
        url = f'{search_url}&totime={time_filter * 60}' if time_filter else search_url
        
        logger.info(f"Starting scraping with max_pages={max_pages}, max_retries={max_retries}")
        logger.info(f"URL: {url}")
        
        # If auto-detection is enabled, try to get the total number of pages first
        if auto_detect_pages:
            try:
                driver = None
                try:
                    driver = self._initialize_driver(max_retries, retry_delay)
                    if self._load_page(driver, url, max_retries, retry_delay):
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        
                        # Look for pagination elements to find the last page number
                        # This selector may need to be adjusted based on the actual HTML structure
                        pagination_elements = soup.select('div[data-name="Pagination"] a, .pagination a')
                        
                        detected_max_page = 1
                        for el in pagination_elements:
                            try:
                                # Try to extract page number from text or link
                                page_text = el.get_text(strip=True)
                                if page_text.isdigit():
                                    detected_max_page = max(detected_max_page, int(page_text))
                                elif 'href' in el.attrs:
                                    href = el['href']
                                    page_match = re.search(r'[?&]p=(\d+)', href)
                                    if page_match and page_match.group(1).isdigit():
                                        detected_max_page = max(detected_max_page, int(page_match.group(1)))
                            except Exception:
                                continue
                        
                        # Find total results count if available
                        total_count_el = soup.select_one('[data-name="SummaryHeader"] span, .summary-header-count')
                        if total_count_el:
                            count_text = total_count_el.get_text(strip=True)
                            count_match = re.search(r'(\d[\d\s]+)', count_text)
                            if count_match:
                                count_str = re.sub(r'\s', '', count_match.group(1))
                                try:
                                    total_results = int(count_str)
                                    # Estimate number of pages based on results per page (typically 28)
                                    estimated_pages = (total_results + 27) // 28  # Ceiling division
                                    detected_max_page = max(detected_max_page, estimated_pages)
                                    logger.info(f"Estimated {estimated_pages} pages based on {total_results} total results")
                                except ValueError:
                                    pass
                        
                        if detected_max_page > 1:
                            logger.info(f"Detected maximum page number: {detected_max_page}")
                            # Use the detected page count, but don't exceed the user-specified maximum
                            max_pages = min(detected_max_page, max_pages)
                            logger.info(f"Will scrape up to {max_pages} pages")
                except Exception as e:
                    logger.error(f"Error detecting total pages: {e}")
                finally:
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
            except Exception as e:
                logger.error(f"Failed to auto-detect page count: {e}")
        
        # Attempt collection with retry
        parsed_apts = []
        for attempt in range(max_retries):
            try:
                logger.info(f"Collection attempt {attempt+1}/{max_retries}")
                parsed_apts = self.collect_listings(url, max_pages, max_retries, retry_delay)
                
                if parsed_apts:
                    logger.info(f"Successfully collected {len(parsed_apts)} listings")
                    break
                else:
                    logger.warning(f"No listings collected on attempt {attempt+1}")
                    
            except Exception as e:
                logger.error(f"Error during collection attempt {attempt+1}: {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.info(f"Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
        
        if not parsed_apts:
            logger.error("Failed to collect any listings after all retries")
            return []
        
        # Process the collected listings
        logger.info(f"Processing {len(parsed_apts)} collected listings")
        
        # Combine with existing data
        combined_apts = self._combine_with_existing(parsed_apts)
        logger.info(f"Combined data: {len(combined_apts)} apartments")
        
        # Process distances
        self._process_distances(combined_apts)
        logger.info("Distance processing completed")
        
        # Filter by distance if needed
        if max_distance_km:
            filtered_apts = [apt for apt in combined_apts 
                             if apt.get('distance') is None or apt.get('distance') <= max_distance_km]
            logger.info(f"Filtered by distance ({max_distance_km} km): {len(filtered_apts)} apartments")
        else:
            filtered_apts = combined_apts
        
        # Save the processed data
        result = self._save_data(filtered_apts)
        
        # Log summary
        logger.info("=" * 50)
        logger.info("SCRAPING COMPLETED")
        logger.info(f"New listings: +{self.new}")
        logger.info(f"Removed listings: -{self.removed}")
        logger.info(f"Price changes: {self.price_changes}")
        logger.info(f"Total records: {len(result)}")
        logger.info("=" * 50)
        
        return result

if __name__ == '__main__':
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape apartment listings from Cian.ru')
    parser.add_argument('--csv', default='cian_apartments.csv', help='CSV filename for results')
    parser.add_argument('--url', default='https://www.cian.ru/cat.php?currency=2&deal_type=rent&district%5B0%5D=13&district%5B1%5D=21&engine_version=2&maxprice=100000&metro%5B0%5D=4&metro%5B10%5D=86&metro%5B11%5D=115&metro%5B12%5D=118&metro%5B13%5D=120&metro%5B14%5D=134&metro%5B15%5D=143&metro%5B16%5D=151&metro%5B17%5D=159&metro%5B18%5D=310&metro%5B1%5D=8&metro%5B2%5D=12&metro%5B3%5D=18&metro%5B4%5D=20&metro%5B5%5D=33&metro%5B6%5D=46&metro%5B7%5D=56&metro%5B8%5D=63&metro%5B9%5D=80&offer_type=flat&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1&room9=1&type=4', 
                       help='Cian.ru search URL')
    parser.add_argument('--pages', type=int, default=100, help='Maximum number of pages to scrape')
    parser.add_argument('--retries', type=int, default=3, help='Number of retries for failed requests')
    parser.add_argument('--delay', type=int, default=5, help='Base delay between retries in seconds')
    parser.add_argument('--no-headless', action='store_true', help='Run Chrome in visible mode (default is headless)')
    parser.add_argument('--max-distance', type=float, help='Maximum distance in km')
    parser.add_argument('--time-filter', type=int, help='Filter by posting time (minutes)')
    parser.add_argument('--reference', default='Москва, переулок Большой Саввинский, 3', 
                       help='Reference address for distance calculations')
    parser.add_argument('--no-auto-detect', action='store_true', 
                       help='Disable automatic detection of the maximum number of pages')
    
    args = parser.parse_args()
    
    try:
        # Initialize and run the scraper - default to headless mode unless --no-headless is specified
        scraper = CianScraper(
            headless=not args.no_headless,  # Default to headless=True unless --no-headless is specified
            csv_filename=args.csv,
            reference_address=args.reference
        )
        
        result = scraper.scrape(
            search_url=args.url, 
            max_pages=args.pages,
            max_retries=args.retries,
            retry_delay=args.delay,
            max_distance_km=args.max_distance,
            time_filter=args.time_filter,
            auto_detect_pages=not args.no_auto_detect  # Enable auto-detection by default
        )
        
        print(f"Scraping completed: {len(result)} apartments processed")
        print(f"Changes: +{scraper.new} new, -{scraper.removed} removed, {scraper.price_changes} price changes")
        
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        logger.critical(traceback.format_exc())
        print(f"ERROR: {e}")