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

# Configuration - Adjusted for new column structure
# Update CONFIG to include new columns
CONFIG = {
    "columns": {
        "display": [
            "offer_id", "title", "updated_time", "updated_time_sort", 
            "price", "price_value", "cian_estimation", "price_difference",
            "address", "metro_station", "offer_link", "distance", "distance_sort",
            "price_change_formatted", "status", "unpublished_date", "unpublished_date_sort",
            "calculated_price_diff", "rental_period_abbr", "utilities_type_abbr", 
            "commission_info_abbr", "deposit_info_abbr", "monthly_burden", "monthly_burden_formatted"
        ],
        "visible": [
            "address", "distance", "price", 
            "commission_info_abbr", "deposit_info_abbr", 
            #"monthly_burden_formatted", 
            "cian_estimation",  
            "updated_time", "price_change_formatted", "title", "metro_station", 
            #"rental_period_abbr", "utilities_type_abbr", 
            "unpublished_date"
        ],
        "headers": {
            "offer_id": "ID", "distance": "Расст.", "price_change_formatted": "Изм.",
            "title": "Описание", "updated_time": "Обновлено", "price": "Цена", "cian_estimation": "Оценка",
            "price_difference": "Разница", "address": "Адрес", "metro_station": "Метро", "offer_link": "Ссылка",
            "status": "Статус", "unpublished_date": "Снято",
            "rental_period_abbr": "Срок", "utilities_type_abbr": "ЖКХ", 
            "commission_info_abbr": "Коммис", "deposit_info_abbr": "Залог",
            "monthly_burden_formatted": "Нагрузка/мес"
        },
        "sort_map": {
            "updated_time": "updated_time_sort", "price": "price_value",
            "price_change_formatted": "price_change_value", "cian_estimation": "cian_estimation_value",
            "price_difference": "price_difference_value", "distance": "distance_sort",
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

BUTTON_STYLES = {
    'nearest': {"backgroundColor": "#d9edf7", **STYLE["button_base"]},
    'below_estimate': {"backgroundColor": "#fef3d5", **STYLE["button_base"]},
    'inactive': {"backgroundColor": "#f4f4f4", **STYLE["button_base"]},
    'updated_today': {"backgroundColor": "#dff0d8", **STYLE["button_base"]}
}

COLUMN_STYLES = [
    {"if": {"filter_query": '{status} contains "non active"'}, "backgroundColor": "#f4f4f4", "color": "#888"},
    {"if": {"filter_query": '{distance_sort} < 1.5 && {status} ne "non active"'}, "backgroundColor": "#d9edf7"},
    {"if": {"filter_query": '{calculated_price_diff} < -5000 && {status} ne "non active"'}, "backgroundColor": "#fef3d5"},
    {"if": {"filter_query": '{updated_time_sort} > "' + (pd.Timestamp.now() - pd.Timedelta(hours=24)).isoformat() + '"'}, 
     "backgroundColor": "#e6f3e0", "fontWeight": "normal"},
    {"if": {"column_id": "price_change_formatted"}, "textAlign": "center"},
    {"if": {"column_id": "updated_time"}, "fontWeight": "bold", "textAlign": "center"},
    {"if": {"column_id": "price"}, "fontWeight": "bold", "textAlign": "center"},
    {"if": {"column_id": "monthly_burden_formatted"}, "fontWeight": "bold", "textAlign": "center"},
    {"if": {"column_id": "address"}, "textAlign": "left"},
    {"if": {"column_id": "title"}, "textAlign": "left"},
]

HEADER_STYLES = [
    {"if": {"column_id": col}, "textAlign": "center"} 
    for col in ["distance", "updated_time", "unpublished_date", "price", "cian_estimation", 
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

def format_date(dt):
    """Format datetime with Russian month names"""
    return f"{dt.day} {CONFIG['months'][dt.month]}, {dt.hour:02}:{dt.minute:02}"

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
        df["price"] = df["price_value"].apply(lambda x: format_text(x, format_price, "--"))
        df["cian_estimation"] = df["cian_estimation_value"].apply(lambda x: format_text(x, format_price, "--"))
        df["price_difference"] = df["price_difference_value"].apply(lambda x: format_text(x, format_price, ""))
        
        # Handle price change specifically - ensure the column exists
        if "price_change_value" in df.columns:
            # Ensure it's numeric when possible
            df["price_change_value"] = pd.to_numeric(df["price_change_value"], errors="coerce").fillna(0)
            df["price_change_formatted"] = df["price_change_value"].apply(format_price_changes)
        else:
            # Create an empty column if missing
            df["price_change_value"] = 0
            df["price_change_formatted"] = df["price_change_value"].apply(format_price_changes)
        
        # Calculate price difference for highlighting
        df["calculated_price_diff"] = df["price_value"] - df["cian_estimation_value"]
        
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
        df["deposit_info_abbr"] = df.apply(lambda row: "0%" if pd.notnull(row["deposit_value"]) and row["deposit_value"] == 0 
                                           else f"{int((row['deposit_value']/row['price_value'])*100)}%" 
                                           if pd.notnull(row["deposit_value"]) and pd.notnull(row["price_value"]) and row["price_value"] > 0 
                                           else "--", axis=1)

        # Make sure price_value is numeric
        if 'price_value' not in df.columns:
            print("WARNING: price_value column missing - attempting to create from price")
            # Try to create price_value from price if it exists
            if 'price' in df.columns:
                df['price_value'] = df['price'].str.replace('[^\d]', '', regex=True).astype(float)
            else:
                df['price_value'] = None

        # Ensure commission_value is numeric
        if 'commission_value' not in df.columns:
            print("WARNING: commission_value column missing - creating from commission_info")
            df['commission_value'] = df['commission_info'].apply(
                lambda x: 0 if pd.isna(x) or 'без комиссии' in str(x) 
                else float(re.search(r'(\d+)%', str(x)).group(1)) if re.search(r'(\d+)%', str(x)) 
                else None
            )
        
        # Print column info for debugging
        print("\nCOLUMN STATUS FOR BURDEN CALCULATION:")
        for col in ['price_value', 'commission_value', 'deposit_value']:
            if col in df.columns:
                non_null = df[col].notnull().sum()
                total = len(df)
                print(f"{col}: {non_null}/{total} non-null values, dtype: {df[col].dtype}")
            else:
                print(f"{col}: MISSING")
        
        # Calculate monthly burden
        df['monthly_burden'] = df.apply(calculate_monthly_burden, axis=1)
        
        # Print stats about the calculation result
        non_null_burden = df['monthly_burden'].notnull().sum()
        print(f"\nMonthly burden calculated for {non_null_burden}/{len(df)} rows")
        if non_null_burden > 0:
            print(f"Sample values: {df['monthly_burden'].dropna().head(3).tolist()}")
        
        # Format the monthly burden AFTER calculating it
        df['monthly_burden_formatted'] = df.apply(format_burden, axis=1)
        
        # Print sample of formatted values
        print("\nSample formatted burden values:")
        sample_formatted = df['monthly_burden_formatted'].head(5).tolist()
        print(sample_formatted)
        
        # Default sorting
        df['sort_key'] = df['status'].apply(lambda x: 1 if x == 'active' else 2)
        df = df.sort_values(['sort_key', 'updated_time_sort'], ascending=[True, False]).drop(columns='sort_key')
        
        return df, update_time
    except Exception as e:
        import traceback
        print(f"Error in load_and_process_data: {e}")
        print(traceback.format_exc())
        return pd.DataFrame(), f"Error: {e}"



def filter_and_sort_data(df, price_thresh=None, dist_thresh=None, filters=None, sort_by=None):
    """Filter and sort data in a single function"""
    if df.empty:
        return df
        
    # Apply thresholds
    if price_thresh:
        df = df[df["price_value"] <= price_thresh]
    if dist_thresh:
        df = df[df["distance_sort"] <= dist_thresh]
    
    # Apply button filters
    if filters and any(filters.values()):
        mask = pd.Series(False, index=df.index)
        
        if filters.get('nearest'):
            mask |= (df["distance_sort"] < 1.5)
        if filters.get('below_estimate'):
            mask |= (df["calculated_price_diff"] < -5000)
        if filters.get('inactive'):
            mask |= (df["status"] == "non active")
        if filters.get('updated_today'):
            mask |= (df["updated_time_sort"] > (pd.Timestamp.now() - pd.Timedelta(hours=24)))
        
        df = df[mask]
    
    # Apply sorting
    if sort_by:
        for item in sort_by:
            col = CONFIG["columns"]["sort_map"].get(item["column_id"], item["column_id"])
            df = df.sort_values(col, ascending=item["direction"] == "asc")
    
    return df

# Initialize the app
app = dash.Dash(__name__, title="", meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}], suppress_callback_exceptions=True)
server = app.server

# App layout
app.layout = html.Div([
    html.H2("", style=STYLE["header"]),
    html.Div(html.Span(id="last-update-time", style=STYLE["update_time"])),
    dcc.Interval(id="interval-component", interval=2 * 60 * 1000, n_intervals=0),
    
    # Filter store
    dcc.Store(id='filter-store', data={
        'nearest': False, 'below_estimate': False, 'inactive': False, 'updated_today': False
    }),
    
    # Container for both inputs and buttons
    html.Div([
        # Input filters - with specific width
        html.Div([
            html.Label('Макс. цена (₽):', className="dash-label"),
            dcc.Input(id="price-threshold", type="number", value=80000, step=5000, min=10000, max=500000, style=STYLE["input_number"]),
            html.Label('Макс. расстояние (км):', className="dash-label"),
            dcc.Input(id="distance-threshold", type="number", value=3, step=0.5, min=0.5, max=10, style=STYLE["input_number"]),
        ], style={"margin": "5px", "textAlign": "left", "width": "100%", "maxWidth": "600px"}),
        
        # Button filters - with matching width to input row
        html.Div([
            html.Button("Ближайшие", id="btn-nearest", style={**BUTTON_STYLES['nearest'], "opacity": "0.6"}),
            html.Button("Цена ниже оценки", id="btn-below-estimate", style={**BUTTON_STYLES['below_estimate'], "opacity": "0.6"}),
            html.Button("Сегодня", id="btn-updated-today", style={**BUTTON_STYLES['updated_today'], "opacity": "0.6"}),
            html.Button("Неактивные", id="btn-inactive", style={**BUTTON_STYLES['inactive'], "opacity": "0.6"}),
        ], style={"margin": "5px", "marginTop": "8px", "textAlign": "left", "width": "100%", "maxWidth": "600px"}),
    ], style={"margin": "5px", "textAlign": "left", "width": "100%"}),
    
    # Table container
    dcc.Loading(id="loading-main", children=[html.Div(id="table-container")], style={"margin": "5px"}),
], style=STYLE["container"])

# Callback to handle filter button clicks
@callback(
    Output('filter-store', 'data'),
    [Input('btn-nearest', 'n_clicks'),
     Input('btn-below-estimate', 'n_clicks'),
     Input('btn-inactive', 'n_clicks'),
     Input('btn-updated-today', 'n_clicks')],
    [State('filter-store', 'data')]
)
def update_filters(nearest_clicks, below_est_clicks, inactive_clicks, updated_today_clicks, current_filters):
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_filters
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    filter_map = {'btn-nearest': 'nearest', 'btn-below-estimate': 'below_estimate', 
                 'btn-inactive': 'inactive', 'btn-updated-today': 'updated_today'}
    
    if button_id in filter_map:
        current_filters[filter_map[button_id]] = not current_filters[filter_map[button_id]]
    
    return current_filters

# Callback to update button styles
@callback(
    [Output('btn-nearest', 'style'),
     Output('btn-below-estimate', 'style'),
     Output('btn-inactive', 'style'),
     Output('btn-updated-today', 'style')],
    [Input('filter-store', 'data')]
)
def update_button_styles(filters):
    return [{**BUTTON_STYLES[key], 
             "opacity": 1.0 if filters[key] else 0.6,
             "boxShadow": '0 0 5px #4682B4' if filters[key] else 'none'} 
            for key in ['nearest', 'below_estimate', 'inactive', 'updated_today']]

# Combined callback for updating table and time
@callback(
    [Output("table-container", "children"),
     Output("last-update-time", "children")],
    [Input("price-threshold", "value"), 
     Input("distance-threshold", "value"),
     Input("filter-store", "data"),
     Input("interval-component", "n_intervals")]
)
def update_table_and_time(price_threshold, distance_threshold, filters, _):
    df, update_time = load_and_process_data()
    df = filter_and_sort_data(df, price_threshold, distance_threshold, filters)
    
    # Define column properties 
    visible = CONFIG["columns"]["visible"]
    numeric_cols = {"distance", "price", "cian_estimation", "price_difference", "monthly_burden_formatted"}
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
    
    return table, f"{update_time}"

# Callback for sorting
@callback(
    Output("apartment-table", "data"), 
    [Input("apartment-table", "sort_by"), 
     Input("price-threshold", "value"), 
     Input("distance-threshold", "value"),
     Input("filter-store", "data")]
)
def update_sort(sort_by, price_threshold, distance_threshold, filters):
    df, _ = load_and_process_data()
    df = filter_and_sort_data(df, price_threshold, distance_threshold, filters, sort_by)
    return df[CONFIG["columns"]["display"]].to_dict("records") if not df.empty else []


if __name__ == "__main__":
    
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))