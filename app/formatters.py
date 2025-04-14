# formatters.py
import pandas as pd
from datetime import datetime, timedelta

from app.config import CONFIG, MOSCOW_TZ
from app.metro import LINE_COLORS, METRO_TO_LINE
import logging

# Updated portion of formatters.py
from app.pills_factory import PillFactory
logger = logging.getLogger(__name__)

class DateFormatter:
    """Datetime formatting utilities."""

    @staticmethod
    def ensure_timezone(dt, target_tz=None):
        """Ensure datetime has correct timezone."""
        if dt is None or pd.isna(dt):
            return None

        # Default to Moscow timezone
        if target_tz is None:
            target_tz = MOSCOW_TZ

        # Convert pandas Timestamp to datetime
        if isinstance(dt, pd.Timestamp):
            dt = dt.to_pydatetime()

        # Add timezone info if missing
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=target_tz)

        return dt

    @staticmethod
    def format_date(dt, threshold_hours=24):
        """Format date with timezone awareness."""
        if dt is None or pd.isna(dt):
            return "--"

        # Ensure dt has Moscow timezone
        dt = DateFormatter.ensure_timezone(dt, MOSCOW_TZ)

        # Get current time in Moscow
        now = datetime.now(MOSCOW_TZ)

        # Calculate delta
        delta = now - dt
        seconds_ago = delta.total_seconds()

        # Russian month abbreviations
        month_names = CONFIG["months"]

        # Format based on time
        if seconds_ago < 60:
            return "только что"
        elif seconds_ago < 3600:
            minutes = int(seconds_ago // 60)
            return f"{minutes} {'минуту' if minutes == 1 else 'минуты' if 2 <= minutes <= 4 else 'минут'} назад"
        elif seconds_ago < 21600:  # 6 hours
            hours = int(seconds_ago // 3600)
            return f"{hours} {'час' if hours == 1 else 'часа' if 2 <= hours <= 4 else 'часов'} назад"

        today = now.date()
        yesterday = today - timedelta(days=1)

        if dt.date() == today:
            return f"сегодня, {dt.hour:02}:{dt.minute:02}"
        elif dt.date() == yesterday:
            return f"вчера, {dt.hour:02}:{dt.minute:02}"
        else:
            return f"{dt.day} {month_names[dt.month]}"


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


class StyleUtils:
    """Style utility functions."""

    @staticmethod
    def camel_to_kebab(s: str) -> str:
        """Convert camelCase to kebab-case."""
        import re

        return re.sub(r"(?<!^)(?=[A-Z])", "-", s).lower()




# Updated portion of formatters.py
import pandas as pd
from app.pills_factory import PillFactory

# Updated portion of formatters.py
import pandas as pd
from app.pills_factory import PillFactory

class ColumnFormatter:
    """Centralized column formatting for consistent display using PillFactory."""

    @staticmethod
    def _create_html_string(pill_component):
        """Convert a pill component to an HTML string for DataTable compatibility."""
        if pill_component is None:
            return ""
            
        # Extract information from the pill component
        try:
            # Get content text
            if hasattr(pill_component, 'children') and pill_component.children:
                content = pill_component.children
            else:
                content = ""
                
            # Get class name
            class_name = pill_component.className if hasattr(pill_component, 'className') else ""
            
            # Get style dictionary
            style_dict = pill_component.style if hasattr(pill_component, 'style') else {}
            
            # Convert style dict to CSS string
            style_str = ""
            if style_dict:
                style_parts = []
                for key, value in style_dict.items():
                    css_key = PillFactory.camel_to_kebab(key)
                    style_parts.append(f"{css_key}: {value}")
                style_str = "; ".join(style_parts)
            
            # Create the HTML string
            return f'<span class="{class_name}" style="{style_str}">{content}</span>'
        except Exception as e:
            logging.error(f"Error converting pill to HTML: {e}")
            return str(pill_component)
    
    @staticmethod
    def _create_container_html(pills, gap="sm", wrap=False, align=None):
        """Create an HTML string container for multiple pills."""
        if not pills:
            return ""
            
        # Filter out None/empty pills
        html_pills = [ColumnFormatter._create_html_string(pill) for pill in pills if pill is not None]
        if not html_pills:
            return ""
        
        # Get configuration from PillFactory
        container_config = PillFactory.CONTAINER_CONFIG
        
        # Set flex container style
        style = f"display: {container_config['default']['display']}; "
        style += f"flex-wrap: {'wrap' if wrap else container_config['default']['flexWrap']};"
        
        if gap:
            gap_size = container_config['spacing'].get(gap, container_config['spacing']['sm'])
            style += f" gap: {gap_size};"
        
        if align:
            style += f" align-items: {align};"
        
        # Join the HTML strings in a container
        return f'<div style="{style}">{"".join(html_pills)}</div>'

    @staticmethod
    def format_price_column(row):
        """Format price column with consistent pills."""
        pills = []

        # Main price pill
        price_formatted = row.get("price_value_formatted", "--")
        if price_formatted and price_formatted != "--":
            pills.append(PillFactory.create_price_pill(price_formatted))

        # Price change pill
        price_change = row.get("price_change_value", 0)
        if price_change:
            pills.append(PillFactory.create_price_change_pill(price_change))

        # Good price pill
        if row.get("price_difference_value", 0) > 0 and row.get("status") != "non active":
            pills.append(PillFactory.create_good_price_pill())

        # CIAN estimation pill
        cian_est = row.get("cian_estimation_formatted")
        if pd.notnull(cian_est) and cian_est != "--" and cian_est != row.get("price_value_formatted"):
            pills.append(PillFactory.create_cian_estimate_pill(cian_est))

        return ColumnFormatter._create_container_html(pills)

    @staticmethod
    def format_update_title(row):
        """Format update title column with activity date if available."""
        pills = []

        # Time string as a pill
        time_str = row.get("updated_time", "--")
        if time_str and time_str != "--":
            pills.append(PillFactory.create_time_pill(time_str))

        # Days active pill
        days_active = row.get("days_active")
        days_value = row.get("days_active_value", 0)
        if pd.notnull(days_active) and days_active != "--":
            pills.append(PillFactory.create_days_active_pill(days_value, row.get("status", "active")))

        # Activity date formatting
        should_add_activity_date = "activity_date" in row and not pd.isna(row["activity_date"])

        # Skip if same as updated time
        if should_add_activity_date and pd.notnull(row.get("updated_time_sort")) and pd.notnull(row.get("activity_date_sort")):
            time_diff = abs((row["activity_date_sort"] - row["updated_time_sort"]).total_seconds())
            if time_diff < 60:
                should_add_activity_date = False

        if should_add_activity_date:
            activity_date = row["activity_date"]
            pills.append(PillFactory.create_activity_date_pill(activity_date, row.get("status", "active")))

        return ColumnFormatter._create_container_html(pills)

    @staticmethod
    def format_property_tags(row):
        """Format property pills column consistently."""
        pills = []

        # Process distance and nearby status
        distance_value = row.get("distance_sort")
        is_nearby = False
        if distance_value is not None and not pd.isna(distance_value):
            pills.append(PillFactory.create_walking_time_pill(distance_value))
            is_nearby = distance_value < 1.5 and row.get("status") != "non active"

        # Process neighborhood information
        is_hamovniki = False
        is_arbat = False
        neighborhood = str(row.get("neighborhood", ""))
        if neighborhood and neighborhood != "nan" and neighborhood != "None":
            # Extract neighborhood name
            if "р-н " in neighborhood:
                neighborhood_name = neighborhood.split("р-н ")[1].strip()
            else:
                neighborhood_name = neighborhood.strip()

            # Set neighborhood flags
            is_hamovniki = "Хамовники" in neighborhood
            is_arbat = "Арбат" in neighborhood

            # Add neighborhood pill
            pills.append(PillFactory.create_neighborhood_pill(neighborhood_name, is_hamovniki, is_arbat))

        # Add metro station pill
        if metro_station := row.get("metro_station"):
            pills.append(PillFactory.create_metro_pill(metro_station))

        return ColumnFormatter._create_container_html(pills)