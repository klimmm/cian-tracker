import logging
import re
import pandas as pd
from dash import html
from app.metro import LINE_COLORS, METRO_TO_LINE
from app.formatters import NumberFormatter
from dash.development.base_component import Component

logger = logging.getLogger(__name__)


class PillFactory:
    """Factory for creating consistent pill components with centralized color logic"""

    # Configuration for special pill types
    PRICE_PILL_CONFIG = {"default": {"variant": "primary"}}
    PRICE_HISTORY_PILL_CONFIG = {"variant": "neutral"}
    FLOOR_PILL_CONFIG = {"variant": "primary"}
    PROPERTY_PILL_CONFIG = {
        "apartment": {"variant": "primary"},
        "building": {"variant": "neutral"},
        "amenity": {"variant": "success"},
    }
    RENTAL_TERM_PILL_CONFIG = {"variant": "neutral"}
    DISTANCE_PILL_CONFIG = {"variant": "neutral"}
    GOOD_PRICE_PILL_CONFIG = {"variant": "success", "text": "хорошая цена"}
    CIAN_ESTIMATE_PILL_CONFIG = {"variant": "neutral", "text_format": "оценка: {}"}
    
    
    ROOM_CONFIG = {
        0: {"variant": "warning", "custom_class": "pill--room", "text": "студия"},
        1: {"variant": "neutral", "custom_class": "pill--room", "text": "1-комн."},
        2: {"variant": "success", "custom_class": "pill--room", "text": "2-комн."},
        3: {"variant": "success", "custom_class": "pill--room", "text": "3-комн."},
        "default": {"variant": "error", "custom_class": "pill--room", "text_format": "{}-комн."}
    }
    
    AREA_CONFIG = {
        "extra_small": {"variant": "error", "custom_class": "pill--area", "max": 16},
        "very_small": {"variant": "warning", "custom_class": "pill--area", "max": 21},
        "small": {"variant": "neutral", "custom_class": "pill--area", "max": 34},
        "medium_small": {"variant": "primary", "custom_class": "pill--area", "max": 50},
        "medium": {"variant": "success", "custom_class": "pill--area", "max": 70},
        "medium_large": {"variant": "warning", "custom_class": "pill--area", "max": 100},
        "large": {"variant": "error", "custom_class": "pill--area"}
    }
    
    FLOOR_CONFIG = {
        "first": {"variant": "warning", "custom_class": "pill--floor"},
        "low": {"variant": "primary", "custom_class": "pill--floor"},  # New tier for floors 2-5
        "middle": {"variant": "neutral", "custom_class": "pill--floor"},
        "top": {"variant": "warning", "custom_class": "pill--floor"}
    }
    
    WALKING_TIME_CONFIG = {
        "very_close": {"variant": "success", "custom_class": "pill--distance", "max_minutes": 12},
        "close": {"variant": "primary", "custom_class": "pill--distance", "max_minutes": 20},
        "medium": {"variant": "neutral", "custom_class": "pill--distance", "max_minutes": 35},  # Changed to neutral
        "far": {"variant": "error", "custom_class": "pill--distance"}
    }
    
    PRICE_CHANGE_CONFIG = {
        "up": {"variant": "error", "custom_class": "pill--price-change", "arrow": "↑"},
        "down": {"variant": "success", "custom_class": "pill--price-change", "arrow": "↓"}
    }
    
    NEIGHBORHOOD_CONFIG = {
        "special": {
            "р-н Хамовники": {"variant": "success", "custom_class": "pill--location"},
            "р-н Арбат": {"variant": "primary", "custom_class": "pill--location"}
        },
        "default": {"variant": "neutral", "custom_class": "pill--location"}
    }
    
    ACTIVITY_CONFIG = {
        "active": {"variant": "primary", "custom_class": "pill--activity", "icon": "🔄"},
        "inactive": {"variant": "neutral", "custom_class": "pill--activity", "icon": "📦"}
    }
    
    TIME_CONFIG = {"variant": "neutral", "custom_class": "pill--time"}

    # Centralized configuration for pill styling
    PRICE_CONFIG = {
        "tiers": {
            "low": {"variant": "success", "custom_class": "pill--price", "max_value": 60000},
            "medium": {"variant": "primary", "custom_class": "pill--price", "max_value": 75000},
            "high": {"variant": "neutral", "custom_class": "pill--price"}
        },
    }
    
    CIAN_ESTIMATE_CONFIG = {
        "variant": "neutral",
        "custom_class": "pill--price",
        "text_format": "оценка: {}"
    }
    
    # Styling for inactive pills
    INACTIVE_STYLE = {
        "backgroundColor": "#e0e0e0",
        "color": "#757575",
        "borderColor": "#bdbdbd"
    }
    
    @classmethod
    def create_property_feature_pill(cls, label, value, feature_type="apartment", status="active"):
        """Create a property feature pill with the correct styling based on type"""
        config = cls.PROPERTY_PILL_CONFIG.get(
            feature_type, cls.PROPERTY_PILL_CONFIG["apartment"]
        )
        text = f"{label}: {value}"
        return cls.create_pill(text, variant=config["variant"], status=status)

    @classmethod
    def create_amenity_pill(cls, amenity_name, status="active"):
        """Create an amenity feature pill"""
        config = cls.PROPERTY_PILL_CONFIG["amenity"]
        return cls.create_pill(amenity_name, variant=config["variant"], status=status)

    @classmethod
    def create_rental_term_pill(cls, label, value, status="active"):
        """Create a rental term pill"""
        config = cls.RENTAL_TERM_PILL_CONFIG
        text = f"{label}: {value}"
        return cls.create_pill(text, variant=config["variant"], status=status)    
    @classmethod
    def create_price_pill(cls, price_value, is_good_price=False, status="active"):
        """Create a price pill with centralized styling logic based on price tiers."""
        # Extract the numeric value for tier determination
        numeric_value = cls._extract_numeric_value(price_value)
        
        # Determine price tier (low/medium/high)
        config = cls.PRICE_CONFIG["tiers"]["high"]  # Default to high
        if numeric_value is not None:
            for tier_name, tier_config in cls.PRICE_CONFIG["tiers"].items():
                if "max_value" in tier_config and numeric_value <= tier_config["max_value"]:
                    config = tier_config
                    break
        
        # Start with the base custom class
        custom_class = config["custom_class"]
        
        # If it's a good deal, just add the good-deal class
        if is_good_price:
            custom_class += " pill--good-deal"
        
        # Use the same variant based on price tier
        return cls.create_pill(
            price_value, 
            variant=config["variant"], 
            custom_class=custom_class,
            status=status
        )


    @classmethod
    def create_price_history_pill(cls, date, price, status="active"):
        """Create a price history pill"""
        config = cls.PRICE_HISTORY_PILL_CONFIG
        text = f"{date}: {price}"
        return cls.create_pill(text, variant=config["variant"], status=status)        
    @staticmethod
    def _extract_numeric_value(price_string):
        """Extract numeric value from a price string."""
        if not price_string:
            return None
            
        try:
            # Remove non-numeric characters except decimal points
            numeric_str = re.sub(r'[^\d.]', '', str(price_string))
            if numeric_str:
                return float(numeric_str)
            return None
        except (ValueError, TypeError):
            return None

    @classmethod
    def create_cian_estimate_pill(cls, estimate, status="active"):
        """Create a CIAN estimate pill with centralized styling."""
        config = cls.CIAN_ESTIMATE_CONFIG
        text = config["text_format"].format(estimate)
        return cls.create_pill(
            text, 
            variant=config["variant"], 
            custom_class=config["custom_class"],
            status=status
        )

    @classmethod
    def create_room_pill(cls, room_count, status="active"):
        """Create a room pill with centralized styling logic."""
        if room_count is None:
            return None
        
        # Try to ensure room_count is an integer
        try:
            room_count = int(float(room_count))
        except (ValueError, TypeError):
            # If conversion fails, use default
            room_count = 0
            
        # Get configuration based on room count
        config = cls.ROOM_CONFIG.get(room_count, cls.ROOM_CONFIG["default"])
        
        # Determine text
        if "text" in config:
            text = config["text"]
        else:
            text = config["text_format"].format(room_count)
            
        return cls.create_pill(
            text, 
            variant=config["variant"], 
            custom_class=config["custom_class"],
            status=status
        )

    @classmethod
    def create_area_pill(cls, area, status="active"):
        """Create an area pill with centralized styling logic."""
        if area is None:
            return None
            
        # Try to ensure area is a number
        try:
            area_value = float(area)
        except (ValueError, TypeError):
            # If conversion fails, use default
            area_value = 0
            
        # Determine area category
        config = cls.AREA_CONFIG["large"]  # Default to large
        for category, category_config in cls.AREA_CONFIG.items():
            if "max" in category_config and area_value < category_config["max"]:
                config = category_config
                break
                
        text = f"{area} м²"
        return cls.create_pill(
            text, 
            variant=config["variant"], 
            custom_class=config["custom_class"],
            status=status
        )

    @classmethod
    def create_floor_pill(cls, floor, total_floors=None, status="active"):
        """Create a floor pill with centralized styling logic including the new 2-5 tier."""
        if floor is None:
            return None
            
        # Try to convert values to integers
        try:
            floor_num = int(float(floor))
            total_floors_num = int(float(total_floors)) if total_floors is not None else None
        except (ValueError, TypeError):
            # If conversion fails, still try to display something
            floor_num = floor
            total_floors_num = total_floors
            
        # Determine configuration
        if total_floors_num is not None:
            if floor_num == 1:
                config = cls.FLOOR_CONFIG["first"]
            elif floor_num == total_floors_num:
                config = cls.FLOOR_CONFIG["top"]
            elif 2 <= floor_num <= 5:
                config = cls.FLOOR_CONFIG["low"]  # New tier for floors 2-5
            else:
                config = cls.FLOOR_CONFIG["middle"]
        else:
            # If total_floors is not available, use floor number to determine tier
            if floor_num == 1:
                config = cls.FLOOR_CONFIG["first"]
            elif 2 <= floor_num <= 5:
                config = cls.FLOOR_CONFIG["low"]
            else:
                config = cls.FLOOR_CONFIG["middle"]
            
        # Format text
        text = f"{floor_num}" if total_floors is None else f"{floor_num}/{total_floors_num} эт."
        
        return cls.create_pill(
            text, 
            variant=config["variant"], 
            custom_class=config["custom_class"],
            status=status
        )

    @classmethod
    def create_distance_pill(cls, distance_text, status="active"):
        """Create a distance pill"""
        config = cls.DISTANCE_PILL_CONFIG
        return cls.create_pill(distance_text, variant=config["variant"], status=status)

    @classmethod
    def create_walking_time_pill(cls, distance_value, status="active"):
        """Create walking time pill with centralized styling logic."""
        if distance_value is None or pd.isna(distance_value):
            return None
            
        # Try to ensure distance is a number
        try:
            distance = float(distance_value)
        except (ValueError, TypeError):
            # If conversion fails, return nothing
            return None

        # Calculate walking time (5 km/h)
        walking_minutes = (distance / 5) * 60

        # Format time text
        if walking_minutes < 60:
            time_text = f"{int(walking_minutes)} мин."
        else:
            hours = int(walking_minutes // 60)
            minutes = int(walking_minutes % 60)
            time_text = f"{hours}ч{minutes}м" if minutes > 0 else f"{hours}ч"

        # Determine configuration based on walking time
        if walking_minutes < cls.WALKING_TIME_CONFIG["very_close"]["max_minutes"]:
            config = cls.WALKING_TIME_CONFIG["very_close"]
        
        elif walking_minutes < cls.WALKING_TIME_CONFIG["close"]["max_minutes"]:
            config = cls.WALKING_TIME_CONFIG["close"]
        elif walking_minutes < cls.WALKING_TIME_CONFIG["medium"]["max_minutes"]:
            config = cls.WALKING_TIME_CONFIG["medium"]
        else:
            config = cls.WALKING_TIME_CONFIG["far"]

        return cls.create_pill(
            time_text, 
            variant=config["variant"], 
            custom_class=config["custom_class"],
            status=status
        )

    @classmethod
    def create_price_change_pill(cls, value, status="active"):
        """Create price change pill with centralized styling logic."""
        if not value or pd.isna(value) or value == 0 or value == "new":
            return None

        try:
            value = float(value)
            if abs(value) < 1:
                return None

            # Determine configuration based on direction
            config = cls.PRICE_CHANGE_CONFIG["down"] if value < 0 else cls.PRICE_CHANGE_CONFIG["up"]
            
            arrow_span = html.Span(config["arrow"], className="arrow")
            display = f"{NumberFormatter.format_number(abs(value))}"
            
            return cls.create_pill(
                [arrow_span, f" {display}"],
                variant=config["variant"],
                custom_class=config["custom_class"],
                status=status
            )

        except:
            return None

    @classmethod
    def create_neighborhood_pill(cls, neighborhood, status="active"):
        """Create neighborhood pill with centralized styling logic."""
        if not neighborhood or neighborhood == "nan" or neighborhood == "None":
            return None

        # Check if it's a special neighborhood
        for special_name, config in cls.NEIGHBORHOOD_CONFIG["special"].items():
            if special_name in neighborhood:
                return cls.create_pill(
                    neighborhood,
                    variant=config["variant"],
                    custom_class=config["custom_class"],
                    status=status
                )

        # Default to "other" config
        config = cls.NEIGHBORHOOD_CONFIG["default"]
        return cls.create_pill(
            neighborhood, 
            variant=config["variant"], 
            custom_class=config["custom_class"],
            status=status
        )

    @classmethod
    def create_activity_date_pill(cls, activity_date, status="active"):
        """Create activity date pill with centralized styling logic."""
        if not activity_date or pd.isna(activity_date):
            return None

        # Choose configuration based on status
        config = cls.ACTIVITY_CONFIG["active"] if status == "active" else cls.ACTIVITY_CONFIG["inactive"]
        
        # Create pill with icon prefix
        activity_text = f"{config['icon']} {activity_date}"
        
        return cls.create_pill(
            activity_text,
            variant=config["variant"],
            custom_class=config["custom_class"],
            status=status
        )

    @classmethod
    def create_time_pill(cls, time_value, status="active"):
        """Create a time display pill with centralized styling."""
        config = cls.TIME_CONFIG
        return cls.create_pill(
            time_value, 
            variant=config["variant"], 
            custom_class=config["custom_class"],
            status=status
        )

    @classmethod
    def create_metro_pill(cls, metro_station, status="active"):
        """Create metro station pill with line color."""
        if (
            not metro_station
            or not isinstance(metro_station, str)
            or not metro_station.strip()
        ):
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

        return cls.create_pill(clean_station, "metro", custom_styles, status=status)

    @classmethod
    def create_pill(cls, text, variant="default", custom_style=None, custom_class=None, status="active"):
        """Create a pill component with standardized styling."""
        if not text:
            return None

        # Build class name based on variant
        class_name = f"pill pill--{variant}"

        # Add custom class if provided
        if custom_class:
            class_name += f" {custom_class}"
            
        # Add inactive class if status is 'non active'
        if status == "non active":
            class_name += " pill--inactive"
            
        # Keep only truly dynamic styles, if any
        dynamic_style = custom_style or {}
        
        # Apply inactive styling if status is non active
        if status == "non active":
            inactive_style = cls.INACTIVE_STYLE.copy()
            dynamic_style.update(inactive_style)

        return html.Div(text, style=dynamic_style, className=class_name)

    @classmethod
    def create_pill_container(
        cls, pills, wrap=False, align=None, custom_style=None, return_as_html=False, status="active"
    ):
        """Create a container for multiple pills with flexible layout."""
        if not pills:
            return "" if return_as_html else None

        # Filter out None pills
        pills = [pill for pill in pills if pill is not None]
        if not pills:
            return "" if return_as_html else None

        # Build container style
        style = {
            "display": "flex",
            "flexWrap": "wrap" if wrap else "nowrap",
            "gap": "0px",
        }

        if align:
            style["alignItems"] = align

        if custom_style:
            style.update(custom_style)

        container = html.Div(pills, style=style)

        if return_as_html:
            return cls.to_html_string(container)

        return container
        
    @staticmethod
    def to_html_string(component):
        """Convert a Dash HTML component to a raw HTML string recursively."""
        if component is None:
            return ""

        if not isinstance(component, Component):
            return str(component)

        tag = component.__class__.__name__.lower()
        class_attr = getattr(component, "className", "")
        style = getattr(component, "style", {})

        style_str = (
            "; ".join(
                f"{re.sub(r'(?<!^)(?=[A-Z])', '-', k).lower()}: {v}"
                for k, v in style.items()
            )
            if style
            else ""
        )

        children = getattr(component, "children", "")
        if isinstance(children, list):
            inner = "".join(PillFactory.to_html_string(child) for child in children)
        else:
            inner = PillFactory.to_html_string(children)

        return f'<{tag} class="{class_attr}" style="{style_str}">{inner}</{tag}>'