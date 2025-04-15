# app/table_factory.py
import logging
from dash import dash_table
logger = logging.getLogger(__name__)


class TableFactory:
    """Factory for creating consistent data tables that rely on external CSS for styling."""

    @classmethod
    def create_data_table(
        cls,
        id='apartment-table',
        data=[],
        columns=[],
        sort_action="custom",
        sort_mode="multi",
        sort_by=[],
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
        if hidden_columns is None:
            hidden_columns = [
                "price_value",
                "distance_sort",
                "updated_time_sort",
                "cian_estimation_value",
                "price_difference_value",
                "unpublished_date_sort",
                'offer_id'
            ]

        if style_header is None:
            style_header = {
                "backgroundColor": "var(--color-primary)",
                "color": "white",
                "fontWeight": "bold",
            }
        
        if style_cell is None:
            style_cell = {
                "textAlign": "left",
                "padding": "8px",
                "fontFamily": "var(--font-family)",
                "fontSize": "var(--font-sm)",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
            }
            
            
        if conditional_styles is None:
            conditional_styles = [
                {
                    "if": {"filter_query": '{status} contains "non active"'},
                    "backgroundColor": "#f4f4f4",
                    "color": "#888",
                },
                # Only kept special conditions that can't be handled with CSS
                {"if": {"column_id": "price_change_formatted"}, "textAlign": "center"},
                {"if": {"column_id": "updated_time"}, "fontWeight": "bold", "textAlign": "center"},
                {"if": {"column_id": "price_value_formatted"}, "fontWeight": "bold", "textAlign": "center"},
            ]
            
        # === Define fixed-width columns and their widths (in %) ===
        fixed_columns = {
            "update_title": 5,
            "property_tags": 30,
            
            "details": 10,
            "address_title": 20,
            "price_text": 15,
        }

        # Optional: alignment overrides
        column_alignments = {
            "price_text": "center",
            "details": "center",
            # All others default to 'left'
        }

        # Extract column IDs from column definitions
        column_ids = [col["id"] for col in columns]

        dynamic_columns = [cid for cid in column_ids if cid not in fixed_columns]

        # Calculate remaining width for dynamic columns
        total_fixed_width = sum(width for col_id, width in fixed_columns.items() if col_id in column_ids)
        remaining_width = 100 - total_fixed_width
        dynamic_width = remaining_width / len(dynamic_columns) if dynamic_columns else 0

        # Build style_cell_conditional
        if style_cell_conditional is None:
            style_cell_conditional = []

        # Fixed-width columns
        for col_id, width in fixed_columns.items():
            if col_id in column_ids:  # Only add if column actually exists
                alignment = column_alignments.get(col_id, "left")
                style_cell_conditional.append(
                    {
                        "if": {"column_id": col_id},
                        "width": f"{width}%",
                        "textAlign": alignment,
                    }
                )

        # Dynamic columns
        for col_id in dynamic_columns:
            alignment = column_alignments.get(col_id, "left")
            style_cell_conditional.append(
                {
                    "if": {"column_id": col_id},
                    "width": f"{dynamic_width:.2f}%",
                    "textAlign": alignment,
                }
            )
        
        table_props = {
            "id": id,
            "data": data,
            "columns": columns,
            "page_size": page_size,
            "page_action": page_action,
            "sort_action": sort_action,
            "sort_mode": sort_mode,
            "sort_by": sort_by,
            "style_header": style_header,
            "style_cell": style_cell,
            "style_cell_conditional": style_cell_conditional,
            "style_data": {"backgroundColor": "white"},
            "style_table": {
                "overflowX": "auto",
                "width": "100%",
                "maxWidth": "100%",
            },
            "style_data_conditional": conditional_styles,
            "cell_selectable": cell_selectable,
            "markdown_options": markdown_options,
            "hidden_columns": hidden_columns,
        }
        
        # Add any additional keyword arguments
        table_props.update(
            {k: v for k, v in kwargs.items() if k not in table_props}
        )
        
        logger.debug("Creating table with properties: %s", table_props)
        return dash_table.DataTable(**table_props)