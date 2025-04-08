import os
import numpy as np
import pandas as pd
import dash
from dash import dcc, html, dash_table, callback
from dash.dependencies import Input, Output, State

# Configuration
CONFIG = {
    "columns": {
        "display": [
            "offer_id", "title", "updated_time", "updated_time_sort", "price", "price_sort",
            "cian_estimation", "cian_estimation_sort", "price_difference", "price_difference_sort",
            "calculated_price_diff", "address", "metro_station", "offer_link", "distance", "days_active",
            "distance_sort", "price_change_value", "price_change_formatted", "status",
            "unpublished_date", "unpublished_date_sort", "cian_estimation_value", "price_difference_value"
        ],
        "visible": [
            "address", "distance", "price", "cian_estimation", "updated_time", "price_change_formatted",
            "title", "metro_station", "unpublished_date"
        ],
        "headers": {
            "offer_id": "ID", "distance": "Расст.", "price_change_formatted": "Изм.",
            "title": "Описание", "updated_time": "Обновлено", "price": "Цена", "cian_estimation": "Оценка",
            "price_difference": "Разница", "address": "Адрес", "metro_station": "Метро", "offer_link": "Ссылка",
            "status": "Статус", "unpublished_date": "Снято"
        },
        "sort_map": {
            "updated_time": "updated_time_sort", "price": "price_sort",
            "price_change_formatted": "price_change_sort", "cian_estimation": "cian_estimation_sort",
            "price_difference": "price_difference_sort"
        },
    },
    "months": {i: m for i, m in enumerate(["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"], 1)},
    "base_url": "https://www.cian.ru/rent/flat/",
    "hidden_cols": [
        "price_sort", "distance_sort", "updated_time_sort", "cian_estimation_sort",
        "price_difference_sort", "unpublished_date_sort"
    ],
}

# Unified styles
FONT = "Arial,sans-serif"
STYLE = {
    "container": {"fontFamily": FONT, "padding": "5px", "maxWidth": "100%"},
    "header": {"fontFamily": FONT, "textAlign": "center", "fontSize": "10px", "borderBottom": "1px solid #ddd"},
    "update_time": {"fontFamily": FONT, "fontStyle": "italic", "fontSize": "10px"},
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
    "margin": "0 5px 5px 0",  # Added bottom margin and reduced right margin
    "cursor": "pointer"
}

BUTTON_STYLES = {
    'nearest': {"backgroundColor": "#d9edf7", **STYLE["button_base"]},
    'below_estimate': {"backgroundColor": "#fef3d5", **STYLE["button_base"]},
    'inactive': {"backgroundColor": "#f4f4f4", **STYLE["button_base"]},
    'updated_today': {"backgroundColor": "#dff0d8", **STYLE["button_base"]}  # Green background instead of just bold
}

COLUMN_STYLES = [
    {"if": {"filter_query": '{status} contains "non active"'}, "backgroundColor": "#f4f4f4", "color": "#888"},
    {"if": {"filter_query": '{distance_sort} < 1.5 && {status} ne "non active"'}, "backgroundColor": "#d9edf7"},
    {"if": {"filter_query": '{calculated_price_diff} < -5000 && {status} ne "non active"'}, "backgroundColor": "#fef3d5"},
    {"if": {"filter_query": '{updated_time_sort} > "' + (pd.Timestamp.now() - pd.Timedelta(hours=24)).isoformat() + '"'}, 
     "backgroundColor": "#e6f3e0", "fontWeight": "normal"},  # Clear green background for today's updates
    {"if": {"column_id": "price_change_formatted"}, "textAlign": "center"},
    {"if": {"column_id": "price"}, "fontWeight": "bold", "textAlign": "center"},
    {"if": {"column_id": "address"}, "textAlign": "left"},
    {"if": {"column_id": "title"}, "textAlign": "left"},
]

HEADER_STYLES = [
    {"if": {"column_id": col}, "textAlign": "center"} 
    for col in ["distance", "updated_time", "unpublished_date", "price", "cian_estimation", 
               "price_change_formatted", "metro_station", "status"]
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
    """Format price changes with HTML styling"""
    if value == "new":
        return "<div style='text-align:center;'><span>—</span></div>"  # Changed 'new' to '—'
    
    try:
        value = int(pd.to_numeric(value, errors='coerce').fillna(0))
    except:
        value = 0
    
    if value == 0:
        return "<div style='text-align:center;'><span>—</span></div>"
    
    color = 'green' if value < 0 else 'red'
    arrow = '↓' if value < 0 else '↑'
    display = f"{abs(value)//1000}K" if abs(value) >= 1000 else str(abs(value))
    
    return f"<div style='text-align:center;'><span style='color:{color};'>{arrow}{display}</span></div>"

def format_price(value):
    """Format price value"""
    if value == 0:
        return "--"
    return f"{'{:,}'.format(int(value)).replace(',', ' ')} ₽/мес."

def format_date(dt):
    """Format datetime with Russian month names"""
    return f"{dt.day} {CONFIG['months'][dt.month]}, {dt.hour:02}:{dt.minute:02}"

def load_and_process_data():
    """Load and process data in a single function"""
    try:
        path = "cian_apartments.csv"
        df = pd.read_csv(path, encoding="utf-8", comment="#")
        
        # Extract update time from file
        with open(path, encoding="utf-8") as f:
            first_line = f.readline()
            update_time = first_line.split("last_updated=")[1].split(",")[0].strip() if "last_updated=" in first_line else "Unknown"
        
        # Process all columns in one pass
        df["offer_id"] = df["offer_id"].astype(str)
        df["address"] = df.apply(lambda r: f"[{r['address']}]({CONFIG['base_url']}{r['offer_id']}/)", axis=1)
        df["offer_link"] = df["offer_id"].apply(lambda x: f"[View]({CONFIG['base_url']}{x}/)")
        
        # Process numeric fields
        df["distance_sort"] = pd.to_numeric(df["distance"], errors="coerce")
        df["distance"] = df["distance_sort"].apply(lambda x: f"{x:.2f} km" if pd.notnull(x) else "")
        
        # Price fields
        df["price_sort"] = pd.to_numeric(df["price"].str.extract(r"(\d+[\s\d]*)")[0].str.replace(" ", ""), errors="coerce")
        df["price_change_sort"] = pd.to_numeric(df["price_change_value"], errors="coerce").fillna(0).astype(int)
        df["price_change_formatted"] = df["price_change_value"].apply(format_price_changes)
        
        # Estimation fields
        df["cian_estimation_sort"] = pd.to_numeric(df["cian_estimation_value"], errors="coerce")
        df["cian_estimation"] = df["cian_estimation_sort"].apply(lambda x: format_text(x, format_price, "--"))
        
        df["price_difference_sort"] = pd.to_numeric(df["price_difference_value"], errors="coerce")
        df["price_difference"] = df["price_difference_sort"].apply(lambda x: format_text(x, format_price, ""))
        
        # Calculate price difference for highlighting
        df["calculated_price_diff"] = df["price_sort"] - df["cian_estimation_sort"]
        
        # Process date-time fields
        df["updated_time_sort"] = pd.to_datetime(df["updated_time"], errors="coerce")
        df["updated_time"] = df["updated_time_sort"].apply(lambda x: format_text(x, format_date, ""))
        
        df["unpublished_date_sort"] = pd.to_datetime(df["unpublished_date"], errors="coerce")
        df["unpublished_date"] = df["unpublished_date_sort"].apply(lambda x: format_text(x, format_date, "--"))
        
        # Other processing
        df["days_active"] = pd.to_numeric(df["days_active"], errors="coerce").fillna(0).astype(int)
        
        # Default sorting
        df['sort_key'] = df['status'].apply(lambda x: 1 if x == 'active' else 2)
        df = df.sort_values(['sort_key', 'updated_time_sort'], ascending=[True, False]).drop(columns='sort_key')
        
        return df, update_time
    except Exception as e:
        return pd.DataFrame(), f"Error: {e}"

def filter_and_sort_data(df, price_thresh=None, dist_thresh=None, filters=None, sort_by=None):
    """Filter and sort data in a single function"""
    if df.empty:
        return df
        
    # Apply thresholds
    if price_thresh:
        df = df[df["price_sort"] <= price_thresh]
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
    numeric_cols = {"distance", "days_active", "price", "cian_estimation", "price_difference"}
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
    
    return table, f"Last updated: {update_time}"

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