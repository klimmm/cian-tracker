# utils.py
import pandas as pd
import re
import json
from datetime import datetime, timedelta
from config import CONFIG, MOSCOW_TZ


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


'''def format_price_changes(value):
    """Format price changes with HTML styling with improved error handling"""
    if value is None or pd.isna(value):
        return "<div style='text-align:center;'><span></span></div>"

    if isinstance(value, str) and value.lower() == "new":
        return "<div style='text-align:center;'><span></span></div>"

    try:
        value = float(value)
    except (ValueError, TypeError):
        value = pd.to_numeric(value, errors="coerce")
        if pd.isna(value):
            return "<div style='text-align:center;'><span>—</span></div>"
        return "<div style='text-align:center;'><span>—</span></div>"

    if abs(value) < 1:
        return "<div style='text-align:center;'><span>—</span></div>"

    color = "green" if value < 0 else "red"
    arrow = "↓" if value < 0 else "↑"
    display = (
        f"{abs(int(value))//1000}K" if abs(value) >= 1000 else str(abs(int(value)))
    )

    return f"<div style='text-align:center;'><span style='color:{color};'>{arrow}{display}</span></div>"'''


def format_price_changes(value):
    """Format price changes with HTML styling but without div wrapper"""
    if value is None or pd.isna(value):
        return '<span style="color:blue;">new</span>'  # Blue color for "new"
    if isinstance(value, str) and value.lower() == "new":
        return '<span style="color:blue;">new</span>'
    try:
        value = float(value)
    except (ValueError, TypeError):
        value = pd.to_numeric(value, errors="coerce")
        if pd.isna(value):
            return '<span style="color:blue;">new</span>'
        return '<span style="color:blue;">new</span>'
    if abs(value) < 1:
        return '<span style="color:blue;">new</span>'
    color = "green" if value < 0 else "red"
    arrow = "↓" if value < 0 else "↑"
    display = (
        f"{abs(int(value))//1000}K" if abs(value) >= 1000 else str(abs(int(value)))
    )
    return f'<span style="color:{color};">{arrow}{display}</span>'


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
    return f"{'{:,}'.format(int(value)).replace(',', ' ')} ₽/мес."


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


def format_update_title(row):
    """Format the update_title field based on status"""
    if row["status"] == "active":
        # For active status
        time_str = row["updated_time"]
        price_str = row["price_change_formatted"]
    else:
        # For non-active status
        # Use unpublished_date if available, otherwise fallback to updated_time
        time_str = (
            row["unpublished_date"]
            if row["unpublished_date"] and row["unpublished_date"] != "--"
            else row["updated_time"]
        )
        price_str = '<span style="color:gray;">cнято</span>'

    return f'<div style="text-align:center;"><strong>{time_str}</strong>&nbsp;&nbsp;{price_str}</div>'


# Then in your data processing code:


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
            lambda x: format_text(x, format_price, "--")
        )
        df["price_difference_formatted"] = df["price_difference_value"].apply(
            lambda x: format_text(x, format_price, "")
        )

        df["price_change_formatted"] = df["price_change_value"].apply(
            format_price_changes
        )
        # Process date-time fields
        # df["updated_time_sort"] = pd.to_datetime(df["updated_time"], errors="coerce")
        # df["updated_time"] = df["updated_time_sort"].apply(
        #    lambda x: format_text(x, format_date, "")
        # )

        """df["update_title"] = df.apply(
            lambda r: f'<strong>{r["updated_time"]}</strong>&nbsp;{r["price_change_formatted"]}', 
            axis=1
        )
        """
        # Then use this modified function in your data processing
        # df["price_change_formatted"] = df["price_change_value"].apply(format_price_changes)
        # df["update_title"] = df.apply(format_update_title, axis=1)

        """# And create the combined column
        df["update_title"] = df.apply(
            lambda r: f'<div style="text-align:center;"><strong>{r["updated_time"]}</strong>&nbsp;&nbsp;{r["price_change_formatted"]}</div>', 
            axis=1
        )"""

        """df["unpublished_date_sort"] = pd.to_datetime(
            df["unpublished_date"], errors="coerce"
        )
        df["unpublished_date"] = df["unpublished_date_sort"].apply(
            lambda x: format_text(x, format_date, "--")
        )"""

        # Process date-time fields
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

        # Create the conditional update_title column
        def format_update_title(row):
            """Format the update_title field based on status"""
            if row["status"] == "active":
                # For active status
                time_str = row["updated_time"]  # Already formatted by previous steps
                price_str = row["price_change_formatted"]
            else:
                # For non-active status
                # Use unpublished_date if available, otherwise fallback to updated_time
                # Both are already formatted by previous steps
                time_str = (
                    row["unpublished_date"]
                    if row["unpublished_date"] and row["unpublished_date"] != "--"
                    else row["updated_time"]
                )
                price_str = '<span style="color:gray;">cнято</span>'

            return f'<div style="text-align:center;"><strong>{time_str}</strong>&nbsp;&nbsp;{price_str}</div>'

        # Apply the formatting function
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
        df["price_text"] = df.apply(
            lambda r: f'<strong>{r["price_value_formatted"]}</strong>', axis=1
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
            columns=["price_text", "cian_text", "commission_text", "deposit_text"]
        )

        df["date_sort_combined"] = df.apply(
            lambda r: (
                r["updated_time_sort"]
                if r["status"] == "active"
                else r["unpublished_date_sort"]
            ),
            axis=1,
        )

        # Default sorting
        # df["sort_key"] = df["status"].apply(lambda x: 1 if x == "active" else 2)
        df["sort_key"] = df["status"].apply(lambda x: 1)

        df = df.sort_values(
            ["sort_key", "date_sort_combined"], ascending=[True, False]
        ).drop(columns="sort_key")

        return df, update_time
    except Exception as e:
        import traceback

        print(f"Error in load_and_process_data: {e}")
        print(traceback.format_exc())
        return pd.DataFrame(), f"Error: {e}"


def filter_and_sort_data(df, filters=None, sort_by=None):
    """Filter and sort data in a single function"""
    if df.empty:
        return df

    # Apply price and distance thresholds from filters
    if filters:
        price_value = filters.get("price_value")
        distance_value = filters.get("distance_value")

        if price_value and price_value != float("inf"):
            df = df[df["price_value"] <= price_value]

        if distance_value and distance_value != float("inf"):
            df = df[df["distance_sort"] <= distance_value]

    # Apply button filters
    if filters and any(
        v
        for k, v in filters.items()
        if k in ["nearest", "below_estimate", "inactive", "updated_today"]
    ):
        mask = pd.Series(False, index=df.index)

        if filters.get("nearest"):
            mask |= df["distance_sort"] < 1.5
        if filters.get("below_estimate"):
            mask |= df["price_difference_value"] < -5000
        if filters.get("inactive"):
            mask |= df["status"] == "non active"
        if filters.get("updated_today"):
            mask |= df["updated_time_sort"] > (
                pd.Timestamp.now() - pd.Timedelta(hours=24)
            )

        if any(mask):
            df = df[mask]

    # Apply sorting
    if sort_by:
        for item in sort_by:
            col = CONFIG["columns"]["sort_map"].get(
                item["column_id"], item["column_id"]
            )
            df = df.sort_values(col, ascending=item["direction"] == "asc")

    #df = df[df["distance_sort"] <= 6]
    return df