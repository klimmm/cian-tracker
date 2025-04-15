import logging
import re
import pandas as pd
from dash import html
from app.metro import LINE_COLORS, METRO_TO_LINE
from app.formatters import NumberFormatter
from dash.development.base_component import Component

logger = logging.getLogger(__name__)


class PillFactory:
    """Factory for creating consistent pill components with unified sizing"""

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

    PRICE_COMPARISON_CONFIG = {
        "equal": {"variant": "neutral", "text": "Соответствует оценке ЦИАН"},
        "lower": {"variant": "success", "text_format": "На {}% ниже оценки ЦИАН"},
        "higher": {"variant": "error", "text_format": "На {}% выше оценки ЦИАН"},
    }

    WALKING_TIME_CONFIG = {
        "close": {
            "variant": "success",
            "custom_class": "pill--walk",
            "threshold_minutes": 12,
        },
        "medium": {
            "variant": "warning",
            "custom_class": "pill--walk",
            "threshold_minutes": 20,
        },
        "far": {"variant": "error", "custom_class": "pill--walk"},
    }

    DAYS_ACTIVE_CONFIG = {
        "new": {"variant": "success", "custom_class": "pill--new", "threshold_days": 0},
        "recent": {
            "variant": "primary",
            "custom_class": "pill--recent",
            "threshold_days": 3,
        },
        "medium": {
            "variant": "warning",
            "custom_class": "pill--medium",
            "threshold_days": 14,
        },
        "old": {"variant": "error", "custom_class": "pill--old"},
        "inactive": {"variant": "neutral", "custom_class": "pill--inactive"},
    }

    PRICE_CHANGE_CONFIG = {
        "up": {"variant": "error", "custom_class": "pill--price-change", "arrow": "↑"},
        "down": {
            "variant": "success",
            "custom_class": "pill--price-change",
            "arrow": "↓",
        },
    }

    NEIGHBORHOOD_CONFIG = {
        "special_neighborhoods": {
            "р-н Хамовники": {
                "variant": "primary",
                "custom_class": "pill--neighborhood",
            },
            "р-н Арбат": {"variant": "success", "custom_class": "pill--neighborhood"},
        },
        "other": {"variant": "neutral", "custom_class": "pill--neighborhood"},
    }

    ACTIVITY_CONFIG = {
        "active": {
            "variant": "primary",
            "custom_class": "pill--activity",
            "icon": "🔄",
        },
        "inactive": {
            "variant": "neutral",
            "custom_class": "pill--activity",
            "icon": "📦",
        },
    }

    TIME_PILL_CONFIG = {"variant": "neutral"}

    @classmethod
    def create_pill(cls, text, variant="default", custom_style=None, custom_class=None):
        """Create a pill component with standardized sizing

        Args:
            text (str): The text to display in the pill
            variant (str): Semantic variant (default, primary, success, warning, error, neutral)
            custom_style (dict): Additional custom styles to apply
            custom_class (str): Additional CSS class to apply

        Returns:
            dash.html.Div: A styled pill component
        """
        if not text:
            return None

        # Build class name based on variant only
        class_name = f"pill pill--{variant}"

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
        return cls.create_pill(price_value, variant=config["variant"])

    @classmethod
    def create_price_history_pill(cls, date, price):
        """Create a price history pill"""
        config = cls.PRICE_HISTORY_PILL_CONFIG
        text = f"{date}: {price}"
        return cls.create_pill(text, variant=config["variant"])

    @classmethod
    def create_floor_pill(cls, floor, total_floors=None):
        """Create a floor information pill"""
        config = cls.FLOOR_PILL_CONFIG
        text = f"Этаж: {floor}" if not total_floors else f"Этаж: {floor}/{total_floors}"
        return cls.create_pill(text, variant=config["variant"])

    @classmethod
    def create_property_feature_pill(cls, label, value, feature_type="apartment"):
        """Create a property feature pill with the correct styling based on type"""
        config = cls.PROPERTY_PILL_CONFIG.get(
            feature_type, cls.PROPERTY_PILL_CONFIG["apartment"]
        )
        text = f"{label}: {value}"
        return cls.create_pill(text, variant=config["variant"])

    @classmethod
    def create_amenity_pill(cls, amenity_name):
        """Create an amenity feature pill"""
        config = cls.PROPERTY_PILL_CONFIG["amenity"]
        return cls.create_pill(amenity_name, variant=config["variant"])

    @classmethod
    def create_rental_term_pill(cls, label, value):
        """Create a rental term pill"""
        config = cls.RENTAL_TERM_PILL_CONFIG
        text = f"{label}: {value}"
        return cls.create_pill(text, variant=config["variant"])

    @classmethod
    def create_distance_pill(cls, distance_text):
        """Create a distance pill"""
        config = cls.DISTANCE_PILL_CONFIG
        return cls.create_pill(distance_text, variant=config["variant"])

    @classmethod
    def create_good_price_pill(cls):
        """Create a 'good price' indicator pill"""
        config = cls.GOOD_PRICE_PILL_CONFIG
        return cls.create_pill(config["text"], variant=config["variant"])

    @classmethod
    def create_cian_estimate_pill(cls, estimate):
        """Create a CIAN estimate pill"""
        config = cls.CIAN_ESTIMATE_PILL_CONFIG
        text = config["text_format"].format(estimate)
        return cls.create_pill(text, variant=config["variant"])

    @classmethod
    def create_time_pill(cls, time_value):
        """Create a time display pill"""
        config = cls.TIME_PILL_CONFIG
        return cls.create_pill(time_value, variant=config["variant"])

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
                return cls.create_pill(config["text"], config["variant"])
            elif diff < 0:
                config = cls.PRICE_COMPARISON_CONFIG["lower"]
                return cls.create_pill(
                    config["text_format"].format(abs(percent)), config["variant"]
                )
            else:
                config = cls.PRICE_COMPARISON_CONFIG["higher"]
                return cls.create_pill(
                    config["text_format"].format(percent), config["variant"]
                )
        except Exception as e:
            logger.error(f"Price comparison error: {e}")
            return None

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

    @classmethod
    def create_pill_container(
        cls, pills, wrap=False, align=None, custom_style=None, return_as_html=False
    ):
        """Create a container for multiple pills with flexible layout.

        Args:
            pills (list): List of pill components.
            wrap (bool): Whether to allow wrapping of pills.
            align (str): Optional align-items setting.
            custom_style (dict): Additional styles to apply to the container.
            return_as_html (bool): If True, returns HTML string instead of component.

        Returns:
            dash.html.Div or str: A Dash component or HTML string.
        """
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
            "gap": "2px",
        }

        if align:
            style["alignItems"] = align

        if custom_style:
            style.update(custom_style)

        container = html.Div(pills, style=style)

        if return_as_html:
            return cls.to_html_string(container)

        return container

    # --- Specialized pill types ---

    @classmethod
    def create_metro_pill(cls, metro_station):
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

        return cls.create_pill(clean_station, "metro", custom_styles)

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
            time_text, variant=config["variant"], custom_class=config["custom_class"]
        )

    @classmethod
    def create_neighborhood_pill(cls, neighborhood):
        """Format neighborhood pill with appropriate styling."""
        if not neighborhood or neighborhood == "nan" or neighborhood == "None":
            return None

        # Check if it's a special neighborhood
        for special_name, config in cls.NEIGHBORHOOD_CONFIG[
            "special_neighborhoods"
        ].items():
            if special_name in neighborhood:
                return cls.create_pill(
                    neighborhood,
                    variant=config["variant"],
                    custom_class=config["custom_class"],
                )

        # Default to "other" config
        config = cls.NEIGHBORHOOD_CONFIG["other"]
        return cls.create_pill(
            neighborhood, variant=config["variant"], custom_class=config["custom_class"]
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
            display_text, variant=config["variant"], custom_class=config["custom_class"]
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
            config = (
                cls.PRICE_CHANGE_CONFIG["down"]
                if value < 0
                else cls.PRICE_CHANGE_CONFIG["up"]
            )

            display = f"{NumberFormatter.format_number(abs(value))}"
            return cls.create_pill(
                f"{config['arrow']} {display}",
                variant=config["variant"],
                custom_class=config["custom_class"],
            )
        except:
            return None

    @classmethod
    def create_activity_date_pill(cls, activity_date, status="active"):
        """Create activity date pill with appropriate styling."""
        if not activity_date or pd.isna(activity_date):
            return None

        # Choose configuration based on status
        config = (
            cls.ACTIVITY_CONFIG["active"]
            if status == "active"
            else cls.ACTIVITY_CONFIG["inactive"]
        )

        # Create pill with icon prefix
        activity_text = f"{config['icon']} {activity_date}"
        return cls.create_pill(
            activity_text,
            variant=config["variant"],
            custom_class=config["custom_class"],
        )
