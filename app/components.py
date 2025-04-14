# app/components.py - Refactored to use CSS classes
import logging
from dash import html, dcc

logger = logging.getLogger(__name__)

class StyleManager:
    """Design system with consistent styling patterns"""
    
    # Typography
    FONT_FAMILY = "'Inter', Arial, sans-serif"
    FONT_SIZES = {
        "xs": "12px",
        "sm": "14px",
        "md": "16px", 
        "lg": "18px",
        "xl": "22px"
    }
    
    # Colors
    COLORS = {
        # Primary palette
        "primary": "#4682B4",
        "primary_light": "#E6F0F9",
        "primary_dark": "#365F8A",
        
        # Semantic colors
        "success": "#2E7D32",
        "success_light": "#E8F5E9",
        "warning": "#F9A825",
        "warning_light": "#FFF8E1",
        "error": "#C62828",
        "error_light": "#FFEBEE",
        "neutral": "#607D8B",
        "neutral_light": "#ECEFF1",
        
        # UI colors
        "text_primary": "#333333",
        "text_secondary": "#666666",
        "text_light": "#999999",
        "bg_main": "#FFFFFF",
        "bg_light": "#F8F9FA",
        "border": "#E0E0E0"
    }
    
    # Spacing
    SPACING = {
        "xs": "4px",
        "sm": "8px",
        "md": "12px",
        "lg": "16px",
        "xl": "24px",
        "xxl": "32px"
    }
    
    # UI Elements
    RADIUS = {
        "sm": "4px",
        "md": "8px",
        "lg": "12px"
    }
    
    SHADOW = {
        "sm": "0 1px 3px rgba(0,0,0,0.1)",
        "md": "0 4px 6px rgba(0,0,0,0.1)",
        "lg": "0 10px 25px rgba(0,0,0,0.1)"
    }
    
    @classmethod
    def merge_styles(cls, base_style, custom_style=None):
        """Merge base and custom styles with validation"""
        if not custom_style:
            return base_style.copy()
        merged = base_style.copy()
        merged.update(custom_style)
        return merged


class PillFactory:
    """Factory for creating consistent pill/tag components"""
    
    @classmethod
    def create_pill(cls, text, variant="default", size="sm", custom_style=None):
        """Create a pill component with a standardized design system
        
        Args:
            text (str): The text to display in the pill
            variant (str): Semantic variant (default, primary, success, warning, error, neutral)
            size (str): Size variant (xs, sm, md)
            custom_style (dict): Additional custom styles to apply
            
        Returns:
            dash.html.Div: A styled pill component
        """
        if not text:
            return None
            
        # Build class name based on variant and size
        class_name = f"pill pill--{variant} pill--{size}"
        
        # Keep only truly dynamic styles, if any
        dynamic_style = {}
        if custom_style:
            # Copy only styles that aren't covered by CSS classes
            dynamic_style = custom_style
            
        return html.Div(text, style=dynamic_style, className=class_name)
    
    @classmethod
    def create_price_pill(cls, price_value, size="md"):
        """Create a specifically styled price pill"""
        return cls.create_pill(
            price_value,
            variant="primary",
            size=size,
            custom_style={"fontWeight": "600"}
        )
    
    @classmethod
    def create_price_comparison(cls, price, estimate):
        """Create a price comparison pill showing percentage difference"""
        if not price or not estimate:
            return None
        
        try:
            price_val = int(price)
            est_val = int(estimate)
            diff = price_val - est_val
            percent = round((diff / est_val) * 100)
            
            if diff == 0:
                return cls.create_pill("Соответствует оценке ЦИАН", "neutral")
            elif diff < 0:
                return cls.create_pill(f"На {abs(percent)}% ниже оценки ЦИАН", "success")
            else:
                return cls.create_pill(f"На {percent}% выше оценки ЦИАН", "error")
        except Exception as e:
            logger.error(f"Price comparison error: {e}")
            return None


class ButtonFactory:
    """Factory for creating consistent button components"""
    
    @classmethod
    def create_button(cls, label, button_id, variant="default", size="md", outline=False,
                     is_active=False, icon=None, custom_style=None, **kwargs):
        """Create a button with consistent styling
        
        Args:
            label (str): Button text
            button_id (str): Button ID for callbacks
            variant (str): Button style variant (default, primary, success, warning, error)
            size (str): Button size (sm, md, lg)
            outline (bool): Whether to use outlined style
            is_active (bool): Whether button is in active state
            icon (str): Optional icon to display before text
            custom_style (dict): Additional custom styles
            **kwargs: Additional props to pass to html.Button
            
        Returns:
            dash.html.Button: A styled button component
        """
        # Build class name based on variant, size, and state
        class_name = f"btn btn--{variant} btn--{size}"
        
        if outline:
            class_name += " btn--outline"
            
        if is_active:
            class_name += " btn--active"
        
        # Keep only truly dynamic styles, if any
        dynamic_style = {}
        if custom_style:
            # Copy only styles that aren't covered by CSS classes
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
        """Create a group of related buttons
        
        Args:
            buttons (list): List of button configuration dictionaries
            label_text (str): Optional label text
            active_button_id (str): ID of the active button if any
            direction (str): Layout direction (horizontal, vertical)
            
        Returns:
            dash.html.Div: A container with the button group
        """
        group_class_name = f"button-group button-group--{direction}"
        
        # Button styles need modification for joined appearance
        button_elements = []
        
        for i, btn in enumerate(buttons):
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


class ContainerFactory:
    """Factory for creating consistent container components"""
    
    @classmethod
    def create_card(cls, children, title=None, footer=None, elevation="md", 
                   padding="md", custom_style=None):
        """Create a card container with consistent styling
        
        Args:
            children: Content to display in the card
            title (str): Optional card title
            footer: Optional footer content
            elevation (str): Shadow elevation (sm, md, lg)
            padding (str): Padding size (sm, md, lg)
            custom_style (dict): Additional custom styles
            
        Returns:
            dash.html.Div: A card container
        """
        # Filter out None values from children
        if isinstance(children, list):
            children = [child for child in children if child is not None]
            if not children:
                return None
        elif children is None:
            return None
            
        # Build class name
        class_name = f"card card--shadow-{elevation} card--padding-{padding}"
        
        # Build card header if title provided
        header = None
        if title:
            header = html.Div(
                html.H3(title),
                className="card-header"
            )
            
        # Build card footer if provided
        footer_element = None
        if footer:
            footer_element = html.Div(
                footer,
                className="card-footer"
            )
            
        # Keep only truly dynamic styles, if any
        dynamic_style = {}
        if custom_style:
            dynamic_style = custom_style
        
        # Build the elements list
        elements = []
        if header:
            elements.append(header)
            
        if isinstance(children, list):
            elements.extend(children)
        else:
            elements.append(children)
            
        if footer_element:
            elements.append(footer_element)
            
        return html.Div(elements, style=dynamic_style, className=class_name)
    
    @classmethod
    def create_flex_container(cls, children, direction="row", justify="flex-start",
                             align="center", wrap=True, gap="md", custom_style=None):
        """Create a flexbox container with consistent styling
        
        Args:
            children: Content to display in the container
            direction (str): Flex direction (row, column)
            justify (str): Justify content setting
            align (str): Align items setting
            wrap (bool): Whether to wrap items
            gap (str): Gap size (xs, sm, md, lg, xl)
            custom_style (dict): Additional custom styles
            
        Returns:
            dash.html.Div: A flex container
        """
        # Filter out None values
        if isinstance(children, list):
            children = [child for child in children if child is not None]
            if not children:
                return None
        elif children is None:
            return None
            
        # Build class name
        wrap_class = "flex-container--wrap" if wrap else "flex-container--nowrap"
        justify_class = f"flex-container--justify-{justify.split('-')[1] if '-' in justify else justify}"
        align_class = f"flex-container--align-{align.split('-')[1] if '-' in align else align}"
        gap_class = f"flex-container--gap-{gap}"
        
        class_name = f"flex-container flex-container--{direction} {wrap_class} {justify_class} {align_class} {gap_class}"
        
        # Keep only truly dynamic styles, if any
        dynamic_style = {}
        if custom_style:
            dynamic_style = custom_style
        
        return html.Div(children, style=dynamic_style, className=class_name)
    
    @classmethod
    def create_section(cls, children, title=None, divider=True, spacing="md", custom_style=None):
        """Create a section container with optional title and divider
        
        Args:
            children: Content to display in the section
            title (str): Optional section title
            divider (bool): Whether to show bottom divider
            spacing (str): Spacing size (sm, md, lg)
            custom_style (dict): Additional custom styles
            
        Returns:
            dash.html.Div: A section container
        """
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


class TableFactory:
    """Factory for creating consistent data tables that rely on external CSS for styling."""
        
    @classmethod
    def create_data_table(cls, id, data, columns, sort_action=None, page_size=10, **kwargs):
        """
        Create a Dash DataTable without inline styling.
        
        All visual appearance (layout, font, colors, widths, etc.) is controlled via external CSS.
        
        Args:
            id (str): Component ID.
            data (list): Table data.
            columns (list): Column definitions.
            sort_action (str, optional): Sorting behavior.
            page_size (int, optional): Number of rows per page.
            **kwargs: Additional keyword arguments for DataTable.
            
        Returns:
            dash_table.DataTable: The configured DataTable component.
        """
        from dash import dash_table
        
        # No inline styles are added here; styling will be controlled by CSS classes.
        return dash_table.DataTable(
            id=id,
            columns=columns,
            data=data,
            page_size=page_size,
            sort_action=sort_action,
            **kwargs
        )
