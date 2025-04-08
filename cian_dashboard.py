import os, logging, numpy as np, pandas as pd
import dash
from dash import dcc, html, dash_table, callback
from dash.dependencies import Input, Output, State

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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

# Styles
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
    "input": {"marginRight": "5px", "width": "110px"},
    "input_number": {"width": "110px"},
    "label": {"fontSize": "11px", "marginRight": "3px", "display": "block"},
}

COLUMN_STYLES = [
    {"if": {"filter_query": '{status} contains "non active"'}, "backgroundColor": "#f4f4f4", "color": "#888"},
    {"if": {"filter_query": '{distance_sort} < 1.5 && {status} ne "non active"'}, "backgroundColor": "#d9edf7"},
    {"if": {"filter_query": '{calculated_price_diff} < -5000 && {status} ne "non active"'}, "backgroundColor": "#fef3d5"},
    {"if": {"filter_query": '{price_difference_sort} < -1000 && {status} ne "non active"'}, "backgroundColor": "#fdf0cc"},
    {"if": {"filter_query": '{updated_time_sort} > "' + (pd.Timestamp.now() - pd.Timedelta(hours=24)).isoformat() + '"'}, "fontWeight": "bold"},
    {"if": {"column_id": "price_change_formatted"}, "textAlign": "center"},
    {"if": {"column_id": "price"}, "fontWeight": "bold"},
    {"if": {"column_id": "address"}, "textAlign": "left"},
    {"if": {"column_id": "title"}, "textAlign": "left"},
]

HEADER_STYLES = [
    {"if": {"column_id": "distance"}, "textAlign": "center"},
    {"if": {"column_id": "updated_time"}, "textAlign": "center"},
    {"if": {"column_id": "unpublished_date"}, "textAlign": "center"},
    {"if": {"column_id": "price"}, "textAlign": "center"},
    {"if": {"column_id": "cian_estimation"}, "textAlign": "center"},
    {"if": {"column_id": "price_change_formatted"}, "textAlign": "center"},
    {"if": {"column_id": "metro_station"}, "textAlign": "center"},
    {"if": {"column_id": "status"}, "textAlign": "center"},
    {"if": {"column_id": "address"}, "textAlign": "left"},
    {"if": {"column_id": "title"}, "textAlign": "left"},
]


def load_data():
    try:
        path = "cian_apartments.csv"
        df = pd.read_csv(path, encoding="utf-8", comment="#")
        with open(path, encoding="utf-8") as f:
            first_line = f.readline()
            update_time = first_line.split("last_updated=")[1].split(",")[0].strip() if "last_updated=" in first_line else "Unknown"

        df["offer_id"] = df.get("offer_id", "").astype(str)
        df["address"] = df.apply(lambda r: f"[{r['address']}]({CONFIG['base_url']}{r['offer_id']}/)" if "address" in r else "", axis=1)
        df["offer_link"] = df["offer_id"].apply(lambda x: f"[View]({CONFIG['base_url']}{x}/)")
        df["distance_sort"] = pd.to_numeric(df.get("distance"), errors="coerce")
        df["distance"] = df["distance_sort"].apply(lambda x: f"{x:.2f} km" if pd.notnull(x) else "")

        df["price_change_sort"] = pd.to_numeric(df.get("price_change_value", 0), errors="coerce").fillna(0).astype(int)
        df["price_change_formatted"] = df.get("price_change_value", 0).apply(format_price_changes)

        # Process price column - it's still a formatted string in input data
        df["price_sort"] = pd.to_numeric(df["price"].astype(str).str.extract(r"(\d+[\s\d]*)")[0].str.replace(" ", ""), errors="coerce")
        
        # Process cian_estimation from cian_estimation_value
        df["cian_estimation_sort"] = pd.to_numeric(df.get("cian_estimation_value"), errors="coerce")
        df["cian_estimation"] = df["cian_estimation_sort"].apply(lambda x: format_price(x) if pd.notnull(x) else "--")
        
        # Process price_difference from price_difference_value
        df["price_difference_sort"] = pd.to_numeric(df.get("price_difference_value"), errors="coerce")
        df["price_difference"] = df["price_difference_sort"].apply(lambda x: format_price(x) if pd.notnull(x) else "")

        # Calculate price difference for color highlighting
        df["calculated_price_diff"] = df["price_sort"] - df["cian_estimation_sort"]
        
        # Process timestamps
        df["updated_time_sort"] = pd.to_datetime(df["updated_time"], errors="coerce")
        df["updated_time"] = df["updated_time_sort"].apply(lambda x: f"{x.day} {CONFIG['months'][x.month]}, {x.hour:02}:{x.minute:02}" if pd.notnull(x) else "")
        df["unpublished_date_sort"] = pd.to_datetime(df.get("unpublished_date"), errors="coerce")
        df["unpublished_date"] = df["unpublished_date_sort"].apply(lambda x: f"{x.day} {CONFIG['months'][x.month]}, {x.hour:02}:{x.minute:02}" if pd.notnull(x) else "--")

        df["days_active"] = pd.to_numeric(df.get("days_active"), errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0).astype(int)

        return df.sort_values("updated_time_sort", ascending=False), update_time
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.DataFrame(), f"Error: {e}"

def format_price_changes(price_change_value):
    """Format price changes in a human-readable format with HTML styling"""
    # Handle "new" special case
    if price_change_value == "new":
        return "<div style='text-align:center;'><span>new</span></div>"
    
    # Convert to integer and handle NaN/None values
    try:
        value = pd.to_numeric(price_change_value, errors='coerce')
        if pd.isna(value):
            value = 0
        value = int(value)
    except (ValueError, TypeError):
        value = 0
    
    # Format the value with HTML
    if value == 0:
        return "<div style='text-align:center;'><span>—</span></div>"
    elif abs(value) >= 1000:
        return f"<div style='text-align:center;'><span style='color:{'green' if value < 0 else 'red'};'>{'↓' if value < 0 else '↑'}{abs(value)//1000}K</span></div>"
    else:
        return f"<div style='text-align:center;'><span style='color:{'green' if value < 0 else 'red'};'>{'↓' if value < 0 else '↑'}{abs(value)}</span></div>"

def format_price(value):
    """Format price value to human-readable string"""
    if value is None:
        return ""
    return f"{'{:,}'.format(int(value)).replace(',', ' ')} ₽/мес."


# Modified filter_dataframe function to apply button filters
def filter_dataframe(df, price_thresh=None, dist_thresh=None, filters=None):
    if filters is None:
        filters = {'nearest': False, 'below_estimate': False, 'inactive': False, 'updated_today': False}
    
    # Apply price and distance thresholds
    if price_thresh: 
        df = df[df["price_sort"] <= price_thresh]
    if dist_thresh: 
        df = df[df["distance_sort"] <= dist_thresh]
    
    # Apply button filters if any are active
    if any(filters.values()):
        mask = pd.Series(False, index=df.index)
        
        if filters['nearest']:
            mask = mask | (df["distance_sort"] < 1.5)
        
        if filters['below_estimate']:
            mask = mask | (df["calculated_price_diff"] < -5000)
        
        if filters['inactive']:
            mask = mask | (df["status"] == "non active")
        
        if filters['updated_today']:
            today = pd.Timestamp.now() - pd.Timedelta(hours=24)
            mask = mask | (df["updated_time_sort"] > today)
        
        df = df[mask]
    
    return df

def sort_table_data(sort_by, price_thresh=None, dist_thresh=None, filters=None):
    df, _ = load_data()
    df = filter_dataframe(df, price_thresh, dist_thresh, filters)
    for item in sort_by or []:
        col = CONFIG["columns"]["sort_map"].get(item["column_id"], item["column_id"])
        df = df.sort_values(col, ascending=item["direction"] == "asc")
    return df[[c for c in CONFIG["columns"]["display"] if c in df]].to_dict("records")

app = dash.Dash(__name__, title="Cian Listings", meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}], suppress_callback_exceptions=True)
server = app.server

# Modified app layout with button filters and Store
app.layout = html.Div([
    html.H2("Cian Listings", style=STYLE["header"]),
    html.Div(html.Span(id="last-update-time", style=STYLE["update_time"])),
    dcc.Interval(id="interval-component", interval=2 * 60 * 1000, n_intervals=0),
    
    # Add store to maintain filter states
    dcc.Store(id='filter-store', data={
        'nearest': False,      # Ближайшие
        'below_estimate': False, # Цена ниже оценки
        'inactive': False,     # Неактивные
        'updated_today': False # Обновлено сегодня
    }),
    
    html.Div([
        html.Div([
            html.Label('Макс. цена (₽):', className="dash-label"),
            dcc.Input(id="price-threshold", type="number", value=80000, step=5000, min=10000, max=500000, style=STYLE["input_number"]),
            html.Label('Макс. расстояние (км):', className="dash-label"),
            dcc.Input(id="distance-threshold", type="number", value=3, step=0.5, min=0.5, max=10, style=STYLE["input_number"]),
        ], style={"display": "inline-block", "marginRight": "15px"}),
        
        # Replace divs with buttons
        html.Div([
            html.Button("Ближайшие", id="btn-nearest", 
                       style={"display": "inline-block", "backgroundColor": "#d9edf7", "padding": "3px 8px", 
                              "fontSize": "10px", "border": "1px solid #ccc", "margin": "0 5px", 
                              "cursor": "pointer", "opacity": "0.6"}),
            html.Button("Цена ниже оценки", id="btn-below-estimate", 
                       style={"display": "inline-block", "backgroundColor": "#fef3d5", "padding": "3px 8px", 
                              "fontSize": "10px", "border": "1px solid #ccc", "margin": "0 5px", 
                              "cursor": "pointer", "opacity": "0.6"}),
            html.Button("Неактивные", id="btn-inactive", 
                       style={"display": "inline-block", "backgroundColor": "#f4f4f4", "padding": "3px 8px", 
                              "fontSize": "10px", "border": "1px solid #ccc", "margin": "0 5px", 
                              "cursor": "pointer", "opacity": "0.6"}),
            html.Button("Обновлено сегодня", id="btn-updated-today", 
                       style={"display": "inline-block", "fontWeight": "bold", "padding": "3px 8px", 
                              "fontSize": "10px", "border": "1px solid #ccc", "margin": "0 5px", 
                              "cursor": "pointer", "opacity": "0.6"})
        ], style={"display": "inline-block"})
    ], style={"margin": "5px", "whiteSpace": "nowrap", "overflow": "auto"}),
    dcc.Loading(id="loading-main", children=[html.Div(id="table-container")], style={"margin": "5px"}),
], style=STYLE["container"])

# Add callback to handle filter button clicks
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
    
    if button_id == 'btn-nearest':
        current_filters['nearest'] = not current_filters['nearest']
    elif button_id == 'btn-below-estimate':
        current_filters['below_estimate'] = not current_filters['below_estimate']
    elif button_id == 'btn-inactive':
        current_filters['inactive'] = not current_filters['inactive']
    elif button_id == 'btn-updated-today':
        current_filters['updated_today'] = not current_filters['updated_today']
    
    return current_filters

# Add callback to update button styles based on filter states
@callback(
    [Output('btn-nearest', 'style'),
     Output('btn-below-estimate', 'style'),
     Output('btn-inactive', 'style'),
     Output('btn-updated-today', 'style')],
    [Input('filter-store', 'data')]
)
def update_button_styles(filters):
    # Base styles for buttons
    base_styles = {
        'nearest': {"display": "inline-block", "backgroundColor": "#d9edf7", "padding": "3px 8px", 
                   "fontSize": "10px", "border": "1px solid #ccc", "margin": "0 5px", "cursor": "pointer"},
        'below_estimate': {"display": "inline-block", "backgroundColor": "#fef3d5", "padding": "3px 8px", 
                          "fontSize": "10px", "border": "1px solid #ccc", "margin": "0 5px", "cursor": "pointer"},
        'inactive': {"display": "inline-block", "backgroundColor": "#f4f4f4", "padding": "3px 8px", 
                    "fontSize": "10px", "border": "1px solid #ccc", "margin": "0 5px", "cursor": "pointer"},
        'updated_today': {"display": "inline-block", "fontWeight": "bold", "padding": "3px 8px", 
                         "fontSize": "10px", "border": "1px solid #ccc", "margin": "0 5px", "cursor": "pointer"}
    }
    
    # Modify styles based on active state
    nearest_style = base_styles['nearest'].copy()
    nearest_style['opacity'] = 1.0 if filters['nearest'] else 0.6
    nearest_style['boxShadow'] = '0 0 5px #4682B4' if filters['nearest'] else 'none'
    
    below_est_style = base_styles['below_estimate'].copy()
    below_est_style['opacity'] = 1.0 if filters['below_estimate'] else 0.6
    below_est_style['boxShadow'] = '0 0 5px #FFA500' if filters['below_estimate'] else 'none'
    
    inactive_style = base_styles['inactive'].copy()
    inactive_style['opacity'] = 1.0 if filters['inactive'] else 0.6
    inactive_style['boxShadow'] = '0 0 5px #888' if filters['inactive'] else 'none'
    
    updated_today_style = base_styles['updated_today'].copy()
    updated_today_style['opacity'] = 1.0 if filters['updated_today'] else 0.6
    updated_today_style['boxShadow'] = '0 0 5px #4682B4' if filters['updated_today'] else 'none'
    
    return nearest_style, below_est_style, inactive_style, updated_today_style

# Update the table update callback to include filter state
@callback(
    Output("table-container", "children"), 
    [Input("price-threshold", "value"), 
     Input("distance-threshold", "value"),
     Input("filter-store", "data")]
)
def update_table(price_threshold, distance_threshold, filters):
    df, _ = load_data()
    df = filter_dataframe(df, price_threshold, distance_threshold, filters)
    visible = [c for c in CONFIG["columns"]["visible"] if c in df]
    hidden = [c for c in CONFIG["hidden_cols"] if c in df]
    numeric = {"distance", "days_active", "price", "cian_estimation", "price_difference"}
    markdown = {"price_change_formatted", "title", "address", "offer_link"}
    columns = [{"name": CONFIG["columns"]["headers"].get(c, c), "id": c, 
                "type": "numeric" if c in numeric else "text", 
                "presentation": "markdown" if c in markdown else None} for c in visible]
    
    logger.info(f"Table updated: {len(df)} rows")
    return dash_table.DataTable(
        id="apartment-table", columns=columns,
        data=df[[c for c in CONFIG["columns"]["display"] if c in df]].to_dict("records"),
        sort_action="custom", sort_mode="multi", sort_by=[], hidden_columns=hidden,
        style_table=STYLE["table"], style_cell=STYLE["cell"],
        style_cell_conditional=[{"if": {"column_id": c["id"]}, "width": "auto"} for c in columns],
        style_header=STYLE["header_cell"], style_header_conditional=HEADER_STYLES,
        style_data=STYLE["data"], style_filter=STYLE["filter"], style_data_conditional=COLUMN_STYLES,
        page_size=100, page_action="native", markdown_options={"html": True})

# Update the sort callback to include filter state
@callback(
    Output("apartment-table", "data"), 
    [Input("apartment-table", "sort_by"), 
     Input("price-threshold", "value"), 
     Input("distance-threshold", "value"),
     Input("filter-store", "data")]
)
def update_sort(sort_by, price_threshold, distance_threshold, filters):
    return sort_table_data(sort_by, price_threshold, distance_threshold, filters)

@callback(
    Output("last-update-time", "children"), 
    Input("interval-component", "n_intervals")
)
def update_time(_):
    _, update_time = load_data()
    return f"Last updated: {update_time}"

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))