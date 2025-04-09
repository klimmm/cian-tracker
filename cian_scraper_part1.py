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
from utils import parse_updated_time
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CianScraper')

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
                cards = soup.select("article[data-name='CardComponent']")
                if not cards:
                    logger.info('No cards found on page. Stopping forward loop.')
                    break
    
                current_page_ids = set()
                page_listings_map[page] = []
                page_new_listings_count = 0
    
                for card in cards:
                    data = self._parse_card(card)
                    if not data or 'offer_id' not in data:
                        continue
    
                    offer_id = str(data['offer_id'])
                    current_page_ids.add(offer_id)
                    page_listings_map[page].append(offer_id)
    
                    if offer_id not in added_ids:
                        data['status'] = 'active'
                        data['unpublished_date'] = '--'
                        if offer_id in self.existing_data and 'distance' in self.existing_data[offer_id]:
                            data['distance'] = self.existing_data[offer_id]['distance']
                        all_apts.append(data)
                        added_ids[offer_id] = page
                        page_new_listings_count += 1
    
                logger.info(f'Page {page}: Collected {page_new_listings_count} new listings')
                logger.info(f'Collected {len(all_apts)} / {total_listings} so far')
    
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
                    cards = soup.select("article[data-name='CardComponent']")
                    if not cards:
                        logger.warning(f"No cards found on page {reverse_page}")
                        continue
    
                    page_new_listings_count = 0
                    for card in cards:
                        data = self._parse_card(card)
                        if not data or 'offer_id' not in data:
                            continue
                        offer_id = str(data['offer_id'])
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
    
        logger.info(f'Collection complete: {len(all_apts)} listings collected after {total_pages_processed} pages')
        return all_apts
    
                    
    def _parse_card(self, card):
        try:
            data = {
                'offer_id': '', 'offer_url': '', 'updated_time': '', 'title': '',
                'price': '', 'price_info': '', 'address': '', 'metro_station': '', 
                'neighborhood': '', 'district': '', 'description': '', 'image_urls': [], 
                'distance': None
            }
            if link := card.select_one("a[href*='/rent/flat/']"):
                url = link.get('href')
                data['offer_url'] = self.url_base + url if url.startswith('/') else url
                if m := re.search(r'/rent/flat/(\d+)/', url):
                    data['offer_id'] = m.group(1)
            if title := card.select_one('[data-mark="OfferTitle"]'):
                data['title'] = title.get_text(strip=True)
            if price := card.select_one('[data-mark="MainPrice"]'):
                data['price'] = price.get_text(strip=True)

            if price_info := card.select_one('[data-mark="PriceInfo"]'):
                price_info_text = price_info.get_text(strip=True)
                data['price_info'] = price_info_text
                
                # Initialize numeric fields
                data['commission_value'] = None
                data['deposit_value'] = None
                
                # Extract info from parts
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
            if desc := card.select_one('div[data-name="Description"] p'):
                data['description'] = desc.get_text(strip=True)
            if time_el := card.select_one('div[data-name="TimeLabel"] div._93444fe79c--absolute--yut0v span'):
                data['updated_time'] = parse_updated_time(time_el.get_text(strip=True))
            data['image_urls'] = [img.get('src') for img in card.select('img._93444fe79c--container--KIwW4') if img.get('src')]
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

    def scrape(self, search_url, max_pages=5, max_distance_km=None, time_filter=None):
        url = f'{search_url}&totime={time_filter * 60}' if time_filter else search_url
        parsed_apts = self.collect_listings(url, max_pages)
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
