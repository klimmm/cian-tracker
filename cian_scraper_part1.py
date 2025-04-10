import os, re, json, time, logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from distance import get_coordinates, calculate_distance
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CianScraper')
import re
from datetime import datetime, timedelta
import requests
import os, re, json, time, logging, random  # Add random to the imports at the top

def parse_updated_time(time_str):
    """Parse Cian time format to datetime string"""
    if not time_str:
        return ''
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    months = {
        'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
        'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12,
    }
    try:
        if 'сегодня' in time_str.lower():
            h, m = map(int, time_str.split(', ')[1].split(':'))
            return today.replace(hour=h, minute=m).strftime('%Y-%m-%d %H:%M:%S')
        if 'вчера' in time_str.lower() and ', ' in time_str:
            h, m = map(int, time_str.split(', ')[1].split(':'))
            return (today - timedelta(days=1)).replace(hour=h, minute=m).strftime('%Y-%m-%d %H:%M:%S')
        if any(x in time_str.lower() for x in ['минут', 'секунд']):
            now = datetime.now()
            if 'минут' in time_str.lower():
                min = int(re.search(r'(\d+)\s+минут', time_str).group(1))
                return (now - timedelta(minutes=min)).strftime('%Y-%m-%d %H:%M:%S')
            sec = int(re.search(r'(\d+)\s+секунд', time_str).group(1))
            return (now - timedelta(seconds=sec)).strftime('%Y-%m-%d %H:%M:%S')
        if ', ' in time_str and any(m in time_str.lower() for m in months.keys()):
            date_part, time_part = time_str.split(', ')
            day = int(re.search(r'(\d+)', date_part).group(1))
            month = next((n for name, n in months.items() if name in date_part.lower()), None)
            if not month:
                return time_str
            h, m = map(int, time_part.split(':'))
            year = today.year
            dt = datetime(year, month, day, h, m)
            if dt > datetime.now() + timedelta(days=1):
                dt = dt.replace(year=year - 1)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    return time_str


class CianScraper:
    def __init__(self, headless=True, csv_filename='cian_apartments.csv', 
                 reference_address='Москва, переулок Большой Саввинский, 3'):
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument('--headless')
        for arg in ['--disable-gpu', '--window-size=1920,1080', '--disable-extensions', 
                    '--no-sandbox', '--disable-dev-shm-usage']:
            self.chrome_options.add_argument(arg)
        self.chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')

        self.url_base = 'https://www.cian.ru'
        self.csv_filename = csv_filename
        self.reference_address = reference_address
        self.new = self.removed = self.price_changes = 0
        self.existing_data = self._load_existing_data()

    def _download_images(self, offers, image_folder='images'):
        os.makedirs(image_folder, exist_ok=True)
        
        for offer in offers:
            offer_id = offer.get('offer_id')
            if not offer_id:
                logger.warning("⚠️ Skipping offer with missing ID.")
                continue
            
            # Handle the image_urls properly whether it's a list or JSON string
            images = offer.get('image_urls', [])
            
            # Convert from string representation if needed
            if isinstance(images, str):
                try:
                    # Try to parse as JSON
                    if images.startswith('[') and images.endswith(']'):
                        images = json.loads(images)
                    # Handle single URL case
                    elif 'http' in images:
                        images = [images]
                    else:
                        images = []
                except Exception as e:
                    logger.warning(f"⚠️ Could not parse image URLs for offer {offer_id}: {str(e)}")
                    images = []
            
            if not images:
                logger.info(f"📭 No images found for offer {offer_id}")
                continue
            
            logger.info(f"🖼️ Found {len(images)} image(s) for offer {offer_id}")
            
            # Create subfolder for this offer
            offer_folder = os.path.join(image_folder, str(offer_id))
            os.makedirs(offer_folder, exist_ok=True)
            
            for idx, image_url in enumerate(images):
                try:
                    # Skip invalid URLs
                    if not image_url or not isinstance(image_url, str):
                        continue
                        
                    # Add a User-Agent header to avoid being blocked
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
                    }
                    
                    logger.info(f"⬇️ Downloading image {idx+1}/{len(images)} for offer {offer_id}")
                    response = requests.get(image_url, timeout=10, headers=headers)
                    
                    if response.status_code == 200:
                        filename = os.path.join(offer_folder, f'{idx + 1}.jpg')
                        with open(filename, 'wb') as f:
                            f.write(response.content)
                        logger.info(f"✅ Downloaded image {idx + 1} for {offer_id} → {filename}")
                    else:
                        logger.warning(f"❌ Failed to download image {idx + 1} for {offer_id}: status {response.status_code}")
                    
                    # Add a small delay between requests
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"⚠️ Error downloading image {idx + 1} for {offer_id}: {e}")
        

        
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
    
    def _get_total_listings(self, driver):
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="SummaryHeader"] h5'))
            )
            header_text = driver.find_element(By.CSS_SELECTOR, '[data-testid="SummaryHeader"] h5').text
            match = re.search(r'Найдено\s+(\d+)', header_text.replace('\xa0', ''))
            if match:
                return int(match.group(1))
        except Exception as e:
            logger.warning(f"Could not extract total listings: {e}")
        return None
    
                
    def collect_listings(self, url, max_pages=1000):
        all_apts = []
        added_ids = {}
        visited_pages = set()
        page_listings_map = {}
        driver = webdriver.Chrome(options=self.chrome_options)
        total_pages_processed = 0
        
        # Create images folder at the beginning
        image_folder = 'images'
        os.makedirs(image_folder, exist_ok=True)
    
        try:
            page = 1
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-name='CardComponent']"))
            )
            logger.info('Starting collection of apartment listings')
    
            total_listings = self._get_total_listings(driver)
            if not total_listings:
                logger.warning("Total listing count not found. Defaulting to max_pages logic.")
                total_listings = float('inf')
    
            logger.info(f'Total listings to collect: {total_listings}')
            previous_page_ids = set()
    
            # -------- FORWARD LOOP --------
            while len(all_apts) < total_listings and page <= max_pages:
                

    


                
                visited_pages.add(page)
                logger.info(f'Parsing page {page}')
                driver.execute_script('window.scrollTo(0, document.body.scrollHeight/2);')
                time.sleep(1.5)
    
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                cards = soup.select("div._93444fe79c--wrapper--W0WqH[data-name='Offers'] article[data-name='CardComponent']")
                if not cards:
                    logger.info('No cards found on page. Stopping forward loop.')
                    break
    
                current_page_ids = set()
                page_listings_map[page] = []
                page_new_listings_count = 0
                page_apts = []
    
                for card in cards:
                    data = self._parse_card(card)
                    if not data or 'offer_id' not in data:
                        continue
    
                    offer_id = str(data['offer_id'])
                    current_page_ids.add(offer_id)
                    page_listings_map[page].append(offer_id)
                    page_apts.append(data)
    
                    if offer_id not in added_ids:
                        data['status'] = 'active'
                        data['unpublished_date'] = '--'
                        if offer_id in self.existing_data and 'distance' in self.existing_data[offer_id]:
                            data['distance'] = self.existing_data[offer_id]['distance']
                        all_apts.append(data)
                        added_ids[offer_id] = page
                        page_new_listings_count += 1

                    # Download images immediately if they exist
                    if 'image_urls' in data and data['image_urls']:
                        self._download_images_for_listing(data, image_folder)

                        
    
                logger.info(f'Page {page}: Collected {page_new_listings_count} new listings')
                logger.info(f'Collected {len(all_apts)} / {total_listings} so far')
                logger.info(f'🧾 Listings on page {page}:')
                for apt in page_apts:
                    logger.info(f"  - {apt.get('offer_id')} | {apt.get('title')} | {apt.get('address')} | {apt.get('price')}")
    
                total_pages_processed += 1
                if current_page_ids == previous_page_ids:
                    logger.info('Same items as previous page. Stopping forward loop.')
                    break
                previous_page_ids = current_page_ids
    
                if len(all_apts) >= total_listings:
                    logger.info('Reached required number of listings. Done.')
                    break
    
                page += 1
                next_url = re.sub(r'p=\d+', f'p={page}', driver.current_url) if 'p=' in driver.current_url else f"{driver.current_url}{'&' if '?' in driver.current_url else '?'}p={page}"
                logger.info(f'Navigating to next page: {next_url}')
                try:
                    driver.get(next_url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-name='CardComponent']"))
                    )
                except Exception as e:
                    logger.error(f"Failed to load page {page}: {e}")
                    break
      

            
            # -------- BACKWARD LOOP --------
            logger.info('Starting reverse crawl to fill missing listings...')
            for reverse_page in range(page - 1, 0, -1):
                if len(all_apts) >= total_listings:
                    break
                if reverse_page not in visited_pages:
                    continue
    
                back_url = re.sub(r'p=\d+', f'p={reverse_page}', url)
                if 'p=' not in back_url:
                    back_url = f"{back_url}{'&' if '?' in back_url else '?'}p={reverse_page}"
                logger.info(f'Revisiting page {reverse_page}: {back_url}')
    
                try:
                    driver.get(back_url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-name='CardComponent']"))
                    )
                    driver.execute_script('window.scrollTo(0, document.body.scrollHeight/2);')
                    time.sleep(1.5)
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    # Replace with this more specific selector in both places
                    cards = soup.select("div._93444fe79c--wrapper--W0WqH[data-name='Offers'] article[data-name='CardComponent']")
                    if not cards:
                        logger.warning(f"No cards found on page {reverse_page}")
                        continue
    
                    page_new_listings_count = 0
                    page_apts = []
    
                    for card in cards:
                        data = self._parse_card(card)
                        if not data or 'offer_id' not in data:
                            continue
                        offer_id = str(data['offer_id'])
                        page_apts.append(data)
                        if offer_id not in added_ids:
                            data['status'] = 'active'
                            data['unpublished_date'] = '--'
                            if offer_id in self.existing_data and 'distance' in self.existing_data[offer_id]:
                                data['distance'] = self.existing_data[offer_id]['distance']
                            all_apts.append(data)
                            added_ids[offer_id] = reverse_page
                            page_new_listings_count += 1
    
                    logger.info(f'Page {reverse_page}: Recovered {page_new_listings_count} new listings')
                    logger.info(f'Total collected: {len(all_apts)} / {total_listings}')
                    logger.info(f'🧾 Listings on page {reverse_page}:')
                    for apt in page_apts:
                        logger.info(f"  - {apt.get('offer_id')} | {apt.get('title')} | {apt.get('address')} | {apt.get('price')}")
                except Exception as e:
                    logger.warning(f'Error while revisiting page {reverse_page}: {e}')
                    continue
    
        except Exception as e:
            logger.error(f'Unexpected error: {e}')
        finally:
            try:
                driver.quit()
            except:
                pass
    
        # -------- Deduplication Check --------
        unique_ids = set()
        duplicates = []
        for apt in all_apts:
            offer_id = apt.get("offer_id")
            if offer_id in unique_ids:
                duplicates.append(offer_id)
            else:
                unique_ids.add(offer_id)
    
        if duplicates:
            logger.warning(f"❗ Found {len(duplicates)} duplicate listings: {duplicates[:10]}{' ...' if len(duplicates) > 10 else ''}")
        else:
            logger.info("✅ No duplicate listings found in final results.")
    
        # -------- Final Listing Log --------
        logger.info(f"📦 Final listing log ({len(all_apts)} total):")
        for apt in all_apts:
            logger.info(f"  - {apt.get('offer_id')} | {apt.get('title')} | {apt.get('address')} | {apt.get('price')}")
    
        logger.info(f'✅ Collection complete: {len(all_apts)} listings collected after {total_pages_processed} pages')
        return all_apts
    
        
                            
    def _parse_card(self, card):
        try:
            data = {
                'offer_id': '', 'offer_url': '', 'updated_time': '', 'title': '',
                'price': '', 'price_info': '', 'address': '', 'metro_station': '', 
                'neighborhood': '', 'district': '', 'description': '', 'image_urls': [], 
                'distance': None
            }
    
            # Basic listing information
            if link := card.select_one("a[href*='/rent/flat/']"):
                url = link.get('href')
                data['offer_url'] = self.url_base + url if url.startswith('/') else url
                if m := re.search(r'/rent/flat/(\d+)/', url):
                    data['offer_id'] = m.group(1)
    
            if title := card.select_one('[data-mark="OfferTitle"]'):
                data['title'] = title.get_text(strip=True)
    
            # Price information
            if price := card.select_one('[data-mark="MainPrice"]'):
                data['price'] = price.get_text(strip=True)
                data['price_value'] = self._extract_price(data['price'])
    
            if price_info := card.select_one('[data-mark="PriceInfo"]'):
                price_info_text = price_info.get_text(strip=True)
                data['price_info'] = price_info_text
    
                # Initialize additional price-related fields
                data['rental_period'] = '--'
                data['utilities_type'] = '--'
                data['commission_info'] = '--'
                data['deposit_info'] = '--'
                data['commission_value'] = None
                data['deposit_value'] = None
                
                parts = [p.strip() for p in price_info_text.split(',')]
                for p in parts:
                    if p in ['От года', 'На несколько месяцев']:
                        data['rental_period'] = p
                    elif 'комм. платежи' in p:
                        data['utilities_type'] = p
                    elif 'комиссия' in p or 'без комиссии' in p:
                        data['commission_info'] = p
                    elif 'залог' in p or 'без залога' in p:
                        data['deposit_info'] = p
    
            # Location information
            if metro := card.select_one('div[data-name="SpecialGeo"]'):
                text = metro.get_text(strip=True)
                data['metro_station'] = text.split('мин')[0].strip() if 'мин' in text else text
    
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
    
            # Description
            if desc := card.select_one('div[data-name="Description"] p'):
                data['description'] = desc.get_text(strip=True)
    
            # Time updated
            if time_el := card.select_one('div[data-name="TimeLabel"] div._93444fe79c--absolute--yut0v span'):
                data['updated_time'] = parse_updated_time(time_el.get_text(strip=True))
    
            # IMAGE EXTRACTION - MULTI-STRATEGY APPROACH
            image_urls = []
    
            # Strategy 1: Find the gallery structure directly
            gallery_container = None
            
            # Try to find the Gallery container within the card
            gallery_container = card.select_one('div[data-name="Gallery"]')
            
            # If not found in card directly, try to find gallery in parent <a> tag
            if not gallery_container:
                # Get the offer_id
                offer_id = data.get('offer_id')
                if offer_id:
                    # Look in the document for a container with this offer in the href
                    gallery_a = card.find_parent('a', href=lambda h: h and f'/rent/flat/{offer_id}/' in h)
                    if gallery_a:
                        gallery_container = gallery_a.select_one('div[data-name="Gallery"]')
                    
                    # Alternative approach - look for the gallery relative to the card's parent
                    if not gallery_container:
                        parent = card.parent
                        if parent:
                            # Look for the closest <a> with the right href
                            gallery_a = parent.find('a', href=lambda h: h and f'/rent/flat/{offer_id}/' in h)
                            if gallery_a:
                                gallery_container = gallery_a.select_one('div[data-name="Gallery"]')
            
            # Extract images from gallery container if found
            if gallery_container:
                imgs = gallery_container.select('img')
                image_urls = [img.get('src') for img in imgs if img.get('src')]
                
            # Strategy 2: Try to find images by class pattern
            if not image_urls:
                # Try direct class search
                imgs = card.select('div._93444fe79c--cont--hnKQl img')
                if imgs:
                    image_urls = [img.get('src') for img in imgs if img.get('src')]
                    
            # Strategy 3: Find the parent A tag containing the gallery
            if not image_urls:
                try:
                    parent_a = card.find_parent('a', class_='_93444fe79c--media--9P6wN')
                    if parent_a:
                        imgs = parent_a.select('img')
                        image_urls = [img.get('src') for img in imgs if img.get('src')]
                except Exception:
                    pass
            
            # Strategy 4: Get images from entire document by offer_id
            if not image_urls and data.get('offer_id'):
                offer_id = data.get('offer_id')
                try:
                    # Get the root document
                    root = card
                    while root.parent:
                        root = root.parent
                    
                    # Look for a tag with the specific offer URL
                    a_with_images = root.select_one(f'a[href*="/rent/flat/{offer_id}/"]')
                    if a_with_images:
                        imgs = a_with_images.select('img')
                        image_urls = [img.get('src') for img in imgs if img.get('src')]
                except Exception:
                    pass
                    
            # Strategy 5: Last resort - find any images in the card
            if not image_urls:
                imgs = card.select('img')
                image_urls = [img.get('src') for img in imgs if img.get('src')]
            
            # Remove any duplicates while preserving order
            seen = set()
            data['image_urls'] = [x for x in image_urls if not (x in seen or seen.add(x))]
            
            # Log results
            if data['image_urls']:
                logger.info(f"📸 Found {len(data['image_urls'])} images for offer {data.get('offer_id')}")
            else:
                logger.info(f"📭 No images found for offer {data.get('offer_id')}")
    
            return data
    
        except Exception as e:
            logger.error(f'Error parsing card: {e}')
            return None

    def _combine_with_existing(self, new_apts):
        combined_apts = []
        new_ids = set(apt['offer_id'] for apt in new_apts if 'offer_id' in apt)
        for apt in new_apts:
            if 'offer_id' not in apt:
                continue
            offer_id = str(apt['offer_id'])
            if offer_id in self.existing_data:
                existing = self.existing_data[offer_id]
                new_price = self._extract_price(apt.get('price'))
                old_price = existing.get('price_value', new_price)
                if new_price != old_price:
                    merged = apt.copy()
                    combined_apts.append(merged)
                    self.price_changes += 1
                else:
                    merged = existing.copy()
                    merged['status'] = 'active'
                    merged['unpublished_date'] = '--'
                    combined_apts.append(merged)
            else:
                combined_apts.append(apt)
                self.new += 1
        for missing_id in set(self.existing_data.keys()) - new_ids:
            if existing := self.existing_data.get(missing_id):
                existing = existing.copy()
                existing['status'] = 'non active'
                existing.setdefault('unpublished_date', '--')
                combined_apts.append(existing)
                self.removed += 1
        return combined_apts

    def _process_distances(self, apartments):
        try:
            ref_coords = get_coordinates(self.reference_address)
            for apt in apartments:
                distance = apt.get('distance')
                if distance and not (isinstance(distance, float) and (np.isnan(distance) or np.isinf(distance))):
                    apt['distance'] = float(distance) if isinstance(distance, str) else distance
                    continue
                address = apt.get('address', '')
                if address:
                    try:
                        full_address = f"Москва, {address}" if 'Москва' not in address else address
                        apt['distance'] = round(calculate_distance(from_point=ref_coords, to_address=full_address), 2)
                    except:
                        pass
        except:
            pass

    def _save_data(self, apartments):
        if not apartments:
            return []
        try:
            
            base_filename = self.csv_filename.replace('.csv', '')
            current_csv = f"{base_filename}.csv"
            current_json = f"{base_filename}.json"
            df = pd.DataFrame([{k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict, np.ndarray)) else v 
                                for k, v in apt.items()} for apt in apartments])
            df['offer_id'] = df['offer_id'].astype(str)
            
            for col in ['price_change', 'cian_estimation', 'price']:
                if col in df.columns:
                    df.drop(columns=col, inplace=True)

                    
            result = df.drop_duplicates('offer_id', keep='first').to_dict('records')
            if result:
                priority_cols = [
                    'offer_id', 'offer_url', 'title', 'updated_time',
                    'address', 'metro_station', 'neighborhood', 'district', 'description',
                    'status', 'unpublished_date'
                ]
                save_df = pd.DataFrame(result)
                cols = [c for c in priority_cols if c in save_df.columns] + \
                       [c for c in save_df.columns if c not in priority_cols and c != 'image_urls']
                save_df = save_df[cols]
                for col in save_df.columns:
                    save_df[col] = save_df[col].map(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict, np.ndarray)) 
                                                    else x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) 
                                                    else x)
                tmp_csv = current_csv + '.tmp'
                with open(tmp_csv, 'w', encoding='utf-8') as f:
                    save_df.to_csv(f, index=False, encoding='utf-8')
                os.replace(tmp_csv, current_csv)
                metadata = {
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "record_count": len(save_df),
                }
                with open(base_filename + '.meta.json', 'w', encoding='utf-8') as meta_f:
                    json.dump(metadata, meta_f, ensure_ascii=False, indent=2)
                with open(current_json, 'w', encoding='utf-8') as f:
                    json.dump([{k: (v.strftime('%Y-%m-%d %H:%M:%S') if isinstance(v, pd.Timestamp) 
                                    else float(v) if isinstance(v, np.float64) 
                                    else int(v) if isinstance(v, np.int64) 
                                    else v) for k, v in apt.items()} for apt in result], 
                               f, ensure_ascii=False, indent=4)
            return result
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            return apartments
    def _download_images_for_listing(self, listing, image_folder='images', max_retries=3):
        """Download images for a single listing with retry and anti-block measures"""
        try:
            offer_id = listing.get('offer_id')
            images = listing.get('image_urls', [])
            
            if not offer_id or not images:
                return
            
            # Create folder for this specific listing
            offer_folder = os.path.join(image_folder, str(offer_id))
            
            # Check if this offer was already downloaded
            if os.path.exists(offer_folder):
                # Count existing images
                existing_images = [f for f in os.listdir(offer_folder) if f.endswith('.jpg')]
                if len(existing_images) > 0:
                    logger.info(f"⏭️ Skipping offer {offer_id}: {len(existing_images)} images already downloaded")
                    return

            os.makedirs(offer_folder, exist_ok=True)
            
            logger.info(f"🖼️ Downloading {len(images)} image(s) for offer {offer_id}")
            
            # Create a session for better connection reuse
            session = requests.Session()
            
            # List of common user agents to rotate through
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            
            # Set common headers to mimic a browser
            session.headers.update({
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
                'Referer': 'https://www.cian.ru/',
                'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
                'Connection': 'keep-alive'
            })
            
            success_count = 0
            error_count = 0
            
            # Process a small batch at a time (5 images) with longer delay between batches
            batch_size = 15
            batches = [images[i:i + batch_size] for i in range(0, len(images), batch_size)]
            
            for batch_idx, batch in enumerate(batches):
                # Add a longer delay between batches (3-7 seconds)
                if batch_idx > 0:
                    sleep_time = 1 + random.random() * 1.1
                    logger.info(f"😴 Sleeping for {sleep_time:.1f} seconds between image batches...")
                    time.sleep(sleep_time)
                
                for idx, image_url in enumerate(batch):
                    if not image_url:
                        continue
                    
                    abs_idx = batch_idx * batch_size + idx
                    
                    # Choose a random user agent for each request
                    current_ua = random.choice(user_agents)
                    session.headers.update({'User-Agent': current_ua})
                    
                    # Add a random delay between requests (0.5-2 seconds)
                    sleep_time = 0.5 + random.random() * 1.1
                    time.sleep(sleep_time)
                    
                    # Retry logic
                    for retry in range(max_retries):
                        try:
                            logger.info(f"⬇️ Downloading image {abs_idx + 1}/{len(images)} for offer {offer_id}")
                            
                            response = session.get(image_url, timeout=7)
                            
                            if response.status_code == 200:
                                filename = os.path.join(offer_folder, f'{abs_idx + 1}.jpg')
                                with open(filename, 'wb') as f:
                                    f.write(response.content)
                                logger.info(f"✅ Downloaded image {abs_idx + 1} for {offer_id} → {filename}")
                                success_count += 1
                                break  # Success, exit retry loop
                            else:
                                logger.warning(f"❌ Failed to download image {abs_idx + 1} for {offer_id}: status {response.status_code}")
                                # If blocked (403 or 429), wait longer before retry
                                if response.status_code in [403, 429]:
                                    time.sleep(5 + retry * 5)  # 5s, 10s, 15s
                                else:
                                    time.sleep(1 + retry * 2)  # 1s, 3s, 5s
                        
                        except (requests.exceptions.RequestException, ConnectionError, TimeoutError) as e:
                            error_msg = str(e)
                            if retry < max_retries - 1:
                                # Increase backoff time for connection errors
                                backoff_time = 5 + retry * 3  # 5s, 15s, 25s
                                logger.warning(f"⚠️ Error downloading image {abs_idx + 1} for {offer_id} (attempt {retry+1}/{max_retries}): {error_msg}. Retrying in {backoff_time}s...")
                                time.sleep(backoff_time)
                            else:
                                logger.error(f"❌ Failed to download image {abs_idx + 1} for {offer_id} after {max_retries} attempts: {error_msg}")
                                error_count += 1
                
                # If we've had too many errors in this batch, pause for longer
                if error_count > success_count and error_count > 3:
                    recovery_time = 30 + random.random() * 30  # 30-60 seconds
                    logger.warning(f"⚠️ Too many errors, possibly being rate-limited. Taking a longer break for {recovery_time:.1f} seconds.")
                    time.sleep(recovery_time)
            
            logger.info(f"📊 Offer {offer_id}: Successfully downloaded {success_count} out of {len(images)} images, {error_count} errors")
            
        except Exception as e:
            logger.error(f"⚠️ Failed to process image download for offer {listing.get('offer_id')}: {e}")
                    
    def scrape(self, search_url, max_pages=5, max_distance_km=None, time_filter=None):
        url = f'{search_url}&totime={time_filter * 60}' if time_filter else search_url
        parsed_apts = self.collect_listings(url, max_pages)
        
        # Immediately save what we've collected, just in case
        backup_file = f'backup_{int(time.time())}_listings.json'
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump([{k: v for k, v in apt.items() if k != 'image_urls'} for apt in parsed_apts], f, ensure_ascii=False)
        logger.info(f"💾 Backup of listings saved to {backup_file}")
        
        # Download images independently, with better error handling
        logger.info(f"🖼️ Starting batch download of images for {len(parsed_apts)} listings")
        image_folder = 'images'
        os.makedirs(image_folder, exist_ok=True)
        
        # Get a list of offers that already have downloaded images
        already_downloaded = set()
        if os.path.exists(image_folder):
            for offer_id in os.listdir(image_folder):
                offer_path = os.path.join(image_folder, offer_id)
                if os.path.isdir(offer_path):
                    # If the folder exists and has at least one image, consider it downloaded
                    image_files = [f for f in os.listdir(offer_path) if f.endswith(('.jpg', '.jpeg', '.png'))]
                    if image_files:
                        already_downloaded.add(offer_id)
        
        logger.info(f"ℹ️ Found {len(already_downloaded)} offers with previously downloaded images")
        
        # Filter offers that need image downloads
        offers_to_download = [apt for apt in parsed_apts 
                             if 'offer_id' in apt 
                             and 'image_urls' in apt 
                             and apt['image_urls'] 
                             and str(apt['offer_id']) not in already_downloaded]
        
        logger.info(f"🖼️ Need to download images for {len(offers_to_download)} out of {len(parsed_apts)} offers")
        
        # Process in small batches with pauses between
        batch_size = 5
        for i in range(0, len(offers_to_download), batch_size):
            batch = offers_to_download[i:i+batch_size]
            logger.info(f"📦 Processing batch {i//batch_size + 1}/{(len(offers_to_download) + batch_size - 1)//batch_size}, listings {i+1}-{min(i+batch_size, len(offers_to_download))}")
            
            # Download images for this batch
            for apt in batch:
                self._download_images_for_listing(apt, image_folder)
            
            # Take a break between batches if not at the end
            if i + batch_size < len(offers_to_download):
                sleep_time = 10 + random.random() * 20  # 10-30 seconds
                logger.info(f"😴 Taking a break between batches: {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
        
        # Continue with the rest of your code
        combined_apts = self._combine_with_existing(parsed_apts)
        self._process_distances(combined_apts)
        result = self._save_data(combined_apts)
        
        print(f"Changes: +{self.new} new, -{self.removed} removed, {self.price_changes} price changes")
        return result

if __name__ == '__main__':
    csv_file = 'cian_apartments.csv'
    base_url = 'https://www.cian.ru/cat.php?currency=2&deal_type=rent&district%5B0%5D=13&district%5B1%5D=21&engine_version=2&maxprice=100000&metro%5B0%5D=4&metro%5B10%5D=86&metro%5B11%5D=115&metro%5B12%5D=118&metro%5B13%5D=120&metro%5B14%5D=134&metro%5B15%5D=143&metro%5B16%5D=151&metro%5B17%5D=159&metro%5B18%5D=310&metro%5B1%5D=8&metro%5B2%5D=12&metro%5B3%5D=18&metro%5B4%5D=20&metro%5B5%5D=33&metro%5B6%5D=46&metro%5B7%5D=56&metro%5B8%5D=63&metro%5B9%5D=80&offer_type=flat&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1&room9=1&sort=creation_date_desc&type=4'
    #csv_file = 'cian_apartments_large.csv'
    #base_url = 'https://www.cian.ru/cat.php?currency=2&deal_type=rent&district%5B0%5D=4&district%5B1%5D=88&district%5B2%5D=101&district%5B3%5D=113&engine_version=2&maxprice=100000&offer_type=flat&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1&room9=1&type=4'

    
    scraper = CianScraper(headless=True, csv_filename=csv_file)
    result = scraper.scrape(search_url=base_url, max_pages=100)
    print(f'Scraping completed: {len(result)} apartments processed')
