# app/components.py - Optimized
from dash import html
import logging

logger = logging.getLogger(__name__)

class StyleManager:
    """Style manager for consistent styling"""
    
    @staticmethod
    def merge_styles(base_style, custom_style=None):
        """Merge base and custom styles"""
        if not custom_style:
            return base_style.copy()
        merged = base_style.copy()
        merged.update(custom_style)
        return merged
        
    @staticmethod
    def create_pill_style(bg_color="#f0f0f0", text_color="#333"):
        """Create pill/tag style"""
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
    def create_button_style(button_type="default", is_active=False, index=0, joined=False):
        """Create button style"""
        from app.config import BUTTON_STYLES, STYLE
        
        base_style = {
            "display": "inline-block",
            "padding": "3px 8px",
            "fontSize": "10px",
            "border": "1px solid #ccc",
            "margin": "0 5px 5px 0",
            "cursor": "pointer",
            "borderRadius": "4px"
        }
        
        if STYLE.get("button_base"):
            base_style.update(STYLE["button_base"])
            
        if button_type in BUTTON_STYLES:
            base_style.update(BUTTON_STYLES.get(button_type, {}))
            
        if joined:
            base_style.update({
                "flex": "1", "margin": "0", "padding": "2px 0", "fontSize": "10px",
                "lineHeight": "1", "borderRadius": "0", 
                "borderLeft": "none" if index > 0 else "1px solid #ccc", "position": "relative"
            })
            
        if is_active:
            base_style.update({"opacity": 1.0, "boxShadow": "0 0 5px #4682B4", "zIndex": 1})
        else:
            base_style.update({"opacity": 0.6, "zIndex": 0})
            
        return base_style
        
    @staticmethod
    def create_container_style(style_type="card", custom_style=None):
        """Create container style"""
        base_style = {}
        
        if style_type == "card":
            base_style = {
                "padding": "10px", "backgroundColor": "#fff", "borderRadius": "6px",
                "boxShadow": "0 2px 8px rgba(0, 0, 0, 0.1)", "width": "100%", "margin": "0 auto"
            }
        elif style_type == "section":
            base_style = {
                "marginBottom": "15px", "borderBottom": "1px solid #eee", "paddingBottom": "10px"
            }
        elif style_type == "flex":
            base_style = {
                "display": "flex", "flexWrap": "wrap", "gap": "3px",
                "justifyContent": "flex-start", "marginBottom": "10px"
            }
        
        return StyleManager.merge_styles(base_style, custom_style)

class PillFactory:
    """Factory for pills/tags"""
    
    @staticmethod
    def create(text, bg_color="#f0f0f0", text_color="#333", custom_style=None):
        """Create pill/tag component"""
        base_style = StyleManager.create_pill_style(bg_color, text_color)
        style = StyleManager.merge_styles(base_style, custom_style)
        return html.Div(text, style=style)
    
    @staticmethod
    def create_price_comparison(price, cian_est):
        """Create price comparison pill"""
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
                return PillFactory.create(f"На {abs(percent)}% ниже оценки ЦИАН", "#e1f5e1", "#2e7d32")
            else:
                return PillFactory.create(f"На {percent}% выше оценки ЦИАН", "#ffebee", "#c62828")
        except Exception as e:
            logger.error(f"Price comparison error: {e}")
            return None

class ButtonFactory:
    """Factory for styled buttons"""
    
    @staticmethod
    def create(label, button_id, button_type="default", is_active=False, custom_style=None, **kwargs):
        """Create styled button"""
        style = StyleManager.create_button_style(button_type, is_active)
        if custom_style:
            style = StyleManager.merge_styles(style, custom_style)
        return html.Button(label, id=button_id, style=style, **kwargs)
    
    @staticmethod
    def create_button_group(buttons, label_text=None, active_button_id=None):
        """Create button group"""
        elements = []
        
        if label_text:
            elements.append(html.Label(label_text, className="dash-label", style={
                "marginBottom": "2px", "marginRight": "5px", "minWidth": "110px",
                "width": "110px", "display": "inline-block", "whiteSpace": "nowrap",
                "fontSize": "10px"
            }))
        
        button_container = html.Div([
            html.Button(
                children=html.Span(btn["label"], id=f"{btn['id']}-text"),
                id=btn["id"],
                style=StyleManager.create_button_style(
                    button_type=btn.get("type", "default"),
                    is_active=btn.get("default", False) or btn["id"] == active_button_id,
                    index=i, joined=True
                )
            ) for i, btn in enumerate(buttons)
        ], style={"display": "flex", "flex": "1", "width": "100%", "gap": "0", "border-collapse": "collapse"})
        
        elements.append(button_container)
        
        return html.Div(elements, style={
            "margin": "2px", "marginBottom": "6px", "textAlign": "left",
            "width": "100%", "display": "flex", "alignItems": "center"
        })

class ContainerFactory:
    """Factory for container elements"""
    
    @staticmethod
    def create_section(children, title=None, custom_style=None):
        """Create section container"""
        style = StyleManager.create_container_style("section", custom_style)
        elements = []
        
        if title:
            elements.append(html.Div(title, style={
                "fontSize": "11px", "fontWeight": "bold", 
                "marginBottom": "10px", "color": "#4682B4"
            }))
            
        if isinstance(children, list):
            elements.extend(children)
        else:
            elements.append(children)
            
        return html.Div(elements, style=style)
    
    @staticmethod
    def create_flex_container(children, is_wrap=True, justify="flex-start", gap="3px", custom_style=None):
        """Create flex container"""
        base_style = {
            "display": "flex", "flexWrap": "wrap" if is_wrap else "nowrap",
            "gap": gap, "justifyContent": justify, "marginBottom": "10px"
        }
        style = StyleManager.merge_styles(base_style, custom_style)
        return html.Div(children, style=style)
    
    @staticmethod
    def create_card(children, custom_style=None):
        """Create card container"""
        style = StyleManager.create_container_style("card", custom_style)
        return html.Div(children, style=style)