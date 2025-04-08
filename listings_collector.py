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
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('CianScraper')


class CianListingCollector:
    """Responsible for collecting apartment listings from search pages"""
    
    def __init__(self, url_base, chrome_options):
        self.url_base = url_base
        self.chrome_options = chrome_options
        
    def __enter__(self):
        self.driver = webdriver.Chrome(options=self.chrome_options)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
    
    def collect_listings(self, url, max_pages=5, existing_data=None):
        """Collect apartment data from search results pages"""
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
                logger.error(f'Timeout loading first page: {e}')
                return []
                
            logger.info('Starting collection of apartment listings')
            while True:
                logger.info(f'Parsing page {page}')
                self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight/2);')
                time.sleep(1.5)
                
                # Parse current page
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                offers = soup.find('div', {'data-name': 'Offers'})
                if not offers:
                    logger.warning('No offers container found')
                    break
                    
                cards = offers.find_all('article', {'data-name': 'CardComponent'})
                if not cards:
                    logger.warning(f'No apartment cards on page {page}')
                    break
                    
                # Check for pagination issues by detecting duplicate listings
                current_page_ids = set()
                for card in cards:
                    if link := card.select_one("a[href*='/rent/flat/']"):
                        if m := re.search(r'/rent/flat/(\d+)/', link.get('href', '')):
                            current_page_ids.add(m.group(1))
                
                # If no new listings found on pages after first, we've reached the end
                new_ids = current_page_ids - seen_ids
                if not new_ids and page > 1:
                    logger.warning('No new listings found. Possible pagination issue.')
                    break
                
                # Extract data from each apartment card
                for card in cards:
                    data = self.parse_card(card)
                    if not data or 'offer_id' not in data or not data['offer_id']:
                        continue
                        
                    id = data['offer_id']
                    if id in seen_ids:
                        continue
                    
                    # Use existing distance if available
                    if existing_data and id in existing_data and 'distance' in existing_data[id]:
                        data['distance'] = existing_data[id]['distance']
                    
                    # Set defaults
                    data['status'] = 'active'
                    data['unpublished_date'] = '--'
                    
                    seen_ids.add(id)
                    all_apts.append(data)
                
                # Check if we've reached max pages
                if max_pages and page >= max_pages:
                    logger.info(f'Reached max pages ({max_pages})')
                    break
                    
                # Navigate to next page
                if not self.go_to_next_page(page):
                    break
                    
                page += 1
            
            logger.info(f'Collected {len(all_apts)} apartments from {page} pages')
            return all_apts

    def parse_card(self, card):
        """Parse apartment card from search results"""
        try:
            data = {
                'offer_id': '', 'offer_url': '', 'updated_time': '', 'title': '',
                'price': '', 'cian_estimation': '', 'price_info': '', 'address': '',
                'metro_station': '', 'neighborhood': '', 'district': '',
                'description': '', 'image_urls': [], 'distance': None
            }
            
            # Extract URL and ID
            if link := card.select_one("a[href*='/rent/flat/']"):
                url = link.get('href')
                data['offer_url'] = self.url_base + url if url.startswith('/') else url
                if m := re.search(r'/rent/flat/(\d+)/', url):
                    data['offer_id'] = m.group(1)
            
            # Extract basic data
            if title := card.select_one('[data-mark="OfferTitle"]'):
                data['title'] = title.get_text(strip=True)
            if price := card.select_one('[data-mark="MainPrice"]'):
                data['price'] = price.get_text(strip=True)
            if price_info := card.select_one('[data-mark="PriceInfo"]'):
                data['price_info'] = price_info.get_text(strip=True)
            
            # Location info
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
                
            # Address
            street = loc_elems[4].get_text(strip=True) if len(loc_elems) > 4 else ''
            building = loc_elems[5].get_text(strip=True) if len(loc_elems) > 5 else ''
            data['address'] = f"{street}, {building}".strip(', ')
            
            # Description and time
            if desc := card.select_one('div[data-name="Description"] p'):
                data['description'] = desc.get_text(strip=True)
            if time_el := card.select_one('div[data-name="TimeLabel"] div._93444fe79c--absolute--yut0v span'):
                data['updated_time'] = parse_updated_time(time_el.get_text(strip=True))
                
            # Images
            data['image_urls'] = [
                img.get('src') for img in card.select('img._93444fe79c--container--KIwW4') if img.get('src')
            ]

            return data
        except Exception as e:
            logger.error(f'Error parsing card: {e}')
            return None

    def go_to_next_page(self, current_page):
        """Navigate to next page by URL modification"""
        try:
            current_url = self.driver.current_url
            next_page = current_page + 1
            
            # Create URL for next page
            if 'p=' in current_url:
                next_url = re.sub(r'p=\d+', f'p={next_page}', current_url)
            else:
                separator = '&' if '?' in current_url else '?'
                next_url = f"{current_url}{separator}p={next_page}"
            
            # Navigate and wait for content
            self.driver.get(next_url)
            time.sleep(2)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-name='CardComponent']"))
            )
            
            # Check if we have results
            cards = self.driver.find_elements(By.CSS_SELECTOR, "article[data-name='CardComponent']")
            return bool(cards)
            
        except Exception as e:
            logger.error(f'Error navigating to page {current_page + 1}: {e}')
            return False

