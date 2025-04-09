import os
import dash
from dash import dash_table, callback
from dash.dependencies import Input, Output
# config.py
from zoneinfo import ZoneInfo
import pandas as pd

# app.py
import os
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State

import pandas as pd
import re
import json
from datetime import datetime, timedelta

# callbacks.py
import dash
from dash.dependencies import Input, Output, State
from dash import callback

# Style definitions
FONT = "Arial,sans-serif"
STYLE = {
    "container": {"fontFamily": FONT, "padding": "5px", "maxWidth": "100%"},
    "header": {
        "fontFamily": FONT,
        "textAlign": "center",
        "fontSize": "10px",
        "borderBottom": "1px solid #ddd",
    },
    "update_time": {"fontFamily": FONT, "fontStyle": "bold", "fontSize": "12px"},
    "table": {"overflowX": "auto", "width": "100%"},
    "cell": {
        "fontFamily": FONT,
        "textAlign": "center",
        "padding": "3px",
        "fontSize": "9px",
        "whiteSpace": "nowrap",
    },
    "header_cell": {
        "fontFamily": FONT,
        "backgroundColor": "#4682B4",
        "color": "white",
        "fontSize": "9px",
    },



    
    "filter": {"display": "none"},
    "data": {"lineHeight": "14px"},
    "input": {"marginRight": "5px", "width": "110px", "height": "15px"},
    "input_number": {"width": "110px", "height": "15px"},
    "label": {"fontSize": "11px", "marginRight": "3px", "display": "block"},
    "button_base": {
        "display": "inline-block",
        "padding": "3px 8px",
        "fontSize": "10px",
        "border": "1px solid #ccc",
        "margin": "0 5px 5px 0",
        "cursor": "pointer",
    },
    "cell_conditional": [
        {"if": {"column_id": "address_title"}, 
         "whiteSpace": "normal", 
         "height": "auto",
         "width": "auto",
         "overflow": "hidden",
         "textOverflow": "ellipsis"}
    ]
}

# Button styles
BUTTON_STYLES = {
    "nearest": {"backgroundColor": "#d9edf7", **STYLE["button_base"]},
    "below_estimate": {"backgroundColor": "#fef3d5", **STYLE["button_base"]},
    "updated_today": {"backgroundColor": "#dff0d8", **STYLE["button_base"]},
    "inactive": {"backgroundColor": "#f4f4f4", **STYLE["button_base"]},
    "price": {"backgroundColor": "#e8e8e0", **STYLE["button_base"]},
    "distance": {"backgroundColor": "#e0e4e8", **STYLE["button_base"]},
}

# In config.py, update the COLUMN_STYLES list:

COLUMN_STYLES = [

    {
        "if": {"filter_query": '{distance_sort} < 1.5 && {status} ne "non active"'},
        "backgroundColor": "#d9edf7",
    },
    {
        "if": {
            "filter_query": '{price_difference_value} < -5000 && {status} ne "non active"'
        },
        "backgroundColor": "#fef3d5",
    },
    {
        "if": {
            "filter_query": '{updated_time_sort} > "'
            + (pd.Timestamp.now() - pd.Timedelta(hours=24)).isoformat()
            + '"'
        },
        "backgroundColor": "#e6f3e0",
        "fontWeight": "normal",
    },
    {"if": {"column_id": "price_change_formatted"}, "textAlign": "center"},
    {"if": {"column_id": "updated_time"}, "fontWeight": "bold", "textAlign": "center"},
    {
        "if": {"column_id": "price_value_formatted"},
        "fontWeight": "bold",
        "textAlign": "center",
    },
    {
        "if": {"column_id": "monthly_burden_formatted"},
        "fontWeight": "bold",
        "textAlign": "center",
    },
    {"if": {"column_id": "address"}, "textAlign": "left"},
    {"if": {"column_id": "metro_station"}, "textAlign": "left"},
    {"if": {"column_id": "title"}, "textAlign": "left"},
    # Add styling for the combined column
    {
        "if": {"column_id": "address_title"}, 
        "textAlign": "left",
        "whiteSpace": "normal", 
        "height": "auto"
    },
    {
        "if": {"filter_query": '{status} contains "non active"'},
        "backgroundColor": "#f4f4f4",
        "color": "#888",
    },

    
]



HEADER_STYLES = [
    {"if": {"column_id": col}, "textAlign": "center"}
    for col in [
        "distance",
        "updated_time",
        "unpublished_date",
        "price_value_formatted",
        "cian_estimation_formatted",
        "price_change_formatted",
        "status",
        "monthly_burden_formatted",
    ]
] + [{"if": {"column_id": col}, "textAlign": "left"} for col in ["address_title", "metro_station"]]



# First, define button configurations in config.py
PRICE_BUTTONS = [
    {"id": "btn-price-60k", "label": "65K", "value": 65000},
    {"id": "btn-price-70k", "label": "75K", "value": 75000},
    {"id": "btn-price-80k", "label": "85K", "value": 85000, "default": True},
    {"id": "btn-price-90k-plus", "label": "любая", "value": float('inf')}
]

DISTANCE_BUTTONS = [
    #{"id": "btn-dist-1km", "label": "1km", "value": 1.0},
    {"id": "btn-dist-2km", "label": "2", "value": 2.0},
    {"id": "btn-dist-3km", "label": "3", "value": 3.0, "default": True},
    #{"id": "btn-dist-4km", "label": "4km", "value": 4.0},
    {"id": "btn-dist-5km", "label": "5", "value": 5.0},
    {"id": "btn-dist-5km-plus", "label": "любое", "value": float('inf')}
]


# Default values
default_price = next(
    (btn["value"] for btn in PRICE_BUTTONS if btn.get("default", False)), 80000
)
default_price_btn = next(
    (btn["id"] for btn in PRICE_BUTTONS if btn.get("default", False)), "btn-price-80k"
)
default_distance = next(
    (btn["value"] for btn in DISTANCE_BUTTONS if btn.get("default", False)), 3.0
)
default_distance_btn = next(
    (btn["id"] for btn in DISTANCE_BUTTONS if btn.get("default", False)), "btn-dist-3km"
)


# Timezone configuration
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

# Column definitions and display settings
CONFIG = {
    "columns": {
        "display": [
            "offer_id",
            "title",
            "updated_time",
            "updated_time_sort",
            "price_value_formatted",
            "price_value",
            "cian_estimation_formatted",
            "price_difference_formatted",
            "address",
            "metro_station",
            "offer_link",
            "distance",
            "distance_sort",
            "price_change_formatted",
            "status",
            "unpublished_date",
            "unpublished_date_sort",
            "price_difference_value",
            "rental_period_abbr",
            "utilities_type_abbr",
            "commission_info_abbr",
            "deposit_info_abbr",
            "monthly_burden",
            "monthly_burden_formatted",
            "address_title",
            "price_info",
            "update_title"
        ],
        "visible": [
            #"address",
            #"updated_time",
            "update_title",
            "address_title",  # Add the combined column
            "distance",
            #"price_info",
            "price_value_formatted",
            "commission_info_abbr",
            "deposit_info_abbr",
            #"monthly_burden_formatted",
            "cian_estimation_formatted",
            #"price_change_formatted",
            #"title",
            # "rental_period_abbr", "utilities_type_abbr",
            "metro_station",
            #"unpublished_date",
        ],
        "headers": {
            "offer_id": "ID",
            "distance": "Расст.",
            "price_change_formatted": "Изм.",
            "title": "Описание",
            "updated_time": "Обновлено",
            "price_value_formatted": "Цена",
            "cian_estimation_formatted": "Оценка",
            "price_difference_formatted": "Разница",
            "address": "Адрес",
            "metro_station": "Метро",
            "offer_link": "Ссылка",
            "status": "Статус",
            "unpublished_date": "Снято",
            "rental_period_abbr": "Срок",
            "utilities_type_abbr": "ЖКХ",
            "commission_info_abbr": "Коммис",
            "deposit_info_abbr": "Залог",
            "monthly_burden_formatted": "Нагрузка/мес",
            "address_title": "Адрес / Описание",
            "price_info": "Цена",
            "update_title": "Посл. обновление"
        },
        "sort_map": {
            "updated_time": "date_sort_combined",
            "price_value_formatted": "price_value",
            "price_change_formatted": "price_change_value",
            "cian_estimation_formatted": "cian_estimation_value",
            "price_difference_formatted": "price_difference_value",
            "distance": "distance_sort",
            "monthly_burden_formatted": "monthly_burden",
        },
    },
    "months": {
        i: m
        for i, m in enumerate(
            [
                "янв",
                "фев",
                "мар",
                "апр",
                "май",
                "июн",
                "июл",
                "авг",
                "сен",
                "окт",
                "ноя",
                "дек",
            ],
            1,
        )
    },
    "base_url": "https://www.cian.ru/rent/flat/",
    "hidden_cols": [
        "price_value",
        "distance_sort",
        "updated_time_sort",
        "cian_estimation_value",
        "price_difference_value",
        "unpublished_date_sort",
        "monthly_burden",
    ],
}




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
            minutes, ['минута', 'минуты', 'минут'], 'минута'
        )
        return f"{minutes} {minutes_text} назад"
    elif delta < timedelta(hours=6):
        hours = int(delta.total_seconds() // 3600)
        hours_text = pluralize_ru_accusative(
            hours, ['час', 'часа', 'часов'], 'час'
        )
        return f"{hours} {hours_text} назад"
    elif dt.date() == today:
        return f"сегодня, {dt.hour:02}:{dt.minute:02}"
    elif dt.date() == yesterday:
        return f"вчера, {dt.hour:02}:{dt.minute:02}"
    else:
        month_name = CONFIG['months'][dt.month]
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
        time_str = row["unpublished_date"] if row["unpublished_date"] and row["unpublished_date"] != "--" else row["updated_time"]
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
            axis=1
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
        #df["updated_time_sort"] = pd.to_datetime(df["updated_time"], errors="coerce")
        #df["updated_time"] = df["updated_time_sort"].apply(
        #    lambda x: format_text(x, format_date, "")
        #)
        
        '''df["update_title"] = df.apply(
            lambda r: f'<strong>{r["updated_time"]}</strong>&nbsp;{r["price_change_formatted"]}', 
            axis=1
        )
        '''
        # Then use this modified function in your data processing
        #df["price_change_formatted"] = df["price_change_value"].apply(format_price_changes)
        #df["update_title"] = df.apply(format_update_title, axis=1)
        
        '''# And create the combined column
        df["update_title"] = df.apply(
            lambda r: f'<div style="text-align:center;"><strong>{r["updated_time"]}</strong>&nbsp;&nbsp;{r["price_change_formatted"]}</div>', 
            axis=1
        )'''
        
        
                

        '''df["unpublished_date_sort"] = pd.to_datetime(
            df["unpublished_date"], errors="coerce"
        )
        df["unpublished_date"] = df["unpublished_date_sort"].apply(
            lambda x: format_text(x, format_date, "--")
        )'''
        
        # Process date-time fields
        df["updated_time_sort"] = pd.to_datetime(df["updated_time"], errors="coerce")
        df["updated_time"] = df["updated_time_sort"].apply(
            lambda x: format_text(x, format_date, "")
        )
        
        # Process unpublished_date fields
        df["unpublished_date_sort"] = pd.to_datetime(df["unpublished_date"], errors="coerce")
        df["unpublished_date"] = df["unpublished_date_sort"].apply(
            lambda x: format_text(x, format_date, "--")
        )
        
        # Format price changes
        df["price_change_formatted"] = df["price_change_value"].apply(format_price_changes)
        
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
                time_str = row["unpublished_date"] if row["unpublished_date"] and row["unpublished_date"] != "--" else row["updated_time"]
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
        df["price_text"] = df.apply(lambda r: f'<strong>{r["price_value_formatted"]}</strong>', axis=1)
        df["cian_text"] = df.apply(lambda r: f'оценка циан: {r["cian_estimation_formatted"]}', axis=1)
        df["commission_text"] = df.apply(lambda r: f'комиссия {r["commission_info_abbr"]}', axis=1)
        df["deposit_text"] = df.apply(lambda r: f'залог {r["deposit_info_abbr"]}', axis=1)
        
        # Combine all variables into a single column with <br> separators
        df["price_info"] = df.apply(
            lambda r: f"{r['price_text']}<br>{r['commission_text']}<br> {r['deposit_text']}", 
            axis=1
        )
        
        # Optionally remove the temporary variables
        df = df.drop(columns=["price_text", "cian_text", "commission_text", "deposit_text"])
        
        df["date_sort_combined"] = df.apply(
            lambda r: r["updated_time_sort"] if r["status"] == "active" else r["unpublished_date_sort"],
            axis=1
        )

        
        # Default sorting
        #df["sort_key"] = df["status"].apply(lambda x: 1 if x == "active" else 2)
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

    df = df[df["distance_sort"] <= 6]
    return df


# Initialize the app
app = dash.Dash(
    __name__,
    title="",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
)
server = app.server
# Add custom CSS to remove paragraph margins
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .dash-cell-value p {
                margin: 0 !important;
                padding: 0 !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

def create_app_layout(app):
    # App layout
    app.layout = html.Div(
        [
            html.H2("", style=STYLE["header"]),
            html.Div(html.Span(id="last-update-time", style=STYLE["update_time"])),
            dcc.Interval(id="interval-component", interval=2 * 60 * 1000, n_intervals=0),
            # Filter store
            dcc.Store(
                id="filter-store",
                data={
                    "nearest": False,
                    "below_estimate": False,
                    "inactive": False,
                    "updated_today": False,
                    "price_value": default_price,
                    "distance_value": default_distance,
                    "active_price_btn": default_price_btn,
                    "active_dist_btn": default_distance_btn,
                },
            ),
            # Outer container for all button rows with fixed width of 375px
            html.Div(
                [
                    # Price buttons row - with label and buttons on the same row
                    html.Div(
                        [
                            # Label on the left
                            html.Label(
                                "Макс. цена (₽):",
                                className="dash-label",
                                style={
                                    "marginBottom": "2px", 
                                    "marginRight": "5px", 
                                    "minWidth": "110px",  # Fixed identical width using minWidth
                                    "width": "110px",     # Both width and minWidth for consistency
                                    "display": "inline-block",
                                    "whiteSpace": "nowrap"
                                },
                            ),
                            # Buttons on the right - completely joined
                            html.Div(
                                [
                                    html.Button(
                                        btn["label"],
                                        id=btn["id"],
                                        style={
                                            **BUTTON_STYLES["price"],
                                            "opacity": 1.0 if btn.get("default", False) else 0.6,
                                            "boxShadow": "0 0 5px #4682B4" if btn.get("default", False) else None,
                                            "flex": "1",  # Each button flex equally
                                            "margin": "0",  # Zero margin
                                            "padding": "2px 0",  # Reduced vertical padding for shorter height
                                            "fontSize": "10px",  # Smaller font size
                                            "lineHeight": "1",  # Tighter line height
                                            "borderRadius": "0",  # No rounded corners
                                            "borderLeft": "none" if i > 0 else "1px solid #ccc",  # Remove left border for all but first button
                                            "position": "relative",  # For z-index to work
                                            "zIndex": "1" if btn.get("default", False) else "0",  # Active button appears on top
                                        },
                                    )
                                    for i, btn in enumerate(PRICE_BUTTONS)
                                ],
                                style={
                                    "display": "flex",
                                    "flex": "1",  # Take all remaining space
                                    "width": "100%",
                                    "gap": "0",  # No gap between buttons
                                    "border-collapse": "collapse",  # Collapse borders
                                },
                            ),
                        ],
                        style={
                            "margin": "2px", 
                            "marginBottom": "6px",  # Add space between rows
                            "textAlign": "left", 
                            "width": "100%",
                            "display": "flex", 
                            "alignItems": "center"
                        },
                    ),
                    # Distance buttons row - with label and buttons on the same row
                    html.Div(
                        [
                            # Label on the left
                            html.Label(
                                "Макс. расстояние (км):",
                                className="dash-label",
                                style={
                                    "marginBottom": "2px", 
                                    "marginRight": "5px", 
                                    "minWidth": "110px",  # Fixed identical width using minWidth
                                    "width": "110px",     # Both width and minWidth for consistency
                                    "display": "inline-block",
                                    "whiteSpace": "nowrap"
                                },
                            ),
                            # Buttons on the right - completely joined
                            html.Div(
                                [
                                    html.Button(
                                        btn["label"],
                                        id=btn["id"],
                                        style={
                                            **BUTTON_STYLES["distance"],
                                            "opacity": 1.0 if btn.get("default", False) else 0.6,
                                            "boxShadow": "0 0 5px #4682B4" if btn.get("default", False) else None,
                                            "flex": "1",  # Each button flex equally
                                            "margin": "0",  # Zero margin
                                            "padding": "2px 0",  # Reduced vertical padding for shorter height
                                            "fontSize": "10px",  # Smaller font size
                                            "lineHeight": "1",  # Tighter line height
                                            "borderRadius": "0",  # No rounded corners
                                            "borderLeft": "none" if i > 0 else "1px solid #ccc",  # Remove left border for all but first button
                                            "position": "relative",  # For z-index to work
                                            "zIndex": "1" if btn.get("default", False) else "0",  # Active button appears on top
                                        },
                                    )
                                    for i, btn in enumerate(DISTANCE_BUTTONS)
                                ],
                                style={
                                    "display": "flex",
                                    "flex": "1",  # Take all remaining space
                                    "width": "100%",
                                    "gap": "0",  # No gap between buttons
                                    "border-collapse": "collapse",  # Collapse borders
                                },
                            ),
                        ],
                        style={
                            "margin": "2px", 
                            "marginBottom": "6px",  # Add space between rows
                            "textAlign": "left", 
                            "width": "100%",
                            "display": "flex", 
                            "alignItems": "center"
                        },
                    ),
                    # Filter buttons - label inside container with consistent alignment
                    html.Div(
                        [
                            html.Label(
                                "Быстрые фильтры:",
                                className="dash-label",
                                style={"marginBottom": "2px", "marginLeft": "4px", "textAlign": "left"},
                            ),
                        ],
                        style={
                            "margin": "2px", 
                            "marginTop": "5px",
                            "textAlign": "left", 
                            "width": "100%",
                        },
                    ),
                    # Filter buttons row 
                    html.Div(
                        [
                            html.Button(
                                "За сутки",
                                id="btn-updated-today",
                                style={**BUTTON_STYLES["updated_today"], "opacity": "0.6", "flex": "1"},
                            ),
                            html.Button(
                                "Рядом",
                                id="btn-nearest",
                                style={**BUTTON_STYLES["nearest"], "opacity": "0.6", "flex": "1"},
                            ),
                            html.Button(
                                "Выгодно",
                                id="btn-below-estimate",
                                style={**BUTTON_STYLES["below_estimate"], "opacity": "0.6", "flex": "1"},
                            ),
                            html.Button(
                                "Неактивные",
                                id="btn-inactive",
                                style={**BUTTON_STYLES["inactive"], "opacity": "0.6", "flex": "1"},
                            ),
                        ],
                        style={
                            "margin": "2px",
                            "display": "flex",
                            "width": "100%",
                            "gap": "0px",  # No gap between buttons
                        },
                    ),
                ],
                style={"textAlign": "left", "width": "355px", "padding": "0px"},  # Fixed width with no padding
            ),
            # Table container
            dcc.Loading(
                id="loading-main",
                children=[html.Div(id="table-container")],
                style={"margin": "5px"},
            ),
        ],
        style=STYLE["container"],
    )
    return app.layout


# App layout
app.layout = create_app_layout(app)

# Combined callback for updating table and time - kept in app.py
@callback(
    [Output("table-container", "children"), Output("last-update-time", "children")],
    [Input("filter-store", "data"), Input("interval-component", "n_intervals")],
)
def update_table_and_time(filters, _):
    df, update_time = load_and_process_data()
    df = filter_and_sort_data(df, filters)
    
    # Define column properties
    visible = CONFIG["columns"]["visible"]
    numeric_cols = {
        "distance",
        "price_value_formatted",
        "cian_estimation_formatted",
        "price_difference_formatted",
        "monthly_burden_formatted",
    }
    # Add address_title to markdown columns
    markdown_cols = {"price_change_formatted", "address_title", "offer_link", 'price_info', 'update_title'}
    
    columns = [
        {
            "name": CONFIG["columns"]["headers"].get(c, c),
            "id": c,
            "type": "numeric" if c in numeric_cols else "text",
            "presentation": "markdown" if c in markdown_cols else None,
        }
        for c in visible
    ]
    
    # Create the table
    # In app.py, update the DataTable creation:

    # Create the table
    table = dash_table.DataTable(
        id="apartment-table",
        columns=columns,
        data=(
            df[CONFIG["columns"]["display"]].to_dict("records") if not df.empty else []
        ),
        sort_action="custom",
        sort_mode="multi",
        sort_by=[],
        hidden_columns=CONFIG["hidden_cols"],
        style_table=STYLE["table"],
        style_cell=STYLE["cell"],
        style_cell_conditional=STYLE.get("cell_conditional", []) + [
            {"if": {"column_id": c["id"]}, "width": "auto"} for c in columns
        ],
        style_header=STYLE["header_cell"],
        style_header_conditional=HEADER_STYLES,
        style_data=STYLE["data"],
        style_filter=STYLE["filter"],
        style_data_conditional=COLUMN_STYLES,
        page_size=100,
        page_action="native",
        markdown_options={"html": True},
    )
    return table, f"Актуально на: {update_time}"

# Callback for sorting - kept in app.py
@callback(
    Output("apartment-table", "data"),
    [Input("apartment-table", "sort_by"), Input("filter-store", "data")],
)
def update_sort(sort_by, filters):
    df, _ = load_and_process_data()
    df = filter_and_sort_data(df, filters, sort_by)
    return df[CONFIG["columns"]["display"]].to_dict("records") if not df.empty else []

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))





# Base layout styles for buttons that should be preserved
PRICE_BUTTON_LAYOUT = {
    "flex": "1",  # Take full width
    "margin": "0",  # No margin
    "padding": "2px 0",  # Reduced vertical padding
    "fontSize": "10px",  # Smaller font size
    "lineHeight": "1",  # Tighter line height
    "borderRadius": "0",  # No rounded corners
}

DISTANCE_BUTTON_LAYOUT = {
    "flex": "1",  # Take full width
    "margin": "0",  # No margin
    "padding": "2px 0",  # Reduced vertical padding
    "fontSize": "10px",  # Smaller font size
    "lineHeight": "1",  # Tighter line height
    "borderRadius": "0",  # No rounded corners
}

# Callback to handle price button clicks
@callback(
    [Output(btn["id"], "style") for btn in PRICE_BUTTONS]
    + [Output("filter-store", "data", allow_duplicate=True)],
    [Input(btn["id"], "n_clicks") for btn in PRICE_BUTTONS],
    [State("filter-store", "data")],
    prevent_initial_call=True,
)
def update_price_buttons(*args):
    n_buttons = len(PRICE_BUTTONS)
    clicks = args[:n_buttons]
    current_filters = args[n_buttons]

    ctx = dash.callback_context
    if not ctx.triggered:
        # Default button
        button_id = default_price_btn
        price_value = default_price
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        price_value = next(
            (btn["value"] for btn in PRICE_BUTTONS if btn["id"] == button_id),
            default_price,
        )

    # Update the filter store
    current_filters["price_value"] = price_value
    current_filters["active_price_btn"] = button_id

    # Create button styles
    styles = []
    for i, btn in enumerate(PRICE_BUTTONS):
        # Base style with layout preserved
        base_style = {
            **BUTTON_STYLES["price"],
            **PRICE_BUTTON_LAYOUT,
        }
        
        # Add buttongroup-specific styling
        if i > 0:
            base_style["borderLeft"] = "none"
        
        # Add active/inactive styling
        if btn["id"] == button_id:
            base_style.update({
                "opacity": 1.0,
                "boxShadow": "0 0 5px #4682B4",
                "position": "relative",
                "zIndex": "1",
            })
        else:
            base_style.update({
                "opacity": 0.6,
                "position": "relative",
                "zIndex": "0",
            })
            
        styles.append(base_style)

    return *styles, current_filters


# Callback to handle distance button clicks
@callback(
    [Output(btn["id"], "style") for btn in DISTANCE_BUTTONS]
    + [Output("filter-store", "data", allow_duplicate=True)],
    [Input(btn["id"], "n_clicks") for btn in DISTANCE_BUTTONS],
    [State("filter-store", "data")],
    prevent_initial_call=True,
)
def update_distance_buttons(*args):
    n_buttons = len(DISTANCE_BUTTONS)
    clicks = args[:n_buttons]
    current_filters = args[n_buttons]

    ctx = dash.callback_context
    if not ctx.triggered:
        # Default button
        button_id = default_distance_btn
        distance_value = default_distance
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        distance_value = next(
            (btn["value"] for btn in DISTANCE_BUTTONS if btn["id"] == button_id),
            default_distance,
        )

    # Update the filter store
    current_filters["distance_value"] = distance_value
    current_filters["active_dist_btn"] = button_id

    # Create button styles
    styles = []
    for i, btn in enumerate(DISTANCE_BUTTONS):
        # Base style with layout preserved
        base_style = {
            **BUTTON_STYLES["distance"],
            **DISTANCE_BUTTON_LAYOUT,
        }
        
        # Add buttongroup-specific styling
        if i > 0:
            base_style["borderLeft"] = "none"
            
        # Add active/inactive styling
        if btn["id"] == button_id:
            base_style.update({
                "opacity": 1.0,
                "boxShadow": "0 0 5px #4682B4",
                "position": "relative",
                "zIndex": "1",
            })
        else:
            base_style.update({
                "opacity": 0.6,
                "position": "relative",
                "zIndex": "0",
            })
            
        styles.append(base_style)

    return *styles, current_filters


# Callback to handle filter button clicks
@callback(
    [
        Output("btn-nearest", "style"),
        Output("btn-below-estimate", "style"),
        Output("btn-inactive", "style"),
        Output("btn-updated-today", "style"),
        Output("filter-store", "data", allow_duplicate=True),
    ],
    [
        Input("btn-nearest", "n_clicks"),
        Input("btn-below-estimate", "n_clicks"),
        Input("btn-inactive", "n_clicks"),
        Input("btn-updated-today", "n_clicks"),
    ],
    [State("filter-store", "data")],
    prevent_initial_call=True,
)
def update_filters(
    nearest_clicks,
    below_est_clicks,
    inactive_clicks,
    updated_today_clicks,
    current_filters,
):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [
            {**BUTTON_STYLES["nearest"], "opacity": 0.6},
            {**BUTTON_STYLES["below_estimate"], "opacity": 0.6},
            {**BUTTON_STYLES["inactive"], "opacity": 0.6},
            {**BUTTON_STYLES["updated_today"], "opacity": 0.6},
            current_filters,
        ]

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    filter_map = {
        "btn-nearest": "nearest",
        "btn-below-estimate": "below_estimate",
        "btn-inactive": "inactive",
        "btn-updated-today": "updated_today",
    }

    if button_id in filter_map:
        current_filters[filter_map[button_id]] = not current_filters[
            filter_map[button_id]
        ]

    # Create button styles
    styles = []
    for key in ["nearest", "below_estimate", "inactive", "updated_today"]:
        filter_style = {**BUTTON_STYLES[key], "flex": "1"}  # Add flex for full width
        
        if current_filters[key]:
            filter_style.update({"opacity": 1.0, "boxShadow": "0 0 5px #4682B4"})
        else:
            filter_style.update({"opacity": 0.6})
            
        styles.append(filter_style)

    return *styles, current_filters
    