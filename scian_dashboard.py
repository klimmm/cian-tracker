import os
import numpy as np
import pandas as pd
import dash
from dash import dcc, html, dash_table, callback
from dash.dependencies import Input, Output, State
import re
import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+



# Configuration - Adjusted for new column structure
# Update CONFIG to include new columns
CONFIG = {
    "columns": {
        "display": [
            "offer_id", "title", "updated_time", "updated_time_sort", 
            "price_value_formatted", "price_value", "cian_estimation_formatted", "price_difference_formatted",
            "address", "metro_station", "offer_link", "distance", "distance_sort",
            "price_change_formatted", "status", "unpublished_date", "unpublished_date_sort",
            "price_difference_value", "rental_period_abbr", "utilities_type_abbr", 
            "commission_info_abbr", "deposit_info_abbr", "monthly_burden", "monthly_burden_formatted"
        ],
        "visible": [
            "address", "distance", "price_value_formatted", 
            "commission_info_abbr", "deposit_info_abbr", 
            #"monthly_burden_formatted", 
            "cian_estimation_formatted",  
            "updated_time", "price_change_formatted", "title", "metro_station", 
            #"rental_period_abbr", "utilities_type_abbr", 
            "unpublished_date"
        ],
        "headers": {
            "offer_id": "ID", "distance": "Расст.", "price_change_formatted": "Изм.",
            "title": "Описание", "updated_time": "Обновлено", "price_value_formatted": "Цена", "cian_estimation_formatted": "Оценка",
            "price_difference_formatted": "Разница", "address": "Адрес", "metro_station": "Метро", "offer_link": "Ссылка",
            "status": "Статус", "unpublished_date": "Снято",
            "rental_period_abbr": "Срок", "utilities_type_abbr": "ЖКХ", 
            "commission_info_abbr": "Коммис", "deposit_info_abbr": "Залог",
            "monthly_burden_formatted": "Нагрузка/мес"
        },
        "sort_map": {
            "updated_time": "updated_time_sort", "price_value_formatted": "price_value",
            "price_change_formatted": "price_change_value", "cian_estimation_formatted": "cian_estimation_value",
            "price_difference_formatted": "price_difference_value", "distance": "distance_sort",
            "monthly_burden_formatted": "monthly_burden"
        },
    },
    "months": {i: m for i, m in enumerate(["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"], 1)},
    "base_url": "https://www.cian.ru/rent/flat/",
    "hidden_cols": [
        "price_value", "distance_sort", "updated_time_sort", "cian_estimation_value",
        "price_difference_value", "unpublished_date_sort", "monthly_burden"
    ],
}





MOSCOW_TZ = ZoneInfo("Europe/Moscow")  # or any timezone you want

def pluralize_ru_accusative(number, forms, word):
    """
    Подбирает правильную форму слова в винительном падеже:
    forms = ['минута', 'минуты', 'минут'] или ['час', 'часа', 'часов']
    word — 'минута' или 'час' — нужен для обработки исключений.
    """
    n = abs(number) % 100
    if 11 <= n <= 19:
        return forms[2]
    n = n % 10
    if n == 1:
        if word == 'минута':
            return 'минуту'
        return forms[0]  # 'час'
    elif 2 <= n <= 4:
        return forms[1]
    else:
        return forms[2]


def format_date(dt):
    now = datetime.now(MOSCOW_TZ)  # или ваша временная зона
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MOSCOW_TZ)
    delta = now - dt
    today = now.date()
    yesterday = today - timedelta(days=1)

    if delta < timedelta(minutes=1):
        return "только что"
    elif delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() // 60)
        return f"{minutes} {pluralize_ru_accusative(minutes, ['минута', 'минуты', 'минут'], 'минута')} назад"
    elif delta < timedelta(hours=6):
        hours = int(delta.total_seconds() // 3600)
        return f"{hours} {pluralize_ru_accusative(hours, ['час', 'часа', 'часов'], 'час')} назад"
    elif dt.date() == today:
        return f"сегодня, {dt.hour:02}:{dt.minute:02}"
    elif dt.date() == yesterday:
        return f"вчера, {dt.hour:02}:{dt.minute:02}"
    else:
        return f"{dt.day} {CONFIG['months'][dt.month]}, {dt.hour:02}:{dt.minute:02}"

        
# Unified styles
FONT = "Arial,sans-serif"
STYLE = {
    "container": {"fontFamily": FONT, "padding": "5px", "maxWidth": "100%"},
    "header": {"fontFamily": FONT, "textAlign": "center", "fontSize": "10px", "borderBottom": "1px solid #ddd"},
    "update_time": {"fontFamily": FONT, "fontStyle": "bold", "fontSize": "12px"},
    "table": {"overflowX": "auto", "width": "100%"},
    "cell": {"fontFamily": FONT, "textAlign": "center", "padding": "3px", "fontSize": "9px", "whiteSpace": "nowrap"},
    "header_cell": {"fontFamily": FONT, "backgroundColor": "#4682B4", "color": "white", "fontSize": "9px"},
    "filter": {"display": "none"},
    "data": {"lineHeight": "14px"},
    "input": {"marginRight": "5px", "width": "110px", "height": "15px"},
    "input_number": {"width": "110px", "height": "15px"},
    "label": {"fontSize": "11px", "marginRight": "3px", "display": "block"},
    "button_base": {"display": "inline-block", "padding": "3px 8px", "fontSize": "9px", 
                  "border": "1px solid #ccc", "margin": "0 5px", "cursor": "pointer"},
}

STYLE["button_base"] = {
    "display": "inline-block", 
    "padding": "3px 8px", 
    "fontSize": "10px", 
    "border": "1px solid #ccc", 
    "margin": "0 5px 5px 0",
    "cursor": "pointer"
}

# Classic, standard colors for button groups
BUTTON_STYLES = {
    'nearest': {"backgroundColor": "#d9edf7", **STYLE["button_base"]},
    'below_estimate': {"backgroundColor": "#fef3d5", **STYLE["button_base"]},
    'updated_today': {"backgroundColor": "#dff0d8", **STYLE["button_base"]},
    'inactive': {"backgroundColor": "#f4f4f4", **STYLE["button_base"]},
    'price': {"backgroundColor": "#e8e8e0", **STYLE["button_base"]},      # Light warm gray
    'distance': {"backgroundColor": "#e0e4e8", **STYLE["button_base"]}    # Light cool gray
}

COLUMN_STYLES = [
    {"if": {"filter_query": '{status} contains "non active"'}, "backgroundColor": "#f4f4f4", "color": "#888"},
    {"if": {"filter_query": '{distance_sort} < 1.5 && {status} ne "non active"'}, "backgroundColor": "#d9edf7"},
    {"if": {"filter_query": '{price_difference_value} < -5000 && {status} ne "non active"'}, "backgroundColor": "#fef3d5"},
    {"if": {"filter_query": '{updated_time_sort} > "' + (pd.Timestamp.now() - pd.Timedelta(hours=24)).isoformat() + '"'}, 
     "backgroundColor": "#e6f3e0", "fontWeight": "normal"},
    {"if": {"column_id": "price_change_formatted"}, "textAlign": "center"},
    {"if": {"column_id": "updated_time"}, "fontWeight": "bold", "textAlign": "center"},
    {"if": {"column_id": "price_value_formatted"}, "fontWeight": "bold", "textAlign": "center"},
    {"if": {"column_id": "monthly_burden_formatted"}, "fontWeight": "bold", "textAlign": "center"},
    {"if": {"column_id": "address"}, "textAlign": "left"},
    {"if": {"column_id": "title"}, "textAlign": "left"},
]

HEADER_STYLES = [
    {"if": {"column_id": col}, "textAlign": "center"} 
    for col in ["distance", "updated_time", "unpublished_date", "price_value_formatted", "cian_estimation_formatted", 
               "price_change_formatted", "metro_station", "status", "monthly_burden_formatted"]
] + [
    {"if": {"column_id": col}, "textAlign": "left"} 
    for col in ["address", "title"]
]

def format_text(value, formatter, default=""):
    """Generic formatter with default handling"""
    if value is None or pd.isna(value):
        return default
    return formatter(value)

def format_price_changes(value):
    """Format price changes with HTML styling with improved error handling"""
    # Handle None and NaN values
    if value is None or pd.isna(value):
        return "<div style='text-align:center;'><span>—</span></div>"
    
    # Handle "new" string
    if isinstance(value, str) and value.lower() == "new":
        return "<div style='text-align:center;'><span>—</span></div>"
    
    # Convert to numeric safely
    try:
        value = float(value)  # Try direct conversion first
    except (ValueError, TypeError):
        try:
            value = pd.to_numeric(value, errors='coerce')
            if pd.isna(value):
                return "<div style='text-align:center;'><span>—</span></div>"
        except:
            return "<div style='text-align:center;'><span>—</span></div>"
    
    # Check if value is effectively zero
    if abs(value) < 1:
        return "<div style='text-align:center;'><span>—</span></div>"
    
    # Format the change
    color = 'green' if value < 0 else 'red'
    arrow = '↓' if value < 0 else '↑'
    display = f"{abs(int(value))//1000}K" if abs(value) >= 1000 else str(abs(int(value)))
    
    return f"<div style='text-align:center;'><span style='color:{color};'>{arrow}{display}</span></div>"

def extract_deposit_value(deposit_info):
    """Extract numeric deposit value from deposit_info string"""
    if deposit_info is None or pd.isna(deposit_info) or deposit_info == "--":
        return None
        
    if "без залога" in deposit_info:
        return 0
        
    if "залог" in deposit_info:
        import re
        match = re.search(r'залог\s+([\d\s\xa0]+)\s*₽', deposit_info)
        
        if not match:
            return None
            
        amount_str = match.group(1)
        clean_amount = re.sub(r'\s', '', amount_str)
        
        try:
            return int(clean_amount)
        except ValueError:
            return None
    
    return None


    
def format_price(value):
    """Format price value"""
    if value == 0:
        return "--"
    return f"{'{:,}'.format(int(value)).replace(',', ' ')} ₽/мес."


def format_rental_period(value):
    """Format rental period with more intuitive abbreviation"""
    if value == "От года":
        return "год+"
    elif value == "На несколько месяцев":
        return "мес+"
    return "--"

def format_utilities(value):
    """Format utilities info with clearer abbreviation"""
    if "без счётчиков" in value:
        return "+счет"
    elif "счётчики включены" in value:
        return "-"
    return "--"

def format_commission(value):
    """Format commission info with compact abbreviation"""
    if "без комиссии" in value:
        return "0%"
    elif "комиссия" in value:
        import re
        match = re.search(r'(\d+)%', value)
        if match:
            return f"{match.group(1)}%"
    return "--"


def format_deposit(value):
    """Robust deposit formatter that handles all cases"""
    # Handle None/NaN/-- values
    if value is None or pd.isna(value) or value == "--":
        return "--"
        
    # Handle "без залога" case
    if "без залога" in value:
        return "0₽"
        
    # Handle deposit with amount
    if "залог" in value:
        # Extract digits using more comprehensive pattern
        # This matches any sequence of digits with optional spaces in between
        import re
        match = re.search(r'залог\s+([\d\s\xa0]+)\s*₽', value)
        
        if not match:
            print(f"Failed to extract amount from: '{value}'")
            return "--"
            
        # Get the matched amount and clean it
        amount_str = match.group(1)
        # Replace all whitespace characters (including non-breaking spaces)
        clean_amount = re.sub(r'\s', '', amount_str)
        
        try:
            amount_num = int(clean_amount)
            # Format based on magnitude
            if amount_num >= 1000000:
                return f"{amount_num//1000000}M"
            elif amount_num >= 1000:
                return f"{amount_num//1000}K"
            return f"{amount_num}₽"
        except ValueError as e:
            print(f"Error converting '{clean_amount}' to integer: {e}")
            return "--"
    
    return "--"

# Calculate monthly burden with explicit numeric conversion and debugging
def calculate_monthly_burden(row):
    """Calculate average monthly financial burden over 12 months with debugging"""
    try:
        # Ensure all values are properly converted to numeric
        price = pd.to_numeric(row['price_value'], errors='coerce')
        comm = pd.to_numeric(row['commission_value'], errors='coerce')
        dep = pd.to_numeric(row['deposit_value'], errors='coerce')
        
        # Check if price is valid
        if pd.isna(price) or price <= 0:
            return None
            
        # Set defaults for missing values
        comm = 0 if pd.isna(comm) else comm
        dep = 0 if pd.isna(dep) else dep
        
        # Calculate components
        annual_rent = price * 12
        commission_fee = price * (comm / 100)
        deposit_value = dep
        
        # Calculate total monthly burden
        total_burden = (annual_rent + commission_fee + deposit_value) / 12
        
        return total_burden
    except Exception as e:
        print(f"Error calculating burden: {e}")
        return None


# Format with more detailed debugging
def format_burden(row):
    try:
        if pd.isna(row['monthly_burden']) or pd.isna(row['price_value']) or row['price_value'] <= 0:
            return '--'
            
        # Ensure values are numeric
        burden = float(row['monthly_burden'])
        price = float(row['price_value'])
        
        # Format the burden value
        burden_formatted = f"{'{:,}'.format(int(burden)).replace(',', ' ')} ₽"
        
        # Calculate percentage difference from base rent
        diff_percent = int(((burden / price) - 1) * 100)
        
        # Format with percentage difference if significant
        if diff_percent > 2:
            return f"{burden_formatted}/мес."
        else:
            return burden_formatted
    except Exception as e:
        print(f"Error formatting burden: {e}")
        return '--'
    
# Update the load_and_process_data function to process new columns


# Modify the load_and_process_data function to read from metadata file
def load_and_process_data():
    """Load and process data with improved price change handling and new columns"""
    try:
        path = "cian_apartments.csv"
        df = pd.read_csv(path, encoding="utf-8", comment="#")
        
        # Extract update time from metadata file instead of CSV comment
        try:
            with open("cian_apartments.meta.json", "r", encoding="utf-8") as f:
                metadata = json.load(f)
                update_time_str = metadata.get("last_updated", "Unknown")
                
                # Parse and reformat the datetime if it's in the expected format
                try:
                    # Parse the timestamp (assuming format like "2025-04-09 09:00:31")
                    dt = pd.to_datetime(update_time_str)
                    # Format as "09.04.2025 09:00:31"
                    update_time = dt.strftime("%d.%m.%Y %H:%M:%S")
                    
                    # If you want to add italics to the time portion:
                    # update_time = f"{dt.strftime('%d.%m.%Y')} *{dt.strftime('%H:%M:%S')}*"
                except:
                    # Fallback if parsing fails
                    update_time = update_time_str
        except Exception as e:
            print(f"Error reading metadata file: {e}")
            # Fallback to original method
            with open(path, encoding="utf-8") as f:
                first_line = f.readline()
                update_time = first_line.split("")[1].split(",")[0].strip() if "last_updated=" in first_line else "Unknown"
        
        # Rest of the function remains the same...
        # Process core columns
        df["offer_id"] = df["offer_id"].astype(str)
        df["address"] = df.apply(lambda r: f"[{r['address']}]({CONFIG['base_url']}{r['offer_id']}/)", axis=1)
        df["offer_link"] = df["offer_id"].apply(lambda x: f"[View]({CONFIG['base_url']}{x}/)")
        
        # Process distance
        df["distance_sort"] = pd.to_numeric(df["distance"], errors="coerce")
        df["distance"] = df["distance_sort"].apply(lambda x: f"{x:.2f} km" if pd.notnull(x) else "")
        
        # Format prices from numeric values
        df["price_value_formatted"] = df["price_value"].apply(lambda x: format_text(x, format_price, "--"))
        df["cian_estimation_formatted"] = df["cian_estimation_value"].apply(lambda x: format_text(x, format_price, "--"))
        df["price_difference_formatted"] = df["price_difference_value"].apply(lambda x: format_text(x, format_price, ""))
        
        df["price_change_formatted"] = df["price_change_value"].apply(format_price_changes)
        
        # Process date-time fields
        df["updated_time_sort"] = pd.to_datetime(df["updated_time"], errors="coerce")
        df["updated_time"] = df["updated_time_sort"].apply(lambda x: format_text(x, format_date, ""))
        
        df["unpublished_date_sort"] = pd.to_datetime(df["unpublished_date"], errors="coerce")
        df["unpublished_date"] = df["unpublished_date_sort"].apply(lambda x: format_text(x, format_date, "--"))
        
        # Process new columns with improved abbreviations
        df["rental_period_abbr"] = df["rental_period"].apply(lambda x: format_rental_period(x))
        df["utilities_type_abbr"] = df["utilities_type"].apply(lambda x: format_utilities(x))
        df["commission_info_abbr"] = df["commission_info"].apply(lambda x: format_commission(x))
        
        # Extract deposit values
        df["deposit_value"] = df["deposit_info"].apply(extract_deposit_value)
        
        # Format deposit as percentage
        df["deposit_info_abbr"] = df.apply(
            lambda row: "0%" if pd.notnull(row["deposit_value"]) and row["deposit_value"] == 0 
            else f"{int((row['deposit_value']/row['price_value'])*100)}%" if pd.notnull(row["deposit_value"]) 
            and pd.notnull(row["price_value"]) and row["price_value"] > 0 else "--", axis=1)
        
        
        df['monthly_burden'] = df.apply(calculate_monthly_burden, axis=1)
        df['monthly_burden_formatted'] = df.apply(format_burden, axis=1)
        
        # Default sorting
        df['sort_key'] = df['status'].apply(lambda x: 1 if x == 'active' else 2)
        df = df.sort_values(['sort_key', 'updated_time_sort'], ascending=[True, False]).drop(columns='sort_key')
        
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
        price_value = filters.get('price_value')
        distance_value = filters.get('distance_value')
        
        # Apply price filter if not infinity (90k+)
        if price_value and price_value != float('inf'):
            df = df[df["price_value"] <= price_value]
            
        # Apply distance filter if not infinity (5km+)
        if distance_value and distance_value != float('inf'):
            df = df[df["distance_sort"] <= distance_value]
    
    # Apply button filters
    if filters and any(v for k, v in filters.items() if k in ['nearest', 'below_estimate', 'inactive', 'updated_today']):
        mask = pd.Series(False, index=df.index)
        
        if filters.get('nearest'):
            mask |= (df["distance_sort"] < 1.5)
        if filters.get('below_estimate'):
            mask |= (df["price_difference_value"] < -5000)
        if filters.get('inactive'):
            mask |= (df["status"] == "non active")
        if filters.get('updated_today'):
            mask |= (df["updated_time_sort"] > (pd.Timestamp.now() - pd.Timedelta(hours=24)))
        
        if any(mask):  # Only apply if any filter is active
            df = df[mask]
    
    # Apply sorting
    if sort_by:
        for item in sort_by:
            col = CONFIG["columns"]["sort_map"].get(item["column_id"], item["column_id"])
            df = df.sort_values(col, ascending=item["direction"] == "asc")

    df = df[df["distance_sort"] <= 6]
    return df

# Initialize the app
app = dash.Dash(__name__, title="", meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}], suppress_callback_exceptions=True)
server = app.server

# App layout
app.layout = html.Div([
    html.H2("", style=STYLE["header"]),
    html.Div(html.Span(id="last-update-time", style=STYLE["update_time"])),
    dcc.Interval(id="interval-component", interval=2 * 60 * 1000, n_intervals=0),
    
    # Filter store - now also storing price and distance values
    dcc.Store(id='filter-store', data={
        'nearest': False, 
        'below_estimate': False, 
        'inactive': False, 
        'updated_today': False,
        'price_value': 80000,  # Default price value (80k)
        'distance_value': 3.0,  # Default distance value (3km)
        'active_price_btn': 'btn-price-80k',  # Default active price button
        'active_dist_btn': 'btn-dist-3km'   # Default active distance button
    }),
    
    # Container for price buttons, distance buttons, and filter buttons
    # Reduced margins between button rows
    html.Div([
        # Price buttons
        html.Div([
            html.Label('Макс. цена (₽):', className="dash-label", style={"marginBottom": "2px"}),
            html.Div([
                html.Button("50K", id="btn-price-50k", style={**BUTTON_STYLES['price'], "opacity": 0.6}),
                html.Button("60K", id="btn-price-60k", style={**BUTTON_STYLES['price'], "opacity": 0.6}),
                html.Button("70K", id="btn-price-70k", style={**BUTTON_STYLES['price'], "opacity": 0.6}),
                html.Button("80K", id="btn-price-80k", style={**BUTTON_STYLES['price'], "opacity": 1.0, "boxShadow": "0 0 5px #4682B4"}),
                html.Button("90K", id="btn-price-90k", style={**BUTTON_STYLES['price'], "opacity": 0.6}),
                html.Button("90K+", id="btn-price-90k-plus", style={**BUTTON_STYLES['price'], "opacity": 0.6}),
            ]),
        ], style={"margin": "3px", "textAlign": "left", "width": "100%", "maxWidth": "600px"}),
        
        # Distance buttons
        html.Div([
            html.Label('Макс. расстояние (км):', className="dash-label", style={"marginBottom": "2px"}),
            html.Div([
                html.Button("1km", id="btn-dist-1km", style={**BUTTON_STYLES['distance'], "opacity": 0.6}),
                html.Button("2km", id="btn-dist-2km", style={**BUTTON_STYLES['distance'], "opacity": 0.6}),
                html.Button("3km", id="btn-dist-3km", style={**BUTTON_STYLES['distance'], "opacity": 1.0, "boxShadow": "0 0 5px #4682B4"}),
                html.Button("4km", id="btn-dist-4km", style={**BUTTON_STYLES['distance'], "opacity": 0.6}),
                html.Button("5km", id="btn-dist-5km", style={**BUTTON_STYLES['distance'], "opacity": 0.6}),
                html.Button("5km+", id="btn-dist-5km-plus", style={**BUTTON_STYLES['distance'], "opacity": 0.6}),
            ]),
        ], style={"margin": "3px", "textAlign": "left", "width": "100%", "maxWidth": "600px"}),
        
        # Filter buttons - add consistent label for filters
        html.Div([
            html.Button("Ближайшие", id="btn-nearest", style={**BUTTON_STYLES['nearest'], "opacity": "0.6"}),
            html.Button("Цена ниже оценки", id="btn-below-estimate", style={**BUTTON_STYLES['below_estimate'], "opacity": "0.6"}),
            html.Button("Сегодня", id="btn-updated-today", style={**BUTTON_STYLES['updated_today'], "opacity": "0.6"}),
            html.Button("Неактивные", id="btn-inactive", style={**BUTTON_STYLES['inactive'], "opacity": "0.6"}),
        ], style={"margin": "3px", "marginTop": "5px", "display": "flex", "alignItems": "center", "flexWrap": "wrap", "width": "100%", "maxWidth": "600px"}),
    ], style={"margin": "3px", "textAlign": "left", "width": "100%"}),
    
    # Table container
    dcc.Loading(id="loading-main", children=[html.Div(id="table-container")], style={"margin": "5px"}),
], style=STYLE["container"])

# Callback to handle price button clicks
@callback(
    [Output('btn-price-50k', 'style'),
     Output('btn-price-60k', 'style'),
     Output('btn-price-70k', 'style'),
     Output('btn-price-80k', 'style'),
     Output('btn-price-90k', 'style'),
     Output('btn-price-90k-plus', 'style'),
     Output('filter-store', 'data', allow_duplicate=True)],
    [Input('btn-price-50k', 'n_clicks'),
     Input('btn-price-60k', 'n_clicks'),
     Input('btn-price-70k', 'n_clicks'),
     Input('btn-price-80k', 'n_clicks'),
     Input('btn-price-90k', 'n_clicks'),
     Input('btn-price-90k-plus', 'n_clicks')],
    [State('filter-store', 'data')],
    prevent_initial_call=True
)
def update_price_buttons(click_50k, click_60k, click_70k, click_80k, click_90k, click_90k_plus, current_filters):
    ctx = dash.callback_context
    if not ctx.triggered:
        # Default to 80k
        button_id = 'btn-price-80k'
        price_value = 80000
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        price_map = {
            'btn-price-50k': 50000,
            'btn-price-60k': 60000,
            'btn-price-70k': 70000,
            'btn-price-80k': 80000,
            'btn-price-90k': 90000,
            'btn-price-90k-plus': float('inf')  # Represents no limit
        }
        price_value = price_map.get(button_id, 80000)
    
    # Update the filter store
    current_filters['price_value'] = price_value
    current_filters['active_price_btn'] = button_id
    
    # Create button styles
    styles = []
    for btn in ['btn-price-50k', 'btn-price-60k', 'btn-price-70k', 'btn-price-80k', 'btn-price-90k', 'btn-price-90k-plus']:
        if btn == button_id:
            styles.append({**BUTTON_STYLES['price'], "opacity": 1.0, "boxShadow": '0 0 5px #4682B4'})
        else:
            styles.append({**BUTTON_STYLES['price'], "opacity": 0.6})
    
    return *styles, current_filters

# Callback to handle distance button clicks
@callback(
    [Output('btn-dist-1km', 'style'),
     Output('btn-dist-2km', 'style'),
     Output('btn-dist-3km', 'style'),
     Output('btn-dist-4km', 'style'),
     Output('btn-dist-5km', 'style'),
     Output('btn-dist-5km-plus', 'style'),
     Output('filter-store', 'data', allow_duplicate=True)],
    [Input('btn-dist-1km', 'n_clicks'),
     Input('btn-dist-2km', 'n_clicks'),
     Input('btn-dist-3km', 'n_clicks'),
     Input('btn-dist-4km', 'n_clicks'),
     Input('btn-dist-5km', 'n_clicks'),
     Input('btn-dist-5km-plus', 'n_clicks')],
    [State('filter-store', 'data')],
    prevent_initial_call=True
)
def update_distance_buttons(click_1km, click_2km, click_3km, click_4km, click_5km, click_5km_plus, current_filters):
    ctx = dash.callback_context
    if not ctx.triggered:
        # Default to 3km
        button_id = 'btn-dist-3km'
        distance_value = 3.0
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        distance_map = {
            'btn-dist-1km': 1.0,
            'btn-dist-2km': 2.0,
            'btn-dist-3km': 3.0,
            'btn-dist-4km': 4.0,
            'btn-dist-5km': 5.0,
            'btn-dist-5km-plus': float('inf')  # Represents no limit
        }
        distance_value = distance_map.get(button_id, 3.0)
    
    # Update the filter store
    current_filters['distance_value'] = distance_value
    current_filters['active_dist_btn'] = button_id
    
    # Create button styles
    styles = []
    for btn in ['btn-dist-1km', 'btn-dist-2km', 'btn-dist-3km', 'btn-dist-4km', 'btn-dist-5km', 'btn-dist-5km-plus']:
        if btn == button_id:
            styles.append({**BUTTON_STYLES['distance'], "opacity": 1.0, "boxShadow": '0 0 5px #4682B4'})
        else:
            styles.append({**BUTTON_STYLES['distance'], "opacity": 0.6})
    
    return *styles, current_filters

# Callback to handle filter button clicks
@callback(
    [Output('btn-nearest', 'style'),
     Output('btn-below-estimate', 'style'),
     Output('btn-inactive', 'style'),
     Output('btn-updated-today', 'style'),
     Output('filter-store', 'data', allow_duplicate=True)],
    [Input('btn-nearest', 'n_clicks'),
     Input('btn-below-estimate', 'n_clicks'),
     Input('btn-inactive', 'n_clicks'),
     Input('btn-updated-today', 'n_clicks')],
    [State('filter-store', 'data')],
    prevent_initial_call=True
)
def update_filters(nearest_clicks, below_est_clicks, inactive_clicks, updated_today_clicks, current_filters):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [
            {**BUTTON_STYLES['nearest'], "opacity": 0.6},
            {**BUTTON_STYLES['below_estimate'], "opacity": 0.6},
            {**BUTTON_STYLES['inactive'], "opacity": 0.6},
            {**BUTTON_STYLES['updated_today'], "opacity": 0.6},
            current_filters
        ]
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    filter_map = {'btn-nearest': 'nearest', 'btn-below-estimate': 'below_estimate', 
                 'btn-inactive': 'inactive', 'btn-updated-today': 'updated_today'}
    
    if button_id in filter_map:
        current_filters[filter_map[button_id]] = not current_filters[filter_map[button_id]]
    
    # Create button styles
    styles = []
    for key in ['nearest', 'below_estimate', 'inactive', 'updated_today']:
        if current_filters[key]:
            styles.append({**BUTTON_STYLES[key], "opacity": 1.0, "boxShadow": '0 0 5px #4682B4'})
        else:
            styles.append({**BUTTON_STYLES[key], "opacity": 0.6})
    
    return *styles, current_filters

# Combined callback for updating table and time
@callback(
    [Output("table-container", "children"),
     Output("last-update-time", "children")],
    [Input("filter-store", "data"),
     Input("interval-component", "n_intervals")]
)
def update_table_and_time(filters, _):
    df, update_time = load_and_process_data()
    df = filter_and_sort_data(df, filters)
    
    # Define column properties 
    visible = CONFIG["columns"]["visible"]
    numeric_cols = {"distance", "price_value_formatted", "cian_estimation_formatted", "price_difference_formatted", "monthly_burden_formatted"}
    markdown_cols = {"price_change_formatted", "title", "address", "offer_link"}
    
    columns = [{"name": CONFIG["columns"]["headers"].get(c, c), "id": c, 
                "type": "numeric" if c in numeric_cols else "text", 
                "presentation": "markdown" if c in markdown_cols else None} for c in visible]
    
    # Create the table
    table = dash_table.DataTable(
        id="apartment-table", 
        columns=columns,
        data=df[CONFIG["columns"]["display"]].to_dict("records") if not df.empty else [],
        sort_action="custom", 
        sort_mode="multi", 
        sort_by=[], 
        hidden_columns=CONFIG["hidden_cols"],
        style_table=STYLE["table"], 
        style_cell=STYLE["cell"],
        style_cell_conditional=[{"if": {"column_id": c["id"]}, "width": "auto"} for c in columns],
        style_header=STYLE["header_cell"], 
        style_header_conditional=HEADER_STYLES,
        style_data=STYLE["data"], 
        style_filter=STYLE["filter"], 
        style_data_conditional=COLUMN_STYLES,
        page_size=100, 
        page_action="native", 
        markdown_options={"html": True}
    )
    
    return table, f"Актуально на: {update_time}"

# Callback for sorting
@callback(
    Output("apartment-table", "data"), 
    [Input("apartment-table", "sort_by"),
     Input("filter-store", "data")]
)
def update_sort(sort_by, filters):
    df, _ = load_and_process_data()
    df = filter_and_sort_data(df, filters, sort_by)
    return df[CONFIG["columns"]["display"]].to_dict("records") if not df.empty else []


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))