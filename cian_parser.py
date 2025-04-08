import os, re, logging
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np
from selenium.webdriver.chrome.options import Options
from distance import get_coordinates, calculate_distance
from listings_collector import CianListingCollector
from details_fetcher import CianDetailFetcher
from data_processor import CianDataProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CianScraper')

class CianScraper:
    def __init__(self, headless=True, csv_filename='cian_apartments.csv', 
                reference_address='Москва, переулок Большой Саввинский, 3'):
        # Setup Chrome options
        chrome_opts = Options()
        chrome_args = ['--disable-gpu', '--window-size=1920,1080', '--disable-extensions', 
                      '--no-sandbox', '--disable-dev-shm-usage']
        if headless:
            chrome_args.append('--headless')
        
        for arg in chrome_args:
            chrome_opts.add_argument(arg)
            
        chrome_opts.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
        
        # Core setup
        self.url_base = 'https://www.cian.ru'
        self.csv_filename = csv_filename
        self.reference_address = reference_address
        self.unpublished_ids = set()
        self.apartments = []
        
        # Load data and initialize components
        self.existing_data = {}
        self._load_existing_data()
        self.collector = CianListingCollector(self.url_base, chrome_opts)
        self.detail_fetcher = CianDetailFetcher(chrome_opts)
        self.data_processor = CianDataProcessor(csv_filename)

    def _load_existing_data(self):
        """Load existing data from CSV if available"""
        if not os.path.exists(self.csv_filename):
            self.existing_data, self.existing_df = {}, pd.DataFrame()
            return
            
        try:
            df = pd.read_csv(self.csv_filename, encoding='utf-8', comment='#')
            self.existing_df = df
            self.existing_data = {str(row.get('offer_id', '')): row.to_dict() 
                                 for _, row in df.iterrows() if row.get('offer_id', '')}
            logger.info(f'Loaded {len(self.existing_data)} existing entries')
        except Exception as e:
            logger.error(f'Error loading data: {e}')
            self.existing_data, self.existing_df = {}, pd.DataFrame()

    def _combine_with_existing(self, new_apts):
        """
        Merge newly parsed apartments with existing data.
        Returns a list of combined apartments with appropriate price change calculations.
        """
        combined_apts = []
        
        for apt in new_apts:
            offer_id = apt.get('offer_id')
            if not offer_id:
                continue
                
            # Check if apartment exists in our records
            if offer_id in self.existing_data:
                existing = self.existing_data[offer_id]
                
                # Extract prices for comparison
                new_price = self._extract_price(apt.get('price', ''))
                old_price = self._extract_price(existing.get('price', ''))
                
                if new_price != old_price:
                    # Price changed - update data
                    merged = apt.copy()
                    
                    # Calculate price change and add it
                    if new_price and old_price:
                        merged['price_change_value'] = new_price - old_price
                    
                    # Preserve estimation if it exists
                    if 'cian_estimation' in existing and not self._is_empty_value(existing.get('cian_estimation')):
                        merged['cian_estimation'] = existing['cian_estimation']
                        
                    combined_apts.append(merged)
                else:
                    # Price unchanged - keep existing data but update with new fields
                    merged = existing.copy()
                    
                    # Update basic data from new listing
                    for field in ['address', 'price']:
                        if field in apt:
                            merged[field] = apt[field]
                    
                    # Keep the offer URL updated
                    if 'offer_url' in apt:
                        merged['offer_url'] = apt['offer_url']
                    
                    combined_apts.append(merged)
            else:
                # New apartment - add with "new" marker
                new_record = apt.copy()
                new_record['price_change_value'] = 'new'
                combined_apts.append(new_record)
        
        return combined_apts

    def _classify_updates(self, apartments):
        """
        Classify apartments to determine what updates are needed.
        Returns a list of items that need estimation updates.
        """
        need_estimation = []
        
        for apt in apartments:
            offer_id = apt.get('offer_id')
            if not offer_id:
                continue
            
            # Skip if no URL available
            if 'offer_url' not in apt:
                continue
                
            # New apartments always need estimation
            if apt.get('price_change_value') == 'new':
                need_estimation.append({
                    'url': apt['offer_url'],
                    'item_id': offer_id,
                    'update_type': 'estimation',
                    'original_data': apt,
                    'data_source': 'new_apartment'
                })
                continue
                
            # Price changed apartments need estimation
            if 'price_change_value' in apt and apt['price_change_value'] != 'new':
                need_estimation.append({
                    'url': apt['offer_url'],
                    'item_id': offer_id,
                    'update_type': 'estimation',
                    'original_data': apt,
                    'data_source': 'price_changed'
                })
                continue
                
            # Apartments missing estimation need it
            if self._is_empty_value(apt.get('cian_estimation')):
                need_estimation.append({
                    'url': apt['offer_url'],
                    'item_id': offer_id,
                    'update_type': 'estimation',
                    'original_data': apt,
                    'data_source': 'missing_estimation'
                })
                
        return need_estimation

    def _identify_unpublished(self, combined_apts, collected_ids):
        """Identify potentially unpublished listings"""
        unpublished_checks = []
        keep_as_is = []
        
        # Get all IDs from combined apartments
        combined_ids = {apt.get('offer_id') for apt in combined_apts if apt.get('offer_id')}
        
        # Find IDs that were in existing data but not in current results
        missing_ids = set(self.existing_data.keys()) - collected_ids
        
        for item_id in missing_ids:
            # Skip if already in combined apartments
            if item_id in combined_ids:
                continue
                
            data = self.existing_data.get(item_id, {})
            if 'offer_url' not in data:
                continue
                
            # Skip if already marked as non-active with valid date
            if data.get('status') == 'non active' and self._has_valid_unpublished_date(data):
                keep_as_is.append(data.copy())
                continue
                
            # Add to unpublished checks
            unpublished_checks.append({
                'url': data['offer_url'],
                'item_id': item_id,
                'update_type': 'unpublished',
                'original_data': data,
                'data_source': 'unpublished_check'
            })
        
        return unpublished_checks, keep_as_is

    def _process_distances(self, apartments):
        """Calculate distances for apartments"""
        try:
            ref_coords = get_coordinates(self.reference_address)
            preserved, calculated, failed = 0, 0, 0
            
            for apt in apartments:
                # Try to use existing distance
                distance = apt.get('distance')
                try:
                    if distance and not (isinstance(distance, float) and (np.isnan(distance) or np.isinf(distance))):
                        apt['distance'] = float(distance) if isinstance(distance, str) else distance
                        preserved += 1
                        continue
                except (ValueError, TypeError):
                    pass
                
                # Calculate new distance
                address = apt.get('address', '')
                if not address:
                    failed += 1
                    continue
                    
                try:
                    full_address = f"Москва, {address}" if 'Москва' not in address else address
                    apt['distance'] = round(calculate_distance(ref_coords, full_address), 2)
                    calculated += 1
                except Exception:
                    failed += 1
            
            logger.info(f'Distance processing: {preserved} preserved, {calculated} calculated, {failed} failed')
        except Exception as e:
            logger.error(f'Distance calculation error: {e}')

    def _extract_price(self, price_str):
        """Extract numeric price value"""
        if not price_str:
            return None
        if isinstance(price_str, (int, float)):
            return float(price_str)
        try:
            return float(re.sub(r'[^\d]', '', str(price_str)) or 0)
        except (ValueError, TypeError):
            return None

    def _is_empty_value(self, val):
        """Check if a value is empty/invalid"""
        if val is None or val == '':
            return True
        if isinstance(val, str) and (val.strip().lower() == 'nan' or val.strip() == ''):
            return True
        if isinstance(val, float) and pd.isna(val):
            return True
        return False

    def _is_within_distance(self, apt, max_distance_km):
        """Check if apartment is within specified distance"""
        try:
            return float(apt.get('distance', float('inf'))) <= max_distance_km
        except (ValueError, TypeError):
            return False

    def _has_valid_unpublished_date(self, data):
        """Check if the apartment has a valid unpublished date"""
        unpub_date = data.get('unpublished_date')
        return unpub_date and unpub_date != '--' and not self._is_empty_value(unpub_date)

    def _process_updates(self, update_items, keep_as_is=None):
        """Process updates for apartments needing additional data"""
        if not update_items:
            return keep_as_is or []
            
        results = []
        logger.info(f'Processing {len(update_items)} update items')
        
        # Process updates in parallel
        update_results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.detail_fetcher.fetch_page_data, item): item 
                      for item in update_items}
            
            for future in futures:
                try:
                    update_results.append(future.result())
                except Exception as e:
                    item = futures[future]
                    logger.error(f'Error processing {item["update_type"]} for ID {item["item_id"]}: {e}')
        
        # Apply updates
        for result in update_results:
            if not result.get('success', False):
                continue
                
            item_id = result.get('item_id')
            update_type = result.get('update_type')
            
            # Find original update item
            update_item = next((item for item in update_items 
                              if item['item_id'] == item_id and 
                              item['update_type'] == update_type), None)
            
            if not update_item:
                continue
                
            original_data = update_item.get('original_data', {}).copy()
            
            # Apply estimation updates
            if update_type == 'estimation' and 'cian_estimation' in result:
                original_data['cian_estimation'] = result['cian_estimation']
                results.append(original_data)
                
            # Apply unpublished updates    
            elif update_type == 'unpublished' and result.get('is_unpublished', False):
                original_data['status'] = 'non active'
                original_data['unpublished_date'] = result.get('unpublished_date', '--')
                results.append(original_data)
                self.unpublished_ids.add(original_data.get('offer_id', ''))
        
        # Add apartments that don't need updates
        if keep_as_is:
            processed_ids = {apt.get('offer_id') for apt in results if apt.get('offer_id')}
            results.extend([apt for apt in keep_as_is if apt.get('offer_id') not in processed_ids])
        
        return results

    def scrape(self, search_url, max_pages=5, max_distance_km=3, time_filter=None):
        """Improved scraping workflow with cleaner separation of processes"""
        logger.info(f'Starting scrape: max_pages={max_pages}, max_distance={max_distance_km}km')
        
        # Apply time filter if provided
        url = f'{search_url}&totime={time_filter * 60}' if time_filter else search_url
        
        # Step 1: Collect listings from search pages
        all_apts = self.collector.collect_listings(url, max_pages, self.existing_data)
        if not all_apts:
            logger.warning('No apartments found!')
            return []
            
        # Get collected IDs for unpublished detection
        collected_ids = {apt['offer_id'] for apt in all_apts if 'offer_id' in apt}
        
        # Step 2: Calculate distances
        self._process_distances(all_apts)
        
        # Step 3: Merge with existing data
        combined_apts = self._combine_with_existing(all_apts)
        
        # Step 4: Filter by distance
        within_distance = []
        outside_distance = []
        
        for apt in combined_apts:
            if self._is_within_distance(apt, max_distance_km):
                within_distance.append(apt)
            else:
                apt['outside_distance'] = True
                outside_distance.append(apt)
        
        # Step 5: Classify what needs updating
        need_estimation = self._classify_updates(within_distance)
        
        # Step 6: Check for unpublished listings
        unpublished_checks, unpublished_keep = self._identify_unpublished(combined_apts, collected_ids)
        
        # Step 7: Process updates
        updated_within = self._process_updates(need_estimation, within_distance)
        unpublished_results = self._process_updates(unpublished_checks) if unpublished_checks else []
        
        # Step 8: Combine all results
        all_results = updated_within + outside_distance + unpublished_results + unpublished_keep
        
        # Step 9: Final processing
        self.apartments = self.data_processor.finalize_data(all_results, self.existing_df)
        return self.apartments

if __name__ == '__main__':
    # Example usage
    csv_file = 'cian_apartments.csv'
    base_url = 'https://www.cian.ru/cat.php?currency=2&deal_type=rent&engine_version=2&maxprice=64000&metro%5B0%5D=118&minprice=64000&offer_type=flat&room1=1&room2=1&type=4'
    
    scraper = CianScraper(headless=True, csv_filename=csv_file)
    apartments = scraper.scrape(search_url=base_url, max_pages=20, max_distance_km=5)
    
    print(f'Total apartments processed: {len(apartments)}')