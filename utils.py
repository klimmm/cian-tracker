# utils.py
import pandas as pd
import re
import json
from datetime import datetime, timedelta
from config import CONFIG, MOSCOW_TZ

# Add to utils.py

import os
import pandas as pd

def load_csv_safely(file_path):
    """Load a CSV file with robust error handling for malformed files"""
    import pandas as pd
    import os
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return pd.DataFrame()
    
    try:
        # First try using Python's built-in CSV module which is more forgiving
        import csv
        
        # Read raw data while auto-detecting dialect
        with open(file_path, 'r', encoding='utf-8') as f:
            # Sample first 1000 chars to detect format
            sample = f.read(1000)
            f.seek(0)
            
            # Try to detect the dialect
            try:
                dialect = csv.Sniffer().sniff(sample)
                reader = csv.reader(f, dialect)
            except:
                # If detection fails, use most permissive settings
                reader = csv.reader(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
            rows = list(reader)
        
        if not rows:
            return pd.DataFrame()
            
        # Find maximum field count
        max_fields = max(len(row) for row in rows)
        
        # Use header as column names, padded if needed
        header = rows[0]
        
        # Pad header if it has fewer columns than data rows
        if len(header) < max_fields:
            header = header + [f'unnamed_{i}' for i in range(len(header), max_fields)]
        
        # Fix possible duplicate column names
        unique_header = []
        seen = set()
        
        for col in header:
            if col in seen or not col:  # Also handle empty column names
                # Add suffix to make the column name unique
                count = 1
                new_col = f"column_{count}" if not col else f"{col}_{count}"
                while new_col in seen:
                    count += 1
                    new_col = f"column_{count}" if not col else f"{col}_{count}"
                unique_header.append(new_col)
            else:
                unique_header.append(col)
            seen.add(unique_header[-1])
        
        # Create DataFrame, padding rows that have fewer fields
        data = []
        for row in rows[1:]:  # Skip header
            # Pad row if needed
            if len(row) < max_fields:
                row = row + [''] * (max_fields - len(row))
            # Truncate if longer (shouldn't happen with max_fields)
            data.append(row[:max_fields])
        
        df = pd.DataFrame(data, columns=unique_header)
        return df
        
    except Exception as e:
        print(f"Error in CSV module parsing for {file_path}: {str(e)}")
        
        # Fallback to pandas with error handling options
        try:
            # Try with some common settings that might help with malformed files
            return pd.read_csv(
                file_path,
                encoding='utf-8',
                on_bad_lines='skip',     # For newer pandas versions
                escapechar='\\',
                quotechar='"',
                low_memory=False
            )
        except Exception as e2:
            try:
                # For older pandas versions
                return pd.read_csv(
                    file_path,
                    encoding='utf-8',
                    error_bad_lines=False,  # Deprecated but works in older pandas
                    warn_bad_lines=True,
                    low_memory=False
                )
            except Exception as e3:
                print(f"All loading methods failed for {file_path}: {str(e3)}")
                return pd.DataFrame()  # Return empty DataFrame

def load_apartment_details(offer_id):
    """
    Load all details for a specific apartment by offer_id, 
    combining data from multiple CSV files with robust error handling.
    """
    # Get the data directory path
    data_dir = "cian_data"
    
    # Initialize the result dictionary
    apartment_data = {"offer_id": offer_id}
    
    # List of files to check and their corresponding field groups
    files_to_check = [
        ("price_history.csv", "price_history"),
        ("stats.csv", "stats"),
        ("features.csv", "features"),
        ("rental_terms.csv", "terms"),
        ("apartment_details.csv", "apartment"),
        ("building_details.csv", "building")
    ]
    
    for filename, group_name in files_to_check:
        filepath = os.path.join(data_dir, filename)
        
        if not os.path.exists(filepath):
            continue
            
        try:
            # Use the safer CSV loading approach
            df = load_csv_safely(filepath)
            
            if df.empty:
                continue
                
            if 'offer_id' not in df.columns:
                print(f"Warning: 'offer_id' column missing in {filepath}")
                continue
                
            # Convert offer_id to string for safer comparison
            df['offer_id'] = df['offer_id'].astype(str)
            offer_id_str = str(offer_id)
            
            # Filter for the specific offer_id
            filtered_df = df[df['offer_id'] == offer_id_str]
            
            if not filtered_df.empty:
                if group_name == "price_history":
                    # For price history, we may have multiple rows
                    apartment_data[group_name] = filtered_df.to_dict('records')
                else:
                    # For other files, we expect just one row per offer_id
                    apartment_data[group_name] = filtered_df.iloc[0].to_dict()
                    
                print(f"Successfully loaded {group_name} data for offer_id {offer_id}")
            else:
                print(f"No data found for offer_id {offer_id} in {filepath}")
        except Exception as e:
            print(f"Error processing data from {filepath}: {e}")
    
    return apartment_data
    
def pluralize_ru_accusative(number, forms, word):
    """Подбирает правильную форму слова в винительном падеже"""
    n = abs(number) % 100
    if 11 <= n <= 19:
        return forms[2]
    n = n % 10
    if n == 1:
        if word == "минута":
            return "минуту"
        return forms[0]  # 'час'
    elif 2 <= n <= 4:
        return forms[1]
    else:
        return forms[2]


def format_date(dt):
    """Format date with relative time for recent dates"""
    now = datetime.now(MOSCOW_TZ)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MOSCOW_TZ)
    delta = now - dt
    today = now.date()
    yesterday = today - timedelta(days=1)

    if delta < timedelta(minutes=1):
        return "только что"
    elif delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() // 60)
        minutes_text = pluralize_ru_accusative(
            minutes, ["минута", "минуты", "минут"], "минута"
        )
        return f"{minutes} {minutes_text} назад"
        #return f"{minutes} мин. назад"
    elif delta < timedelta(hours=6):
        hours = int(delta.total_seconds() // 3600)
        hours_text = pluralize_ru_accusative(hours, ["час", "часа", "часов"], "час")
        return f"{hours} {hours_text} назад"
    elif dt.date() == today:
        return f"сегодня, {dt.hour:02}:{dt.minute:02}"
    elif dt.date() == yesterday:
        return f"вчера, {dt.hour:02}:{dt.minute:02}"
    else:
        month_name = CONFIG["months"][dt.month]
        return f"{dt.day} {month_name}, {dt.hour:02}:{dt.minute:02}"


def format_text(value, formatter, default=""):
    """Generic formatter with default handling"""
    if value is None or pd.isna(value):
        return default
    return formatter(value)

def format_price_changes(value):
    if value is None or pd.isna(value):
        return ''
    if isinstance(value, str) and value.lower() == "new":
        return ''
    try:
        value = float(value)
    except (ValueError, TypeError):
        return ''
    if abs(value) < 1:
        return ''
    
    # 🎨 Новые цвета
    color = "#2a9d8f" if value < 0 else "#d62828"
    arrow = "↓" if value < 0 else "↑"
    display = f"{abs(int(value))//1000}K" if abs(value) >= 1000 else str(abs(int(value)))

    return (
        f'<span style="color:{color}; font-weight:bold;">'
        f'<span style="font-size:11px;">{arrow}</span>{display}</span>'
    )


def format_update_title(row):
    tag_style = "display:inline-block; padding:1px 4px; border-radius:8px; margin:0 1px; font-size:7px; white-space:nowrap;"
    tag_flags = generate_tags_for_row(row)

    # Показываем дату
    if row["status"] == "active":
        time_str = row["updated_time"]
    else:
        time_str = row["unpublished_date"] or row["updated_time"]

    html = f'<span style="display:inline-block; text-align:center;">'
    html += f'<strong>{time_str}</strong>'

    # ⬇️ Показываем изменение цены только если статус активный
    if row["status"] == "active" and row.get("price_change_formatted"):
        html += f'<br>{row["price_change_formatted"]}'

    # Теги
    tags = []
    if row["status"] != "active":
        tags.append(f'<span style="{tag_style} background-color:#f5f5f5; color:#666;">📦 архив</span>')

    if tags:
        html += "<br>" + "".join(tags)

    html += "</span>"
    return html


def generate_tags_for_row(row):
    """Generate tag flags for various row conditions"""
    # Initialize tag dictionary
    tags = {
        "below_estimate": False,
        "nearby": False,
        "updated_today": False,
        "neighborhood": None,  # Store the neighborhood name
        "is_hamovniki": False, # Special flag for Хамовники
        "is_arbat": False      # Special flag for Арбат
    }
    
    # Check for "below estimate" condition
    if row.get("price_difference_value", 0) > 0 and row.get("status") != "non active":
        tags["below_estimate"] = True
    
    # Check for "nearby" condition (within 1.5km)
    if row.get("distance_sort", 999) < 1.5 and row.get("status") != "non active":
        tags["nearby"] = True
    
    # Check for "updated today" condition
    import pandas as pd
    try:
        # Get the timestamp from 24 hours ago
        recent_time = pd.Timestamp.now() - pd.Timedelta(hours=24)
        
        # Get the row's timestamp (or a default far past date if not available)
        row_time = row.get("updated_time_sort")
        if row_time and not pd.isna(row_time):
            row_dt = pd.to_datetime(row_time)
            if row_dt.date() == pd.Timestamp.now().date():
                tags["updated_today"] = True
    except Exception as e:
        # Add error handling to prevent crashes
        print(f"Error processing timestamp: {e}")
    
    # Extract neighborhood if available
    neighborhood = str(row.get("neighborhood", ""))
    if neighborhood and neighborhood != "nan" and neighborhood != "None":
        # Extract just the neighborhood name if it follows a pattern like "р-н Хамовники"
        if "р-н " in neighborhood:
            neighborhood_name = neighborhood.split("р-н ")[1].strip()
        else:
            neighborhood_name = neighborhood.strip()
        
        tags["neighborhood"] = neighborhood_name
        
        # Check if this is Хамовники
        if "Хамовники" in neighborhood:
            tags["is_hamovniki"] = True
        
        # Check if this is Арбат
        if "Арбат" in neighborhood:
            tags["is_arbat"] = True
    
    return tags

def format_property_tags(row):
    """Format property tags in a flex container, including walking time"""
    tag_style = "display:inline-block; padding:1px 4px; border-radius:8px; margin-right:2px; font-size:8px; white-space:nowrap;"
    tags = []
    tag_flags = generate_tags_for_row(row)
    distance_value = row.get("distance_sort")
    
    if distance_value is not None and not pd.isna(distance_value):
        # Calculate walking time in minutes
        walking_minutes = (distance_value / 5) * 60
        
        # Format time display
        if walking_minutes < 60:
            time_text = f"{int(walking_minutes)}мин"
        else:
            hours = int(walking_minutes // 60)
            minutes = int(walking_minutes % 60)
            if minutes == 0:
                time_text = f"{hours}ч"
            else:
                time_text = f"{hours}ч{minutes}м"
        
        # Different background colors based on time
        if walking_minutes < 12:  # Less than 12 minutes (1km)
            bg_color = "#4285f4"  # Bright blue for very close
            text_color = "#ffffff"  # White text for contrast
        elif walking_minutes < 20:  # Less than 20 minutes (1.67km)
            bg_color = "#aecbfa"  # Medium blue for nearby
            text_color = "#174ea6"  # White text
        elif walking_minutes < 30:  # Less than 40 minutes (3.33km)
            bg_color = "#aecbfa"  # Light blue for moderate distance
            text_color = "#174ea6"  # Dark blue text
        else:
            bg_color = "#dadce0"  # Gray for farther distances
            text_color = "#3c4043"  # Dark gray text
            
        tags.append(f'<span style="{tag_style} background-color:{bg_color}; color:{text_color};">{time_text}</span>')
    
    # Add neighborhood tag if available
    if tag_flags.get("neighborhood"):
        neighborhood = tag_flags["neighborhood"]
        
        # Special style for Хамовники
        if tag_flags["is_hamovniki"]:
            bg_color = "#e0f7f7"  # Teal
            text_color = "#0c5460"  # Dark teal
        # Special style for Арбат - purple-ish to distinguish from walking minutes blues
        elif tag_flags["is_arbat"]:
            bg_color = "#d0d1ff"  # Light indigo/purple
            text_color = "#3f3fa3"  # Dark indigo/purple
        else:
            # Default style for all other neighborhoods
            bg_color = "#dadce0"  # Gray
            text_color = "#3c4043"  # Dark gray
            
        tags.append(f'<span style="{tag_style} background-color:{bg_color}; color:{text_color};">{neighborhood}</span>')
    
    return f'<div style="display:flex; flex-wrap:wrap; gap:2px; justify-content:flex-start;">{"".join(tags)}</div>' if tags else ""
    
def extract_deposit_value(deposit_info):
    """Extract numeric deposit value from deposit_info string"""
    if deposit_info is None or pd.isna(deposit_info) or deposit_info == "--":
        return None

    if "без залога" in deposit_info:
        return 0

    if "залог" in deposit_info:
        match = re.search(r"залог\s+([\d\s\xa0]+)\s*₽", deposit_info)

        if not match:
            return None

        amount_str = match.group(1)
        clean_amount = re.sub(r"\s", "", amount_str)

        try:
            return int(clean_amount)
        except ValueError:
            return None

    return None


def extract_commission_value(value):
    """Format commission info with compact abbreviation and return as float"""
    if "без комиссии" in value:
        return 0.0  # Return as float, not string
    elif "комиссия" in value:
        match = re.search(r"(\d+)%", value)
        if match:
            # Convert the matched number to float
            return float(match.group(1))
    return None  # Return None instead of "--" for non-commission values


def format_price(value):
    """Format price value with K notation for thousands"""
    if value is None or pd.isna(value) or value == 0:
        return "--"

    amount_num = int(value)
    if amount_num >= 1000000:
        return f"{amount_num//1000000}M"
    elif amount_num >= 1000:
        return f"{amount_num//1000}K"
    else:
        return f"{amount_num} ₽"


def format_rental_period(value):
    """Format rental period with more intuitive abbreviation"""
    if value == "От года":
        return "год+"
    elif value == "На несколько месяцев":
        return "мес+"
    return "--"


def format_price_r(value):
    """Format price value"""
    if value == 0:
        return "--"
    return f"{'{:,}'.format(int(value)).replace(',', ' ')} ₽" #₽/мес."


def format_utilities(value):
    """Format utilities info with clearer abbreviation"""
    if "без счётчиков" in value:
        return "+счет"
    elif "счётчики включены" in value:
        return "-"
    return "--"


def format_commission(value):
    """Format commission value as percentage or '--' if unknown"""
    if value == 0:
        return "0%"
    elif isinstance(value, (int, float)):
        return f"{int(value)}%" if value.is_integer() else f"{value}%"
    else:
        return "--"


def format_deposit(value):
    """Robust deposit formatter that handles all cases"""
    if value is None or pd.isna(value) or value == "--":
        return "--"
    if value == 0:
        return "0₽"
    elif isinstance(value, (int, float)):
        # Direct numeric formatting instead of regex
        amount_num = int(value)  # Ensure it's an integer
        if amount_num >= 1000000:
            return f"{amount_num//1000000}M"
        elif amount_num >= 1000:
            return f"{amount_num//1000}K"
        return f"{amount_num}₽"
    return "--"


def calculate_monthly_burden(row):
    """Calculate average monthly financial burden over 12 months"""
    try:
        price = pd.to_numeric(row["price_value"], errors="coerce")
        comm = pd.to_numeric(row["commission_value"], errors="coerce")
        dep = pd.to_numeric(row["deposit_value"], errors="coerce")

        if pd.isna(price) or price <= 0:
            return None

        comm = 0 if pd.isna(comm) else comm
        dep = 0 if pd.isna(dep) else dep

        annual_rent = price * 12
        commission_fee = price * (comm / 100)
        deposit_value = dep

        total_burden = (annual_rent + commission_fee + deposit_value) / 12

        return total_burden
    except Exception as e:
        print(f"Error calculating burden: {e}")
        return None


def format_burden(row):
    try:
        if (
            pd.isna(row["monthly_burden"])
            or pd.isna(row["price_value"])
            or row["price_value"] <= 0
        ):
            return "--"

        burden = float(row["monthly_burden"])
        price = float(row["price_value"])

        burden_formatted = f"{'{:,}'.format(int(burden)).replace(',', ' ')} ₽"

        diff_percent = int(((burden / price) - 1) * 100)

        if diff_percent > 2:
            return f"{burden_formatted}/мес."
        else:
            return burden_formatted
    except Exception as e:
        print(f"Error formatting burden: {e}")
        return "--"



def load_and_process_data():
    """Load and process data with improved price change handling and new columns"""
    try:
        path = "cian_apartments.csv"
        df = pd.read_csv(path, encoding="utf-8", comment="#")

        # Extract update time from metadata file
        try:
            with open("cian_apartments.meta.json", "r", encoding="utf-8") as f:
                metadata = json.load(f)
                update_time_str = metadata.get("last_updated", "Unknown")

                try:
                    dt = pd.to_datetime(update_time_str)
                    update_time = dt.strftime("%d.%m.%Y %H:%M:%S")
                except:
                    update_time = update_time_str
        except Exception as e:
            print(f"Error reading metadata file: {e}")
            with open(path, encoding="utf-8") as f:
                first_line = f.readline()
                update_time = (
                    first_line.split("")[1].split(",")[0].strip()
                    if "last_updated=" in first_line
                    else "Unknown"
                )

        # Process core columns
        df["offer_id"] = df["offer_id"].astype(str)
        df["address"] = df.apply(
            lambda r: f"[{r['address']}]({CONFIG['base_url']}{r['offer_id']}/)", axis=1
        )
        df["offer_link"] = df["offer_id"].apply(
            lambda x: f"[View]({CONFIG['base_url']}{x}/)"
        )

        # Process distance and prices
        df["distance_sort"] = pd.to_numeric(df["distance"], errors="coerce")
        df["distance"] = df["distance_sort"].apply(
            lambda x: f"{x:.2f} km" if pd.notnull(x) else ""
        )
        # Create combined address_title column
        df["address_title"] = df.apply(
            lambda r: f"[{r['address']}]({CONFIG['base_url']}{r['offer_id']}/)<br>{r['title']}",
            axis=1,
        )

        df["price_value_formatted"] = df["price_value"].apply(
            lambda x: format_text(x, format_price_r, "--")
        )
        df["cian_estimation_formatted"] = df["cian_estimation_value"].apply(
            lambda x: format_text(x, format_price_r, "--")
        )
        df["price_difference_formatted"] = df["price_difference_value"].apply(
            lambda x: format_text(x, format_price, "")
        )

        df["price_change_formatted"] = df["price_change_value"].apply(
            format_price_changes
        )

        df["updated_time_sort"] = pd.to_datetime(df["updated_time"], errors="coerce")
        df["updated_time"] = df["updated_time_sort"].apply(
            lambda x: format_text(x, format_date, "")
        )

        # Process unpublished_date fields with explicit format
        df["unpublished_date_sort"] = pd.to_datetime(
            df["unpublished_date"],
            format="%Y-%m-%d %H:%M:%S",  # Format matching "2025-04-10 00:04:00"
            errors="coerce",
        )
        df["unpublished_date"] = df["unpublished_date_sort"].apply(
            lambda x: format_text(x, format_date, "--")
        )

        # Format price changes
        df["price_change_formatted"] = df["price_change_value"].apply(
            format_price_changes
        )

        df["update_title"] = df.apply(format_update_title, axis=1)

        # Process new columns with improved abbreviations
        df["rental_period_abbr"] = df["rental_period"].apply(
            lambda x: format_rental_period(x)
        )
        df["utilities_type_abbr"] = df["utilities_type"].apply(
            lambda x: format_utilities(x)
        )
        df["commission_value"] = df["commission_info"].apply(extract_commission_value)
        df["commission_info_abbr"] = df["commission_value"].apply(format_commission)

        # Extract deposit values
        df["deposit_value"] = df["deposit_info"].apply(extract_deposit_value)
        df["deposit_info_abbr"] = df["deposit_value"].apply(format_deposit)

        df["monthly_burden"] = df.apply(calculate_monthly_burden, axis=1)
        df["monthly_burden_formatted"] = df.apply(format_burden, axis=1)

        # Create temporary variables with the formatted strings
                        
        # Update the price_text calculation to remove price change information
        # Update the price_text calculation to correctly check for below_estimate condition
        df["price_text"] = df.apply(
            lambda r: (
                f'<div style="display:block; text-align:center; margin:0; padding:0;">'
                f'<strong style="margin:0; padding:0;">{r["price_value_formatted"]}</strong>'
                + (
                    # Check the actual condition used in generate_tags_for_row instead of using the tags column
                    f'<br><span style="display:inline-block; padding:1px 4px; border-radius:8px; margin-top:2px; font-size:8px; background-color:#fcf3cd; color:#856404;">хорошая цена</span>'
                    if r.get("price_difference_value", 0) > 0 and r.get("status") != "non active" else ""
                )
                + '</div>'
            ),
            axis=1
        )        
                        



        df["cian_text"] = df.apply(
            lambda r: f'оценка циан: {r["cian_estimation_formatted"]}', axis=1
        )
        df["commission_text"] = df.apply(
            lambda r: f'комиссия {r["commission_info_abbr"]}', axis=1
        )
        df["deposit_text"] = df.apply(
            lambda r: f'залог {r["deposit_info_abbr"]}', axis=1
        )

        # Combine all variables into a single column with <br> separators
        df["price_info"] = df.apply(
            lambda r: f"{r['price_text']}<br>{r['commission_text']}<br> {r['deposit_text']}",
            axis=1,
        )

        # Optionally remove the temporary variables
        df = df.drop(
            columns=["cian_text", "commission_text", "deposit_text"]
        )

        df["date_sort_combined"] = df.apply(
            lambda r: (
                r["updated_time_sort"]
                if r["status"] == "active"
                else r["unpublished_date_sort"]
            ),
            axis=1,
        )

        df["update_time"] = df.apply(
            lambda r: f'<strong>{r["updated_time" if r["status"] == "active" else "unpublished_date"]}</strong>', 
            axis=1
        )
        
        df["price_change"] = df["price_change_formatted"]  # Keep as is
        
        # Create a dedicated tags column with flex layout
        df["property_tags"] = df.apply(format_property_tags, axis=1)
        
        # Create a dedicated walking time column with consistent styling
        #df["walking_time"] = df.apply(format_walking_time, axis=1)

        #df["sort_key"] = df["status"].apply(lambda x: 1 if x == "active" else 2)
        df["sort_key"] = df["status"].apply(lambda x: 1)
        
        df = df.sort_values(
            ["sort_key", "distance_sort"], ascending=[True, True]
        ).drop(columns="sort_key")

        
        '''df = df.sort_values(
            ["sort_key", "date_sort_combined"], ascending=[True, False]
        ).drop(columns="sort_key")'''
        df["tags"] = df.apply(generate_tags_for_row, axis=1)

        return df, update_time
    except Exception as e:
        import traceback

        print(f"Error in load_and_process_data: {e}")
        print(traceback.format_exc())
        return pd.DataFrame(), f"Error: {e}"

# In cian_dashboard.py, find the filter_and_sort_data function in utils.py 
# and modify it to change the "inactive" filter to "active":

def filter_and_sort_data(df, filters=None, sort_by=None):
    """Filter and sort data in a single function"""
    if df.empty:
        return df

    # Apply price and distance thresholds from filters
    if filters:
        price_value = filters.get("price_value")
        distance_value = filters.get("distance_value")

        if price_value and price_value != float("inf"):
            if "price_value" in df.columns:
                df = df[df["price_value"] <= price_value]

        if distance_value and distance_value != float("inf"):
            if "distance_sort" in df.columns:
                df = df[df["distance_sort"] <= distance_value]

    # Apply button filters
    if filters and any(
        v
        for k, v in filters.items()
        if k in ["nearest", "below_estimate", "inactive", "updated_today"]
    ):
        mask = pd.Series(False, index=df.index)

        if filters.get("nearest") and "distance_sort" in df.columns:
            mask |= df["distance_sort"] < 1.5
        if filters.get("below_estimate") and "price_difference_value" in df.columns:
            mask |= df["price_difference_value"] >= 5000
        if filters.get("inactive") and "status" in df.columns:
            mask |= df["status"] == "active"
        
        if filters.get("updated_today") and "updated_time_sort" in df.columns:
            df["updated_time_sort"] = pd.to_datetime(df["updated_time_sort"], errors='coerce')
            mask |= df["updated_time_sort"] > (
                pd.Timestamp.now() - pd.Timedelta(hours=24)
            )

        if any(mask):
            df = df[mask]

    # Apply sorting from filter store
    if filters and "sort_column" in filters and "sort_direction" in filters:
        sort_column = filters["sort_column"]
        
        # Make sure the sort column exists in the DataFrame
        if sort_column in df.columns:
            sort_ascending = filters["sort_direction"] == "asc"
            df = df.sort_values(sort_column, ascending=sort_ascending)
        else:
            print(f"Warning: Sort column '{sort_column}' not found in DataFrame")
            # Fallback to default sort if column doesn't exist
            if "price_value" in df.columns:
                df = df.sort_values("price_value", ascending=True)
    
    # Backward compatibility for table sort_by parameter
    elif sort_by:
        for item in sort_by:
            col = CONFIG["columns"]["sort_map"].get(
                item["column_id"], item["column_id"]
            )
            if col in df.columns:
                df = df.sort_values(col, ascending=item["direction"] == "asc")

    return df