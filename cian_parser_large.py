import re, os, json, time, logging
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
from listings_collector import CianListingCollector
from details_fetcher import CianDetailFetcher
from data_processor import CianDataProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CianScraper')


class CianScraper:
    def __init__(self, headless=True, csv_filename='cian_apartments_large.csv', 
                reference_address='Москва, переулок Большой Саввинский, 3'):
        # Browser options
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--disable-extensions')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        
        # Core attributes
        self.url_base = 'https://www.cian.ru'
        self.apartments = []
        self.csv_filename = csv_filename
        self.reference_address = reference_address
        
        # Load existing data
        self.existing_data = {}
        self._load_existing_data()
        
        # Initialize helper classes
        self.collector = CianListingCollector(self.url_base, self.chrome_options)
        self.detail_fetcher = CianDetailFetcher(self.chrome_options)
        self.data_processor = CianDataProcessor(csv_filename)

    def _load_existing_data(self):
        """Load existing data for comparison"""
        if os.path.exists(self.csv_filename):
            try:
                df = pd.read_csv(self.csv_filename, encoding='utf-8', comment='#')
                self.existing_df = df
                self.existing_data = {str(row.get('offer_id', '')): row.to_dict() 
                                    for _, row in df.iterrows() if row.get('offer_id', '')}
                logger.info(f'Loaded {len(self.existing_data)} existing entries')
            except Exception as e:
                logger.error(f'Error loading data: {e}')
                self.existing_data = {}
                self.existing_df = pd.DataFrame()

    def scrape(self, search_url, max_pages=5, max_distance_km=3, time_filter=None):
        """Main scraping workflow"""
        logger.info(f'Starting scrape: max_pages={max_pages}, max_distance={max_distance_km}km')
        
        # Apply time filter if provided
        url = f'{search_url}&totime={time_filter * 60}' if time_filter else search_url
        
        # Step 1: Collect basic data from search pages
        all_apts = self.collector.collect_listings(url, max_pages, self.existing_data)
        collected_ids = {apt['offer_id'] for apt in all_apts if 'offer_id' in apt}
        
        if not all_apts:
            logger.warning('No apartments found!')
            return []
            
        # Step 2: Calculate distances and categorize apartments
        self._process_distances(all_apts)
        
        # Step 3: Determine update strategy and process
        full_updates, estimation_updates, keep_as_is = self._classify_updates(all_apts, max_distance_km)
        self._process_updates(full_updates, estimation_updates, keep_as_is)
        
        # Step 4: Check for unpublished listings
        self._check_for_unpublished_listings(collected_ids)
        
        # Step 5: Final processing and saving
        self.apartments = self.data_processor.finalize_data(self.apartments, self.existing_df)
        return self.apartments

    def _process_distances(self, apartments):
        """Calculate distances for apartments"""
        logger.info('Processing distances...')
        try:
            ref_coords = get_coordinates(self.reference_address)
            preserved, calculated, failed = 0, 0, 0
            
            for apt in apartments:
                # Use existing valid distance if available
                distance = apt.get('distance')
                if distance is not None and distance != '':
                    try:
                        distance_val = float(distance) if isinstance(distance, str) else distance
                        if not np.isnan(distance_val) and not np.isinf(distance_val):
                            apt['distance'] = distance_val
                            preserved += 1
                            continue
                    except (ValueError, TypeError):
                        pass
                
                # Calculate new distance
                try:
                    address = apt.get('address', '')
                    if not address:
                        failed += 1
                        continue
                        
                    full_address = f"Москва, {address}" if 'Москва' not in address else address
                    distance_km = calculate_distance(from_point=ref_coords, to_address=full_address)
                    apt['distance'] = round(distance_km, 2)
                    calculated += 1
                    
                except Exception as e:
                    logger.error(f'Error calculating distance: {e}')
                    failed += 1
            
            logger.info(f'Distance processing: {preserved} preserved, {calculated} calculated, {failed} failed')
            
        except Exception as e:
            logger.error(f'Distance calculation error: {e}')

    def extract_price_value(self, price_str):
        """Extract numeric value from price string"""
        if not price_str:
            return None
        if isinstance(price_str, (int, float)):
            return float(price_str)
        digits = re.sub(r'[^\d]', '', str(price_str))
        try:
            return float(digits) if digits else None
        except ValueError:
            return None

    
    def _classify_updates(self, apartments, max_distance_km):
        """Determine which apartments need which updates"""

        within_distance, outside_distance = [], []
        
        for apt in apartments:
            try:
                distance = float(apt.get('distance', float('inf')))
                (within_distance if distance <= max_distance_km else outside_distance).append(apt)
            except (ValueError, TypeError):
                outside_distance.append(apt)
        
        logger.info(f'Distance categorization: {len(within_distance)} within {max_distance_km}km, {len(outside_distance)} outside')

        full_updates = []        # Need detail page fetch
        estimation_updates = []  # Only need estimation fetch
        keep_as_is = []          # Keep without changes


        # Process apartments within distance
        for apt in within_distance:
            id = apt['offer_id']
            
            if id in self.existing_data:
                # Compare prices
                ex_price = self.existing_data[id].get('price', '')
                ex_price_val = self.extract_price_value(ex_price)
                cur_price_val = self.extract_price_value(apt.get('price', ''))
                
                # Check if estimation is missing
                est = self.existing_data[id].get('cian_estimation', '')
                est_empty = (
                    est is None or est == '' or 
                    (isinstance(est, str) and (est.strip().lower() == 'nan' or est.strip() == '')) or
                    (isinstance(est, float) and pd.isna(est))
                )
                
                if ex_price_val != cur_price_val:
                    # Price changed - do full update
                    price_diff = cur_price_val - ex_price_val if ex_price_val and cur_price_val else None
                    if price_diff is not None:
                        apt['price_change'] = f'From {ex_price_val} to {cur_price_val} ({price_diff:+.0f} ₽)'
                        apt['price_change_value'] = price_diff
                    full_updates.append(apt)
                    '''elif est_empty:
                        estimation_updates.append(apt)'''
                else:
                    keep_as_is.append(apt)
            else:
                # New apartment - do full update
                apt['price_change_value'] = 'new'
                full_updates.append(apt)
        
        # For apartments outside distance, keep without fetching details
        for apt in outside_distance:
            apt['outside_distance'] = True
            keep_as_is.append(apt)
        
        logger.info(f'Update classification: {len(full_updates)} full, {len(estimation_updates)} estimation, {len(keep_as_is)} unchanged')
        return full_updates, estimation_updates, keep_as_is

    def _process_updates(self, full_updates, estimation_updates, keep_as_is):
        """Process apartment updates based on classification"""
        results = []
        
        # Process full updates
        if full_updates:
            logger.info(f'Processing {len(full_updates)} full updates')
            with ThreadPoolExecutor(max_workers=4) as ex:
                updated_full = list(ex.map(self.detail_fetcher.fetch_details, full_updates))
            results.extend(updated_full)
            
        # Process estimation-only updates
        if estimation_updates:
            logger.info(f'Processing {len(estimation_updates)} estimation updates')
            with ThreadPoolExecutor(max_workers=4) as ex:
                updated_estimation = list(ex.map(self.detail_fetcher.fetch_details, estimation_updates))
            
            # Update existing listings with new estimation
            for apt in updated_estimation:
                if apt.get('offer_id') and apt.get('cian_estimation'):
                    orig_apt = next((a for a in keep_as_is if a.get('offer_id') == apt.get('offer_id')), None)
                    if orig_apt:
                        orig_apt['cian_estimation'] = apt['cian_estimation']
                    else:
                        results.append({
                            'offer_id': apt['offer_id'],
                            'cian_estimation': apt['cian_estimation']
                        })
        
        # Add apartments that don't need updates
        if keep_as_is:
            logger.info(f'Adding {len(keep_as_is)} apartments without changes')
            processed_ids = {apt.get('offer_id') for apt in results if apt.get('offer_id')}
            results.extend([apt for apt in keep_as_is if apt.get('offer_id') not in processed_ids])
        
        self.apartments = results

    def _check_for_unpublished_listings(self, collected_ids):
        """Check which existing listings are now unpublished"""
        if not self.existing_data:
            return
            
        # Find IDs that were in existing data but not in current results
        existing_ids = set(self.existing_data.keys())
        missing_ids = existing_ids - collected_ids
        
        if not missing_ids:
            logger.info('No missing listings to check')
            return
            
        logger.info(f'Found {len(missing_ids)} previously listed but now missing IDs')
        unpublished_data = []
        already_unpublished = 0
        needs_checking = 0
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            # Submit tasks only for IDs that aren't already marked as unpublished
            for id in missing_ids:
                if id not in self.existing_data or 'offer_url' not in self.existing_data[id]:
                    continue
                    
                # Skip if already marked as non-active in previous runs
                existing_status = self.existing_data[id].get('status', '')
                if existing_status == 'non active':
                    # Add the existing unpublished data directly
                    unpublished_data.append(self.existing_data[id].copy())
                    already_unpublished += 1
                    continue
                    
                # Only check active listings that disappeared
                url = self.existing_data[id]['offer_url']
                futures[executor.submit(
                    self.detail_fetcher.check_single_unpublished, 
                    id, 
                    url, 
                    self.existing_data
                )] = id
                needs_checking += 1
                
            logger.info(f'Checking unpublished status: {needs_checking} need checking, {already_unpublished} already marked as unpublished')
                
            # Process results
            for future in futures:
                try:
                    result = future.result()
                    if result:
                        unpublished_data.append(result)
                except Exception as e:
                    logger.error(f'Error checking unpublished status: {e}')

        if unpublished_data:
            # Add unpublished listings to results
            self.unpublished_ids = {item['offer_id'] for item in unpublished_data if 'offer_id' in item}
            self.apartments.extend(unpublished_data)
            logger.info(f'Added {len(unpublished_data)} unpublished listings to results')

  
if __name__ == '__main__':
    # Example usage
    csv_file = 'cian_apartments_large.csv'
    base_url = 'https://www.cian.ru/cat.php?currency=2&deal_type=rent&district%5B0%5D=4&district%5B1%5D=88&district%5B2%5D=101&district%5B3%5D=113&engine_version=2&maxprice=100000&offer_type=flat&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1&room9=1&type=4'
    
    # Create scraper and run full workflow
    scraper = CianScraper(headless=True, csv_filename=csv_file)
    apartments = scraper.scrape(
        search_url=base_url,
        max_pages=50,
        max_distance_km=20
    )
    
    print(f'Total apartments processed: {len(apartments)}')