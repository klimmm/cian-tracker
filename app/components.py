# app/components.py
from dash import html
import logging

logger = logging.getLogger(__name__)

class PillFactory:
    """Factory for creating pill/tag components with consistent styling."""
    
    @staticmethod
    def create(text, bg_color="#f0f0f0", text_color="#333", custom_style=None):
        """Create a pill/tag component with standard styling.
        
        Args:
            text: Text content for the pill
            bg_color: Background color (hex or named)
            text_color: Text color (hex or named)
            custom_style: Additional style attributes (dict)
        
        Returns:
            html.Div component with pill styling
        """
        base_style = {
            "display": "inline-block",
            "fontSize": "10px", 
            "backgroundColor": bg_color,
            "color": text_color,
            "borderRadius": "12px",
            "padding": "2px 6px",
            "whiteSpace": "nowrap",
            "margin": "1px",
            "boxShadow": "0 1px 1px rgba(0,0,0,0.03)"
        }
        
        # Merge custom style if provided
        if custom_style:
            base_style.update(custom_style)
            
        return html.Div(text, style=base_style)
    
    @staticmethod
    def create_price_comparison(price, cian_est):
        """Create a specialized pill showing price vs Cian estimation difference."""
        if not price or not cian_est:
            return None

        try:
            price_val = int(price)
            est_val = int(cian_est)
            diff = price_val - est_val
            percent = round((diff / est_val) * 100)

            if diff == 0:
                return PillFactory.create("Соответствует оценке ЦИАН", "#f0f0f0", "#333")

            if diff < 0:
                return PillFactory.create(
                    f"На {abs(percent)}% ниже оценки ЦИАН", "#e1f5e1", "#2e7d32"
                )
            else:
                return PillFactory.create(
                    f"На {percent}% выше оценки ЦИАН", "#ffebee", "#c62828"
                )
        except Exception as e:
            logger.error(f"Error creating price comparison pill: {e}")
            return None


class ButtonFactory:
    """Factory for creating styled buttons with consistent appearance."""
    
    @staticmethod
    def create(label, button_id, button_type="default", is_active=False, custom_style=None, **kwargs):
        """Create a styled button.
        
        Args:
            label: Button text
            button_id: HTML ID for the button
            button_type: Type identifier for style (default, price, distance, etc.)
            is_active: Whether the button should have active styling
            custom_style: Additional style attributes (dict)
            **kwargs: Additional HTML attributes
            
        Returns:
            html.Button component
        """
        # Base style for all buttons
        base_style = {
            "display": "inline-block",
            "padding": "3px 8px",
            "fontSize": "10px",
            "border": "1px solid #ccc",
            "margin": "0 5px 5px 0",
            "cursor": "pointer",
            "borderRadius": "4px"
        }
        
        # Apply type-specific styling
        type_styles = {
            "default": {"backgroundColor": "#f5f5f5"},
            "price": {"backgroundColor": "#e8e8e0"},
            "distance": {"backgroundColor": "#e0e4e8"},
            "nearest": {"backgroundColor": "#d9edf7"},
            "below_estimate": {"backgroundColor": "#fef3d5"},
            "updated_today": {"backgroundColor": "#dff0d8"},
            "inactive": {"backgroundColor": "#f4f4f4"},
            "sort": {"backgroundColor": "#e0e0e8"}
        }
        
        if button_type in type_styles:
            base_style.update(type_styles[button_type])
            
        # Apply active styling if button is active
        if is_active:
            base_style.update({
                "opacity": 1.0,
                "boxShadow": "0 0 5px #4682B4",
                "zIndex": 1
            })
        else:
            base_style.update({
                "opacity": 0.6,
                "zIndex": 0
            })
            
        # Apply any custom styles
        if custom_style:
            base_style.update(custom_style)
            
        return html.Button(label, id=button_id, style=base_style, **kwargs)


class ContainerFactory:
    """Factory for creating container elements with consistent styling."""
    
    @staticmethod
    def create_section(children, title=None, custom_style=None):
        """Create a styled section container.
        
        Args:
            children: Child components
            title: Optional section title
            custom_style: Additional style attributes (dict)
            
        Returns:
            html.Div container with consistent styling
        """
        base_style = {
            "marginBottom": "15px",
            "borderBottom": "1px solid #eee",
            "paddingBottom": "10px"
        }
        
        if custom_style:
            base_style.update(custom_style)
            
        elements = []
        
        # Add title if provided
        if title:
            elements.append(html.Div(
                title,
                style={
                    "fontSize": "11px",
                    "fontWeight": "bold",
                    "marginBottom": "10px",
                    "color": "#4682B4"
                }
            ))
            
        # Add the main children
        if isinstance(children, list):
            elements.extend(children)
        else:
            elements.append(children)
            
        return html.Div(elements, style=base_style)
    
    @staticmethod
    def create_flex_container(children, is_wrap=True, justify="flex-start", gap="3px", custom_style=None):
        """Create a flexbox container with common settings.
        
        Args:
            children: Child components
            is_wrap: Whether to wrap items
            justify: Flexbox justification (flex-start, center, etc.)
            gap: Gap between items
            custom_style: Additional style attributes (dict)
            
        Returns:
            html.Div with flexbox styling
        """
        base_style = {
            "display": "flex",
            "flexWrap": "wrap" if is_wrap else "nowrap",
            "gap": gap,
            "justifyContent": justify,
            "marginBottom": "10px",
        }
        
        if custom_style:
            base_style.update(custom_style)
            
        return html.Div(children, style=base_style)