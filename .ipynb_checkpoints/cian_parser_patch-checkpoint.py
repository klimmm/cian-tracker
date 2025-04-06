"""
This file shows the changes needed for cian_parser.py to work on Render.com
Replace the CianParser class initialization with this code
"""

# Import the helper
from selenium_helper import get_chrome_options, setup_driver

class CianParser:
    def __init__(self, headless=True):
        # Use the helper function to get Chrome options
        self.chrome_options = get_chrome_options(headless)
        self.url_base = "https://www.cian.ru"
        self.apartments = []
        self.driver = None

    def __enter__(self):
        # Use the helper function to set up the driver
        self.driver = setup_driver(headless=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()
            
    # Rest of the CianParser class remains the same
    
    def parse_apartment_details(self, url, max_retries=3):
        logger.info(f"Getting details: {url}")
        info = {"cian_estimation": ""}
        selectors = {
            "cian_estimation": [
                "[data-testid='valuation_estimationPrice']",
                ".a10a3f92e9--price-value--QPB7v",
                ".a10a3f92e9--price--nVvqM",
            ]
        }
        for attempt in range(1, max_retries + 1):
            driver = None
            try:
                # Use the helper function here too
                driver = setup_driver(headless=True)
                driver.get(url)
                # Rest of the method remains the same