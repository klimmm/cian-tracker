import dash
from dash.exceptions import PreventUpdate
from dash import dcc, html, dash_table, callback
from dash.dependencies import Input, Output, State
import subprocess
from datetime import datetime
import time
import threading
from queue import Queue, Empty
from table_config import get_table_config, sort_table_data, load_data
from dash import Dash, html
import os

app = Dash(__name__)
server = app.server  # Needed for deployment


# Initialize the Dash app with compact styling
app = dash.Dash(
    __name__,
    title="Cian Listings",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,  # Allow callbacks to refer to components not in the initial layout
)

# Define a consistent style dictionary
styles = {
    "fontFamily": "Arial, sans-serif",
    "fontSize": "12px",
    "containerPadding": "5px",
    "componentMargin": "3px",
    "headerFontSize": "16px",
    "subheaderFontSize": "14px",
    "buttonPadding": "5px 10px",
    "tableCellPadding": "4px",
}

# Define the layout with logger panel at the beginning
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
                "fontFamily": styles["fontFamily"],
                "borderBottom": "1px solid #ddd",
            },
        ),
        # Control bar with status and refresh button
        html.Div(
            [
                html.Div(
                    [
                        html.Span(
                            id="last-update-time",
                            style={"fontStyle": "italic", "fontSize": "11px"},
                        )
                    ],
                    style={
                        "margin": styles["componentMargin"],
                        "display": "inline-block",
                        "flex": "1",
                    },
                ),
                html.Div(
                    [
                        html.Button(
                            "Refresh Data",
                            id="refresh-button",
                            style={
                                "margin": "2px",
                                "backgroundColor": "#007BFF",
                                "color": "white",
                                "border": "none",
                                "padding": styles["buttonPadding"],
                                "borderRadius": "3px",
                                "cursor": "pointer",
                                "fontSize": "12px",
                            },
                        )
                    ],
                    style={"textAlign": "right"},
                ),
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "padding": "2px 5px",
                "backgroundColor": "#f5f5f5",
                "borderRadius": "3px",
            },
        ),
        # Logs section - auto show/hide when scraper runs
        html.Div(
            [
                html.H4(
                    "Scraper Logs",
                    style={"margin": "5px 0", "fontSize": "13px", "fontWeight": "bold"},
                ),
                html.Div(
                    id="logs-container",
                    style={
                        "height": "150px",
                        "overflowY": "auto",
                        "backgroundColor": "#f8f9fa",
                        "padding": "5px",
                        "borderRadius": "3px",
                        "fontFamily": "Consolas, monospace",
                        "whiteSpace": "pre-wrap",
                        "fontSize": "11px",
                        "border": "1px solid #ddd",
                    },
                ),
            ],
            id="logs-section",
            style={
                "margin": "3px",
                "padding": "3px",
                "backgroundColor": "#f9f9f9",
                "borderRadius": "3px",
                "display": "none",
            },
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
        # Auto-refresh interval component (refresh every 2 minutes)
        dcc.Interval(
            id="interval-component",
            interval=2 * 60 * 1000,  # in milliseconds (2 minutes)
            n_intervals=0,
        ),
        # Add alert for notifications
        html.Div(
            id="notification-container",
            style={
                "position": "fixed",
                "bottom": "10px",
                "right": "10px",
                "zIndex": "1000",
                "fontSize": "12px",
            },
        ),
        # Interval for checking logs (checks every 1 second while scraper is running)
        dcc.Interval(
            id="log-update-interval",
            interval=1000,  # 1 second
            n_intervals=0,
            disabled=True,  # Initially disabled
        ),
    ],
    style={
        "fontFamily": styles["fontFamily"],
        "margin": "0",
        "padding": "5px",
        "maxWidth": "100%",
        "overflowX": "hidden",
    },
)


# Global variables
scraper_running = False
last_manual_refresh_time = None
scraper_logs = []
log_update_time = 0  # Track when logs were last updated


def enqueue_output(out, queue):
    """Read output from a stream and put it into a queue"""
    for line in iter(out.readline, b""):
        queue.put(line)
    out.close()


def run_scraper_job():
    """Run the scraper script and capture its output"""
    global scraper_running, last_manual_refresh_time, scraper_logs

    try:
        scraper_running = True
        scraper_logs = []  # Clear previous logs
        scraper_logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Starting manual scraper run..."
        )

        # Run the scraper process and capture output in real-time
        process = subprocess.Popen(
            ["python", "cian_parser.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Use a queue to capture output without blocking
        q = Queue()
        t = threading.Thread(target=enqueue_output, args=(process.stdout, q))
        t.daemon = True
        t.start()

        # Process output while the script is running
        while process.poll() is None:
            try:
                line = q.get_nowait().strip()
                timestamp = datetime.now().strftime("%H:%M:%S")
                scraper_logs.append(f"[{timestamp}] {line}")
                time.sleep(0.01)  # Small delay to reduce CPU usage
            except Empty:
                time.sleep(0.1)

        # Process any remaining output
        try:
            while True:
                line = q.get_nowait().strip()
                timestamp = datetime.now().strftime("%H:%M:%S")
                scraper_logs.append(f"[{timestamp}] {line}")
        except Empty:
            pass

        # Check return code
        if process.returncode == 0:
            scraper_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Обновлено")
            last_manual_refresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            scraper_logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Scraper failed with return code {process.returncode}"
            )

    except Exception as e:
        scraper_logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Error running scraper: {e}"
        )
    finally:
        scraper_running = False


@callback(
    [
        Output("intermediate-value", "children"),
        Output("last-update-time", "children"),
        Output("refresh-button", "children"),
        Output("refresh-button", "disabled"),
        Output("logs-section", "style"),
    ],
    [
        Input("interval-component", "n_intervals"),
        Input("refresh-button", "n_clicks"),
        Input("log-update-interval", "n_intervals"),
    ],
    [State("refresh-button", "children"), State("logs-section", "style")],
)
def update_data(n_intervals, n_clicks, log_intervals, button_text, logs_style):
    """Update the intermediate data store, last update time, and logs visibility"""
    global scraper_running, last_manual_refresh_time

    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""

    # Base style for logs section
    base_logs_style = {
        "margin": "3px",
        "padding": "3px",
        "backgroundColor": "#f9f9f9",
        "borderRadius": "3px",
    }

    # If refresh button clicked and scraper not already running
    if trigger == "refresh-button" and n_clicks and not scraper_running:
        # Start the scraper in a background thread
        threading.Thread(target=run_scraper_job, daemon=True).start()

        # Show logs when scraper starts
        logs_style_visible = {**base_logs_style, "display": "block"}

        # Return immediately with "Running..." status
        return "", "Scraper running...", "Scraping...", True, logs_style_visible

    # If log update triggered, update button state and logs visibility
    if trigger == "log-update-interval":
        if scraper_running:
            logs_style_visible = {**base_logs_style, "display": "block"}
            return (
                dash.no_update,
                dash.no_update,
                "Scraping...",
                True,
                logs_style_visible,
            )
        elif button_text == "Scraping...":  # Scraper just finished
            _, update_time = load_data()
            if last_manual_refresh_time:
                update_info = f"{update_time} | Man: {last_manual_refresh_time}"
            else:
                update_info = f"{update_time}"

            # Hide logs when scraper finishes
            logs_style_hidden = {**base_logs_style, "display": "none"}

            return "", update_info, "Refresh Data", False, logs_style_hidden
        else:
            raise PreventUpdate

    # Normal interval update
    _, update_time = load_data()

    # If scraper is running, update button state and show logs
    if scraper_running:
        logs_style_visible = {**base_logs_style, "display": "block"}
        return "", "Scraper running...", "Scraping...", True, logs_style_visible

    # Add manual refresh time info if available (in shortened format)
    if last_manual_refresh_time:
        update_info = f"{update_time} | Man: {last_manual_refresh_time}"
    else:
        update_info = f"{update_time}"

    # Keep logs hidden during normal state
    logs_style_hidden = {**base_logs_style, "display": "none"}

    # Return empty string for data (DataTable will handle the empty DataFrame)
    return "", update_info, "Refresh Data", False, logs_style_hidden


@callback(
    Output("log-update-interval", "disabled"),
    [Input("refresh-button", "n_clicks"), Input("log-update-interval", "n_intervals")],
)
def manage_log_interval(n_clicks, n_intervals):
    """Enable or disable the log update interval based on scraper status"""
    # Keep interval active while scraper is running
    return not scraper_running


@callback(
    Output("logs-container", "children"), Input("log-update-interval", "n_intervals")
)
def update_logs(n):
    """Update the logs container with the latest logs"""
    if not scraper_logs:
        return "No logs available. Run the scraper to see logs here."

    # Format logs with appropriate coloring
    formatted_logs = []
    for log in scraper_logs:
        if "ERROR" in log or "error" in log.lower() or "failed" in log.lower():
            formatted_logs.append(html.Div(log, style={"color": "red"}))
        elif "WARNING" in log or "warning" in log.lower():
            formatted_logs.append(html.Div(log, style={"color": "orange"}))
        elif "SUCCESS" in log or "completed successfully" in log:
            formatted_logs.append(html.Div(log, style={"color": "green"}))
        else:
            formatted_logs.append(html.Div(log))

    return formatted_logs


@callback(
    Output("notification-container", "children"),
    [
        Input("log-update-interval", "n_intervals"),
        Input("interval-component", "n_intervals"),
    ],
)
def update_notification(log_intervals, refresh_intervals):
    """Show notification when scraper finishes"""
    global scraper_running, last_manual_refresh_time, log_update_time

    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""

    # Only show notification when triggered by log update and scraper just finished
    if (
        trigger == "log-update-interval"
        and not scraper_running
        and last_manual_refresh_time
    ):
        # Get time since last refresh
        last_time = datetime.strptime(last_manual_refresh_time, "%Y-%m-%d %H:%M:%S")
        time_diff = (datetime.now() - last_time).total_seconds()

        # Only show notification if scraper finished in the last 5 seconds
        if time_diff < 5:
            return html.Div(
                [
                    html.Div(
                        "Scraper completed successfully!",
                        style={
                            "backgroundColor": "#4CAF50",
                            "color": "white",
                            "padding": "8px",
                            "borderRadius": "3px",
                            "boxShadow": "0 2px 4px rgba(0,0,0,0.2)",
                            "fontSize": "12px",
                        },
                    )
                ]
            )

    # Prevent updates from regular interval to reduce flickering
    if trigger == "interval-component":
        raise PreventUpdate

    return None


@callback(
    Output("table-container", "children"),
    [
        Input("intermediate-value", "children"),
        Input("log-update-interval", "n_intervals"),
        Input("interval-component", "n_intervals"),
    ],
)
def update_table(_, log_intervals, refresh_intervals):
    """Update the DataTable from the intermediate data"""
    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""
    # Prevent unnecessary updates to reduce flickering
    if trigger == "log-update-interval" and scraper_running:
        raise PreventUpdate

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
            # "overflow": "visible",
            "width": "auto",
            "maxWidth": "200px",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "fontSize": "10px",
            "fontFamily": styles["fontFamily"],
        },
        style_header={
            # 'backgroundColor': '#f2f2f2',    # Lighter background color
            "backgroundColor": "#007BFF",
            "color": "white",
            # 'color': '#333',                 # Darker text for better readability
            "fontWeight": "normal",  # Remove bold to make it simpler
            "textAlign": "left",  # Left align text (like the data cells)
            "padding": "2px",  # Reduced padding
            "fontSize": "11px",  # Smaller font size
            "height": "18px",  # Reduced height
            "borderBottom": "1px solid #ddd",  # Simple bottom border
        },
        style_data_conditional=column_specific_style
        + [{"if": {"row_index": "odd"}, "backgroundColor": "rgb(248, 248, 248)"}],
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


# Add callback for custom sorting using the new sort function
@callback(Output("apartment-table", "data"), [Input("apartment-table", "sort_by")])
def update_table_sorting(sort_by):
    return sort_table_data(sort_by)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(debug=True, host="0.0.0.0", port=port)
