# app/components.py
from dash import html
import logging

logger = logging.getLogger(__name__)

class UIComponentFactory:
    """Base factory for all UI components with consistent styling."""
    
    @staticmethod
    def create_container(children, style=None, custom_class=None, **kwargs):
        """Create a generic container with consistent styling."""
        base_style = {
            "margin": "0",
            "padding": "0",
        }
        
        if style:
            base_style.update(style)
            
        return html.Div(children, style=base_style, className=custom_class, **kwargs)

class PillFactory:
    """Factory for creating pill/tag components with consistent styling."""
    
    @staticmethod
    def create(text, bg_color="#f0f0f0", text_color="#333", custom_style=None):
        """Create a pill/tag component with standard styling."""
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
    
    # Define button type style mappings once
    BUTTON_STYLES = {
        "default": {"backgroundColor": "#f5f5f5"},
        "price": {"backgroundColor": "#e8e8e0"},
        "distance": {"backgroundColor": "#e0e4e8"},
        "nearest": {"backgroundColor": "#d9edf7"},
        "below_estimate": {"backgroundColor": "#fef3d5"},
        "updated_today": {"backgroundColor": "#dff0d8"},
        "inactive": {"backgroundColor": "#f4f4f4"},
        "sort": {"backgroundColor": "#e0e0e8"}
    }
    
    @staticmethod
    def create(label, button_id, button_type="default", is_active=False, custom_style=None, **kwargs):
        """Create a styled button."""
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
        if button_type in ButtonFactory.BUTTON_STYLES:
            base_style.update(ButtonFactory.BUTTON_STYLES[button_type])
            
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
    
    @staticmethod
    def create_button_group(buttons, label_text=None, active_button_id=None):
        """Create a button group with joined buttons and optional label."""
        button_elements = []
        
        # Add label if provided
        if label_text:
            button_elements.append(
                html.Label(
                    label_text,
                    className="dash-label",
                    style={
                        "marginBottom": "2px",
                        "marginRight": "5px",
                        "minWidth": "110px",
                        "width": "110px",
                        "display": "inline-block",
                        "whiteSpace": "nowrap",
                    },
                )
            )
        
        # Create container for buttons
        button_container = html.Div(
            [
                ButtonFactory.create(
                    btn["label"],
                    btn["id"],
                    button_type=btn.get("type", "default"),
                    is_active=btn.get("default", False) or btn["id"] == active_button_id,
                    custom_style={
                        "flex": "1",
                        "margin": "0",
                        "padding": "2px 0",
                        "lineHeight": "1",
                        "borderRadius": "0",
                        "borderLeft": "none" if i > 0 else "1px solid #ccc",
                        "position": "relative",
                    }
                )
                for i, btn in enumerate(buttons)
            ],
            style={
                "display": "flex",
                "flex": "1",
                "width": "100%",
                "gap": "0",
                "border-collapse": "collapse",
            },
        )
        
        button_elements.append(button_container)
        
        # Return the complete button group
        return html.Div(
            button_elements,
            style={
                "margin": "2px",
                "marginBottom": "6px",
                "textAlign": "left",
                "width": "100%",
                "display": "flex",
                "alignItems": "center",
            },
        )


class ContainerFactory:
    """Factory for creating container elements with consistent styling."""
    
    @staticmethod
    def create_section(children, title=None, custom_style=None):
        """Create a styled section container."""
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
        """Create a flexbox container with common settings."""
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
    
    @staticmethod
    def create_card(children, custom_style=None):
        """Create a card container with shadow and rounded corners."""
        base_style = {
            "padding": "10px",
            "backgroundColor": "#fff",
            "borderRadius": "6px",
            "boxShadow": "0 2px 8px rgba(0, 0, 0, 0.1)",
            "width": "100%",
            "margin": "0 auto"
        }
        
        if custom_style:
            base_style.update(custom_style)
            
        return html.Div(children, style=base_style)
    
    @staticmethod
    def create_overlay_panel(children, visible=False, custom_style=None):
        """Create a modal overlay panel."""
        base_style = {
            "position": "fixed",
            "top": "50%",
            "left": "50%",
            "transform": "translate(-50%, -50%)",
            "width": "90%",
            "maxWidth": "500px",
            "maxHeight": "100%",
            "zIndex": "1000",
            "backgroundColor": "#fff",
            "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.2)",
            "borderRadius": "8px",
            "padding": "15px",
            "overflow": "auto",
            "opacity": "1" if visible else "0",
            "visibility": "visible" if visible else "hidden",
            "pointer-events": "auto" if visible else "none"
        }
        
        if custom_style:
            base_style.update(custom_style)
            
        return html.Div(children, style=base_style)