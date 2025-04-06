import dash
from dash import dcc, html, dash_table, callback
from dash.dependencies import Input, Output
from table_config import get_table_config, sort_table_data, load_data
from dash import Dash
import os

app = Dash(__name__)
server = app.server  # Needed for deployment

# Initialize the Dash app with compact styling
app = dash.Dash(
    __name__,
    title="Cian Listings",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
)


# Define the layout without logger panel, refresh, notifications
app.layout = html.Div(
    [
        # Compact App header
        html.H2(
            "",
            style={
                "textAlign": "center",
                "margin": "3px 0",
                "padding": "3px",
                "fontSize": "10px",
                "fontFamily": "Arial, sans-serif",
                "borderBottom": "1px solid #ddd",
            },
        ),
        # Add back the update time span (simplified)
        html.Div(
            html.Span(
                id="last-update-time",
                style={"fontStyle": "italic", "fontSize": "11px", "margin": "5px"}
            ),
            style={"margin": "5px 0", "padding": "3px"}
        ),
        
        dcc.Interval(
            id="interval-component",
            interval=2 * 60 * 1000,  # in milliseconds (2 minutes)
            n_intervals=0,
        ),

        
        # Main data section with loading indicator
        dcc.Loading(
            id="loading-main",
            type="default",
            children=[
                # Add a loading component around the DataTable
                html.Div(id="table-container", style={"margin": "5px", "padding": "0"})
            ],
            style={"margin": "5px"},
        ),
        # Hidden div for storing the data
        html.Div(id="intermediate-value", style={"display": "none"}),
    ],
    style={
        "fontFamily": "Arial, sans-serif",
        "margin": "0",
        "padding": "5px",
        "maxWidth": "100%",
        "overflowX": "hidden",
    },
)

@callback(
    Output("table-container", "children"),
    [Input("intermediate-value", "children")]
)
def update_table(_):
    """Update the DataTable from the intermediate data"""
    columns, data, display_cols, sort_map, hidden_columns = get_table_config()

    # Define column-specific styling
    column_specific_style = [
        # Make address column wider and wrap text
        {
            "if": {"column_id": "address"},
            "minWidth": "150px",
            "width": "200px",
            "maxWidth": "300px",
            "whiteSpace": "normal",
            "textOverflow": "initial",
            "overflow": "visible",
            "height": "auto",
        },
        # Highlight price differences
        {
            "if": {
                "column_id": "price_difference",
                "filter_query": "{price_difference_sort} < 0",
            },
            "color": "green",
            "fontWeight": "bold",
        },
        {"if": {"column_id": "title"}, "width": "200px", "minWidth": "150px"},
        {"if": {"column_id": "distance"}, "maxWidth": "30px", "width": "30px"},
        # Bold the price
        {"if": {"column_id": "price"}, "fontWeight": "bold"},
    ]

    return dash_table.DataTable(
        id="apartment-table",
        columns=columns,
        data=data,
        sort_action="custom",
        sort_mode="multi",
        filter_action="none",
        sort_by=[],
        hidden_columns=hidden_columns,
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "3px 4px",
            "minWidth": "50px",
            "width": "auto",
            "maxWidth": "200px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "fontSize": "10px",
            "fontFamily": "Arial, sans-serif",
        },
        style_header={
            "backgroundColor": "#007BFF",
            "color": "white",
            "fontWeight": "normal",
            "textAlign": "left",
            "padding": "2px",
            "fontSize": "11px",
            "height": "18px",
            "borderBottom": "1px solid #ddd",
        },
        style_data_conditional=column_specific_style + [
            {"if": {"row_index": "odd"},
             "backgroundColor": "rgb(248, 248, 248)"}
        ],
        page_size=100,
        page_action="native",
        markdown_options={"html": True},
        style_as_list_view=True,
        style_filter={
            "fontSize": "1px",
            "padding": "1px",
            "height": "2px",
            "display": "none",
        },
        style_data={
            "height": "auto",
            "lineHeight": "14px",
            "whiteSpace": "normal",  # Allow text to wrap within cells
        },
        css=[
            {
                "selector": ".dash-cell-value",
                "rule": "line-height: 15px; display: block; white-space: normal;",
            }
        ],
    )


@callback(Output("apartment-table", "data"), [Input("apartment-table", "sort_by")])
def update_table_sorting(sort_by):
    return sort_table_data(sort_by)


# Modify the callback to use the interval
@callback(
    Output("last-update-time", "children"),
    [Input("interval-component", "n_intervals")]
)
def update_time_display(n):
    """Update the last update time display"""
    _, update_time = load_data()
    return f"Last updated: {update_time}"

    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=True, host="0.0.0.0", port=port)