import dash
from dash import dcc, html, dash_table, callback
from dash.dependencies import Input, Output
import os
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Core configuration
COLUMNS_CONFIG = {
    "display": [
        "offer_id", "title", "updated_time", "updated_time_sort", "price", "price_sort",
        "cian_estimation", "cian_estimation_sort", "price_difference", "price_difference_sort",
        "address", "metro_station", "offer_link", "distance", "distance_sort", "price_change_value", 
        "price_change_formatted"
    ],
    "visible": [
       "address", "distance", "price", "cian_estimation", "updated_time", "price_change_formatted", "title",  "metro_station"
    ],
    "headers": {
        "offer_id": "ID", "distance": "расст.", "price_change_formatted": "изм. цены",
        "title": "описание", "updated_time": "обновл.", "days_active": "Days",
        "price": "тек. цена", "cian_estimation": "ЦИАН", "price_difference": "разн.",
        "address": "адрес", "metro_station": "метро", "offer_link": "Link"
    },
    "sort_map": {
        "updated_time": "updated_time_sort", "price": "price_sort",
        "cian_estimation": "cian_estimation_sort", "price_difference": "price_difference_sort"
    }
}

# Russian month mapping for date formatting
MONTHS = {
    1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
    7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек"
}

def load_data(cache=[]):
    """Load and process data from CSV with caching"""
    if cache:
        return cache[0], cache[1]
    
    try:
        csv_path = "cian_apartments.csv"
        df = pd.read_csv(csv_path, encoding="utf-8", comment="#")
        
        # Extract update time from CSV header comment
        with open(csv_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        
        update_time = "Unknown"
        for part in first_line.replace("# ", "").split(","):
            if part.startswith("last_updated="):
                update_time = part.split("=")[1].strip()
        
        # Process data columns
        
        # Process offer_id
        if "offer_id" in df.columns:
            df["offer_id"] = df["offer_id"].astype(str)
            
            # Create offer links
            if "address" in df.columns:
                df["address"] = df.apply(
                    lambda row: f"[{row['address']}](https://www.cian.ru/rent/flat/{row['offer_id']}/)", 
                    axis=1
                )
            
            if "offer_url" in df.columns:
                df["offer_link"] = df.apply(
                    lambda row: f"[View](https://www.cian.ru/rent/flat/{row['offer_id']}/)",
                    axis=1
                )
        
        # Process distance
        if "distance" in df.columns:
            df["distance_sort"] = pd.to_numeric(df["distance"], errors="coerce")
            df["distance"] = df["distance_sort"].apply(
                lambda x: f"{x:.2f} km" if pd.notnull(x) else ""
            )
        
        # Process price change
        if "price_change_value" in df.columns:
            df["price_change_sort"] = pd.to_numeric(df["price_change_value"], errors="coerce")
                
            # First update your format_price_change function to just show arrows
            def format_price_change(value):
                if pd.isna(value):
                    formatted = '--'
                    return f"<div style='text-align:center'><span style='color:black;'>{formatted}</span></div>"
                try:
                    value = float(value)
                    if value == 0:
                        return "<div style='text-align:center'>—</div>"
                    
                    # Format abbreviation for large numbers
                    abs_value = abs(value)
                    if abs_value >= 10000:
                        formatted = f"{abs_value/1000:.0f}K"
                    else:
                        formatted = f"{abs_value:.0f}"
                        
                    if value < 0:
                        return f"<div style='text-align:center'><span style='color:green;'>↓{formatted}</span></div>"
                    else:
                        return f"<div style='text-align:center'><span style='color:red;'>↑{formatted}</span></div>"
                except Exception as e:
                    logger.error(f"Price format error: {e}")
                    return "<div style='text-align:center'>—</div>"
            
                        
            df["price_change_formatted"] = df["price_change_sort"].apply(format_price_change)
        
        # Process price columns
        for col in ["price", "cian_estimation", "price_difference"]:
            if col in df.columns:
                df[f"{col}_sort"] = (
                    df[col].astype(str)
                    .str.extract(r"(\d+[\s\d]*)", expand=False)
                    .str.replace(" ", "")
                    .astype(float, errors="ignore")
                )
        
        # Process dates
        if "updated_time" in df.columns:
            df["updated_time_sort"] = pd.to_datetime(df["updated_time"], errors="coerce")
            df["updated_time"] = df["updated_time_sort"].apply(
                lambda x: f"{x.day} {MONTHS[x.month]}, {x.hour:02d}:{x.minute:02d}" 
                if pd.notnull(x) else ""
            )
        
        # Process days active
        if "days_active" in df.columns:
            df["days_active"] = pd.to_numeric(df["days_active"].fillna(0), errors="coerce").astype(int)
        
        # Sort by update time
        if "updated_time_sort" in df.columns:
            df = df.sort_values("updated_time_sort", ascending=False)
            
        cache.clear()
        cache.extend([df, update_time])
        return df, update_time
    
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.DataFrame(), f"Error: {e}"

def get_table_config(price_threshold=None, distance_threshold=None):
    """Generate DataTable configuration based on filters"""
    df, _ = load_data()
    
    # Apply filters
    if price_threshold is not None and "price_sort" in df.columns:
        df = df[df["price_sort"] <= price_threshold]
    
    if distance_threshold is not None and "distance_sort" in df.columns:
        df = df[df["distance_sort"] <= distance_threshold]
    
    # Filter available columns
    display_cols = [col for col in COLUMNS_CONFIG["display"] if col in df.columns]
    visible_cols = [col for col in COLUMNS_CONFIG["visible"] if col in df.columns]
    
    # Make sure sort columns are included in the data but hidden in display
    sort_cols = ["price_sort", "distance_sort", "updated_time_sort", 
                "cian_estimation_sort", "price_difference_sort"]
    hidden_cols = [col for col in sort_cols if col in df.columns]
    
    # Log for debugging
    if not df.empty:
        sample_row = df.iloc[0]
        logger.info(f"Sample row - Price: {sample_row.get('price', 'N/A')}, "
                  f"Price sort: {sample_row.get('price_sort', 'N/A')}, "
                  f"Distance: {sample_row.get('distance', 'N/A')}, "
                  f"Distance sort: {sample_row.get('distance_sort', 'N/A')}")
    # Отладочная информация
    if not df.empty:
        logger.info(f"Columns in the dataframe: {df.columns.tolist()}")
        logger.info(f"Sample distance_sort values: {df['distance_sort'].head(5).tolist() if 'distance_sort' in df.columns else 'Column not found!'}")
        # Проверим, какие строки должны быть выделены
        if 'distance_sort' in df.columns:
            highlighted_rows = df[df['distance_sort'] < 1.5].shape[0]
            logger.info(f"Number of rows with distance_sort < 1.5: {highlighted_rows}")
    


    
    # Generate column definitions
    columns = []
    for col in visible_cols:
        col_config = {
            "name": COLUMNS_CONFIG["headers"].get(col, col),
            "id": col,
            "type": "numeric" if col in ["distance", "days_active", "price", "cian_estimation", 
                                         "price_difference"] else "text"
        }
        
        # Add markdown presentation for certain columns
        if col in ["price_change_formatted", "title", "address", "offer_link"]:
            col_config["presentation"] = "markdown"
            
        columns.append(col_config)
    
    return columns, df[display_cols].to_dict("records"), display_cols, hidden_cols

def sort_table_data(sort_by, price_threshold=None, distance_threshold=None):
    """Sort table data based on user selection"""
    df, _ = load_data()
    
    # Apply filters
    if price_threshold is not None and "price_sort" in df.columns:
        df = df[df["price_sort"] <= price_threshold]
    
    if distance_threshold is not None and "distance_sort" in df.columns:
        df = df[df["distance_sort"] <= distance_threshold]
    
    display_cols = [col for col in COLUMNS_CONFIG["display"] if col in df.columns]
    
    # Default sorting
    if not sort_by or df.empty:
        if "updated_time_sort" in df.columns:
            df = df.sort_values("updated_time_sort", ascending=False)
        return df[display_cols].to_dict("records")
    
    # Apply custom sorting
    for sort_item in sort_by:
        col_id = sort_item["column_id"]
        ascending = sort_item["direction"] == "asc"
        sort_col = COLUMNS_CONFIG["sort_map"].get(col_id, col_id)
        df = df.sort_values(sort_col, ascending=ascending)
    
    return df[display_cols].to_dict("records")

# Initialize Dash app
app = dash.Dash(
    __name__,
    title="Cian Listings",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
)

server = app.server  # For deployment

# Define styling
styles = {
    "container": {
        "fontFamily": "Arial, sans-serif",
        "margin": "0",
        "padding": "5px",
        "maxWidth": "100%",
        "overflowX": "hidden",
    },
    "header": {
        "textAlign": "center",
        "margin": "3px 0",
        "padding": "3px",
        "fontSize": "10px",
        "fontFamily": "Arial, sans-serif",
        "borderBottom": "1px solid #ddd",
    },
    "update_time": {
        "fontStyle": "italic", 
        "fontSize": "10px", 
        "margin": "5px"
    },
    "filters": {
        "margin": "5px", 
        "display": "flex", 
        "alignItems": "center", 
        "gap": "10px"
    },
    "input": {
        "marginRight": "5px",
        "width": "50px",
        "fontSize": "10px"
    },
    "label": {
        "fontSize": "10px"
    },
    "table": {
        "overflowX": "auto"
    },
    "table_cell": {
        "textAlign": "center",
        "padding": "3px 4px",
        "minWidth": "50px",
        "width": "auto",
        "maxWidth": "200px",
        "overflow": "hidden",
        "textOverflow": "ellipsis",
        "fontSize": "9px",
        "fontFamily": "Arial, sans-serif",
    },
    "table_header": {
        "backgroundColor": "#4682B4",  # Steel blue - приглушенный синий
        "color": "white",
        "fontWeight": "normal",
        "textAlign": "left",
        "padding": "4px",
        "fontSize": "11px",
        "height": "18px",
        "borderBottom": "1px solid #ddd",
    },
    "table_data": {
        "height": "auto",
        "lineHeight": "14px",
        "whiteSpace": "normal",
    },
    "table_filter": {
        "fontSize": "1px",
        "padding": "1px",
        "height": "2px",
        "display": "none",
    }
}

column_styles = [
    # Более умеренный зеленый фон для строк с расстоянием <= 1.5 км
    {
        "if": {"filter_query": "{distance_sort} < 1.5"},
        "backgroundColor": "#e6f5e6"  # Очень мягкий, спокойный зеленый
    },
    # Center alignment for price_change_formatted column
    {
        "if": {"column_id": "price_change_formatted"},
        "textAlign": "center"
    },
    
    # Обычные стили колонок
    {"if": {"column_id": "title"}, "width": "170px", "minWidth": "170px"},
    {"if": {"column_id": "updated_time"}, "width": "60px", "minWidth": "60px"},
    {"if": {"column_id": "address"}, "width": "150px", "minWidth": "150px"},
    {"if": {"column_id": "distance"}, "width": "50px", "minWidth": "50px"},
    {"if": {"column_id": "price"}, "fontWeight": "bold", "width": "70px", "minWidth": "70px"},
    {"if": {"column_id": "cian_estimation"}, "width": "65px", "minWidth": "65px"},
    {"if": {"column_id": "price_change_formatted"}, "width": "70px", "minWidth": "70px"},
    {"if": {"column_id": "metro_station"}, "width": "70px", "minWidth": "70px"},
]


# App layout
app.layout = html.Div([
    # Header

    
    html.H2("", style=styles["header"]),
    
    # Update time
    html.Div(
        html.Span(id="last-update-time", style=styles["update_time"]),
        style={"margin": "5px 0", "padding": "3px"}
    ),
    
    # Refresh interval
    dcc.Interval(
        id="interval-component",
        interval=2 * 60 * 1000,  # 2 minutes
        n_intervals=0,
    ),
    
    # Filters
    html.Div([
        html.Label("Макс. цена (₽):", style=styles["label"]),
        dcc.Input(
            id='price-threshold',
            type='number',
            value=80000,
            step=5000,
            style=styles["input"]
        ),
        
        html.Label("Макс. расстояние (км):", style=styles["label"]),
        dcc.Input(
            id='distance-threshold',
            type='number',
            value=3,
            step=0.5,
            style={**styles["input"], "width": "30px"}
        ),
    ], style=styles["filters"]),
    
    # Main data table with loading indicator
    dcc.Loading(
        id="loading-main",
        type="default",
        children=[html.Div(id="table-container", style={"margin": "5px", "padding": "0"})],
        style={"margin": "5px"},
    ),
    
    # Hidden storage
    html.Div(id="intermediate-value", style={"display": "none"}),
], style=styles["container"])

# Callbacks
@callback(
    Output("table-container", "children"),
    Input("price-threshold", "value"),
    Input("distance-threshold", "value"),
)
def update_table(price_threshold, distance_threshold):
    """Update the DataTable based on filters"""
    columns, data, display_cols, hidden_columns = get_table_config(price_threshold, distance_threshold)
    
    # Add debug info for a few rows
    if data:
        logger.info(f"Table has {len(data)} rows")
        for i in range(min(3, len(data))):
            row = data[i]
            logger.info(f"Row {i}: price_sort={row.get('price_sort')}, distance_sort={row.get('distance_sort')}")
    
    return dash_table.DataTable(
        id="apartment-table",
        columns=columns,
        data=data,
        sort_action="custom",
        sort_mode="multi",
        filter_action="none",
        sort_by=[],
        hidden_columns=hidden_columns,
        style_table=styles["table"],
        style_cell=styles["table_cell"],
        style_header=styles["table_header"],
        style_data=styles["table_data"],
        style_filter=styles["table_filter"],
        style_data_conditional=column_styles,
        page_size=100,
        page_action="native",
        markdown_options={"html": True},
        style_as_list_view=False,  # Changed to false to allow cell borders to be visible
        css=[{
            "selector": ".dash-cell-value",
            "rule": "line-height: 15px; display: block; white-space: normal;"
        }],
    )
@callback(
    Output("apartment-table", "data"),
    Input("apartment-table", "sort_by"),
    Input("price-threshold", "value"),
    Input("distance-threshold", "value"),
)
def update_table_sorting(sort_by, price_threshold, distance_threshold):
    """Update table sorting"""
    return sort_table_data(sort_by, price_threshold, distance_threshold)

@callback(
    Output("last-update-time", "children"),
    Input("interval-component", "n_intervals")
)
def update_time_display(_):
    """Update the last update time display"""
    _, update_time = load_data()
    return f"Last updated: {update_time}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=True, host="0.0.0.0", port=port)