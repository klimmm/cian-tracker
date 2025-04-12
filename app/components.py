# app/components.py
from dash import html
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

class StyleManager:
    """Manager for consistent style creation and application."""
    
    @staticmethod
    def merge_styles(base_style: Dict[str, Any], custom_style: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Merge a base style with custom overrides.
        
        Args:
            base_style: Base style dictionary
            custom_style: Custom style overrides
            
        Returns:
            Merged style dictionary
        """
        if not custom_style:
            return base_style.copy()
            
        merged = base_style.copy()
        merged.update(custom_style)
        return merged
        
    @staticmethod
    def create_pill_style(bg_color: str = "#f0f0f0", text_color: str = "#333") -> Dict[str, Any]:
        """Create a standard pill/tag style.
        
        Args:
            bg_color: Background color
            text_color: Text color
            
        Returns:
            Style dictionary
        """
        return {
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
        
    @staticmethod
    def create_button_style(button_type: str = "default", is_active: bool = False, 
                           index: int = 0, joined: bool = False) -> Dict[str, Any]:
        """Create a standard button style.
        
        Args:
            button_type: Type of button (default, price, distance, etc.)
            is_active: Whether the button is active
            index: Index in button group (for joined buttons)
            joined: Whether the button is part of a joined group
            
        Returns:
            Style dictionary
        """
        # Import button styles from config
        from app.config import BUTTON_STYLES, STYLE
        
        # Get base style
        base_style = {
            "display": "inline-block",
            "padding": "3px 8px",
            "fontSize": "10px",
            "border": "1px solid #ccc",
            "margin": "0 5px 5px 0",
            "cursor": "pointer",
            "borderRadius": "4px"
        }
        
        # Update with style from config
        if STYLE.get("button_base"):
            base_style.update(STYLE["button_base"])
            
        # Apply type-specific styling
        if button_type in BUTTON_STYLES:
            base_style.update(BUTTON_STYLES.get(button_type, {}))
            
        # Apply joined button styling
        if joined:
            base_style.update({
                "flex": "1",
                "margin": "0",
                "padding": "2px 0",
                "fontSize": "10px",
                "lineHeight": "1",
                "borderRadius": "0",
                "borderLeft": "none" if index > 0 else "1px solid #ccc",
                "position": "relative",
            })
            
        # Apply active styling
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
            
        return base_style
        
    @staticmethod
    def create_container_style(style_type: str = "card", 
                               custom_style: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a standard container style.
        
        Args:
            style_type: Type of container (card, section, flex)
            custom_style: Custom style overrides
            
        Returns:
            Style dictionary
        """
        base_style = {}
        
        if style_type == "card":
            base_style = {
                "padding": "10px",
                "backgroundColor": "#fff",
                "borderRadius": "6px",
                "boxShadow": "0 2px 8px rgba(0, 0, 0, 0.1)",
                "width": "100%",
                "margin": "0 auto"
            }
        elif style_type == "section":
            base_style = {
                "marginBottom": "15px",
                "borderBottom": "1px solid #eee",
                "paddingBottom": "10px"
            }
        elif style_type == "flex":
            base_style = {
                "display": "flex",
                "flexWrap": "wrap",
                "gap": "3px",
                "justifyContent": "flex-start",
                "marginBottom": "10px",
            }
        
        return StyleManager.merge_styles(base_style, custom_style)


class PillFactory:
    """Factory for creating pill/tag components with consistent styling."""
    
    @staticmethod
    def create(text: str, bg_color: str = "#f0f0f0", text_color: str = "#333", 
               custom_style: Optional[Dict[str, Any]] = None) -> html.Div:
        """Create a pill/tag component with standard styling."""
        base_style = StyleManager.create_pill_style(bg_color, text_color)
        style = StyleManager.merge_styles(base_style, custom_style)
            
        return html.Div(text, style=style)
    
    @staticmethod
    def create_price_comparison(price: Optional[Union[str, int]], 
                                cian_est: Optional[Union[str, int]]) -> Optional[html.Div]:
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
    def create(label: str, button_id: str, button_type: str = "default", 
               is_active: bool = False, custom_style: Optional[Dict[str, Any]] = None, 
               **kwargs) -> html.Button:
        """Create a styled button."""
        style = StyleManager.create_button_style(button_type, is_active)
        
        # Apply any custom styles
        if custom_style:
            style = StyleManager.merge_styles(style, custom_style)
            
        return html.Button(label, id=button_id, style=style, **kwargs)
    
    @staticmethod
    def create_button_group(buttons: List[Dict[str, Any]], label_text: Optional[str] = None, 
                            active_button_id: Optional[str] = None) -> html.Div:
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
                        "fontSize": "10px",
                    },
                )
            )
        
        # Create container for buttons
        button_container = html.Div(
            [
                html.Button(
                    children=html.Span(btn["label"], id=f"{btn['id']}-text"),
                    id=btn["id"],
                    style=StyleManager.create_button_style(
                        button_type=btn.get("type", "default"),
                        is_active=btn.get("default", False) or btn["id"] == active_button_id,
                        index=i,
                        joined=True
                    )
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
    def create_section(children: Union[List[Any], Any], title: Optional[str] = None, 
                       custom_style: Optional[Dict[str, Any]] = None) -> html.Div:
        """Create a styled section container."""
        style = StyleManager.create_container_style("section", custom_style)
            
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
            
        return html.Div(elements, style=style)
    
    @staticmethod
    def create_flex_container(children: List[Any], is_wrap: bool = True, 
                              justify: str = "flex-start", gap: str = "3px", 
                              custom_style: Optional[Dict[str, Any]] = None) -> html.Div:
        """Create a flexbox container with common settings."""
        base_style = {
            "display": "flex",
            "flexWrap": "wrap" if is_wrap else "nowrap",
            "gap": gap,
            "justifyContent": justify,
            "marginBottom": "10px",
        }
        
        style = StyleManager.merge_styles(base_style, custom_style)
            
        return html.Div(children, style=style)
    
    @staticmethod
    def create_card(children: List[Any], 
                    custom_style: Optional[Dict[str, Any]] = None) -> html.Div:
        """Create a card container with shadow and rounded corners."""
        style = StyleManager.create_container_style("card", custom_style)
            
        return html.Div(children, style=style)
    
    @staticmethod
    def create_overlay_panel(children: List[Any], visible: bool = False, 
                             custom_style: Optional[Dict[str, Any]] = None) -> html.Div:
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
        
        style = StyleManager.merge_styles(base_style, custom_style)
            
        return html.Div(children, style=style)