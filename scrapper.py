from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import csv
import re
import os
import datetime
from selenium.common.exceptions import TimeoutException
import json

def save_cookies(driver, path="cookies.json"):
    cookies = driver.get_cookies()
    with open(path, "w") as f:
        json.dump(cookies, f)
    print(f"Saved {len(cookies)} cookies to {path}")

def load_cookies(driver, path="cookies.json", domain=".cian.ru"):
    try:
        with open(path, "r") as f:
            cookies = json.load(f)
        for cookie in cookies:
            if "sameSite" in cookie:
                cookie.pop("sameSite")  # Prevent compatibility issues
            driver.add_cookie(cookie)
        print(f"Loaded {len(cookies)} cookies from {path}")
    except Exception as e:
        print(f"Failed to load cookies: {e}")

# Define mapping of Russian month abbreviations to numbers
russian_months = {
    "янв": "01",  # January
    "фев": "02",  # February
    "мар": "03",  # March
    "апр": "04",  # April
    "мая": "05",  # May
    "июн": "06",  # June
    "июл": "07",  # July
    "авг": "08",  # August
    "сен": "09",  # September
    "окт": "10",  # October
    "ноя": "11",  # November
    "дек": "12",  # December
}


def convert_date(date_str):
    """Convert date string to YYYY-MM-DD HH:MM:SS format"""
    # Clean input
    date_str = date_str.strip()
    today = datetime.datetime.now()

    # Check for "Today" in Russian
    if date_str == "Сегодня":
        return f"{today.year}-{today.month:02d}-{today.day:02d} 00:00:00"

    # Check for "Yesterday" in Russian (вчера)
    if "вчера" in date_str:
        yesterday = today - datetime.timedelta(days=1)
        # Check if there's a time component
        time_match = re.search(r"(\d{2}):(\d{2})", date_str)
        if time_match:
            hours, minutes = time_match.groups()
            return f"{yesterday.year}-{yesterday.month:02d}-{yesterday.day:02d} {hours}:{minutes}:00"
        else:
            return (
                f"{yesterday.year}-{yesterday.month:02d}-{yesterday.day:02d} 00:00:00"
            )

    # Check for "DD month, HH:MM" format (e.g., "6 апр, 22:35")
    update_date_pattern = re.compile(r"(\d{1,2})\s+(\w{3}),\s+(\d{2}):(\d{2})")
    match = update_date_pattern.match(date_str)

    if match:
        day, month_abbr, hours, minutes = match.groups()
        month = russian_months.get(month_abbr)
        if month:
            return f"{today.year}-{month}-{day.zfill(2)} {hours}:{minutes}:00"

    # Check for DD.MM.YYYY format using regex
    dd_mm_yyyy_pattern = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")
    match = dd_mm_yyyy_pattern.match(date_str)

    if match:
        # Format is DD.MM.YYYY
        day, month, year = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)} 00:00:00"

    # Try Russian format (day month year)
    parts = date_str.split(" ")
    if len(parts) == 3:
        day = parts[0].zfill(2)  # Pad with leading zero if needed
        month = russian_months.get(parts[1])
        year = parts[2]

        if month:
            return f"{year}-{month}-{day} 00:00:00"

    # If we get here, the format is unrecognized
    return f"Invalid date format: {date_str}"


def scrape_apartment_features(driver):
    """Extract specific apartment features/amenities"""
    features_data = {
        "has_refrigerator": False,
        "has_dishwasher": False,
        "has_washing_machine": False,
        "has_air_conditioner": False,
        "has_tv": False,
        "has_internet": False,
        "has_kitchen_furniture": False,
        "has_room_furniture": False,
        "has_bathtub": False,
        "has_shower_cabin": False,
    }

    try:
        # Find the features container
        features_section = driver.find_elements(
            By.CSS_SELECTOR, "div[data-name='FeaturesLayout']"
        )

        if not features_section:
            print("Features section not found")
            return features_data

        print("\nApartment Features:")

        # Look for all feature items
        feature_items = driver.find_elements(
            By.CSS_SELECTOR, "div[data-name='FeaturesItem']"
        )

        if not feature_items:
            print("No feature items found")
            return features_data

        # Map Russian feature names to our data keys
        feature_name_map = {
            "Холодильник": "has_refrigerator",
            "Посудомоечная машина": "has_dishwasher",
            "Стиральная машина": "has_washing_machine",
            "Кондиционер": "has_air_conditioner",
            "Телевизор": "has_tv",
            "Интернет": "has_internet",
            "Мебель на кухне": "has_kitchen_furniture",
            "Мебель в комнатах": "has_room_furniture",
            "Ванна": "has_bathtub",
            "Душевая кабина": "has_shower_cabin",
        }

        # Process each feature item
        for item in feature_items:
            feature_text = driver.execute_script(
                "return arguments[0].textContent;", item
            ).strip()

            # Check if this item matches any of our known features
            if feature_text in feature_name_map:
                features_data[feature_name_map[feature_text]] = True
                print(f"  ✓ {feature_text}")
            else:
                print(f"  Unknown feature: {feature_text}")

    except Exception as e:
        print(f"Error extracting apartment features: {e}")

    return features_data


def scrape_rental_terms(driver):
    """Extract specific rental terms"""
    terms_data = {
        "utilities_payment": "",
        "security_deposit": "",
        "commission": "",
        "prepayment": "",
        "rental_period": "",
        "living_conditions": "",
        "negotiable": "",
    }

    # For extracting monetary values
    def clean_money(text):
        return re.sub(r"[^\d]", "", text) if text else ""

    try:
        # Find the terms container
        terms_section = driver.find_elements(
            By.CSS_SELECTOR, "div[data-name='OfferFactsInSidebar']"
        )

        if not terms_section:
            print("Rental terms section not found")
            return terms_data

        print("\nRental Terms:")

        # Get all term items
        term_items = driver.find_elements(
            By.CSS_SELECTOR, "div[data-name='OfferFactItem']"
        )

        # Russian term names to our field mapping
        term_mapping = {
            "Оплата ЖКХ": "utilities_payment",
            "Залог": "security_deposit",
            "Комиссии": "commission",
            "Комиссия": "commission",
            "Предоплата": "prepayment",
            "Предоплаты": "prepayment",
            "Срок аренды": "rental_period",
            "Условия проживания": "living_conditions",
            "Торг": "negotiable",
        }

        for item in term_items:
            spans = item.find_elements(By.TAG_NAME, "span")

            if len(spans) >= 2:
                term_name = driver.execute_script(
                    "return arguments[0].textContent;", spans[0]
                ).strip()
                term_value = driver.execute_script(
                    "return arguments[0].textContent;", spans[1]
                ).strip()

                # Map the Russian term to our field name
                field_name = term_mapping.get(term_name)

                if field_name:
                    # Special handling for monetary values
                    if field_name == "security_deposit":
                        terms_data[field_name] = clean_money(term_value)
                    else:
                        terms_data[field_name] = term_value

                    print(f"  {term_name}: {term_value}")
                else:
                    print(f"  Unknown term: {term_name}: {term_value}")

    except Exception as e:
        print(f"Error extracting rental terms: {e}")

    return terms_data


def clean_price(price_text):
    # Remove "₽/мес." and spaces
    return re.sub(r"[^\d]", "", price_text) if price_text else ""


def clean_change(change_text):
    # Remove "₽" and spaces, preserve the - sign if present
    if not change_text or change_text.strip() == "":
        return ""

    # Extract just the numeric value
    return re.sub(r"[^\d]", "", change_text)


def scrape_apartment_details(driver):
    """Extract apartment details from OfferSummaryInfoLayout section"""
    apartment_details = {
        "total_area": "",
        "living_area": "",
        "layout": "",
        "apartment_type": "",
        "kitchen_area": "",
        "ceiling_height": "",
        "bathroom": "",
        "balcony": "",
        "sleeping_places": "",
        "renovation": "",
        "view": "",  # Вид из окон
    }

    try:
        # Find the apartment details section
        apartment_sections = driver.find_elements(
            By.CSS_SELECTOR, "div[data-name='OfferSummaryInfoGroup']"
        )

        if not apartment_sections:
            print("Apartment details section not found")
            return apartment_details

        # Process the first group - Apartment info
        # Look for all apartment info items
        apartment_items = apartment_sections[0].find_elements(
            By.CSS_SELECTOR, "div[data-name='OfferSummaryInfoItem']"
        )

        print("\nApartment Details:")

        # Field mapping from Russian to our dictionary keys
        field_map = {
            "Тип жилья": "apartment_type",
            "Планировка": "layout",
            "Общая площадь": "total_area",
            "Жилая площадь": "living_area",
            "Площадь кухни": "kitchen_area",
            "Высота потолков": "ceiling_height",
            "Санузел": "bathroom",
            "Балкон/лоджия": "balcony",
            "Спальных мест": "sleeping_places",
            "Ремонт": "renovation",
            "Вид из окон": "view",
        }

        # Extract all details
        for item in apartment_items:
            p_tags = item.find_elements(By.TAG_NAME, "p")
            if len(p_tags) >= 2:
                field_name = driver.execute_script(
                    "return arguments[0].textContent;", p_tags[0]
                ).strip()
                field_value = driver.execute_script(
                    "return arguments[0].textContent;", p_tags[1]
                ).strip()

                # Map to our field names
                field_key = field_map.get(field_name)
                if field_key:
                    apartment_details[field_key] = field_value
                    print(f"  {field_name}: {field_value}")
                else:
                    print(f"  Unknown field: {field_name}: {field_value}")

    except Exception as e:
        print(f"Error extracting apartment details: {e}")

    return apartment_details


def scrape_building_details(driver):
    """Extract building details from OfferSummaryInfoLayout section"""
    building_details = {
        "year_built": "",
        "building_series": "",
        "garbage_chute": "",
        "elevators": "",
        "building_type": "",
        "ceiling_type": "",
        "parking": "",
        "entrances": "",
        "heating": "",
        "emergency": "",
        "gas_supply": "",
    }

    try:
        # Find the building details section (usually the second group)
        building_sections = driver.find_elements(
            By.CSS_SELECTOR, "div[data-name='OfferSummaryInfoGroup']"
        )

        if len(building_sections) < 2:
            print("Building details section not found")
            return building_details

        # Process the second group - Building info
        # Look for all building info items
        building_items = building_sections[1].find_elements(
            By.CSS_SELECTOR, "div[data-name='OfferSummaryInfoItem']"
        )

        print("\nBuilding Details:")

        # Field mapping from Russian to our dictionary keys
        field_map = {
            "Год постройки": "year_built",
            "Строительная серия": "building_series",
            "Мусоропровод": "garbage_chute",
            "Количество лифтов": "elevators",
            "Тип дома": "building_type",
            "Тип перекрытий": "ceiling_type",
            "Парковка": "parking",
            "Подъезды": "entrances",
            "Отопление": "heating",
            "Аварийность": "emergency",
            "Газоснабжение": "gas_supply",
        }

        # Extract all details
        for item in building_items:
            p_tags = item.find_elements(By.TAG_NAME, "p")
            if len(p_tags) >= 2:
                field_name = driver.execute_script(
                    "return arguments[0].textContent;", p_tags[0]
                ).strip()
                field_value = driver.execute_script(
                    "return arguments[0].textContent;", p_tags[1]
                ).strip()

                # Map to our field names
                field_key = field_map.get(field_name)
                if field_key:
                    building_details[field_key] = field_value
                    print(f"  {field_name}: {field_value}")
                else:
                    print(f"  Unknown field: {field_name}: {field_value}")

    except Exception as e:
        print(f"Error extracting building details: {e}")

    return building_details


def check_if_unpublished(driver):
    """Check if the listing has been unpublished"""
    try:
        unpublished_elements = driver.find_elements(
            By.XPATH,
            "//div[@data-name='OfferUnpublished' and contains(text(), 'Объявление снято с публикации')]",
        )
        is_unpublished = len(unpublished_elements) > 0
        print(f"Listing unpublished: {is_unpublished}")
        return is_unpublished
    except Exception as e:
        print(f"Error checking if unpublished: {e}")
        return False


def get_updated_date(driver):
    """Extract the updated date from metadata-updated-date element"""
    try:
        updated_date_element = driver.find_element(
            By.CSS_SELECTOR, "div[data-testid='metadata-updated-date']"
        )
        if updated_date_element:
            updated_text = driver.execute_script(
                "return arguments[0].textContent;", updated_date_element
            ).strip()
            # Extract date after "Обновлено:"
            date_match = re.search(r"Обновлено:\s+(.+)$", updated_text)
            if date_match:
                updated_date = date_match.group(1).strip()
                updated_date_iso = convert_date(updated_date)
                print(f"Updated date: {updated_date} -> {updated_date_iso}")
                return updated_date, updated_date_iso

        print("Updated date not found")
        return "", ""
    except Exception as e:
        print(f"Error extracting updated date: {e}")
        return "", ""


def get_estimated_price(driver):
    """Extract the estimated price with multiple selectors and diagnostic information"""
    max_attempts = 3

    # List of possible selectors to try
    selectors = [
        "[data-testid='valuation_estimationPrice'] .a10a3f92e9--price--w7ha0 span",
        "[data-testid='valuation_estimationPrice'] span",
        ".a10a3f92e9--price--w7ha0 span",
        ".a10a3f92e9--price--w7ha0",
        "[data-testid='valuation_estimationPrice']",
        ".a10a3f92e9--valuation-price--RwTI_",  # Alternative class name
        ".a10a3f92e9--valuation-price-container--AY2Rq",  # Parent container class
    ]

    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Estimation attempt {attempt}/{max_attempts}...")

            # Refresh the page on retry attempts
            if attempt > 1:
                print("Refreshing page...")
                driver.refresh()
                time.sleep(3)

            # Take screenshot to diagnose the page
            screenshot_path = f"page_screenshot_attempt_{attempt}.png"
            driver.save_screenshot(screenshot_path)
            print(f"Saved screenshot to {screenshot_path}")

            # Use multiple scroll positions
            scroll_positions = [0.2, 0.4, 0.6, 0.8, 1.0]

            for pos in scroll_positions:
                # Scroll to position
                driver.execute_script(
                    f"window.scrollTo(0, document.body.scrollHeight * {pos});"
                )
                print(f"Scrolled to {int(pos*100)}% of page height")
                time.sleep(2)

                # Take a screenshot at this scroll position
                scroll_screenshot = f"scroll_{int(pos*100)}_attempt_{attempt}.png"
                driver.save_screenshot(scroll_screenshot)
                print(f"Saved scroll position screenshot to {scroll_screenshot}")

                # Try all selectors at each scroll position
                for selector in selectors:
                    try:
                        print(f"Trying selector: {selector}")
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)

                        if elements:
                            print(
                                f"Found {len(elements)} elements with selector: {selector}"
                            )

                            for i, el in enumerate(elements):
                                try:
                                    # Try direct text property
                                    text = el.text.strip()
                                    print(f"Element {i+1} text: '{text}'")

                                    # Also try JavaScript textContent
                                    js_text = driver.execute_script(
                                        "return arguments[0].textContent;", el
                                    ).strip()
                                    print(f"Element {i+1} JS text: '{js_text}'")

                                    # Look for prices in either text
                                    for content in [text, js_text]:
                                        if content and any(
                                            c.isdigit() for c in content
                                        ):
                                            digits = re.sub(r"[^\d]", "", content)
                                            if digits:
                                                print(
                                                    f"Estimated price found: {content} -> {digits}"
                                                )
                                                return content, digits
                                except Exception as el_err:
                                    print(f"Error processing element {i+1}: {el_err}")
                    except Exception as sel_err:
                        print(f"Error with selector '{selector}': {sel_err}")

            print(f"No estimation found on attempt {attempt}")

        except Exception as e:
            print(f"Error during estimation attempt {attempt}: {e}")
            if attempt < max_attempts:
                print(f"Waiting before retry...")
                time.sleep(3 * attempt)
            else:
                print("All attempts failed")

        finally:
            try:
                driver.execute_script("window.scrollTo(0, 0);")
            except:
                pass

    print("Failed to find estimated price after all attempts")
    return "", ""


def get_already_processed_ids(
    price_history_file,
    stats_file,
    features_file,
    terms_file,
    apartment_details_file,
    building_details_file,
):
    """Get sets of offer_ids that have been fully processed (appear in all files)"""
    file_id_sets = []
    all_ids = set()  # For reporting total unique IDs

    # Check all data files
    for file_path in [
        price_history_file,
        stats_file,
        features_file,
        terms_file,
        apartment_details_file,
        building_details_file,
    ]:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    file_ids = set(row["offer_id"] for row in reader)
                file_id_sets.append(file_ids)
                all_ids.update(file_ids)
                print(
                    f"Found {len(file_ids)} offer IDs in {os.path.basename(file_path)}"
                )
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                # If we can't read a file, add an empty set
                file_id_sets.append(set())
        else:
            print(f"File does not exist: {file_path}")
            file_id_sets.append(set())

    # Find the intersection of all sets (IDs that appear in ALL files)
    if file_id_sets:
        fully_processed_ids = set.intersection(*file_id_sets)
        print(f"Total of {len(all_ids)} unique offer IDs across all files")
        print(
            f"Total of {len(fully_processed_ids)} offer IDs fully processed (in all files)"
        )
    else:
        fully_processed_ids = set()
        print("No files found, no fully processed IDs")

    return fully_processed_ids


def get_category_processed_ids(file_path):
    """Get set of offer_ids that have been processed for a specific category"""
    processed_ids = set()
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                processed_ids = set(row["offer_id"] for row in reader)
            print(
                f"Found {len(processed_ids)} offer IDs in {os.path.basename(file_path)}"
            )
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    else:
        print(f"File does not exist: {file_path}")
    return processed_ids


def scrape_price_history_with_direction(driver, offer_id):
    """Extract price history with proper change direction"""
    price_history = []

    try:
        # Find the price history table
        price_history_table = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "div.a10a3f92e9--history-wrapper--dymNq table, div._25d45facb5--history-wrapper--dymNq table",
                )
            )
        )

        rows = price_history_table.find_elements(By.TAG_NAME, "tr")

        if rows:
            print("\nPrice History Information:")
            entry_count = 0
            for i, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:  # Need at least date and price
                    # Get date and price
                    date_text = driver.execute_script(
                        "return arguments[0].textContent;", cells[0]
                    ).strip()
                    price_text = driver.execute_script(
                        "return arguments[0].textContent;", cells[1]
                    ).strip()

                    # Initialize change variables
                    change_text = ""
                    is_increase = False

                    # Get change if available (third cell)
                    if len(cells) >= 3:
                        # Get the class attribute of the change cell
                        change_cell_class = cells[2].get_attribute("class")

                        # Check if it's an increase or decrease
                        is_increase = "event-diff-increase" in change_cell_class

                        # Get the change text
                        change_text = driver.execute_script(
                            "return arguments[0].textContent;", cells[2]
                        ).strip()

                    # Skip if we couldn't get date or price
                    if not date_text or not price_text:
                        print(f"  Skipping entry {i+1} - missing date or price")
                        continue

                    # Convert Russian date to ISO format
                    date_iso = convert_date(date_text)

                    # Clean the price and change values
                    price_clean = clean_price(price_text)
                    change_clean = ""
                    if change_text:
                        change_numeric = re.sub(r"[^\d]", "", change_text)
                        if change_numeric:
                            change_clean = (
                                "+" if is_increase else "-"
                            ) + change_numeric

                    # Store the processed data
                    price_history.append(
                        {
                            "offer_id": offer_id,
                            "date": date_text,
                            "date_iso": date_iso,
                            "price": price_text,
                            "change": change_text,
                            "price_clean": price_clean,
                            "change_clean": change_clean,
                            "is_increase": is_increase,
                        }
                    )
                    entry_count += 1

                    print(f"Entry {i+1}:")
                    print(f"  Date: {date_text} -> {date_iso}")
                    print(f"  Price: {price_text}")
                    print(
                        f"  Change: {change_text} -> {change_clean} ({'Increase' if is_increase else 'Decrease'})"
                    )

            return price_history, entry_count > 0

    except Exception as e:
        print(f"Error extracting price history: {e}")

    return price_history, False


def initialize_csv_files(
    price_history_file,
    stats_file,
    features_file,
    terms_file,
    apartment_details_file,
    building_details_file,
    estimation_file,
):
    """Initialize CSV files with specific headers for each data type"""
    # CSV headers
    price_history_header = [
        "offer_id",
        "date",
        "date_iso",
        "price",
        "price_clean",
        "change",
        "change_clean",
        "is_increase",
    ]

    stats_header = [
        "offer_id",
        "creation_date",
        "creation_date_iso",
        "updated_date",  # New field
        "updated_date_iso",  # New field
        "total_views",
        "recent_views",
        "unique_views",
        "is_unpublished",  # New field
    ]

    # New estimation header
    estimation_header = ["offer_id", "estimated_price", "estimated_price_clean"]

    # Specific features fields (updated with new fields)
    features_header = [
        "offer_id",
        "has_refrigerator",
        "has_dishwasher",
        "has_washing_machine",
        "has_air_conditioner",
        "has_tv",
        "has_internet",
        "has_kitchen_furniture",
        "has_room_furniture",
        "has_bathtub",
        "has_shower_cabin",
    ]

    # Specific terms fields (updated with new fields)
    terms_header = [
        "offer_id",
        "utilities_payment",
        "security_deposit",
        "commission",
        "prepayment",
        "rental_period",
        "living_conditions",
        "negotiable",
    ]

    # Apartment details fields
    apartment_details_header = [
        "offer_id",
        "layout",
        "apartment_type",
        "total_area",
        "living_area",
        "kitchen_area",
        "ceiling_height",
        "bathroom",
        "balcony",
        "sleeping_places",
        "renovation",
        "view",
    ]

    # Building details fields
    building_details_header = [
        "offer_id",
        "year_built",
        "building_series",
        "garbage_chute",
        "elevators",
        "building_type",
        "ceiling_type",
        "parking",
        "entrances",
        "heating",
        "emergency",
        "gas_supply",
    ]

    # Initialize each file with its specific headers
    for file_path, headers in [
        (price_history_file, price_history_header),
        (stats_file, stats_header),
        (features_file, features_header),
        (terms_file, terms_header),
        (apartment_details_file, apartment_details_header),
        (building_details_file, building_details_header),
        (estimation_file, estimation_header),  # Add the new file
    ]:
        if not os.path.exists(file_path):
            try:
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                print(f"Created new file: {file_path}")
            except Exception as e:
                print(f"Error creating file {file_path}: {e}")

    return (
        price_history_header,
        stats_header,
        features_header,
        terms_header,
        apartment_details_header,
        building_details_header,
        estimation_header,
    )


def scrape_cian_apartment(driver, offer_id, offer_url):
    print(f"\n{'='*50}")
    print(f"Processing listing {offer_id}: {offer_url}")
    print(f"{'='*50}")

    # Store all extracted data
    price_history = []
    stats_info = {"offer_id": offer_id}
    features_info = {"offer_id": offer_id}
    terms_info = {"offer_id": offer_id}
    apartment_details = {"offer_id": offer_id}
    building_details = {"offer_id": offer_id}
    estimation_info = {"offer_id": offer_id}  # New
    has_price_history = False
    has_stats = False
    has_features = False
    has_terms = False
    has_apartment_details = False
    has_building_details = False
    has_estimation = False  # New
    try:
        # Navigate to the property page
        driver.get(offer_url)
        print(f"Accessing: {offer_url}")

        # Wait for page to load
        time.sleep(5)

        # First, try to close any existing overlays
        try:
            # Look for overlay elements
            overlays = driver.find_elements(
                By.CSS_SELECTOR,
                "._25d45facb5--overlay--nBBXF, .a10a3f92e9--overlay--nBBXF",
            )

            if overlays:
                print("Found overlay blocking clicks. Attempting to close...")
                # Try pressing Escape key to close overlay
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
        except Exception as e:
            print(f"Error when trying to close overlays: {e}")

        # NEW: Check if listing is unpublished
        is_unpublished = check_if_unpublished(driver)
        stats_info["is_unpublished"] = is_unpublished

        # NEW: Get updated date
        updated_date, updated_date_iso = get_updated_date(driver)
        stats_info["updated_date"] = updated_date
        stats_info["updated_date_iso"] = updated_date_iso

        # NEW: Get estimated price - now stored in separate object
        estimated_price, estimated_price_clean = get_estimated_price(driver)
        if estimated_price:
            estimation_info["estimated_price"] = estimated_price
            estimation_info["estimated_price_clean"] = estimated_price_clean
            has_estimation = True

        # Try extracting price history with more reliable approach
        try:
            # First check if price history section exists
            price_history_sections = driver.find_elements(
                By.CSS_SELECTOR,
                "div.a10a3f92e9--history-wrapper--dymNq, div._25d45facb5--history-wrapper--dymNq",
            )

            if not price_history_sections:
                print("Price history section not found on this page")
            else:
                price_history_table = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "div.a10a3f92e9--history-wrapper--dymNq table, div._25d45facb5--history-wrapper--dymNq table",
                        )
                    )
                )

                rows = price_history_table.find_elements(By.TAG_NAME, "tr")

                if rows:
                    print("\nPrice History Information:")
                    entry_count = 0
                    for i, row in enumerate(rows):
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 2:  # Need at least date and price
                            # Get date and price
                            date_text = driver.execute_script(
                                "return arguments[0].textContent;", cells[0]
                            ).strip()
                            price_text = driver.execute_script(
                                "return arguments[0].textContent;", cells[1]
                            ).strip()

                            # Initialize change variables
                            change_text = ""
                            is_increase = False

                            # Get change if available (third cell)
                            if len(cells) >= 3:
                                # Get the class attribute of the change cell
                                change_cell_class = cells[2].get_attribute("class")

                                # Check if it's an increase or decrease
                                is_increase = "event-diff-increase" in change_cell_class

                                # Get the change text
                                change_text = driver.execute_script(
                                    "return arguments[0].textContent;", cells[2]
                                ).strip()

                            # Skip if we couldn't get date or price
                            if not date_text or not price_text:
                                print(f"  Skipping entry {i+1} - missing date or price")
                                continue

                            # Convert Russian date to ISO format
                            date_iso = convert_date(date_text)

                            # Clean the price and change values
                            price_clean = clean_price(price_text)

                            # UPDATED: Use direction info to properly format change
                            change_clean = ""
                            if change_text:
                                change_numeric = re.sub(r"[^\d]", "", change_text)
                                if change_numeric:
                                    change_clean = (
                                        "+" if is_increase else "-"
                                    ) + change_numeric

                            # Store the raw text data
                            # When creating price history entries:
                            price_history.append(
                                {
                                    "offer_id": offer_id,
                                    "date": date_text,
                                    "date_iso": date_iso,
                                    "price": price_text,
                                    "change": change_text,
                                    "price_clean": clean_price(price_text),
                                    "change_clean": change_clean,
                                    "is_increase": is_increase,
                                }
                            )
                            entry_count += 1

                            print(f"Entry {i+1}:")
                            print(f"  Date: {date_text} -> {date_iso}")
                            print(f"  Price: {price_text}")
                            print(
                                f"  Change: {change_text} -> {change_clean} ({'Increase' if is_increase else 'Decrease' if change_text else 'No change'})"
                            )

                    # Only set has_price_history if we actually got data
                    if entry_count > 0:
                        has_price_history = True
                        print(
                            f"Successfully extracted {entry_count} price history entries"
                        )
                    else:
                        print(
                            "Found price history table but couldn't extract any entries"
                        )
                else:
                    print("Price history table has no rows")

        except Exception as e:
            print(f"Could not extract price history information: {e}")
        # 2. Click the button to show additional information using JavaScript
        try:
            # First check if stats button exists
            stats_buttons = driver.find_elements(
                By.CSS_SELECTOR, "button[data-name='OfferStats']"
            )

            if not stats_buttons:
                print("Stats button not found on this page")
            else:
                stats_button = stats_buttons[0]

                print("\nClicking stats button using JavaScript...")
                driver.execute_script("arguments[0].click();", stats_button)

                time.sleep(2)

                # Try to get information from popup
                popup_info = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "div.a10a3f92e9--information--JQbJ6, div._25d45facb5--information--JQbJ6",
                        )
                    )
                )

                # Get individual stats elements
                stats_elements = popup_info.find_elements(By.TAG_NAME, "div")

                # Process stats data
                stats_extracted = False
                if stats_elements:
                    for element in stats_elements:
                        stat_text = driver.execute_script(
                            "return arguments[0].textContent;", element
                        ).strip()
                        print(f"Stat: {stat_text}")

                        # Extract creation date
                        if "с даты создания объявления" in stat_text:
                            creation_date = re.search(r"(\d+\.\d+\.\d+)", stat_text)
                            if creation_date:
                                stats_info["creation_date"] = creation_date.group(1)
                                # Convert the dot format date to ISO format
                                stats_info["creation_date_iso"] = convert_date(
                                    stats_info["creation_date"]
                                )
                                stats_extracted = True

                                views_match = re.search(r"(\d+)\s+просмотр", stat_text)
                                if views_match:
                                    stats_info["total_views"] = views_match.group(1)

                        # Extract recent views - handle both просмотр and просмотров
                        if "за последние" in stat_text:
                            recent_views = re.search(r"(\d+)\s+просмотр", stat_text)
                            if recent_views:
                                stats_info["recent_views"] = recent_views.group(1)
                                stats_extracted = True

                        # Extract unique views - handle both уникальных and уникальный
                        if "уникальн" in stat_text:
                            unique_views = re.search(r"(\d+)\s+уникальн", stat_text)
                            if unique_views:
                                stats_info["unique_views"] = unique_views.group(1)
                                stats_extracted = True

                # Only set has_stats if we actually extracted something
                has_stats = stats_extracted

                # Print the extracted stats info
                print("\nExtracted Stats Information:")
                for key, value in stats_info.items():
                    print(f"  {key}: {value}")

                if has_stats:
                    print("Successfully extracted stats information")
                else:
                    print("Could not extract any useful stats information")

                # Close this popup before proceeding
                print("Pressing ESC to close popup...")
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)

        except Exception as e:
            print(f"Could not click stats button or extract popup information: {e}")

        # Extract specific apartment features
        try:
            features_data = scrape_apartment_features(driver)
            if any(value for key, value in features_data.items() if key != "offer_id"):
                features_info.update(features_data)
                has_features = True
                print("Successfully extracted features information")
            else:
                print("No features found for this apartment")
        except Exception as e:
            print(f"Error extracting apartment features: {e}")

        # Extract specific rental terms
        try:
            terms_data = scrape_rental_terms(driver)
            if any(value for key, value in terms_data.items() if key != "offer_id"):
                terms_info.update(terms_data)
                has_terms = True
                print("Successfully extracted rental terms information")
            else:
                print("No rental terms found for this apartment")
        except Exception as e:
            print(f"Error extracting rental terms: {e}")

        # Extract apartment details
        try:
            apartment_data = scrape_apartment_details(driver)
            if any(value for key, value in apartment_data.items()):
                apartment_details.update(apartment_data)
                has_apartment_details = True
                print("Successfully extracted apartment details")
            else:
                print("No apartment details found")
        except Exception as e:
            print(f"Error extracting apartment details: {e}")

        # Extract building details
        try:
            building_data = scrape_building_details(driver)
            if any(value for key, value in building_data.items()):
                building_details.update(building_data)
                has_building_details = True
                print("Successfully extracted building details")
            else:
                print("No building details found")
        except Exception as e:
            print(f"Error extracting building details: {e}")

        return (
            offer_id,
            price_history,
            stats_info,
            features_info,
            terms_info,
            apartment_details,
            building_details,
            has_price_history,
            has_stats,
            has_features,
            has_terms,
            has_apartment_details,
            has_building_details,
        )

    except Exception as e:
        print(f"An error occurred processing listing {offer_id}: {e}")
        empty_features = {"offer_id": offer_id}
        empty_terms = {"offer_id": offer_id}
        empty_apartment = {"offer_id": offer_id}
        empty_building = {"offer_id": offer_id}
        return (
            offer_id,
            [],
            {"offer_id": offer_id},
            empty_features,
            empty_terms,
            empty_apartment,
            empty_building,
            False,
            False,
            False,
            False,
            False,
            False,
        )


def main():
    # Create output directory with explicit permissions
    output_dir = "cian_data"
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, mode=0o755)
            print(f"Created directory: {output_dir}")
        except Exception as e:
            print(f"Error creating directory: {e}")

    # Define output file paths
    price_history_file = os.path.join(output_dir, "price_history.csv")
    stats_file = os.path.join(output_dir, "stats.csv")
    features_file = os.path.join(output_dir, "features.csv")
    terms_file = os.path.join(output_dir, "rental_terms.csv")
    apartment_details_file = os.path.join(output_dir, "apartment_details.csv")
    building_details_file = os.path.join(output_dir, "building_details.csv")
    estimation_file = os.path.join(output_dir, "estimation.csv")  # New file
    # Get processed IDs for each category separately
    price_history_ids = get_category_processed_ids(price_history_file)
    stats_ids = get_category_processed_ids(stats_file)
    features_ids = get_category_processed_ids(features_file)
    terms_ids = get_category_processed_ids(terms_file)
    apartment_details_ids = get_category_processed_ids(apartment_details_file)
    building_details_ids = get_category_processed_ids(building_details_file)
    estimation_ids = get_category_processed_ids(estimation_file)  # New
    # Create a set of all IDs that have at least one category processed
    all_processed_ids = set().union(
        price_history_ids,
        stats_ids,
        features_ids,
        terms_ids,
        apartment_details_ids,
        building_details_ids,
        estimation_ids,  # Updated
    )

    # Get fully processed IDs (all categories complete)
    fully_processed_ids = (
        set.intersection(
            price_history_ids,
            stats_ids,
            features_ids,
            terms_ids,
            apartment_details_ids,
            building_details_ids,
            estimation_ids,  # Updated
        )
        if all_processed_ids
        else set()
    )

    print(f"Total of {len(all_processed_ids)} unique offer IDs across all files")
    print(
        f"Total of {len(fully_processed_ids)} offer IDs fully processed (in all files)"
    )

    # Initialize CSV files if they don't exist and get headers
    headers = initialize_csv_files(
        price_history_file,
        stats_file,
        features_file,
        terms_file,
        apartment_details_file,
        building_details_file,
        estimation_file,  # Updated
    )

    (
        price_history_header,
        stats_header,
        features_header,
        terms_header,
        apartment_details_header,
        building_details_header,
        estimation_header,
    ) = headers  # Updated

    # Track statistics for this run
    stats = {
        "total": 0,
        "skipped": 0,
        "processed": 0,
        "failed": 0,
        "new_price_history": 0,
        "new_stats": 0,
        "new_features": 0,
        "new_terms": 0,
        "new_apartment_details": 0,
        "new_building_details": 0,
        "new_estimation": 0,  # New stat
    }

    # Connect to existing Chrome session
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    # Try to connect to the running Chrome instance
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("Successfully connected to existing Chrome session")
    except Exception as e:
        print(f"Could not connect to Chrome: {e}")
        print("\nPlease make sure Chrome is running with remote debugging enabled.")
        print("Run this command in Terminal first:")
        print(
            "/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222"
        )
        return
    save_cookies(driver)  # <-- Add this after you're logged in

    # Read the input CSV with offer IDs and URLs
    input_file = "cian_apartments.csv"
    max_distance = 3.0  # Set your desired maximum distance here

    try:
        # Use pandas to read and filter the CSV
        import pandas as pd

        apartments_df = pd.read_csv(input_file, encoding="utf-8")
        print(f"Loaded {len(apartments_df)} apartments from {input_file}")

        # Filter apartments by distance
        filtered_df = apartments_df[apartments_df["distance"] <= max_distance].copy()
        print(
            f"Filtered from {len(apartments_df)} to {len(filtered_df)} apartments with distance <= {max_distance}"
        )

        # Convert offer_id to string for consistency
        filtered_df["offer_id"] = filtered_df["offer_id"].astype(str)

        # Filter out completely processed apartments
        to_process_df = filtered_df[~filtered_df["offer_id"].isin(fully_processed_ids)]

        print(
            f"Filtered out {len(filtered_df) - len(to_process_df)} fully processed apartments"
        )
        print(f"Remaining {len(to_process_df)} apartments to process")

        # Convert back to list of dictionaries for processing
        apartments = to_process_df.to_dict("records")

        stats["total"] = len(filtered_df)
        stats["skipped"] = len(filtered_df) - len(to_process_df)

        # Process each apartment
        for i, apartment in enumerate(apartments):
            offer_id = apartment["offer_id"]
            offer_url = apartment["offer_url"]

            # Ensure URL is properly formatted
            if not offer_url.startswith("http"):
                offer_url = f"https://www.cian.ru/rent/flat/{offer_id}/"

            # Determine which categories need processing for this apartment
            need_price_history = offer_id not in price_history_ids
            need_stats = offer_id not in stats_ids
            need_features = offer_id not in features_ids
            need_terms = offer_id not in terms_ids
            need_apartment_details = offer_id not in apartment_details_ids
            need_building_details = offer_id not in building_details_ids
            need_estimation = offer_id not in estimation_ids  # New

            # Print what needs to be processed
            needed_categories = []
            if need_price_history:
                needed_categories.append("price history")
            if need_stats:
                needed_categories.append("stats")
            if need_features:
                needed_categories.append("features")
            if need_terms:
                needed_categories.append("rental terms")
            if need_apartment_details:
                needed_categories.append("apartment details")
            if need_building_details:
                needed_categories.append("building details")
            if need_estimation:
                needed_categories.append("estimation")  # New

            print(f"\nApartment {i+1}/{len(apartments)}: {offer_id}")
            print(f"Needed data: {', '.join(needed_categories)}")

            if not needed_categories:
                print("All data already present, skipping.")
                continue

            print(f"{'='*50}")
            print(f"Processing listing {offer_id}: {offer_url}")
            print(f"{'='*50}")

            # Navigate to the property page
            try:
                driver.get(offer_url)
                print(f"Accessing: {offer_url}")

                # Wait for page to load
                time.sleep(5)

                # First, try to close any existing overlays
                try:
                    # Look for overlay elements
                    overlays = driver.find_elements(
                        By.CSS_SELECTOR,
                        "._25d45facb5--overlay--nBBXF, .a10a3f92e9--overlay--nBBXF",
                    )

                    if overlays:
                        print("Found overlay blocking clicks. Attempting to close...")
                        # Try pressing Escape key to close overlay
                        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                        time.sleep(1)
                except Exception as e:
                    print(f"Error when trying to close overlays: {e}")

                # Initialize results with default values
                price_history = []
                stats_info = {"offer_id": offer_id}
                features_info = {"offer_id": offer_id}
                terms_info = {"offer_id": offer_id}
                apartment_details = {"offer_id": offer_id}
                building_details = {"offer_id": offer_id}
                estimation_info = {"offer_id": offer_id}  # New
                has_price_history = False
                has_stats = False
                has_features = False
                has_terms = False
                has_apartment_details = False
                has_building_details = False
                has_estimation = False  # New
                # Only scrape price history if needed
                if need_price_history:
                    try:
                        # Use the function that already handles direction detection
                        price_history, has_price_history = (
                            scrape_price_history_with_direction(driver, offer_id)
                        )
                        if has_price_history:
                            print(
                                f"Successfully extracted {len(price_history)} price history entries"
                            )
                        else:
                            print("Could not extract price history information")
                    except Exception as e:
                        print(f"Error extracting price history: {e}")
                        price_history = []
                        has_price_history = False

                # Only scrape stats if needed
                if need_stats:
                    try:
                        # NEW: Check if listing is unpublished
                        is_unpublished = check_if_unpublished(driver)
                        stats_info["is_unpublished"] = is_unpublished

                        # NEW: Get updated date
                        updated_date, updated_date_iso = get_updated_date(driver)
                        stats_info["updated_date"] = updated_date
                        stats_info["updated_date_iso"] = updated_date_iso

                        # Then continue with existing stats button clicking and data extraction
                        # First check if stats button exists
                        stats_buttons = driver.find_elements(
                            By.CSS_SELECTOR, "button[data-name='OfferStats']"
                        )

                        if not stats_buttons:
                            print("Stats button not found on this page")
                        else:
                            stats_button = stats_buttons[0]

                            print("\nClicking stats button using JavaScript...")
                            driver.execute_script("arguments[0].click();", stats_button)

                            time.sleep(2)

                            # Try to get information from popup
                            popup_info = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located(
                                    (
                                        By.CSS_SELECTOR,
                                        "div.a10a3f92e9--information--JQbJ6, div._25d45facb5--information--JQbJ6",
                                    )
                                )
                            )

                            # Get individual stats elements
                            stats_elements = popup_info.find_elements(
                                By.TAG_NAME, "div"
                            )

                            # Process stats data
                            stats_extracted = False
                            if stats_elements:
                                for element in stats_elements:
                                    stat_text = driver.execute_script(
                                        "return arguments[0].textContent;", element
                                    ).strip()
                                    print(f"Stat: {stat_text}")

                                    # Extract creation date
                                    if "с даты создания объявления" in stat_text:
                                        creation_date = re.search(
                                            r"(\d+\.\d+\.\d+)", stat_text
                                        )
                                        if creation_date:
                                            stats_info["creation_date"] = (
                                                creation_date.group(1)
                                            )
                                            # Convert the dot format date to ISO format
                                            stats_info["creation_date_iso"] = (
                                                convert_date(
                                                    stats_info["creation_date"]
                                                )
                                            )
                                            stats_extracted = True

                                            views_match = re.search(
                                                r"(\d+)\s+просмотр", stat_text
                                            )
                                            if views_match:
                                                stats_info["total_views"] = (
                                                    views_match.group(1)
                                                )

                                    # Extract recent views - handle both просмотр and просмотров
                                    if "за последние" in stat_text:
                                        recent_views = re.search(
                                            r"(\d+)\s+просмотр", stat_text
                                        )
                                        if recent_views:
                                            stats_info["recent_views"] = (
                                                recent_views.group(1)
                                            )
                                            stats_extracted = True

                                    # Extract unique views - handle both уникальных and уникальный
                                    if "уникальн" in stat_text:
                                        unique_views = re.search(
                                            r"(\d+)\s+уникальн", stat_text
                                        )
                                        if unique_views:
                                            stats_info["unique_views"] = (
                                                unique_views.group(1)
                                            )
                                            stats_extracted = True

                            # Only set has_stats if we actually extracted something
                            has_stats = stats_extracted

                            # Print the extracted stats info
                            print("\nExtracted Stats Information:")
                            for key, value in stats_info.items():
                                print(f"  {key}: {value}")

                            if has_stats:
                                print("Successfully extracted stats information")
                            else:
                                print("Could not extract any useful stats information")

                            # Close this popup before proceeding
                            print("Pressing ESC to close popup...")
                            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                            time.sleep(1)
                    except Exception as e:
                        print(
                            f"Could not click stats button or extract popup information: {e}"
                        )
                else:
                    print("Stats already processed, skipping")

                # Extract specific apartment features if needed
                if need_features:
                    try:
                        features_data = scrape_apartment_features(driver)
                        if any(
                            value
                            for key, value in features_data.items()
                            if key != "offer_id"
                        ):
                            features_info.update(features_data)
                            has_features = True
                            print("Successfully extracted features information")
                        else:
                            print("No features found for this apartment")
                    except Exception as e:
                        print(f"Error extracting apartment features: {e}")
                else:
                    print("Features already processed, skipping")

                # Extract specific rental terms if needed
                if need_terms:
                    try:
                        terms_data = scrape_rental_terms(driver)
                        if any(
                            value
                            for key, value in terms_data.items()
                            if key != "offer_id"
                        ):
                            terms_info.update(terms_data)
                            has_terms = True
                            print("Successfully extracted rental terms information")
                        else:
                            print("No rental terms found for this apartment")
                    except Exception as e:
                        print(f"Error extracting rental terms: {e}")
                else:
                    print("Rental terms already processed, skipping")

                # Extract apartment details if needed
                if need_apartment_details:
                    try:
                        apartment_data = scrape_apartment_details(driver)
                        if any(value for key, value in apartment_data.items()):
                            apartment_details.update(apartment_data)
                            has_apartment_details = True
                            print("Successfully extracted apartment details")
                        else:
                            print("No apartment details found")
                    except Exception as e:
                        print(f"Error extracting apartment details: {e}")
                else:
                    print("Apartment details already processed, skipping")

                # Extract building details if needed
                if need_building_details:
                    try:
                        building_data = scrape_building_details(driver)
                        if any(value for key, value in building_data.items()):
                            building_details.update(building_data)
                            has_building_details = True
                            print("Successfully extracted building details")
                        else:
                            print("No building details found")
                    except Exception as e:
                        print(f"Error extracting building details: {e}")
                else:
                    print("Building details already processed, skipping")

                # Only get estimated price if needed
                if need_estimation:
                    try:
                        estimated_price, estimated_price_clean = get_estimated_price(
                            driver
                        )
                        if estimated_price:
                            estimation_info = {
                                "offer_id": offer_id,
                                "estimated_price": estimated_price,
                                "estimated_price_clean": estimated_price_clean,
                            }
                            has_estimation = True
                            print("Successfully extracted estimation information")
                        else:
                            estimation_info = {"offer_id": offer_id}
                            has_estimation = False
                            print("No estimation information found")
                    except Exception as e:
                        print(f"Error extracting estimated price: {e}")
                        estimation_info = {"offer_id": offer_id}
                        has_estimation = False
                else:
                    print("Estimation already processed, skipping")
                    estimation_info = {"offer_id": offer_id}
                    has_estimation = False

                stats["processed"] += 1

                # Append price history data to CSV if available
                if has_price_history and price_history:
                    print(
                        f"Writing {len(price_history)} price history entries to {price_history_file}"
                    )
                    try:
                        with open(
                            price_history_file, "a", newline="", encoding="utf-8"
                        ) as f:
                            writer = csv.DictWriter(f, fieldnames=price_history_header)
                            for entry in price_history:
                                writer.writerow(
                                    {
                                        "offer_id": entry["offer_id"],
                                        "date": entry["date"],
                                        "date_iso": entry["date_iso"],
                                        "price": entry["price"],
                                        "price_clean": entry["price_clean"],
                                        "change": entry["change"],
                                        "change_clean": entry["change_clean"],
                                        "is_increase": entry["is_increase"],
                                    }
                                )
                        print(
                            f"Successfully wrote price history data to {price_history_file}"
                        )
                        stats["new_price_history"] += 1
                        # Add to processed set
                        price_history_ids.add(offer_id)
                    except Exception as e:
                        print(f"Error writing price history data: {e}")

                # Append stats data to CSV if available
                if has_stats:
                    print(f"Writing stats data to {stats_file}")
                    try:
                        with open(stats_file, "a", newline="", encoding="utf-8") as f:
                            writer = csv.DictWriter(f, fieldnames=stats_header)
                            writer.writerow(
                                {
                                    field: stats_info.get(field, "")
                                    for field in stats_header
                                }
                            )
                        print(f"Successfully wrote stats data to {stats_file}")
                        stats["new_stats"] += 1
                        # Add to processed set
                        stats_ids.add(offer_id)
                    except Exception as e:
                        print(f"Error writing stats data: {e}")

                # Append features data to CSV if available
                if has_features:
                    print(f"Writing features data to {features_file}")
                    try:
                        with open(
                            features_file, "a", newline="", encoding="utf-8"
                        ) as f:
                            writer = csv.DictWriter(f, fieldnames=features_header)
                            writer.writerow(
                                {
                                    field: features_info.get(field, "")
                                    for field in features_header
                                }
                            )
                        print(f"Successfully wrote features data to {features_file}")
                        stats["new_features"] += 1
                        # Add to processed set
                        features_ids.add(offer_id)
                    except Exception as e:
                        print(f"Error writing features data: {e}")

                # Append terms data to CSV if available
                if has_terms:
                    print(f"Writing terms data to {terms_file}")
                    try:
                        with open(terms_file, "a", newline="", encoding="utf-8") as f:
                            writer = csv.DictWriter(f, fieldnames=terms_header)
                            writer.writerow(
                                {
                                    field: terms_info.get(field, "")
                                    for field in terms_header
                                }
                            )
                        print(f"Successfully wrote terms data to {terms_file}")
                        stats["new_terms"] += 1
                        # Add to processed set
                        terms_ids.add(offer_id)
                    except Exception as e:
                        print(f"Error writing terms data: {e}")

                # Append apartment details to CSV if available
                if has_apartment_details:
                    print(f"Writing apartment details to {apartment_details_file}")
                    try:
                        with open(
                            apartment_details_file, "a", newline="", encoding="utf-8"
                        ) as f:
                            writer = csv.DictWriter(
                                f, fieldnames=apartment_details_header
                            )
                            writer.writerow(
                                {
                                    field: apartment_details.get(field, "")
                                    for field in apartment_details_header
                                }
                            )
                        print(
                            f"Successfully wrote apartment details to {apartment_details_file}"
                        )
                        stats["new_apartment_details"] += 1
                        # Add to processed set
                        apartment_details_ids.add(offer_id)
                    except Exception as e:
                        print(f"Error writing apartment details: {e}")

                # Append building details to CSV if available
                if has_building_details:
                    print(f"Writing building details to {building_details_file}")
                    try:
                        with open(
                            building_details_file, "a", newline="", encoding="utf-8"
                        ) as f:
                            writer = csv.DictWriter(
                                f, fieldnames=building_details_header
                            )
                            writer.writerow(
                                {
                                    field: building_details.get(field, "")
                                    for field in building_details_header
                                }
                            )
                        print(
                            f"Successfully wrote building details to {building_details_file}"
                        )
                        stats["new_building_details"] += 1
                        # Add to processed set
                        building_details_ids.add(offer_id)
                    except Exception as e:
                        print(f"Error writing building details: {e}")

                if has_estimation:
                    print(f"Writing estimation data to {estimation_file}")
                    try:
                        with open(
                            estimation_file, "a", newline="", encoding="utf-8"
                        ) as f:
                            writer = csv.DictWriter(f, fieldnames=estimation_header)
                            writer.writerow(
                                {
                                    field: estimation_info.get(field, "")
                                    for field in estimation_header
                                }
                            )
                        print(
                            f"Successfully wrote estimation data to {estimation_file}"
                        )
                        stats["new_estimation"] += 1
                        # Add to processed set
                        estimation_ids.add(offer_id)
                    except Exception as e:
                        print(f"Error writing estimation data: {e}")

                is_now_complete = all(
                    [
                        offer_id in price_history_ids,
                        offer_id in stats_ids,
                        offer_id in features_ids,
                        offer_id in terms_ids,
                        offer_id in apartment_details_ids,
                        offer_id in building_details_ids,
                        offer_id in estimation_ids,  # New
                    ]
                )
                if is_now_complete:
                    print(f"Apartment {offer_id} is now fully processed!")
                else:
                    # List remaining categories
                    remaining = []
                    if offer_id not in price_history_ids:
                        remaining.append("price history")
                    if offer_id not in stats_ids:
                        remaining.append("stats")
                    if offer_id not in features_ids:
                        remaining.append("features")
                    if offer_id not in terms_ids:
                        remaining.append("rental terms")
                    if offer_id not in apartment_details_ids:
                        remaining.append("apartment details")
                    if offer_id not in building_details_ids:
                        remaining.append("building details")
                    if offer_id not in estimation_ids:
                        remaining.append("estimation")  # New

                    if remaining:
                        print(
                            f"Apartment {offer_id} still missing: {', '.join(remaining)}"
                        )

            except Exception as e:
                print(f"Error processing apartment {offer_id}: {e}")
                stats["failed"] += 1

            # Add a delay between requests to avoid rate limiting
            if i < len(apartments) - 1:  # Don't delay after the last apartment
                delay = 3  # seconds
                print(f"Waiting {delay} seconds before next request...")
                time.sleep(delay)

        # Print summary statistics
        print("\n" + "=" * 50)
        print("PROCESSING SUMMARY")
        print("=" * 50)
        print(f"Total apartments in input file: {stats['total']}")
        print(f"Already fully processed (skipped): {stats['skipped']}")
        print(f"Attempted to process: {stats['processed']}")
        print(f"Failed to process: {stats['failed']}")
        print(f"New price history entries added: {stats['new_price_history']}")
        print(f"New stats entries added: {stats['new_stats']}")
        print(f"New features entries added: {stats['new_features']}")
        print(f"New terms entries added: {stats['new_terms']}")
        print(f"New apartment details added: {stats['new_apartment_details']}")
        print(f"New building details added: {stats['new_building_details']}")
        print(f"New estimation entries added: {stats['new_estimation']}")  # New
        # Count fully processed IDs now
        now_fully_processed = set.intersection(
            price_history_ids,
            stats_ids,
            features_ids,
            terms_ids,
            apartment_details_ids,
            building_details_ids,
        )
        print(f"Total unique offer IDs now fully processed: {len(now_fully_processed)}")
        print("=" * 50)

        # Final verification of files
        # Final verification of files
        for file_path, label in [
            (price_history_file, "Price history"),
            (stats_file, "Stats"),
            (features_file, "Features"),
            (terms_file, "Rental terms"),
            (apartment_details_file, "Apartment details"),
            (building_details_file, "Building details"),
            (estimation_file, "Estimation"),  # New
        ]:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    row_count = sum(1 for row in reader) - 1  # Subtract header
                print(f"Final verification: {label} file has {row_count} data rows")
            else:
                print(f"Warning: {label} file not found at end of script!")

        print("\nResults saved to:")
        print(f"- Price history: {price_history_file}")
        print(f"- Stats: {stats_file}")
        print(f"- Features: {features_file}")
        print(f"- Rental terms: {terms_file}")
        print(f"- Apartment details: {apartment_details_file}")
        print(f"- Building details: {building_details_file}")
        print(f"- Estimation: {estimation_file}")  # New
    except Exception as e:
        print(f"Error processing apartments: {e}")

    finally:
        print("\nScript completed. The browser session was not closed.")


if __name__ == "__main__":
    main()
