# Modified PillFactory in components.py to remove duplicate styling
import logging
from dash import html

logger = logging.getLogger(__name__)


class ContainerFactory:
    """Factory for creating consistent container components"""
    
    @classmethod
    def create_section(cls, children, title=None, divider=True, spacing="md", custom_style=None):
        """Create a section container with optional title and divider"""
        # Filter out None values
        if isinstance(children, list):
            children = [child for child in children if child is not None]
            if not children:
                return None
        elif children is None:
            return None
            
        # Build class name
        class_name = f"section section--spacing-{spacing}"
        if divider:
            class_name += " section--divider"
        
        # Build section elements
        elements = []
        
        # Add title if provided
        if title:
            elements.append(
                html.H4(title, className="section-title")
            )
            
        # Add children
        if isinstance(children, list):
            elements.extend(children)
        else:
            elements.append(children)
            
        # Keep only truly dynamic styles, if any
        dynamic_style = {}
        if custom_style:
            dynamic_style = custom_style
        
        return html.Div(elements, style=dynamic_style, className=class_name)


class ButtonFactory:
    """Factory for creating consistent button components"""
    
    @classmethod
    def create_button(cls, label, button_id, variant="default", size="md", 
                      is_active=False, icon=None, custom_style=None, **kwargs):
        """Create a button with consistent styling"""
        # Build class name based on variant, size, and state
        class_name = f"btn btn--{variant} btn--{size}"
            
        if is_active:
            class_name += " btn--active"
        
        # Allow passing custom style
        dynamic_style = custom_style if custom_style else {}
        
        # Create the button content with optional icon
        if icon:
            content = html.Div([
                html.I(className=icon, style={"marginRight": "0.5rem"}),
                html.Span(label, id=f"{button_id}-text" if label else None)
            ], className="flex-container flex-container--align-center flex-container--gap-xs")
        else:
            content = html.Span(label, id=f"{button_id}-text" if label else None)
        
        return html.Button(content, id=button_id, style=dynamic_style, className=class_name, **kwargs)
    
    @classmethod
    def create_button_group(cls, buttons, label_text=None, active_button_id=None, direction="horizontal", inline=False):
        """Create a group of related buttons with optional inline label and layout.
        
        When inline=True, the label and buttons are forced onto one line by setting
        the container display to flex with row direction.
        """
        # Determine styles based on inline parameter
        if inline:
            container_style = {"display": "flex", "flexDirection": "row", "alignItems": "center"}
            label_style = {"marginRight": "10px", "display": "flex", "alignItems": "center"}
            button_container_style = {"display": "flex", "flexDirection": "row", "alignItems": "center"}
        else:
            container_style = {}
            label_style = {}
            button_container_style = {}
        
        group_class_name = f"button-group button-group--{direction}"
        
        # Build each button element
        button_elements = []
        for btn in buttons:
            # Determine whether this button is active
            is_active = btn.get("default", False) or btn["id"] == active_button_id
            
            # Create the button with consistent styling
            button = cls.create_button(
                label=btn.get("label", ""),
                button_id=btn["id"],
                variant=btn.get("variant", "default"),
                size=btn.get("size", "xs"),
                is_active=is_active
            )
            button_elements.append(button)
        
        # Wrap the buttons in a container, applying inline styles if needed
        button_container = html.Div(
            button_elements,
            className=group_class_name,
            style=button_container_style
        )
        
        # If there is no label, return only the button container
        if not label_text:
            return button_container
        
        # Create the label element
        label = html.Label(
            label_text,
            className="dash-label",
            style=label_style
        )
        
        # Combine the label and button container in a flex row
        return html.Div(
            [label, button_container],
            style=container_style,
            className="button-group-container"
        )



class TableFactory:
    """Factory for creating consistent data tables that rely on external CSS for styling."""

    @classmethod
    def create_data_table(cls, id, data, columns, sort_action=None, page_size=10, conditional_styles=None, **kwargs):
        from dash import dash_table

        # === Define fixed-width columns and their widths (in %) ===
        fixed_columns = {
            'update_title': 18,
            'details': 5,
            'address_title': 34,
            'price_text': 15,
            'property_tags': 28,
        }

        # Optional: alignment overrides
        column_alignments = {
            'price_text': 'center',
            'details': 'center',
            # All others default to 'left'
        }

        # Extract column IDs from column definitions
        column_ids = [col['id'] for col in columns]

        # Identify dynamic columns
        dynamic_columns = [cid for cid in column_ids if cid not in fixed_columns]

        # Calculate remaining width for dynamic columns
        total_fixed_width = sum(fixed_columns.values())
        remaining_width = 100 - total_fixed_width
        dynamic_width = remaining_width / len(dynamic_columns) if dynamic_columns else 0


        
        # Build style_cell_conditional
        style_cell_conditional = []

        # Fixed-width columns
        for col_id, width in fixed_columns.items():
            alignment = column_alignments.get(col_id, 'left')
            style_cell_conditional.append({
                'if': {'column_id': col_id},
                'width': f'{width}%',
                'textAlign': alignment,
            })

        # Dynamic columns
        for col_id in dynamic_columns:
            alignment = column_alignments.get(col_id, 'left')
            style_cell_conditional.append({
                'if': {'column_id': col_id},
                'width': f'{dynamic_width:.2f}%',
                'textAlign': alignment,
            })
        test_style = [
            {
                "if": {"column_id": "price_text"},  # Target a column you know exists
                "backgroundColor": "yellow",  # Very visible style
            }
        ]
          
        # Table config
        table_props = {
            'columns': columns,
            'data': data,
            'page_size': page_size,
            'sort_action': sort_action,
            'style_cell_conditional': test_style,
            'style_data': {
                'backgroundColor': 'white'
            },
                    
            'style_table': {
                'overflowX': 'auto',
                'width': '100%',
                'maxWidth': '100%',
            },
            # Add style_data_conditional for conditional styling
            'style_data_conditional': conditional_styles or [],
        }

      
        # Add any additional keyword arguments
        table_props.update({
            k: v for k, v in kwargs.items()
            if k != 'css' or 'css' not in table_props
        })
        print("Conditional styles:", conditional_styles)
        return dash_table.DataTable(id="apartment-table",  # Force the ID to be apartment-table
**table_props)
        print("Final table properties:", {k: v for k, v in table_props.items() if k == 'style_data_conditional'})

