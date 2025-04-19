import dash
from dash import dash_table
import logging

logger = logging.getLogger(__name__)

class TableFactory:
    """Factory for creating consistent data tables that rely on external CSS for styling."""

    @classmethod
    def create_data_table(
        cls,
        id='apartment-table',
        data=None,
        columns=None,
        sort_action="custom",
        sort_mode="multi",
        sort_by=None,
        page_size=100,
        page_action="native",
        conditional_styles=None,
        markdown_options={"html": True},
        cell_selectable=True,
        hidden_columns=None,
        style_header=None,
        style_cell=None,
        style_cell_conditional=None,
        **kwargs,
    ):
        # Add these debug logs
        logger.debug(f"===== TableFactory.create_data_table called =====")
        logger.debug(f"Table ID: {id}")
        logger.debug(f"Data length: {len(data) if data else 0}")
        logger.debug(f"Columns count: {len(columns) if columns else 0}")
        if columns:
            logger.debug(f"Column IDs: {[col.get('id') for col in columns]}")
        # Defaults
        if data is None:
            data = []
        if columns is None:
            columns = []
        if sort_by is None:
            sort_by = []

        if hidden_columns is None:
            hidden_columns = [
                "price_value",
                "distance_sort",
                'property_tags',
                "updated_time_sort",
                "cian_estimation_value",
                "price_difference_value",
                "unpublished_date_sort",
                'offer_id'
            ]

        # Header style
        if style_header is None:
            style_header = {
                "backgroundColor": "var(--color-primary)",
                "color": "white",
                "fontWeight": "bold",
            }

        # Cell base style
        if style_cell is None:
            style_cell = {
                "textAlign": "left",
                "padding": "8px",
                'verticalAlign': 'top',
                "fontFamily": "var(--font-family)",
                "fontSize": "var(--font-sm)",
                "minWidth": "0",          # allow shrinking
                "whiteSpace": "normal",   # enable wrapping
                "overflow": "hidden",
                "textOverflow": "ellipsis",
            }

        # Conditional styles default
        if conditional_styles is None:
            conditional_styles = [
                {
                    "if": {"filter_query": '{status} contains "non active"'},
                    "backgroundColor": "#f4f4f4",
                    "color": "#888",
                },
                {"if": {"column_id": "price_change_formatted"}, "textAlign": "center"},
                {"if": {"column_id": "updated_time"}, "fontWeight": "bold", "textAlign": "center"},
                {"if": {"column_id": "price_value_formatted"}, "fontWeight": "bold", "textAlign": "center"},
                {"if": {"column_id": "price_text"}, "fontWeight": "bold", "textAlign": "center", 'verticalAlign': 'top'},
                
            ]

        # Fixed-width columns (percentages)
        fixed_columns = {
            "update_title": 30,
            #"property_tags": 25,
            "address_title": 25,
            "condition_summary": 20,
            "price_text": 25,
        }
        column_alignments = {"price_text": "center"}

        # Build style_cell_conditional
        if style_cell_conditional is None:
            style_cell_conditional = []

        # Extract IDs
        column_ids = [col['id'] for col in columns]
        dynamic_columns = [cid for cid in column_ids if cid not in fixed_columns]

        total_fixed = sum(width for cid,width in fixed_columns.items() if cid in column_ids)
        remaining = max(0, 100 - total_fixed)
        dyn_width = remaining / len(dynamic_columns) if dynamic_columns else 0

        # Fixed widths
        for cid, pct in fixed_columns.items():
            if cid in column_ids:
                align = column_alignments.get(cid, 'left')
                style_cell_conditional.append({
                    'if': {'column_id': cid},
                    'width': f"{pct}%",
                    'textAlign': align,
                })

        # Dynamic widths
        for cid in dynamic_columns:
            align = column_alignments.get(cid, 'left')
            style_cell_conditional.append({
                'if': {'column_id': cid},
                'width': f"{dyn_width:.2f}%",
                'textAlign': align,
            })

        # Compose table props
        table_props = {
            'id': id,
            'data': data,
            'columns': columns,
            'page_size': page_size,
            'page_action': page_action,
            'sort_action': sort_action,
            'sort_mode': sort_mode,
            'sort_by': sort_by,
            'style_header': style_header,
            'style_cell': style_cell,
            'style_cell_conditional': style_cell_conditional,
            'style_data': {'backgroundColor': 'white'},
            'style_table': {
                'overflowX': 'auto',
                'width': '100%',
                'maxWidth': '650px',
                'width': 'fit-content'    # shrink to content
            },
            'style_data_conditional': conditional_styles,
            'cell_selectable': cell_selectable,
            'markdown_options': markdown_options,
            'hidden_columns': hidden_columns,
        }

        # Merge extras
        table_props.update({k: v for k,v in kwargs.items() if k not in table_props})

        logger.debug("Creating table with properties: %s", table_props)

        # Before returning, log the complete table configuration
        logger.debug(f"Final table configuration:")
        logger.debug(f"- data length: {len(table_props['data'])}")
        logger.debug(f"- columns length: {len(table_props['columns'])}")
        logger.debug(f"- CSS rules: {table_props.get('css')}")
        
        # Log specific column IDs that will be visible
        visible_column_ids = [col['id'] for col in table_props['columns'] 
                             if col['id'] not in (hidden_columns or [])]
        logger.debug(f"Visible column IDs after hiding: {visible_column_ids}")
        
        # Return DataTable
        return dash_table.DataTable(
            style_as_list_view=True,
            css=[{
                'selector': '.dash-header',
                'rule': 'display: none;'  # HIGHLIGHT THIS - it hides headers!
            }],
            **table_props
        )
