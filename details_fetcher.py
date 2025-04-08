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
from utils import parse_updated_time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CianScraper')

class CianDetailFetcher:
    """Responsible for fetching detailed information about apartment listings"""
    
    def __init__(self, chrome_options):
        self.chrome_options = chrome_options
    
    def fetch_page_data(self, update_item):
        """
        Unified method to fetch data from a Cian listing page
        
        Args:
            update_item (dict): Contains all information needed for the update:
                - url (str): The page URL
                - update_type (str): 'estimation' or 'unpublished'
                - item_id (str): Identifier for the listing
        
        Returns:
            dict: Update data containing the requested information
        """
        url = update_item.get('url')
        update_type = update_item.get('update_type')
        item_id = update_item.get('item_id')
        
        if not url or not update_type or not item_id:
            return {'item_id': item_id, 'success': False, 'error': 'Invalid update item'}
        
        logger.info(f'Fetching {update_type} data for ID {item_id}: {url}')
        
        max_retries = 3
        base_delay = 2
        
        for attempt in range(1, max_retries + 1):
            driver = None
            try:
                # Setup and navigate
                driver = webdriver.Chrome(options=self.chrome_options)
                driver.get(url)
                time.sleep(1)
                
                # Scroll to load lazy content
                positions = [0.5] if attempt == 1 else [0.2, 0.5, 0.8]
                for pos in positions:
                    driver.execute_script(f'window.scrollTo(0, document.body.scrollHeight*{pos});')
                    time.sleep(1)
                
                result = {
                    'item_id': item_id,
                    'update_type': update_type,
                    'success': True
                }
                
                # Extract information based on update_type
                if update_type == 'estimation':
                    query_selector = "[data-testid='valuation_estimationPrice'] .a10a3f92e9--price--w7ha0 span"
                    page_elements = driver.find_elements(By.CSS_SELECTOR, query_selector)
                    
                    for page_element in page_elements:
                        element_text = page_element.text.strip()
                        if element_text:
                            result['cian_estimation'] = element_text
                            return result
                    
                    # No estimation found but page loaded successfully
                    return result
                
                elif update_type == 'unpublished':
                    query_selector = "//div[@data-name='OfferUnpublished' and contains(text(), 'Объявление снято с публикации')]"
                    page_elements = driver.find_elements(By.XPATH, query_selector)
                    
                    if page_elements:
                        # Get the update date
                        date_query_selector = "//span[contains(text(), 'Обновлено:')]"
                        date_elements = driver.find_elements(By.XPATH, date_query_selector)
                        
                        status_date = '--'
                        if date_elements:
                            element_text = date_elements[0].text
                            if 'Обновлено:' in element_text:
                                status_date = parse_updated_time(
                                    element_text.replace('Обновлено:', '').strip()
                                )
                        
                        result['is_unpublished'] = True
                        result['unpublished_date'] = status_date
                        return result
                    else:
                        # Not unpublished
                        result['is_unpublished'] = False
                        return result
                
            except Exception as e:
                if attempt < max_retries:
                    # Exponential backoff
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(f'Attempt {attempt}/{max_retries} failed for URL {url}: {e}')
                    time.sleep(delay)
                else:
                    logger.error(f'All attempts failed for URL {url}: {e}')
                    
                    # Handle final failure with consistent format
                    result = {
                        'item_id': item_id,
                        'update_type': update_type,
                        'success': False,
                        'error': str(e)
                    }
                    
                    # Add specific data for unpublished type
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
    
        # All attempts failed without explicit exception handling
        return {
            'item_id': item_id,
            'update_type': update_type,
            'success': False,
            'error': 'Maximum retry attempts reached'
        }
