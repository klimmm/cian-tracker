import re, os, json, time, logging, traceback
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from distance import get_coordinates, get_distance_osrm

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CianParser")


def parse_updated_time(time_str):
    if not time_str:
        return ""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    months = {
        "янв": 1,
        "фев": 2,
        "мар": 3,
        "апр": 4,
        "май": 5,
        "июн": 6,
        "июл": 7,
        "авг": 8,
        "сен": 9,
        "окт": 10,
        "ноя": 11,
        "дек": 12,
    }
    try:
        if "сегодня" in time_str.lower():
            h, m = map(int, time_str.split(", ")[1].split(":"))
            return today.replace(hour=h, minute=m).strftime("%Y-%m-%d %H:%M:%S")
        elif "вчера" in time_str.lower() and ", " in time_str:
            h, m = map(int, time_str.split(", ")[1].split(":"))
            return (
                (today - timedelta(days=1))
                .replace(hour=h, minute=m)
                .strftime("%Y-%m-%d %H:%M:%S")
            )
        elif any(x in time_str.lower() for x in ["минут", "секунд"]):
            now = datetime.now()
            if "минут" in time_str.lower():
                min = int(re.search(r"(\d+)\s+минут", time_str).group(1))
                return (now - timedelta(minutes=min)).strftime("%Y-%m-%d %H:%M:%S")
            else:
                sec = int(re.search(r"(\d+)\s+секунд", time_str).group(1))
                return (now - timedelta(seconds=sec)).strftime("%Y-%m-%d %H:%M:%S")
        elif ", " in time_str and any(m in time_str.lower() for m in months.keys()):
            date_part, time_part = time_str.split(", ")
            day = int(re.search(r"(\d+)", date_part).group(1))
            month = next(
                (n for name, n in months.items() if name in date_part.lower()), None
            )
            if not month:
                return time_str
            h, m = map(int, time_part.split(":"))
            year = today.year
            dt = datetime(year, month, day, h, m)
            if dt > datetime.now() + timedelta(days=1):
                dt = dt.replace(year=year - 1)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return time_str


def extract_price_value(price_str):
    if not price_str:
        return None
    if isinstance(price_str, (int, float)):
        return float(price_str)
    digits = re.sub(r"[^\d]", "", str(price_str))
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def add_distance_calculations(
    apartments, reference_address="Москва, переулок Большой Саввинский, 3"
):
    """
    Calculate distances for apartments that don't have distance values
    using the distance.py module.
    Args:
        apartments: List of apartment dictionaries
        reference_address: The central address to calculate distances from
    Returns:
        Updated apartments list with distance values
    """
    logger.info("Calculating missing distance values...")
    try:
        # Get coordinates for the reference address once
        reference_coords = get_coordinates(reference_address)
        logger.info(f"Reference coordinates: {reference_coords}")

        # Properly check for missing distances
        missing_apts = []
        for apt in apartments:
            distance = apt.get("distance")
            # Handle different types of distance values
            if distance is not None and distance != "":
                try:
                    # Convert string to float if needed
                    if isinstance(distance, str):
                        distance = float(distance)

                    # Check for NaN or infinite values
                    if np.isnan(distance) or np.isinf(distance):
                        logger.info(
                            f"Invalid distance value (NaN/Inf) for {apt.get('offer_id', 'unknown')}, will recalculate"
                        )
                        missing_apts.append(apt)
                    else:
                        apt["distance"] = distance  # Store back as float
                        logger.debug(
                            f"Apartment {apt.get('offer_id', 'unknown')} already has distance: {distance} km"
                        )
                except (ValueError, TypeError):
                    # If conversion fails, consider it missing
                    logger.info(
                        f"Invalid distance value for {apt.get('offer_id', 'unknown')}: {distance}, will recalculate"
                    )
                    missing_apts.append(apt)
            else:
                missing_apts.append(apt)

        logger.info(
            f"Found {len(missing_apts)} apartments without valid distance values"
        )

        # Process each apartment that needs distance calculation
        calculated_count = 0
        for apt in missing_apts:
            try:
                # Get the full address
                address = apt.get("address", "")
                if not address:
                    continue

                # Add city to address if not present
                full_address = address
                if "Москва" not in address:
                    full_address = f"Москва, {address}"

                # Calculate coordinates and distance
                apt_coords = get_coordinates(full_address)
                distance_km = get_distance_osrm(reference_coords, apt_coords)

                # Store rounded distance value as float
                apt["distance"] = round(distance_km, 2)
                calculated_count += 1
                logger.info(
                    f"New distance calculated for '{full_address}': {apt['distance']} km"
                )

                # Log progress periodically
                if calculated_count % 5 == 0:
                    logger.info(
                        f"Calculated {calculated_count}/{len(missing_apts)} distances"
                    )

            except Exception as e:
                logger.error(f"Error calculating distance for {address}: {e}")

        logger.info(
            f"Distance calculation complete. Added {calculated_count} new distance values"
        )
        return apartments

    except Exception as e:
        logger.error(f"Error in distance calculation: {e}")
        return apartments


class CianParser:
    def __init__(self, headless=True):
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        self.url_base = "https://www.cian.ru"
        self.apartments = []
        self.driver = None

    def __enter__(self):
        self.driver = webdriver.Chrome(options=self.chrome_options)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()

    def add_price_difference(self):
        for apt in self.apartments:
            try:
                pv = extract_price_value(apt.get("price", ""))
                ev = extract_price_value(apt.get("cian_estimation", ""))
                if pv is not None and ev is not None:
                    diff = ev - pv
                    apt["price_difference_value"] = diff
                    apt["price_difference"] = self.format_price(diff)
                else:
                    apt["price_difference_value"] = None
                    apt["price_difference"] = ""
            except Exception as e:
                logger.error(f"Error calc price diff: {e}")
                apt["price_difference_value"] = None
                apt["price_difference"] = ""

    def add_days_active(self):
        now = datetime.now()
        for apt in self.apartments:
            t_str = apt.get("updated_time", "")
            if t_str:
                try:
                    t = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")
                    apt["days_active"] = (now - t).days
                except (ValueError, TypeError):
                    apt["days_active"] = None
            else:
                apt["days_active"] = None

    def sort_by_updated_time(self, descending=True):
        def parse_date(d):
            if not d:
                return datetime(1900, 1, 1)
            try:
                return datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
            except:
                return datetime(1900, 1, 1)

        self.apartments.sort(
            key=lambda x: parse_date(x.get("updated_time", "")), reverse=descending
        )

    def load_existing_data(self, csv_filename="cian_apartments.csv"):
        self.existing_data = {}
        self.existing_df = None
        if os.path.exists(csv_filename):
            try:
                self.existing_df = pd.read_csv(csv_filename, encoding="utf-8")
                for _, row in self.existing_df.iterrows():
                    id = str(row.get("offer_id", ""))
                    if id:
                        self.existing_data[id] = row.to_dict()
                logger.info(f"Loaded {len(self.existing_data)} existing entries")
            except Exception as e:
                logger.error(f"Error loading data: {e}")
                self.existing_data = {}
                self.existing_df = pd.DataFrame()
        else:
            self.existing_data = {}
            self.existing_df = pd.DataFrame()
        return self.existing_data

    def fetch_details_for_apartment(self, apt, max_retries=3):
        if "offer_url" in apt:
            details = self.parse_apartment_details(apt["offer_url"], max_retries)
            if details:
                apt.update({k: v for k, v in details.items() if v})
        return apt

    def parse_search_results(
        self,
        url,
        max_pages=None,
        get_detailed_info=True,
        max_retries=3,
        csv_filename="cian_apartments.csv",
    ):
        self.load_existing_data(csv_filename)
        self.apartments = []
        seen_ids = set()
        with self:
            page = 1
            self.driver.get(url)
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "article[data-name='CardComponent']")
                    )
                )
            except Exception as e:
                logger.error(f"Timeout loading first page: {e}")
                return []
            while True:
                logger.info(f"Parsing page {page}")
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight/2);"
                )
                time.sleep(1.5)  # Increased wait time

                # Get current page content
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                offers = soup.find("div", {"data-name": "Offers"})
                if not offers:
                    logger.warning("No offers container")
                    break

                # Store current page URL to verify navigation later
                current_url = self.driver.current_url
                logger.debug(f"Current URL: {current_url}")

                # Get page number from pagination if available
                try:
                    pagination = soup.select("li._93444fe79c--list-item--LafhZ")
                    active_page = None
                    for p in pagination:
                        if "_93444fe79c--active--YElYg" in p.get("class", []):
                            active_page = p.text.strip()
                            break
                    if active_page:
                        logger.info(f"Active page indicator: {active_page}")
                except Exception as e:
                    logger.debug(f"Couldn't get pagination: {e}")

                # Process cards
                cards = offers.find_all("article", {"data-name": "CardComponent"})
                if not cards:
                    logger.warning(f"No cards on page {page}")
                    break

                logger.info(f"Processing {len(cards)} cards on page {page}")

                # Get IDs of cards on this page to check for duplicates later
                current_page_ids = set()
                for card in cards:
                    if link := card.select_one("a[href*='/rent/flat/']"):
                        url = link.get("href")
                        if m := re.search(r"/rent/flat/(\d+)/", url):
                            current_page_ids.add(m.group(1))

                # Check if we have any new IDs (avoid processing duplicate pages)
                new_ids = current_page_ids - seen_ids
                if not new_ids and page > 1:
                    logger.warning(
                        f"No new listings found on page {page}. Possible navigation issue."
                    )
                    break

                parsed_full_update = []  # For new apartments or price changes
                parsed_estimation_only = (
                    []
                )  # For apartments that only need estimation updates

                for i, card in enumerate(cards):
                    data = self.parse_apartment_card(card)
                    if not data or "offer_id" not in data or not data["offer_id"]:
                        continue
                    id = data["offer_id"]
                    if id in seen_ids:
                        logger.debug(f"{id} already seen")
                        continue
                    seen_ids.add(id)
                    price = data.get("price", "")

                    if id in self.existing_data:
                        ex_price = self.existing_data[id].get("price", "")
                        ex_price_val = extract_price_value(ex_price)
                        cur_price_val = extract_price_value(price)
                        est = self.existing_data[id].get("cian_estimation", "")
                        logger.debug(f"{id} ex_price_val {ex_price_val}")
                        logger.debug(f"{id} cur_price_val {cur_price_val}")
                        logger.debug(f"{id} est {est}")
                        # Check for invalid distance
                        # Check for invalid or missing distance
                        existing_distance = self.existing_data[id].get("distance")
                        has_invalid_distance = False

                        # Case 1: Distance is None or empty string
                        if existing_distance is None or existing_distance == "":
                            has_invalid_distance = True
                        # Case 2: Distance has a value but might be invalid (NaN, Inf, etc.)
                        else:
                            try:
                                distance_val = (
                                    float(existing_distance)
                                    if isinstance(existing_distance, str)
                                    else existing_distance
                                )
                                has_invalid_distance = np.isnan(
                                    distance_val
                                ) or np.isinf(distance_val)
                            except (ValueError, TypeError):
                                has_invalid_distance = True

                        if ex_price_val != cur_price_val:
                            # Price changed - do full update
                            price_diff = (
                                cur_price_val - ex_price_val
                            )  # Calculate the actual difference
                            logger.info(
                                f"Offer {id}: Price changed from {ex_price_val} to {cur_price_val} - updating all fields"
                            )
                            data["price_change"] = (
                                f"From {ex_price_val} to {cur_price_val} ({price_diff:+.0f} ₽)"
                            )
                            data["price_change_value"] = (
                                price_diff  # Store numerical value separately
                            )
                            parsed_full_update.append(data)
                            """elif est_empty:
                                # Missing estimation - update only estimation
                                logger.info(
                                    f"Offer {id}: Price unchanged but estimation missing - updating ONLY estimation"
                                )
                                parsed_estimation_only.append(
                                    {"offer_id": id, "offer_url": data["offer_url"]}
                                )"""
                        elif has_invalid_distance:
                            # Only distance is invalid - preserve existing data but mark for distance update
                            logger.info(
                                f"Offer {id}: Invalid distance - will recalculate"
                            )
                            # Create a copy of existing data with current address for distance calculation
                            apt_copy = self.existing_data[id].copy()
                            apt_copy["address"] = data[
                                "address"
                            ]  # Use current address from parsed data
                            apt_copy["distance"] = (
                                None  # Reset distance to ensure recalculation
                            )
                            self.apartments.append(apt_copy)
                        else:
                            # No changes needed
                            logger.debug(f"Offer {id}: No changes, skipping")
                            continue
                    else:
                        logger.info(f"Offer {id} is new - adding all fields")
                        parsed_full_update.append(data)

                # Process apartments needing full updates
                if get_detailed_info and parsed_full_update:
                    with ThreadPoolExecutor(max_workers=4) as ex:
                        updated_full = list(
                            ex.map(
                                lambda a: self.fetch_details_for_apartment(
                                    a, max_retries
                                ),
                                parsed_full_update,
                            )
                        )
                    self.apartments.extend(updated_full)

                # Process apartments needing only estimation updates
                if get_detailed_info and parsed_estimation_only:
                    with ThreadPoolExecutor(max_workers=4) as ex:
                        updated_estimation = list(
                            ex.map(
                                lambda a: self.fetch_details_for_apartment(
                                    a, max_retries
                                ),
                                parsed_estimation_only,
                            )
                        )

                    # For estimation-only updates, only merge the estimation field with existing data
                    for apt in updated_estimation:
                        if apt.get("offer_id") and apt.get("cian_estimation"):
                            id = apt["offer_id"]
                            est = apt["cian_estimation"]
                            logger.info(f"Updated estimation for {id}: {est}")

                            # Create a copy that only has offer_id and cian_estimation
                            estimation_update = {"offer_id": id, "cian_estimation": est}
                            self.apartments.append(estimation_update)

                if max_pages and page >= max_pages:
                    logger.info(f"Reached max pages ({max_pages})")
                    break

                try:
                    # First check if we're on the last page by looking for disabled button
                    disabled_buttons = self.driver.find_elements(
                        By.XPATH,
                        "//button[contains(@class, '_93444fe79c--button--KVooB') and @disabled]/span[text()='Дальше']/..",
                    )

                    if disabled_buttons:
                        logger.info(
                            "Reached the last page (disabled next button found), stopping pagination"
                        )
                        break

                    # If no disabled button, try to find and click the active next button
                    try:
                        next_btn = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable(
                                (
                                    By.XPATH,
                                    "//a[contains(@class, '_93444fe79c--button--KVooB')]/span[text()='Дальше']/..",
                                )
                            )
                        )

                        # Retry mechanism for clicking
                        max_click_attempts = 3
                        for click_attempt in range(max_click_attempts):
                            try:
                                # Scroll to button
                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView({block: 'center'});",
                                    next_btn,
                                )
                                time.sleep(1)

                                # Try JavaScript click instead of Selenium click
                                self.driver.execute_script(
                                    "arguments[0].click();", next_btn
                                )

                                # Wait for URL or content to change
                                start_time = time.time()
                                url_changed = False
                                while (
                                    time.time() - start_time < 10
                                ):  # 10 second timeout
                                    if self.driver.current_url != current_url:
                                        url_changed = True
                                        break
                                    time.sleep(0.5)

                                if url_changed:
                                    logger.debug(
                                        f"URL changed to: {self.driver.current_url}"
                                    )
                                    break
                                else:
                                    logger.warning(
                                        f"Click attempt {click_attempt+1}: URL didn't change"
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"Click attempt {click_attempt+1} failed: {e}"
                                )
                                if click_attempt == max_click_attempts - 1:
                                    raise
                                time.sleep(1)

                        # Wait for page to load
                        time.sleep(3)  # Extra wait time for page load

                        # Wait for elements to be present
                        WebDriverWait(self.driver, 15).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "article[data-name='CardComponent']")
                            )
                        )

                        page += 1

                    except Exception as e:
                        logger.warning(f"Could not find clickable next button: {e}")
                        logger.info("Assuming we've reached the last page")
                        break

                except Exception as e:
                    logger.error(f"Error navigating: {e}")
                    logger.debug(traceback.format_exc())
                    break
        logger.info(f"Collected {len(self.apartments)} apartments")
        return self.apartments

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
                driver = webdriver.Chrome(options=self.chrome_options)
                driver.get(url)
                time.sleep(1)
                positions = [0.5] if attempt == 1 else [0.2, 0.5, 0.8]
                for pos in positions:
                    driver.execute_script(
                        f"window.scrollTo(0, document.body.scrollHeight*{pos});"
                    )
                    time.sleep(1)
                for selector in selectors["cian_estimation"]:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        text = el.text.strip()
                        if "Оценка Циан" in text or "₽" in text:
                            info["cian_estimation"] = text.replace(
                                "Оценка Циан", ""
                            ).strip()
                            break
                    if info["cian_estimation"]:
                        break
                if info["cian_estimation"]:
                    break
            except Exception as e:
                logger.error(f"Error on attempt {attempt}: {e}")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        return info

    def format_price_changes(self):
        """Format price changes in a human-readable format"""
        logger.info(f"Formatting price changes for {len(self.apartments)} apartments")
        count_new = 0
        count_formatted = 0

        for apt in self.apartments:
            offer_id = apt.get("offer_id", "")
            price_change_value = apt.get("price_change_value")

            logger.warning(
                f"Offer {offer_id}: Processing with price_change_value='{price_change_value}'"
            )

            # CASE 1: If price_change_value is "new" - mark as new
            if price_change_value == "new":
                apt["price_change_formatted"] = "new"
                logger.warning(
                    f"Offer {offer_id}: Marked as new (price_change_value is 'new')"
                )
                count_new += 1

            # CASE 2: If price_change_value is numeric - format it
            elif price_change_value is not None:
                try:
                    price_diff = float(price_change_value)
                    if price_diff >= 0:
                        apt["price_change_formatted"] = (
                            f"{int(price_diff):,}".replace(",", " ") + " ₽/мес."
                        )
                    else:
                        apt["price_change_formatted"] = (
                            f"-{int(abs(price_diff)):,}".replace(",", " ") + " ₽/мес."
                        )
                    logger.warning(
                        f"Offer {offer_id}: Formatted to '{apt['price_change_formatted']}'"
                    )
                    count_formatted += 1
                except (ValueError, TypeError) as e:
                    # Not a valid number, default to new
                    apt["price_change_formatted"] = "new"
                    logger.warning(
                        f"Offer {offer_id}: Error converting '{price_change_value}' to number: {e}"
                    )
                    count_new += 1

            # CASE 3: No price_change_value - mark as new
            else:
                apt["price_change_formatted"] = "new"
                logger.warning(
                    f"Offer {offer_id}: No price_change_value, marking as new"
                )
                count_new += 1

        logger.info(
            f"Price change formatting complete: {count_new} new, {count_formatted} with price changes"
        )
        return self.apartments

    def format_price(self, value):
        if value is None:
            return ""
        return f"{'{:,}'.format(int(value)).replace(',', ' ')} ₽/мес."

    def parse_apartment_card(self, card):
        try:
            data = {
                "offer_id": "",
                "offer_url": "",
                "updated_time": "",
                "title": "",
                "price": "",
                "cian_estimation": "",
                "price_info": "",
                "address": "",
                "metro_station": "",
                "neighborhood": "",
                "district": "",
                "description": "",
                "image_urls": [],
                "distance": None,  # Initialize as None instead of empty string
                "price_change": "",
            }
            if link := card.select_one("a[href*='/rent/flat/']"):
                url = link.get("href")
                data["offer_url"] = self.url_base + url if url.startswith("/") else url
                if m := re.search(r"/rent/flat/(\d+)/", url):
                    data["offer_id"] = m.group(1)
            if title := card.select_one("[data-mark='OfferTitle']"):
                data["title"] = title.get_text(strip=True)
            if price := card.select_one("[data-mark='MainPrice']"):
                data["price"] = price.get_text(strip=True)
            if price_info := card.select_one("[data-mark='PriceInfo']"):
                data["price_info"] = price_info.get_text(strip=True)
            if metro := card.select_one("div[data-name='SpecialGeo']"):
                text = metro.get_text(strip=True)
                data["metro_station"] = (
                    text.split("мин")[0].strip() if "мин" in text else text
                )
            loc_elems = card.select("a[data-name='GeoLabel']")
            if len(loc_elems) > 3:
                data["metro_station"] = loc_elems[3].get_text(strip=True)
            if len(loc_elems) > 2:
                data["neighborhood"] = loc_elems[2].get_text(strip=True)
            if len(loc_elems) > 1:
                data["district"] = loc_elems[1].get_text(strip=True)
            street = loc_elems[4].get_text(strip=True) if len(loc_elems) > 4 else ""
            building = loc_elems[5].get_text(strip=True) if len(loc_elems) > 5 else ""
            data["address"] = f"{street}, {building}".strip(", ")
            if desc := card.select_one("div[data-name='Description'] p"):
                data["description"] = desc.get_text(strip=True)
            if time_el := card.select_one(
                "div[data-name='TimeLabel'] div._93444fe79c--absolute--yut0v span"
            ):
                data["updated_time"] = parse_updated_time(time_el.get_text(strip=True))
            data["image_urls"] = [
                img.get("src")
                for img in card.select("img._93444fe79c--container--KIwW4")
                if img.get("src")
            ]
            # Check if this apartment already exists and has a distance
            # In parse_apartment_card when preserving distances:
            if data["offer_id"] in self.existing_data:
                existing_distance = self.existing_data[data["offer_id"]].get("distance")
                if existing_distance and existing_distance != "":
                    try:
                        # Convert to float if it's a string
                        if isinstance(existing_distance, str):
                            existing_distance = float(existing_distance)

                        # Check if the value is NaN or infinite
                        if np.isnan(existing_distance) or np.isinf(existing_distance):
                            logger.info(
                                f"Found invalid distance (NaN/Inf) for {data['offer_id']}, will recalculate"
                            )
                        else:
                            data["distance"] = existing_distance
                            logger.debug(
                                f"Preserved existing distance for {data['offer_id']}: {existing_distance} km"
                            )
                    except (ValueError, TypeError):
                        pass  # If conversion fails, we'll recalculate

            return data
        except Exception as e:
            logger.error(f"Error parsing card: {e}")
            return None

    def merge_with_existing_data(self):
        if (
            not hasattr(self, "existing_df")
            or self.existing_df is None
            or self.existing_df.empty
        ):
            return self.apartments
        if not self.apartments:
            self.apartments = self.existing_df.to_dict("records")
            return self.apartments
        current_df = pd.DataFrame(self.apartments)

        for col in current_df.columns:
            logger.debug(f"Column {col}: {current_df[col].apply(type).unique()}")
        merged_df = self.existing_df.copy()
        for df in [current_df, merged_df]:
            if "offer_id" in df.columns:
                df["offer_id"] = df["offer_id"].astype(str)
        for _, row in current_df.iterrows():
            id = row.get("offer_id", "")
            if not id:
                merged_df = pd.concat(
                    [merged_df, pd.DataFrame([row])], ignore_index=True
                )
                continue
            idx = merged_df[merged_df["offer_id"] == id].index
            if len(idx) > 0:
                for col in row.index:
                    if (
                        col in merged_df.columns
                        and pd.notna(row[col])
                        and row[col] != ""
                    ):
                        merged_df.loc[idx[0], col] = row[col]
            else:
                merged_df = pd.concat(
                    [merged_df, pd.DataFrame([row])], ignore_index=True
                )
        merged_df = merged_df.drop_duplicates(subset=["offer_id"], keep="first")
        if "updated_time" in merged_df.columns:
            merged_df["updated_time"] = pd.to_datetime(
                merged_df["updated_time"], format="%Y-%m-%d %H:%M:%S", errors="coerce"
            )
            merged_df = merged_df.sort_values("updated_time", ascending=False)
        self.apartments = merged_df.to_dict("records")
        return self.apartments

    def save_to_csv(self, filename="cian_apartments.csv"):
        try:
            # self.merge_with_existing_data()
            if not self.apartments:
                logger.warning("No data to save")
                return
            # Define columns to save
            cols = [
                "offer_id",
                "offer_url",
                "title",
                "updated_time",
                "price_change",
                "days_active",
                "price",
                "cian_estimation",
                "price_difference",
                "price_difference_value",
                "price_info",
                "address",
                "metro_station",
                "neighborhood",
                "district",
                "description",
            ]
            df = pd.DataFrame(self.apartments)

            cols = [c for c in cols if c in df.columns]
            for c in df.columns:
                if c not in cols and c != "image_urls":
                    cols.append(c)

            df_save = df[cols].copy()

            # Modified serialization function to handle arrays properly
            for c in df_save.columns:

                def serialize(x):
                    try:
                        if isinstance(x, np.ndarray):
                            return json.dumps(x.tolist(), ensure_ascii=False)
                        elif isinstance(x, (list, dict)):
                            return json.dumps(x, ensure_ascii=False)
                        elif isinstance(
                            x, (str, int, float, bool, type(None), np.generic)
                        ):
                            return x
                        else:
                            return str(x)
                    except Exception as e:
                        return str(x)

                df_save[c] = df_save[c].apply(serialize)

            df_save.to_csv(filename, index=False, encoding="utf-8")
            logger.info(f"Saved to {filename}: {len(df)} entries")
        except Exception as e:
            logger.error(f"CSV save error: {e}")
            logger.warning(
                traceback.format_exc()
            )  # Add this for more detailed error info

    def add_distances(self, reference_address="Москва, переулок Большой Саввинский, 3"):
        """Calculate distances for apartments that don't have distance values"""
        self.apartments = add_distance_calculations(self.apartments, reference_address)
        return self.apartments

    def save_to_json(self, filename="cian_apartments.json"):
        if not self.apartments:
            logger.warning("No data to save")
            return
        for apt in self.apartments:
            for k, v in apt.items():
                if isinstance(v, pd.Timestamp):
                    apt[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.apartments, f, ensure_ascii=False, indent=4)
            logger.info(f"Saved to {filename}")
        except Exception as e:
            logger.error(f"JSON save error: {e}")


if __name__ == "__main__":
    csv_file = "cian_apartments.csv"
    base_url = "https://www.cian.ru/cat.php?currency=2&deal_type=rent&district%5B0%5D=13&district%5B1%5D=21&engine_version=2&maxprice=100000&metro%5B0%5D=56&metro%5B1%5D=86&metro%5B2%5D=115&metro%5B3%5D=118&metro%5B4%5D=143&offer_type=flat&room1=1&room2=1&room9=1&type=4"
    time_filter = None
    search_url = (
        base_url if time_filter is None else f"{base_url}&totime={time_filter * 60}"
    )
    parser = CianParser(headless=True)
    apartments = parser.parse_search_results(
        search_url, max_pages=5, get_detailed_info=True, csv_filename=csv_file
    )
    parser.add_price_difference()
    parser.add_days_active()

    parser.merge_with_existing_data()
    parser.add_distances()
    parser.format_price_changes()  # New method that formats all price changes
    parser.sort_by_updated_time(descending=True)
    parser.save_to_csv(csv_file)
    parser.save_to_json("cian_apartments.json")
    logger.info("Done")
