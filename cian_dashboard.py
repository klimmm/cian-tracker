import dash
from dash import dcc, html, dash_table, callback
from dash.dependencies import Input, Output
import os
import pandas as pd
import logging
import numpy as np
# Configure minimal logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Core configuration
CONFIG = {
    'columns': {
        'display': ['offer_id', 'title', 'updated_time', 'updated_time_sort', 'price', 'price_sort',
                   'cian_estimation', 'cian_estimation_sort', 'price_difference', 'price_difference_sort',
                   'calculated_price_diff', 'address', 'metro_station', 'offer_link', 'distance', 'days_active', 'distance_sort', 
                   'price_change_value', 'price_change_formatted', 'status', 'unpublished_date', 'unpublished_date_sort'],
        'visible': ['address', 'distance', 'price', 'cian_estimation', 'updated_time', 
                    'price_change_formatted', 'title', 'metro_station', 
                    #'status',
                    'unpublished_date'
                   ],
        'headers': {
            'offer_id': 'ID', 'distance': 'Расст.', 'price_change_formatted': 'Изм.',
            'title': 'Описание', 'updated_time': 'Обновлено', 'price': 'Цена',
            'cian_estimation': 'Оценка', 'price_difference': 'Разница', 
            'address': 'Адрес', 'metro_station': 'Метро', 'offer_link': 'Ссылка',
            'status': 'Статус', 'unpublished_date': 'Снято'
        },
        'sort_map': {'updated_time': 'updated_time_sort', 
                     'price': 'price_sort', 
                     'price_change_formatted': 'price_change_sort',
                    'cian_estimation': 'cian_estimation_sort', 
                     'price_difference': 'price_difference_sort'
                    }
    },
    'months': {1:'янв', 2:'фев', 3:'мар', 4:'апр', 5:'май', 6:'июн', 
               7:'июл', 8:'авг', 9:'сен', 10:'окт', 11:'ноя', 12:'дек'},
    'base_url': 'https://www.cian.ru/rent/flat/',
    'hidden_cols': ['price_sort', 'distance_sort', 'updated_time_sort', 
                   'cian_estimation_sort', 'price_difference_sort', 'unpublished_date_sort'],
}

# Define styles
FONT_FAMILY = 'Arial,sans-serif'
STYLE_COMMON = {'fontFamily': FONT_FAMILY}
STYLES = {
    'container': {**STYLE_COMMON, 'margin': '0', 'padding': '5px', 'maxWidth': '100%', 'overflowX': 'hidden'},
    'header': {**STYLE_COMMON, 'textAlign': 'center', 'margin': '3px 0', 'padding': '3px', 
              'fontSize': '10px', 'borderBottom': '1px solid #ddd'},
    'update_time': {**STYLE_COMMON, 'fontStyle': 'italic', 'fontSize': '10px', 'margin': '5px'},
    'table': {'overflowX': 'auto', 'tableLayout': 'auto', 'width': '100%'},
    'table_cell': {**STYLE_COMMON, 'textAlign': 'center', 'padding': '3px 4px', 'overflow': 'hidden', 
                  'textOverflow': 'ellipsis', 'fontSize': '9px', 'whiteSpace': 'nowrap'},
    'table_header': {**STYLE_COMMON, 'backgroundColor': '#4682B4', 'color': 'white', 'fontWeight': 'normal',
                    'textAlign': 'left', 'padding': '4px', 'fontSize': '10px', 'height': '18px', 
                    'borderBottom': '1px solid #ddd'},
    'table_data': {'height': 'auto', 'lineHeight': '14px'},
    'table_filter': {'display': 'none'}
}

# Column and header styles
COLUMN_STYLES = [
    # Non-active listings styling (this must be first to take precedence)
    {'if': {'filter_query': '{status} contains "non active"'}, 'backgroundColor': '#e0e0e0', 'color': '#888888'},
    
    # Close proximity styling - but not for non-active listings
    {'if': {
        'filter_query': '{distance_sort} < 1.5 && {status} ne "non active"'
    }, 'backgroundColor': '#e6f0f5'},
    
    # Price is significantly below Cian estimation - but not for non-active listings
    {'if': {
        'filter_query': '{calculated_price_diff} < -5000 && {status} ne "non active"'
    }, 'backgroundColor': '#fff8e6'},
    
    # Alternative price difference - but not for non-active listings
    {'if': {
        'filter_query': '{price_difference_sort} < -1000 && {status} ne "non active"'
    }, 'backgroundColor': '#fff8e6'},
    
    # Recently updated listings - styling applies to all listings
    {'if': {'filter_query': '{updated_time_sort} > "' + (pd.Timestamp.now() - pd.Timedelta(hours=24)).isoformat() + '"'}, 
     'fontWeight': 'bold'},
    
    # Styling for specific columns
    {'if': {'column_id': 'price_change_formatted'}, 'textAlign': 'center'},
    {'if': {'column_id': 'price'}, 'fontWeight': 'bold'},
]

HEADER_STYLES = [{'if': {'column_id': c}, 'textAlign': 'center'} 
                for c in ['distance', 'updated_time', 'unpublished_date', 'price', 'cian_estimation', 
                         'price_change_formatted', 'metro_station', 'status']]

def load_data():
    """Load and process data from CSV without caching"""
    try:
        csv_path = 'cian_apartments.csv'
        df = pd.read_csv(csv_path, encoding='utf-8', comment='#')
        
        # Extract update time from CSV header
        with open(csv_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        update_time = 'Unknown' if 'last_updated=' not in first_line else first_line.split('last_updated=')[1].split(',')[0].strip()
        
        # Process columns
        if 'offer_id' in df.columns:
            df['offer_id'] = df['offer_id'].astype(str)
            if 'address' in df.columns:
                df['address'] = df.apply(lambda r: f"[{r['address']}]({CONFIG['base_url']}{r['offer_id']}/)", axis=1)
            if 'offer_url' in df.columns:
                df['offer_link'] = df['offer_id'].apply(lambda x: f"[View]({CONFIG['base_url']}{x}/)")
        
        if 'distance' in df.columns:
            df['distance_sort'] = pd.to_numeric(df['distance'], errors='coerce')
            df['distance'] = df['distance_sort'].apply(lambda x: f"{x:.2f} km" if pd.notnull(x) else "")
        
        if 'price_change_value' in df.columns:
            df['price_change_sort'] = pd.to_numeric(df['price_change_value'].fillna(0), errors='coerce')
            df['price_change_sort'] = df['price_change_sort'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
            def format_price_change(v):
                if v == 0: return "<div style='text-align:center;'><span>—</span></div>"
                color = 'green' if v < 0 else 'red'
                arrow = '↓' if v < 0 else '↑'
                val = f"{abs(v)/1000:.00f}K" if abs(v) >= 1000 else f"{abs(v):.0f}"
                return f"<div style='text-align:center;'><span style='color:{color};'>{arrow}{val}</span></div>"
            
            df['price_change_formatted'] = df['price_change_sort'].apply(format_price_change)
        
        # Process price columns
        for col in ['price', 'cian_estimation', 'price_difference']:
            if col in df.columns:
                df[f"{col}_sort"] = (df[col].astype(str)
                                   .str.extract(r'(\d+[\s\d]*)', expand=False)
                                   .str.replace(' ', '')
                                   .astype(float, errors='ignore'))
        
        # Explicitly calculate price difference if it doesn't exist or for more accuracy
        if 'price_sort' in df.columns and 'cian_estimation_sort' in df.columns:
            df['calculated_price_diff'] = df['price_sort'] - df['cian_estimation_sort']
        
        if 'cian_estimation' in df.columns:
            df['cian_estimation'] = df['cian_estimation'].apply(lambda v: '--' if pd.isna(v) else v)
        
        if 'updated_time' in df.columns:
            # Specify the format explicitly to avoid warnings
            # Adjust the format string to match your actual date format
            df['updated_time_sort'] = pd.to_datetime(df['updated_time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
            df['updated_time'] = df['updated_time_sort'].apply(
                lambda x: f"{x.day} {CONFIG['months'][x.month]}, {x.hour:02d}:{x.minute:02d}" if pd.notnull(x) else "")
        
        if 'unpublished_date' in df.columns:
            # Specify the format explicitly to avoid warnings
            # Adjust the format string to match your actual date format  
            df['unpublished_date_sort'] = pd.to_datetime(df['unpublished_date'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
            # Then apply formatting with '--' for null values in one step
            df['unpublished_date'] = df['unpublished_date_sort'].apply(
                lambda x: f"{x.day} {CONFIG['months'][x.month]}, {x.hour:02d}:{x.minute:02d}" if pd.notnull(x) else "--")
        
        if 'days_active' in df.columns:
            df['days_active'] = pd.to_numeric(df['days_active'].fillna(0), errors='coerce').astype(int)
        
        # Default sort
        if 'updated_time_sort' in df.columns:
            df = df.sort_values('updated_time_sort', ascending=False)
        
        return df, update_time
    
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.DataFrame(), f"Error: {e}"

def filter_dataframe(df, price_threshold=None, distance_threshold=None):
    """Apply filters to dataframe"""
    if price_threshold is not None and 'price_sort' in df.columns:
        df = df[df['price_sort'] <= price_threshold]
    if distance_threshold is not None and 'distance_sort' in df.columns:
        df = df[df['distance_sort'] <= distance_threshold]
    return df

def sort_table_data(sort_by, price_threshold=None, distance_threshold=None):
    """Sort table data based on user selection"""
    df, _ = load_data()
    df = filter_dataframe(df, price_threshold, distance_threshold)
    display_cols = [col for col in CONFIG['columns']['display'] if col in df.columns]
    
    # Apply sorting
    if sort_by and not df.empty:
        for sort_item in sort_by:
            sort_col = CONFIG['columns']['sort_map'].get(sort_item['column_id'], sort_item['column_id'])
            df = df.sort_values(sort_col, ascending=sort_item['direction'] == 'asc')
    elif 'updated_time_sort' in df.columns:
        df = df.sort_values('updated_time_sort', ascending=False)
    
    return df[display_cols].to_dict('records')

# Initialize Dash app
app = dash.Dash(__name__, title='Cian Listings',
               meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}],
               suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.H2('Cian Listings', style=STYLES['header']),
    html.Div(html.Span(id='last-update-time', style=STYLES['update_time']),
             style={'margin': '5px 0', 'padding': '3px'}),
    dcc.Interval(id='interval-component', interval=2*60*1000, n_intervals=0),
    
    # Filters container with legend in the same row
    html.Div([
        # Input filters
        html.Div([
            html.Label('Макс. цена (₽):', className='dash-label'),
            dcc.Input(id='price-threshold', type='number', value=80000, step=5000, min=10000, max=500000),
            html.Label('Макс. расстояние (км):', className='dash-label'),
            dcc.Input(id='distance-threshold', type='number', value=3, step=0.5, min=0.5, max=10),
        ], style={'display': 'inline-block', 'marginRight': '15px', 'verticalAlign': 'middle'}),
        
        # Color legend in same row
        html.Div([
            html.Div(style={
                'display': 'inline-block', 
                'backgroundColor': '#e6f0f5', 
                'padding': '3px 8px', 
                'margin': '0 5px',
                'borderRadius': '3px',
                'fontSize': '10px',
                'border': '1px solid #ccc'
            }, children="Близко к адресу"),
            
            html.Div(style={
                'display': 'inline-block', 
                'backgroundColor': '#fff8e6', 
                'padding': '3px 8px', 
                'margin': '0 5px',
                'borderRadius': '3px',
                'fontSize': '10px',
                'border': '1px solid #ccc'
            }, children="Цена ниже оценки"),
            
            html.Div(style={
                'display': 'inline-block', 
                'backgroundColor': '#e0e0e0', 
                'padding': '3px 8px', 
                'margin': '0 5px',
                'borderRadius': '3px',
                'fontSize': '10px',
                'border': '1px solid #ccc'
            }, children="Неактивные"),
            
            html.Div(style={
                'display': 'inline-block', 
                'fontWeight': 'bold',
                'padding': '3px 8px', 
                'margin': '0 5px',
                'borderRadius': '3px',
                'fontSize': '10px',
                'border': '1px solid #ccc'
            }, children="Обновлено сегодня"),
        ], style={'display': 'inline-block', 'verticalAlign': 'middle'})
    ], id='filters-container', style={'margin': '5px', 'whiteSpace': 'nowrap', 'overflow': 'auto'}),
    
    dcc.Loading(
        id='loading-main', type='default',
        children=[html.Div(id='table-container', style={'margin': '5px', 'padding': '0'})],
        style={'margin': '5px'}
    ),
], style=STYLES['container'])

def get_table_config(price_threshold=None, distance_threshold=None):
    """Generate DataTable configuration based on filters"""
    df, _ = load_data()
    df = filter_dataframe(df, price_threshold, distance_threshold)
    
    # Filter columns
    display_cols = [col for col in CONFIG['columns']['display'] if col in df.columns]
    visible_cols = [col for col in CONFIG['columns']['visible'] if col in df.columns]
    hidden_cols = [col for col in CONFIG['hidden_cols'] if col in df.columns]
    
    # Make sure price_change_formatted is in visible columns
    if 'price_change_formatted' in df.columns and 'price_change_formatted' not in visible_cols:
        visible_cols.append('price_change_formatted')
    
    # Generate column definitions
    numeric_cols = ['distance', 'days_active', 'price', 'cian_estimation', 'price_difference']
    markdown_cols = ['price_change_formatted', 'title', 'address', 'offer_link']
    
    columns = [{
        'name': CONFIG['columns']['headers'].get(col, col),
        'id': col,
        'type': 'numeric' if col in numeric_cols else 'text',
        'presentation': 'markdown' if col in markdown_cols else None
    } for col in visible_cols]
    
    return columns, df[display_cols].to_dict('records'), display_cols, hidden_cols

@callback(
    Output('table-container', 'children'),
    Input('price-threshold', 'value'),
    Input('distance-threshold', 'value')
)
def update_table(price_threshold, distance_threshold):
    """Update the DataTable based on filters"""
    columns, data, _, hidden_columns = get_table_config(price_threshold, distance_threshold)
    logger.info(f"Table updated: {len(data)} rows")
    
    return dash_table.DataTable(
        id='apartment-table', 
        columns=columns, 
        data=data,
        sort_action='custom', 
        sort_mode='multi', 
        filter_action='none', 
        sort_by=[],
        hidden_columns=hidden_columns,
        style_table=STYLES['table'],
        style_cell=STYLES['table_cell'],
        style_cell_conditional=[{'if': {'column_id': col['id']}, 'width': 'auto'} for col in columns],
        style_header=STYLES['table_header'],
        style_header_conditional=HEADER_STYLES,
        style_data=STYLES['table_data'],
        style_filter=STYLES['table_filter'],
        style_data_conditional=COLUMN_STYLES,
        page_size=100, 
        page_action='native',
        markdown_options={'html': True}
    )

@callback(
    Output('apartment-table', 'data'),
    Input('apartment-table', 'sort_by'),
    Input('price-threshold', 'value'),
    Input('distance-threshold', 'value')
)
def update_table_sorting(sort_by, price_threshold, distance_threshold):
    """Update table sorting"""
    return sort_table_data(sort_by, price_threshold, distance_threshold)

@callback(
    Output('last-update-time', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_time_display(_):
    """Update the last update time display"""
    _, update_time = load_data()
    return f"Last updated: {update_time}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=True, host='0.0.0.0', port=port)