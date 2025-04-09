import os
import dash
from dash import dash_table, callback
from dash.dependencies import Input, Output
from config import CONFIG, STYLE, COLUMN_STYLES, HEADER_STYLES
from utils import load_and_process_data, filter_and_sort_data
from layout import create_app_layout
import callbacks

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