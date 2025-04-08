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
    
    def fetch_details(self, apt):
        """Fetch additional details for an apartment"""
        if 'offer_url' not in apt:
            return apt
                
        url = apt['offer_url']
        logger.info(f'Getting details: {url}')
            
        # Try to get estimation price with retries
        for attempt in range(1, 4):
            driver = None
            try:
                driver = webdriver.Chrome(options=self.chrome_options)
                driver.get(url)
                time.sleep(1)
                    
                # Scroll to load lazy content
                positions = [0.5] if attempt == 1 else [0.2, 0.5, 0.8]
                for pos in positions:
                    driver.execute_script(f'window.scrollTo(0, document.body.scrollHeight*{pos});')
                    time.sleep(1)
                        
                # Find price estimation element
                selector = "[data-testid='valuation_estimationPrice'] .a10a3f92e9--price--w7ha0 span"
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                for el in elements:
                    text = el.text.strip()
                    if text:
                        apt['cian_estimation'] = text
                        return apt
                        
            except Exception as e:
                logger.error(f'Error on attempt {attempt}: {e}')
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
            
        return apt
    
    def check_single_unpublished(self, id, url, existing_data):
        """Check if a listing has been unpublished"""
        logger.info(f'Checking unpublished status for ID {id}')
            
        max_retries = 3
        base_delay = 2
            
        for attempt in range(1, max_retries + 1):
            driver = None
            try:
                driver = webdriver.Chrome(options=self.chrome_options)
                driver.get(url)
                time.sleep(1)
                    
                # Check for unpublished indication
                unpublished_divs = driver.find_elements(By.XPATH, 
                    "//div[@data-name='OfferUnpublished' and contains(text(), 'Объявление снято с публикации')]")
                    
                if unpublished_divs:
                    # Get the update date
                    date_spans = driver.find_elements(By.XPATH, "//span[contains(text(), 'Обновлено:')]")
                        
                    unpublished_date = '--'
                    if date_spans:
                        date_text = date_spans[0].text
                        if 'Обновлено:' in date_text:
                            unpublished_date = parse_updated_time(
                                date_text.replace('Обновлено:', '').strip()
                            )
                        
                    # Create data with unpublished status
                    data = existing_data[id].copy()
                    data['status'] = 'non active'
                    data['unpublished_date'] = unpublished_date
                        
                    logger.info(f'Listing {id} is unpublished, date: {unpublished_date}')
                    return data
                        
                return None
                        
            except Exception as e:
                if attempt < max_retries:
                    # Exponential backoff
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(f'Attempt {attempt}/{max_retries} failed for ID {id}: {e}')
                    time.sleep(delay)
                else:
                    # On final failure, mark as non-active
                    if id in existing_data:
                        data = existing_data[id].copy()
                        data['status'] = 'non active'
                        data['unpublished_date'] = f"-- (connection error on {datetime.now().strftime('%Y-%m-%d')})"
                        return data
            finally:
                if driver:
                    try:
                        driver.quit()
                    except Exception:
                        pass
            
        return None

