import os, re, logging
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np
from selenium.webdriver.chrome.options import Options
from distance import get_coordinates, calculate_distance
from listings_collector import CianListingCollector
from details_fetcher import CianDetailFetcher
from datetime import datetime
import json

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
        self.apartments = []
        
        # Load data and initialize components
        self._load_existing_data()
        self.collector = CianListingCollector(self.url_base, chrome_opts)
        self.detail_fetcher = CianDetailFetcher(chrome_opts)

    def _load_existing_data(self):
        self.existing_data, self.existing_df = {}, pd.DataFrame()
        if not os.path.exists(self.csv_filename):
            logger.info('No existing data file found')
            return
            
        try:
            df = pd.read_csv(self.csv_filename, encoding='utf-8', comment='#')
            self.existing_df = df
            
            # Convert dataframe to dictionary with proper handling of estimations
            self.existing_data = {}
            for _, row in df.iterrows():
                if 'offer_id' in row:
                    offer_id = str(row['offer_id'])
                    data = row.to_dict()
                    
                    # Handle the case where cian_estimation is missing but cian_estimation_value exists
                    if self._is_empty(data.get('cian_estimation')) and not self._is_empty(data.get('cian_estimation_value')):
                        data['cian_estimation'] = str(data['cian_estimation_value'])
                    
                    self.existing_data[offer_id] = data
            
            logger.info(f'Loaded {len(self.existing_data)} existing entries')
            
            # Log missing data in original file
            missing_est = sum(1 for _, data in self.existing_data.items() if self._is_empty(data.get('cian_estimation')))
            missing_unpub = sum(1 for _, data in self.existing_data.items() 
                            if data.get('status') == 'non active' and self._is_empty(data.get('unpublished_date')))
            
            logger.info(f'Original data - Missing: {missing_est} estimations, {missing_unpub} unpublished dates')
        except Exception as e:
            logger.error(f'Error loading data: {e}')

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
                (isinstance(val, str) and (val.strip().lower() == 'nan' or val.strip() == '')) or
                (isinstance(val, float) and pd.isna(val)))

    def _combine_with_existing(self, new_apts):
        logger.info(f'Combining {len(new_apts)} new apartments with {len(self.existing_data)} existing entries')
        combined_apts = []
        new_ids = set(apt['offer_id'] for apt in new_apts if 'offer_id' in apt)
    
        for apt in new_apts:
            if 'offer_id' not in apt:
                continue
            offer_id = apt['offer_id']
            
            # Explicitly mark as active for all apartments in new data
            apt['status'] = 'active'
            apt.setdefault('unpublished_date', '--')
    
            if offer_id in self.existing_data:
                existing = self.existing_data[offer_id]
                
                # Compare prices
                new_price = self._extract_price(apt.get('price'))
                old_price = self._extract_price(existing.get('price'))
                
                if new_price != old_price:
                    merged = apt.copy()
                    if new_price and old_price:
                        merged['price_change_value'] = new_price - old_price
                    
                    # Preserve estimation if it exists
                    if not self._is_empty(existing.get('cian_estimation')):
                        merged['cian_estimation'] = existing['cian_estimation']
                    if not self._is_empty(existing.get('cian_estimation_value')):
                        merged['cian_estimation_value'] = existing['cian_estimation_value']
                    
                    combined_apts.append(merged)
                else:
                    merged = existing.copy()
                    # Set status to active for existing apartments that are still active
                    merged['status'] = 'active'
                    merged['unpublished_date'] = '--'
                    
                    combined_apts.append(merged)
            else:
                apt['price_change_value'] = '--'
                combined_apts.append(apt)
    
        # Add missing apartments (mark as non-active)
        missing_ids = set(self.existing_data.keys()) - new_ids
        for missing_id in missing_ids:
            existing = self.existing_data.get(missing_id)
            if existing:
                existing = existing.copy()
                existing['status'] = 'non active'
                
                # Ensure unpublished_date is preserved or set default
                if 'unpublished_date' not in existing or self._is_empty(existing.get('unpublished_date')):
                    existing['unpublished_date'] = '--'
                
                combined_apts.append(existing)
        
        logger.info(f'Combined total: {len(combined_apts)} entries, {len(missing_ids)} marked non-active')
        return combined_apts

    def _process_distances(self, apartments):
        try:
            ref_coords = get_coordinates(self.reference_address)
            preserved, calculated, failed = 0, 0, 0
            
            for apt in apartments:
                distance = apt.get('distance')
                if distance and not (isinstance(distance, float) and (np.isnan(distance) or np.isinf(distance))):
                    apt['distance'] = float(distance) if isinstance(distance, str) else distance
                    preserved += 1
                    continue
                
                address = apt.get('address', '')
                if address:
                    try:
                        full_address = f"Москва, {address}" if 'Москва' not in address else address
                        apt['distance'] = round(calculate_distance(from_point=ref_coords, to_address=full_address), 2)
                        calculated += 1
                    except:
                        failed += 1
                else:
                    failed += 1
            
            logger.info(f'Distance processing: {preserved} preserved, {calculated} calculated, {failed} failed')
        except Exception as e:
            logger.error(f'Distance calculation error: {e}')

    def _process_updates(self, apartments, max_distance_km=3):
        update_items = []
        keep_as_is = []
        
        # Count items needing updates
        need_estimation = 0
        need_unpublished = 0
        need_distance = 0
        
        for apt in apartments:
            if 'offer_id' not in apt or 'offer_url' not in apt:
                keep_as_is.append(apt)
                continue
            
            update_type = None
            distance = float(apt.get('distance', float('inf')))
            
            if self._is_empty(apt.get('cian_estimation')) and distance <= max_distance_km:
                update_type = 'estimation'
                need_estimation += 1
            elif apt.get('status') == 'non active' and self._is_empty(apt.get('unpublished_date')):
                update_type = 'unpublished'
                need_unpublished += 1
            elif apt.get('distance') is None or (isinstance(apt.get('distance'), float) and 
                  (np.isnan(apt.get('distance')) or np.isinf(apt.get('distance')))):
                update_type = 'distance'
                need_distance += 1
            
            if update_type:
                update_items.append({
                    'url': apt['offer_url'],
                    'item_id': apt['offer_id'],
                    'update_type': update_type,
                    'original_data': apt
                })
            else:
                keep_as_is.append(apt)
        
        logger.info(f'Updates needed: {len(update_items)} total '
                   f'({need_estimation} estimation, {need_unpublished} unpublished, {need_distance} distance)')
        
        if not update_items:
            return keep_as_is
            
        results = list(keep_as_is)
        updated_est = 0
        updated_unpub = 0
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.detail_fetcher.fetch_page_data, item): item for item in update_items}
            for future in futures:
                try:
                    result = future.result()
                    if not result.get('success', False):
                        continue
                        
                    item = futures[future]
                    updated = item['original_data'].copy()
                    
                    if item['update_type'] == 'estimation':
                        updated['cian_estimation'] = result['cian_estimation']
                        updated_est += 1
                    elif item['update_type'] == 'unpublished':
                        updated['status'] = 'non active'
                        updated['unpublished_date'] = result.get('unpublished_date', '--')
                        updated_unpub += 1
                    
                    results.append(updated)
                except Exception as e:
                    logger.error(f"Update failed for {futures[future]['item_id']}: {e}")
        
        logger.info(f'Successfully updated: {updated_est} estimations, {updated_unpub} unpublished dates')
        return results

    def _prepare_and_save_data(self, apartments, filename_suffix=""):
        """Prepare and save data to CSV and JSON with optional filename suffix"""
        if not apartments:
            return []
    
        try:
            # Set defaults and handle complex types
            for apt in apartments:
                apt.setdefault('status', 'active')
                apt.setdefault('unpublished_date', '--')
                apt.setdefault('cian_estimation', None)

            # Create a base for the output files
            base_filename = self.csv_filename.replace('.csv', '')
            current_csv = f"{base_filename}{filename_suffix}.csv"
            current_json = f"{base_filename}{filename_suffix}.json"

            # Convert to DataFrame and handle complex types
            df = pd.DataFrame([{k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict, np.ndarray)) else v 
                              for k, v in apt.items()} for apt in apartments])
            
            df['offer_id'] = df['offer_id'].astype(str)
            
            # Calculate days_active from updated_time
            if 'updated_time' in df.columns:
                try:
                    df['days_active'] = (datetime.now() - pd.to_datetime(df['updated_time'], errors='coerce')).dt.days
                except:
                    pass
            
            # Price calculations with preservation of original values
            if 'price' in df.columns:
                price_value = df['price'].apply(self._extract_price)
                
                if 'cian_estimation' in df.columns:
                    cian_value = df['cian_estimation'].apply(self._extract_price)
                    
                    valid_mask = price_value.notna() & cian_value.notna()
                    if valid_mask.any():
                        df.loc[valid_mask, 'price_difference_value'] = cian_value[valid_mask] - price_value[valid_mask]
                        df.loc[valid_mask, 'cian_estimation_value'] = cian_value[valid_mask]
            
            result = df.drop_duplicates('offer_id', keep='first').to_dict('records')
            
            # Save data
            if result:
                # Prioritize columns
                priority_cols = ['offer_id', 'offer_url', 'title', 'updated_time', 'price_change', 'days_active',
                                'price', 'cian_estimation', 'cian_estimation_value', 'price_difference_value', 
                                'price_info', 'address', 'metro_station', 'neighborhood', 'district', 
                                'description', 'status', 'unpublished_date']
                
                save_df = pd.DataFrame(result)
                cols = [c for c in priority_cols if c in save_df.columns] + [c for c in save_df.columns if c not in priority_cols and c != 'image_urls']
                save_df = save_df[cols]
    
                # Format data - using map instead of applymap
                for col in save_df.columns:
                    save_df[col] = save_df[col].map(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict, np.ndarray)) 
                                   else x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) 
                                   else x)
    
                # Log stats
                active = sum(1 for apt in result if apt.get('status') != 'non active')
                non_active = sum(1 for apt in result if apt.get('status') == 'non active')
                logger.info(f'Saving {len(save_df)} entries to {current_csv} ({active} active, {non_active} non-active)')
    
                # Save CSV
                with open(current_csv + '.tmp', 'w', encoding='utf-8') as f:
                    f.write(f'# last_updated={datetime.now().strftime("%Y-%m-%d %H:%M:%S")},record_count={len(save_df)}\n')
                    save_df.to_csv(f, index=False, encoding='utf-8')
                os.replace(current_csv + '.tmp', current_csv)
    
                # Save JSON
                with open(current_json, 'w', encoding='utf-8') as f:
                    json.dump([{k: (v.strftime('%Y-%m-%d %H:%M:%S') if isinstance(v, pd.Timestamp) 
                                  else float(v) if isinstance(v, np.float64) 
                                  else int(v) if isinstance(v, np.int64) 
                                  else v) for k, v in apt.items()} for apt in result], 
                             f, ensure_ascii=False, indent=4)
                logger.info(f'Data also saved to {current_json}')
            
            return result
        except Exception as e:
            logger.error(f'Data save error: {e}')
            return apartments

    def scrape(self, search_url, max_pages=5, max_distance_km=3, time_filter=None):
        logger.info(f'Starting scrape: max_pages={max_pages}, max_distance={max_distance_km}km')
        url = f'{search_url}&totime={time_filter * 60}' if time_filter else search_url
    
        # Collect and combine listings
        parsed_apts = self.collector.collect_listings(url, max_pages, self.existing_data)
        logger.info(f'Collected {len(parsed_apts)} apartments from {max_pages} pages')
        
        combined_apts = self._combine_with_existing(parsed_apts)
        
        # Process distances
        self._process_distances(combined_apts)
        
        # SAVE INTERMEDIATE RESULTS - after distances but before other updates
        logger.info("Saving intermediate data (after distance processing)")
        intermediate_data = self._prepare_and_save_data(combined_apts, "")
        
        # Process remaining updates
        updated_apts = self._process_updates(combined_apts, max_distance_km)
        
        # SAVE FINAL RESULTS
        logger.info("Saving final data (after all processing)")
        self.apartments = self._prepare_and_save_data(updated_apts, "")  # Final save with original filename
        
        return self.apartments


if __name__ == '__main__':
    csv_file = 'cian_apartments.csv'
    base_url = 'https://www.cian.ru/cat.php?currency=2&deal_type=rent&district%5B0%5D=13&district%5B1%5D=21&engine_version=2&maxprice=100000&metro%5B0%5D=4&metro%5B10%5D=86&metro%5B11%5D=115&metro%5B12%5D=118&metro%5B13%5D=120&metro%5B14%5D=134&metro%5B15%5D=143&metro%5B16%5D=151&metro%5B17%5D=159&metro%5B18%5D=310&metro%5B1%5D=8&metro%5B2%5D=12&metro%5B3%5D=18&metro%5B4%5D=20&metro%5B5%5D=33&metro%5B6%5D=46&metro%5B7%5D=56&metro%5B8%5D=63&metro%5B9%5D=80&offer_type=flat&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1&room9=1&type=4'
    
    scraper = CianScraper(headless=True, csv_filename=csv_file)
    apartments = scraper.scrape(search_url=base_url, max_pages=20, max_distance_km=5)
    
    print(f'Total apartments processed: {len(apartments)}')