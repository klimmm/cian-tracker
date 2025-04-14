# app/pills_factory.py - Complete centralization of pill configuration
import logging
import pandas as pd
import re
from dash import html
from app.config import CONFIG, MOSCOW_TZ
from app.metro import LINE_COLORS, METRO_TO_LINE
from app.components import StyleManager

logger = logging.getLogger(__name__)

class NumberFormatter:
    """Number formatting utilities."""

    @staticmethod
    def is_numeric(value):
        """Check if value can be converted to a number."""
        if value is None or pd.isna(value):
            return False
        try:
            float(str(value).replace(" ", "").replace("₽", ""))
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def format_number(value, include_currency=True, abbreviate=False, default="--"):
        """Format numbers with options."""
        if not NumberFormatter.is_numeric(value):
            return default

        import re

        clean_value = re.sub(r"[^\d.]", "", str(value))
        try:
            num = int(float(clean_value))

            if abbreviate:
                if num >= 1000000:
                    result = f"{num//1000000}M"
                elif num >= 1000:
                    result = f"{num//1000}K"
                else:
                    result = f"{num}"
            else:
                result = "{:,}".format(num).replace(",", " ")

            return f"{result} ₽" if include_currency else result
        except:
            return default

class PillFactory:
    """Factory for creating consistent pill components across the application"""
    
    # ===== PILL CONFIGURATION =====
    
    # Size configurations
    SIZE_CONFIG = {
        "xs": {
            "fontSize": "0.75rem", 
            "padding": "0.125rem 0.25rem"
        },
        "sm": {
            "fontSize": "0.875rem", 
            "padding": "0.25rem 0.5rem"
        },
        "md": {
            "fontSize": "1rem", 
            "padding": "0.375rem 0.75rem"
        },
        "lg": {
            "fontSize": "1.125rem", 
            "padding": "0.5rem 1rem"
        }
    }
    
    # Variant/type configurations
    VARIANT_CONFIG = {
        "default": {
            "backgroundColor": "#f3f4f6",
            "color": "#374151",
            "border": "1px solid #e5e7eb"
        },
        "primary": {
            "backgroundColor": "#e0f2fe",
            "color": "#0369a1",
            "border": "1px solid #bae6fd"
        },
        "success": {
            "backgroundColor": "#dcfce7",
            "color": "#166534",
            "border": "1px solid #bbf7d0"
        },
        "warning": {
            "backgroundColor": "#fef3c7",
            "color": "#9a3412",
            "border": "1px solid #fde68a"
        },
        "error": {
            "backgroundColor": "#fee2e2",
            "color": "#b91c1c",
            "border": "1px solid #fecaca"
        },
        "neutral": {
            "backgroundColor": "#f9fafb",
            "color": "#6b7280",
            "border": "1px solid #f3f4f6"
        },
        "metro": {
            "color": "#ffffff",
            "border": "none",
            "fontWeight": "500"
        }
    }
    
    # Special pill configurations
    
    # Price pill configuration
    PRICE_PILL_CONFIG = {
        "default": {
            "variant": "primary",
            "size": "md",
            "custom_style": {"fontWeight": "600"}
        }
    }
    
    # Price history pill configuration
    PRICE_HISTORY_PILL_CONFIG = {
        "variant": "neutral",
        "size": "xs"
    }
    
    # Floor pill configuration 
    FLOOR_PILL_CONFIG = {
        "variant": "primary",
        "size": "sm"
    }
    
    # Property feature pill configurations
    PROPERTY_PILL_CONFIG = {
        "apartment": {
            "variant": "primary",
            "size": "sm"
        },
        "building": {
            "variant": "neutral",
            "size": "sm"
        },
        "amenity": {
            "variant": "success",
            "size": "sm"
        }
    }
    
    # Rental term pill configuration
    RENTAL_TERM_PILL_CONFIG = {
        "variant": "neutral",
        "size": "sm"
    }
    
    # Distance pill configuration
    DISTANCE_PILL_CONFIG = {
        "variant": "neutral",
        "size": "sm"
    }
    
    # Good price pill configuration
    GOOD_PRICE_PILL_CONFIG = {
        "variant": "success",
        "size": "sm",
        "text": "хорошая цена"
    }
    
    # CIAN estimate pill configuration
    CIAN_ESTIMATE_PILL_CONFIG = {
        "variant": "neutral",
        "size": "sm",
        "text_format": "оценка: {}"
    }
    
    # Price comparison configuration
    PRICE_COMPARISON_CONFIG = {
        "equal": {
            "variant": "neutral",
            "size": "sm",
            "text": "Соответствует оценке ЦИАН"
        },
        "lower": {
            "variant": "success",
            "size": "sm",
            "text_format": "На {}% ниже оценки ЦИАН"
        },
        "higher": {
            "variant": "error",
            "size": "sm",
            "text_format": "На {}% выше оценки ЦИАН"
        }
    }
    
    # Walking time pill configuration
    WALKING_TIME_CONFIG = {
        "close": {
            "variant": "success",
            "custom_class": "pill--walk",
            "threshold_minutes": 12
        },
        "medium": {
            "variant": "warning",
            "custom_class": "pill--walk",
            "threshold_minutes": 20
        },
        "far": {
            "variant": "error", 
            "custom_class": "pill--walk"
        }
    }
    
    # Days active pill configuration
    DAYS_ACTIVE_CONFIG = {
        "new": {
            "variant": "success",
            "custom_class": "pill--new",
            "threshold_days": 0
        },
        "recent": {
            "variant": "primary",
            "custom_class": "pill--recent",
            "threshold_days": 3
        },
        "medium": {
            "variant": "warning",
            "custom_class": "pill--medium",
            "threshold_days": 14
        },
        "old": {
            "variant": "error",
            "custom_class": "pill--old"
        },
        "inactive": {
            "variant": "neutral",
            "custom_class": "pill--inactive"
        }
    }
    
    # Price change pill configuration
    PRICE_CHANGE_CONFIG = {
        "up": {
            "variant": "error",
            "custom_class": "pill--price-change",
            "arrow": "↑"
        },
        "down": {
            "variant": "success",
            "custom_class": "pill--price-change",
            "arrow": "↓"
        }
    }
    
    # Neighborhood pill configuration
    NEIGHBORHOOD_CONFIG = {
        "hamovniki": {
            "variant": "primary",
            "custom_class": "pill--neighborhood"
        },
        "arbat": {
            "variant": "success",
            "custom_class": "pill--neighborhood"
        },
        "other": {
            "variant": "neutral",
            "custom_class": "pill--neighborhood"
        }
    }
    
    # Activity date pill configuration
    ACTIVITY_CONFIG = {
        "active": {
            "variant": "primary",
            "custom_class": "pill--activity",
            "icon": "🔄"
        },
        "inactive": {
            "variant": "neutral",
            "custom_class": "pill--activity",
            "icon": "📦"
        }
    }
    
    # Time pill configuration
    TIME_PILL_CONFIG = {
        "variant": "neutral", 
        "size": "sm"
    }
    
    # Container configuration
    CONTAINER_CONFIG = {
        "default": {
            "display": "flex",
            "flexWrap": "nowrap",
            "alignItems": None
        },
        "spacing": {
            "xs": StyleManager.SPACING.get("xs", "0.25rem"),
            "sm": StyleManager.SPACING.get("sm", "0.5rem"),
            "md": StyleManager.SPACING.get("md", "1rem"),
            "lg": StyleManager.SPACING.get("lg", "1.5rem")
        }
    }
    
    # Style utility functions
    @staticmethod
    def camel_to_kebab(s: str) -> str:
        """Convert camelCase to kebab-case."""
        return re.sub(r"(?<!^)(?=[A-Z])", "-", s).lower()
    
    @classmethod
    def create_pill(cls, text, variant="default", size="sm", custom_style=None, custom_class=None):
        """Create a pill component with a standardized design system
        
        Args:
            text (str): The text to display in the pill
            variant (str): Semantic variant (default, primary, success, warning, error, neutral)
            size (str): Size variant (xs, sm, md)
            custom_style (dict): Additional custom styles to apply
            custom_class (str): Additional CSS class to apply
            
        Returns:
            dash.html.Div: A styled pill component
        """
        if not text:
            return None
            
        # Build class name based on variant and size
        class_name = f"pill pill--{variant} pill--{size}"
        
        # Add custom class if provided
        if custom_class:
            class_name += f" {custom_class}"
            
        # Keep only truly dynamic styles, if any
        dynamic_style = custom_style or {}
            
        return html.Div(text, style=dynamic_style, className=class_name)
    
    @classmethod
    def create_price_pill(cls, price_value):
        """Create a specifically styled price pill"""
        config = cls.PRICE_PILL_CONFIG["default"]
        
        return cls.create_pill(
            price_value,
            variant=config["variant"],
            size=config["size"],
            custom_style=config["custom_style"]
        )
    
    @classmethod
    def create_price_history_pill(cls, date, price):
        """Create a price history pill"""
        config = cls.PRICE_HISTORY_PILL_CONFIG
        text = f"{date}: {price}"
        
        return cls.create_pill(
            text,
            variant=config["variant"],
            size=config["size"]
        )
    
    @classmethod
    def create_floor_pill(cls, floor, total_floors=None):
        """Create a floor information pill"""
        config = cls.FLOOR_PILL_CONFIG
        text = f"Этаж: {floor}" if not total_floors else f"Этаж: {floor}/{total_floors}"
        
        return cls.create_pill(
            text,
            variant=config["variant"],
            size=config["size"]
        )
    
    @classmethod
    def create_property_feature_pill(cls, label, value, feature_type="apartment"):
        """Create a property feature pill with the correct styling based on type"""
        config = cls.PROPERTY_PILL_CONFIG.get(feature_type, cls.PROPERTY_PILL_CONFIG["apartment"])
        text = f"{label}: {value}"
        
        return cls.create_pill(
            text,
            variant=config["variant"],
            size=config["size"]
        )
    
    @classmethod
    def create_amenity_pill(cls, amenity_name):
        """Create an amenity feature pill"""
        config = cls.PROPERTY_PILL_CONFIG["amenity"]
        
        return cls.create_pill(
            amenity_name,
            variant=config["variant"],
            size=config["size"]
        )
    
    @classmethod
    def create_rental_term_pill(cls, label, value):
        """Create a rental term pill"""
        config = cls.RENTAL_TERM_PILL_CONFIG
        text = f"{label}: {value}"
        
        return cls.create_pill(
            text,
            variant=config["variant"],
            size=config["size"]
        )
    
    @classmethod
    def create_distance_pill(cls, distance_text):
        """Create a distance pill"""
        config = cls.DISTANCE_PILL_CONFIG
        
        return cls.create_pill(
            distance_text,
            variant=config["variant"],
            size=config["size"]
        )
    
    @classmethod
    def create_good_price_pill(cls):
        """Create a 'good price' indicator pill"""
        config = cls.GOOD_PRICE_PILL_CONFIG
        
        return cls.create_pill(
            config["text"],
            variant=config["variant"],
            size=config["size"]
        )
    
    @classmethod
    def create_cian_estimate_pill(cls, estimate):
        """Create a CIAN estimate pill"""
        config = cls.CIAN_ESTIMATE_PILL_CONFIG
        text = config["text_format"].format(estimate)
        
        return cls.create_pill(
            text,
            variant=config["variant"],
            size=config["size"]
        )
    
    @classmethod
    def create_time_pill(cls, time_value):
        """Create a time display pill"""
        config = cls.TIME_PILL_CONFIG
        
        return cls.create_pill(
            time_value,
            variant=config["variant"],
            size=config["size"]
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
                config = cls.PRICE_COMPARISON_CONFIG["equal"]
                return cls.create_pill(config["text"], config["variant"], config["size"])
            elif diff < 0:
                config = cls.PRICE_COMPARISON_CONFIG["lower"]
                return cls.create_pill(config["text_format"].format(abs(percent)), config["variant"], config["size"])
            else:
                config = cls.PRICE_COMPARISON_CONFIG["higher"]
                return cls.create_pill(config["text_format"].format(percent), config["variant"], config["size"])
        except Exception as e:
            logger.error(f"Price comparison error: {e}")
            return None
    
    @classmethod
    def create_pill_container(cls, pills, gap="sm", wrap=False, align=None, custom_style=None):
        """Create a container for multiple pills with flexible layout
        
        Args:
            pills (list): List of pill components
            gap (str): Size of gap between pills (xs, sm, md, lg)
            wrap (bool): Whether to wrap pills
            align (str): Alignment of pills (center, start, end)
            custom_style (dict): Additional custom styles
            
        Returns:
            dash.html.Div: A container with pills
        """
        if not pills:
            return None
            
        # Filter out None/empty pills
        pills = [pill for pill in pills if pill is not None]
        if not pills:
            return None
        
        # Default styles with spacing from config
        style = {
            "display": cls.CONTAINER_CONFIG["default"]["display"],
            "flexWrap": "wrap" if wrap else cls.CONTAINER_CONFIG["default"]["flexWrap"],
            "gap": cls.CONTAINER_CONFIG["spacing"].get(gap, cls.CONTAINER_CONFIG["spacing"]["sm"]),
        }
        
        if align:
            style["alignItems"] = align
        
        # Merge custom styles
        if custom_style:
            style.update(custom_style)
        
        return html.Div(pills, style=style)
    
    # --- Specialized pill types (migrated from TagFormatter) ---
    
    @classmethod
    def create_metro_pill(cls, metro_station):
        """Create metro station pill with line color."""
        if not metro_station or not isinstance(metro_station, str) or not metro_station.strip():
            return None

        # Clean station name
        clean_station = re.sub(r"\s*\([^)]*\)", "", metro_station).strip()

        # Find matching line
        line_number = None
        for station, line in METRO_TO_LINE.items():
            if station in clean_station or clean_station in station:
                line_number = line
                break

        # Get line color and create pill
        bg_color = LINE_COLORS.get(line_number, "#dadce0")

        # Dynamic styling based on line (only color is dynamic)
        custom_styles = {
            "backgroundColor": bg_color,
        }
        
        # Add text color for line 14
        if line_number == 14:
            custom_styles["color"] = "#000000"
            custom_styles["border"] = "1px solid #EF161E"
        
        return cls.create_pill(clean_station, "metro", "sm", custom_styles)
    
    @classmethod
    def create_walking_time_pill(cls, distance_value):
        """Create walking time pill based on distance."""
        if distance_value is None or pd.isna(distance_value):
            return None

        # Calculate walking time (5 km/h)
        walking_minutes = (distance_value / 5) * 60

        # Format time text
        if walking_minutes < 60:
            time_text = f"{int(walking_minutes)}м"
        else:
            hours = int(walking_minutes // 60)
            minutes = int(walking_minutes % 60)
            time_text = f"{hours}ч{minutes}м" if minutes > 0 else f"{hours}ч"

        # Choose configuration based on walking time
        if walking_minutes < cls.WALKING_TIME_CONFIG["close"]["threshold_minutes"]:
            config = cls.WALKING_TIME_CONFIG["close"]
        elif walking_minutes < cls.WALKING_TIME_CONFIG["medium"]["threshold_minutes"]:
            config = cls.WALKING_TIME_CONFIG["medium"]
        else:
            config = cls.WALKING_TIME_CONFIG["far"]

        return cls.create_pill(
            time_text, 
            variant=config["variant"], 
            size="sm", 
            custom_class=config["custom_class"]
        )
    
    @classmethod
    def create_neighborhood_pill(cls, neighborhood, is_hamovniki=False, is_arbat=False):
        """Format neighborhood pill with appropriate styling."""
        if not neighborhood or neighborhood == "nan" or neighborhood == "None":
            return None

        # Choose configuration based on neighborhood
        if is_hamovniki:
            config = cls.NEIGHBORHOOD_CONFIG["hamovniki"]
        elif is_arbat:
            config = cls.NEIGHBORHOOD_CONFIG["arbat"]
        else:
            config = cls.NEIGHBORHOOD_CONFIG["other"]

        return cls.create_pill(
            neighborhood, 
            variant=config["variant"], 
            size="sm", 
            custom_class=config["custom_class"]
        )
    
    @classmethod
    def create_days_active_pill(cls, days_value, status="active"):
        """Create days active pill with appropriate styling."""
        if pd.isna(days_value) or days_value == "--":
            return None

        # Convert days to integer if possible
        try:
            days = int(days_value) if not isinstance(days_value, str) else 0
        except:
            days = 0

        # Format display text
        if isinstance(days_value, str):
            display_text = days_value
        else:
            display_text = f"{days} дн."

        # Choose configuration based on age and status
        if status == "non active":
            config = cls.DAYS_ACTIVE_CONFIG["inactive"]
        elif days == 0:
            config = cls.DAYS_ACTIVE_CONFIG["new"]
        elif days <= cls.DAYS_ACTIVE_CONFIG["recent"]["threshold_days"]:
            config = cls.DAYS_ACTIVE_CONFIG["recent"]
        elif days <= cls.DAYS_ACTIVE_CONFIG["medium"]["threshold_days"]:
            config = cls.DAYS_ACTIVE_CONFIG["medium"]
        else:
            config = cls.DAYS_ACTIVE_CONFIG["old"]

        return cls.create_pill(
            display_text, 
            variant=config["variant"], 
            size="sm", 
            custom_class=config["custom_class"]
        )
    
    @classmethod
    def create_price_change_pill(cls, value):
        """Format price change with dynamic styling."""
        if not value or pd.isna(value) or value == 0 or value == "new":
            return None

        try:
            value = float(value)
            if abs(value) < 1:
                return None

            # Choose configuration based on price change direction
            config = cls.PRICE_CHANGE_CONFIG["down"] if value < 0 else cls.PRICE_CHANGE_CONFIG["up"]
            
            display = f"{NumberFormatter.format_number(abs(value))}"
            return cls.create_pill(
                f"{config['arrow']} {display}", 
                variant=config["variant"], 
                size="sm", 
                custom_class=config["custom_class"]
            )
        except:
            return None
    
    @classmethod
    def create_activity_date_pill(cls, activity_date, status="active"):
        """Create activity date pill with appropriate styling."""
        if not activity_date or pd.isna(activity_date):
            return None
            
        # Choose configuration based on status
        config = cls.ACTIVITY_CONFIG["active"] if status == "active" else cls.ACTIVITY_CONFIG["inactive"]
        
        # Create pill with icon prefix
        activity_text = f"{config['icon']} {activity_date}"
        return cls.create_pill(
            activity_text, 
            variant=config["variant"], 
            size="sm", 
            custom_class=config["custom_class"]
        )