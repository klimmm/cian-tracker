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
        
        # Keep only truly dynamic styles
        dynamic_style = {}
        if custom_style:
            dynamic_style = custom_style
        
        # Create the button content
        if icon:
            content = html.Div([
                html.I(className=icon, style={"marginRight": StyleManager.SPACING["xs"]}),
                html.Span(label, id=f"{button_id}-text" if label else None)
            ], className="flex-container flex-container--align-center flex-container--gap-xs")
        else:
            content = html.Span(label, id=f"{button_id}-text" if label else None)
        
        return html.Button(content, id=button_id, style=dynamic_style, className=class_name, **kwargs)
    
    @classmethod
    def create_button_group(cls, buttons, label_text=None, active_button_id=None, direction="horizontal"):
        """Create a group of related buttons"""
        group_class_name = f"button-group button-group--{direction}"
        
        # Button styles need modification for joined appearance
        button_elements = []
        
        for btn in buttons:
            # Determine whether this button is active
            is_active = btn.get("default", False) or btn["id"] == active_button_id
            
            # Create the button with joined styling
            button = cls.create_button(
                label=btn.get("label", ""),
                button_id=btn["id"],
                variant=btn.get("variant", "default"),
                size=btn.get("size", "md"),
                is_active=is_active
            )
            
            button_elements.append(button)
        
        # Create button container
        button_container = html.Div(
            button_elements,
            className=group_class_name
        )
        
        # If no label, just return the button container
        if not label_text:
            return button_container
        
        # Create label if provided
        label = html.Label(
            label_text,
            className="dash-label"
        )
        
        # Create container for everything
        return html.Div(
            [label, button_container],
            className="button-group-container"
        )


class TableFactory:
    """Factory for creating consistent data tables that rely on external CSS for styling."""

    @classmethod
    def create_data_table(cls, id, data, columns, sort_action=None, page_size=10, **kwargs):
        from dash import dash_table

        # === Define fixed-width columns and their widths ===
        fixed_columns = {
            'address_title': 48,
            'property_tags': 20,
            'price_text': 20,
            'details': 5,
        }

        # Extract all column IDs
        column_ids = [col['id'] for col in columns]

        # Dynamically identify remaining columns
        dynamic_columns = [cid for cid in column_ids if cid not in fixed_columns]

        # Compute available width for dynamic columns
        total_fixed_width = sum(fixed_columns.values())
        remaining_width = 100 - total_fixed_width
        dynamic_width = remaining_width / len(dynamic_columns) if dynamic_columns else 0

        # Construct style_cell_conditional
        style_cell_conditional = []

        # Add fixed column styles
        for col_id, width in fixed_columns.items():
            style_cell_conditional.append({
                'if': {'column_id': col_id},
                'width': f'{width}%',
                'textAlign': 'left',
            })

        # Add dynamic column styles
        for col_id in dynamic_columns:
            style_cell_conditional.append({
                'if': {'column_id': col_id},
                'width': f'{dynamic_width:.2f}%',
                'textAlign': 'left',
            })

        table_props = {
            'id': id,
            'columns': columns,
            'data': data,
            'page_size': page_size,
            'sort_action': sort_action,
            'style_cell_conditional': style_cell_conditional,
            'style_table': {
                'overflowX': 'auto',
                'width': '100%',
                'maxWidth': '100%',
            }
        }

        # Add additional kwargs (preserve flexibility)
        table_props.update({k: v for k, v in kwargs.items() if k != 'css' or 'css' not in table_props})

        return dash_table.DataTable(**table_props)
