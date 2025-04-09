# filename: cian_scraper_part2.py

import os, time, logging, math, re
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from utils import parse_updated_time  # Make sure this is working!

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CianScraper')


class CianDetailFetcher:
    def __init__(self, chrome_options):
        self.chrome_options = chrome_options

    def fetch_page_data(self, update_item):
        url = update_item.get('url')
        update_type = update_item.get('update_type')
        item_id = update_item.get('item_id')

        if not url or not update_type or not item_id:
            return {'item_id': item_id, 'success': False, 'error': 'Invalid update item'}

        logger.info(f'Fetching {update_type} data for ID {item_id}: {url}')
        max_retries, base_delay = 3, 2

        for attempt in range(1, max_retries + 1):
            driver = None
            try:
                driver = webdriver.Chrome(options=self.chrome_options)
                driver.get(url)
                time.sleep(1)

                scroll_steps = [0.5] if attempt == 1 else [0.2, 0.5, 0.8]
                for pos in scroll_steps:
                    driver.execute_script(f'window.scrollTo(0, document.body.scrollHeight*{pos});')
                    time.sleep(1)

                result = {
                    'item_id': item_id,
                    'update_type': update_type,
                    'success': True
                }

                if update_type == 'estimation':
                    selector = "[data-testid='valuation_estimationPrice'] .a10a3f92e9--price--w7ha0 span"
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)

                    # Set default empty values
                    result['cian_estimation'] = ''
                    result['cian_estimation_value'] = None
                    
                    # Update with actual values if found
                    for el in elements:
                        text = el.text.strip()
                        if text:
                            result['cian_estimation'] = text
                            # Extract numeric value directly here
                            try:
                                digits = re.sub(r'[^\d]', '', text)
                                result['cian_estimation_value'] = float(digits) if digits else None
                            except (ValueError, TypeError):
                                result['cian_estimation_value'] = None
                            break
                            
                    return result

                elif update_type == 'unpublished':
                    unpublished_xpath = "//div[@data-name='OfferUnpublished' and contains(text(), 'Объявление снято с публикации')]"
                    elements = driver.find_elements(By.XPATH, unpublished_xpath)
                    result['is_unpublished'] = bool(elements)

                    if result['is_unpublished']:
                        date_xpath = "//span[contains(text(), 'Обновлено:')]"
                        date_elements = driver.find_elements(By.XPATH, date_xpath)
                        status_date = '--'
                        if date_elements:
                            text = date_elements[0].text
                            if 'Обновлено:' in text:
                                status_date = parse_updated_time(text.replace('Обновлено:', '').strip())
                        result['unpublished_date'] = status_date

                    return result

            except Exception as e:
                if attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(f'Attempt {attempt}/{max_retries} failed for ID {item_id}: {e}')
                    time.sleep(delay)
                else:
                    logger.error(f'All attempts failed for ID {item_id}: {e}')
                    result = {
                        'item_id': item_id,
                        'update_type': update_type,
                        'success': False,
                        'error': str(e)
                    }
                    if update_type == 'unpublished':
                        result['is_unpublished'] = True
                        result['unpublished_date'] = f"-- (connection error on {datetime.now().strftime('%Y-%m-%d')})"
                    return result
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass

        return {
            'item_id': item_id,
            'update_type': update_type,
            'success': False,
            'error': 'Maximum retry attempts reached'
        }


class CianScraper:
    def __init__(self, headless=True, intermediate_csv='cian_apartments_large.csv',
                 final_csv='cian_apartments_large.csv', max_distance_km=3):
        chrome_opts = Options()
        if headless:
            chrome_opts.add_argument('--headless')
        for arg in ['--disable-gpu', '--window-size=1920,1080', '--disable-extensions',
                    '--no-sandbox', '--disable-dev-shm-usage']:
            chrome_opts.add_argument(arg)
        chrome_opts.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36')
        self.chrome_options = chrome_opts
        self.intermediate_csv = intermediate_csv
        self.final_csv = final_csv
        self.max_distance_km = max_distance_km
        self.fetcher = CianDetailFetcher(chrome_options=self.chrome_options)

    def _is_empty(self, val):
        return (
            val in [None, '', '--']
            or (isinstance(val, str) and val.strip().lower() in ['nan', 'n/a', 'none', ''])
            or (isinstance(val, float) and math.isnan(val))
        )

    def _load_data(self):
        if not os.path.exists(self.intermediate_csv):
            logger.warning("Intermediate CSV not found.")
            return []
        try:
            df = pd.read_csv(self.intermediate_csv, encoding='utf-8', comment='#')
            logger.info(f"Loaded {len(df)} rows from intermediate CSV.")
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            return []

    def _process_updates(self, apartments):
        update_items, keep_as_is = [], []
        stats = {'estimation': 0, 'unpublished': 0, 'unchanged': 0}

        for apt in apartments:
            offer_id = str(apt.get('offer_id', ''))
            distance_raw = str(apt.get('distance', '')).replace(',', '.')
            try:
                distance = float(distance_raw)
            except:
                distance = float('inf')

            # Use cian_estimation_value instead of cian_estimation
            est_value = apt.get('cian_estimation_value')
            status = apt.get('status')
            unpub = apt.get('unpublished_date')
            update_type = None

            if self._is_empty(est_value) and distance <= self.max_distance_km:
                update_type = 'estimation'
            elif status == 'non active' and self._is_empty(unpub):
                update_type = 'unpublished'

            if update_type:
                update_items.append({
                    'url': apt['offer_url'], 'item_id': offer_id,
                    'update_type': update_type, 'original_data': apt
                })
            else:
                keep_as_is.append(apt)
                stats['unchanged'] += 1

        logger.info(f"Queued {len(update_items)} updates: "
                    f"{sum(1 for i in update_items if i['update_type'] == 'estimation')} estimation, "
                    f"{sum(1 for i in update_items if i['update_type'] == 'unpublished')} unpublished")

        results = list(keep_as_is)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.fetcher.fetch_page_data, item): item for item in update_items}
            for future in futures:
                try:
                    result = future.result()
                    item = futures[future]
                    apt = item['original_data'].copy()
                    offer_id = item['item_id']
                    update_type = item['update_type']

                    if not result.get('success'):
                        logger.warning(f"[{offer_id}] Update failed: {result.get('error')}")
                        results.append(apt)
                        continue

                    if update_type == 'estimation':
                        # Use values directly from the fetcher result
                        apt['cian_estimation'] = result['cian_estimation']
                        apt['cian_estimation_value'] = result['cian_estimation_value']
                        
                        logger.info(f"[{offer_id}] Estimation updated: {apt['cian_estimation']} (value: {apt['cian_estimation_value']})")
                        stats['estimation'] += 1

                    elif update_type == 'unpublished':
                        apt['status'] = 'non active'
                        apt['unpublished_date'] = result.get('unpublished_date', '--')
                        logger.info(f"[{offer_id}] Marked unpublished: {apt['unpublished_date']}")
                        stats['unpublished'] += 1

                    results.append(apt)

                except Exception as e:
                    logger.error(f"Future failed: {e}")

        total = len(apartments)
        logger.info(f"Processed {total} listings: {stats['estimation']} updated (estimation), "
                    f"{stats['unpublished']} unpublished, {stats['unchanged']} unchanged")
        return results

    def process(self):
        apartments = self._load_data()
        if not apartments:
            logger.info("No apartment data loaded.")
            return []
        updated = self._process_updates(apartments)
        pd.DataFrame(updated).to_csv(self.final_csv, index=False)
        return updated


if __name__ == '__main__':
    scraper = CianScraper(headless=True)
    final = scraper.process()
    print(f"Completed: {len(final)} listings processed.")