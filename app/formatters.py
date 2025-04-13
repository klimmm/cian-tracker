# app/formatters.py
import re
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Union, Optional, Callable, Any, Dict

logger = logging.getLogger(__name__)

class FormatUtils:
    """Utility functions for text and value formatting."""
    
    @staticmethod
    def is_numeric(value: Any) -> bool:
        """Check if a value can be converted to a number."""
        if value is None:
            return False
        try:
            float(str(value).replace(" ", "").replace("₽", ""))
            return True
        except (ValueError, TypeError):
            return False
            
    @staticmethod
    def format_number(value: Any, include_currency: bool = True, 
                     abbreviate: bool = False, default: str = "--") -> str:
        """Format numbers with flexible options.
        
        Args:
            value: Numeric value to format
            include_currency: Whether to append currency symbol
            abbreviate: Whether to use K/M abbreviations for large numbers
            default: Value to return for None/invalid inputs
            
        Returns:
            Formatted number string
        """
        if not FormatUtils.is_numeric(value):
            return default

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
                
            if include_currency:
                result = f"{result} ₽"
                
            return result
        except (ValueError, TypeError):
            return default
            
    @staticmethod
    def format_text(value: Any, formatter: Callable[[Any], str], default: str = "") -> str:
        """Apply a formatter function to a value with default handling.
        
        Args:
            value: Value to format
            formatter: Function to apply
            default: Default value if input is None/NaN
            
        Returns:
            Formatted string
        """
        if value is None or pd.isna(value):
            return default
        return formatter(value)
    
    @staticmethod
    def pluralize_ru(number: int, default_form: str, 
                    acc_one_form: str, acc_few_form: str, 
                    acc_many_form: str) -> str:
        """Returns the correct Russian word form based on number.
        
        Args:
            number: The number to base the form on
            default_form: Default form to use if no specific form applies
            acc_one_form: Form for accusative case, singular (1)
            acc_few_form: Form for accusative case, few (2-4)
            acc_many_form: Form for accusative case, many (5+)
            
        Returns:
            The appropriate word form
        """
        n = abs(number) % 100
        if 11 <= n <= 19:
            return acc_many_form
            
        n = n % 10
        if n == 1:
            if default_form == "минута": 
                return "минуту"  # Special case
            return acc_one_form
        elif 2 <= n <= 4:
            return acc_few_form
        else:
            return acc_many_form


class PriceFormatter:
    """Unified price and financial value formatting functions."""
    
    @staticmethod
    def format_price(value: Any, include_currency: bool = True, 
                    abbreviate: bool = False, default: str = "--") -> str:
        """Format price with flexible options.
        
        Args:
            value: Numeric price value
            include_currency: Whether to append currency symbol
            abbreviate: Whether to use K/M abbreviations for large numbers
            default: Value to return for None/invalid inputs
            
        Returns:
            Formatted price string
        """
        if value is None or pd.isna(value) or value == 0:
            return default
            
        try:
            amount_num = int(float(value))
            
            if abbreviate:
                if amount_num >= 1000000:
                    result = f"{amount_num//1000000}M"
                elif amount_num >= 1000:
                    result = f"{amount_num//1000}K"
                else:
                    result = f"{amount_num}"
            else:
                result = f"{'{:,}'.format(amount_num).replace(',', ' ')}"
                
            if include_currency:
                result = f"{result} ₽"
                
            return result
            
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def format_price_change(value: Any, decimal_places: int = 0) -> str:
        """Enhanced format for price changes with styling hints.
        
        Args:
            value: Change in price value (positive or negative)
            decimal_places: Number of decimal places to show
            
        Returns:
            Formatted string with styling information or empty string
        """
        if value is None or pd.isna(value):
            return ""
        if isinstance(value, str) and value.lower() == "new":
            return ""
            
        try:
            value = float(value)
        except (ValueError, TypeError):
            return ""
            
        if abs(value) < 1:
            return ""

        # Colors for price changes
        color = "#2a9d8f" if value < 0 else "#d62828"
        bg_color = "#e6f7f5" if value < 0 else "#fbe9e7"
        arrow = "↓" if value < 0 else "↑"
        
        # Format the number based on size
        if abs(value) >= 1000:
            display = f"{abs(int(value))//1000}K"
        else:
            formatter = f"{{:.{decimal_places}f}}" if decimal_places > 0 else "{:.0f}"
            display = formatter.format(abs(value))

        return (
            f'<span style="color:{color}; font-weight:bold; background-color:{bg_color}; '
            f'padding:2px 4px; font-size:0.5rem !important; border-radius:4px; display:inline-block; margin-top:2px;">'
            f"{arrow} {display}</span>"
        )
    
    @staticmethod
    def format_commission(value: Any) -> str:
        """Format commission value as percentage or default if unknown."""
        if value == 0:
            return "0%"
        elif isinstance(value, (int, float)):
            return f"{int(value)}%" if value.is_integer() else f"{value}%"
        else:
            return "--"
    
    @staticmethod
    def format_deposit(value: Any) -> str:
        """Format deposit values with appropriate abbreviations."""
        if value is None or pd.isna(value) or value == "--":
            return "--"
        if value == 0:
            return "0₽"
        elif isinstance(value, (int, float)):
            return PriceFormatter.format_price(value, include_currency=False, abbreviate=True) + "₽"
        return "--"
    
    @staticmethod
    def calculate_monthly_burden(rent: float, commission_pct: float, deposit: float) -> Optional[float]:
        """Calculate average monthly financial burden over 12 months."""
        try:
            if pd.isna(rent) or rent <= 0:
                return None

            comm = 0 if pd.isna(commission_pct) else commission_pct
            dep = 0 if pd.isna(deposit) else deposit

            annual_rent = rent * 12
            commission_fee = rent * (comm / 100)
            
            total_burden = (annual_rent + commission_fee + deposit) / 12
            return total_burden
            
        except Exception as e:
            logger.error(f"Error calculating burden: {e}")
            return None


class TimeFormatter:
    """Time and date formatting utilities."""
    
    @staticmethod
    def format_date(dt: datetime, timezone=None, relative_threshold_hours: int = 24) -> str:
        """Format date with relative time for recent dates and improved month formatting.
        
        Args:
            dt: Datetime to format
            timezone: Timezone to use (optional)
            relative_threshold_hours: Hours threshold for relative time
            
        Returns:
            Formatted date/time string
        """
        if dt is None or pd.isna(dt):
            return "--"
            
        # Russian month names abbreviations
        month_names = {
            1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
            7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек"
        }
            
        now = datetime.now(timezone) if timezone else datetime.now()
        if dt.tzinfo is None and timezone:
            dt = dt.replace(tzinfo=timezone)
            
        delta = now - dt
        today = now.date()
        yesterday = today - timedelta(days=1)
    
        if delta < timedelta(minutes=1):
            return "только что"
        elif delta < timedelta(hours=1):
            minutes = int(delta.total_seconds() // 60)
            return f"{minutes} {FormatUtils.pluralize_ru(minutes, 'минут', 'минута', 'минуты', 'минут')} назад"
        elif delta < timedelta(hours=6):  # Show exact hours only up to 6 hours
            hours = int(delta.total_seconds() // 3600)
            return f"{hours} {FormatUtils.pluralize_ru(hours, 'час', 'час', 'часа', 'часов')} назад"
        elif dt.date() == today:
            # Use "сегодня" for today but more than 6 hours ago
            return f"сегодня, {dt.hour:02}:{dt.minute:02}"
        elif dt.date() == yesterday:
            return f"вчера, {dt.hour:02}:{dt.minute:02}"
        else:
            # Format with month name
            return f"{dt.day} {month_names[dt.month]}, {dt.hour:02}:{dt.minute:02}"
    
    @staticmethod
    def format_walking_time(distance_km: Optional[float]) -> str:
        """Format walking distance into human-readable time."""
        if distance_km is None or pd.isna(distance_km):
            return ""
            
        # Calculate walking time based on average speed (5 km/h)
        walking_minutes = (distance_km / 5) * 60

        # Format time display
        if walking_minutes < 60:
            return f"{int(walking_minutes)}м"  # Short version
        else:
            hours = int(walking_minutes // 60)
            minutes = int(walking_minutes % 60)
            if minutes == 0:
                return f"{hours}ч"
            else:
                return f"{hours}ч{minutes}м"


class DataExtractor:
    """Utilities for extracting structured data from text."""
    
    @staticmethod
    def extract_deposit_value(deposit_info: Optional[str]) -> Optional[int]:
        """Extract numeric deposit value from deposit_info string."""
        if deposit_info is None or pd.isna(deposit_info) or deposit_info == "--":
            return None

        if "без залога" in deposit_info.lower():
            return 0

        match = re.search(r"залог\s+([\d\s\xa0]+)\s*₽", deposit_info, re.IGNORECASE)
        if match:
            amount_str = match.group(1)
            clean_amount = re.sub(r"\s", "", amount_str)
            try:
                return int(clean_amount)
            except ValueError:
                return None

        return None
    
    @staticmethod
    def extract_commission_value(value: Any) -> Optional[float]:
        """Extract commission percentage from text description."""
        if value is None or pd.isna(value):
            return None
            
        value = str(value).lower()
        if "без комиссии" in value:
            return 0.0
        elif "комиссия" in value:
            match = re.search(r"(\d+)%", value)
            if match:
                return float(match.group(1))
        return None
    
    @staticmethod
    def extract_neighborhood(text: Optional[str]) -> Optional[str]:
        """Extract neighborhood name from address or district text."""
        if text is None or pd.isna(text) or text in ("nan", "None"):
            return None
            
        # Extract just the neighborhood name if it follows a pattern like "р-н Хамовники"
        if "р-н " in text:
            return text.split("р-н ")[1].strip()
        else:
            return text.strip()


class HtmlFormatter:
    """Utilities for creating HTML formatted content."""
    
    @staticmethod
    def create_tag_span(text: str, bg_color: str, text_color: str) -> str:
        """Create an HTML span tag with styling for a tag/pill.
        
        Args:
            text: Text content
            bg_color: Background color
            text_color: Text color
            
        Returns:
            HTML span tag string
        """
        tag_style = "display:inline-block; padding:1px 4px; border-radius:3px; margin-right:1px; white-space:nowrap;"
        return f'<span style="{tag_style} background-color:{bg_color}; color:{text_color};">{text}</span>'
    
    @staticmethod
    def create_flex_container(content: str) -> str:
        """Wrap content in a flex container.
        
        Args:
            content: HTML content
            
        Returns:
            HTML div with flex container
        """
        return f'<div style="display:flex; flex-wrap:wrap; gap:1px; justify-content:flex-start; padding:0;">{content}</div>'
    
    @staticmethod
    def create_centered_text(text: str, add_border: bool = False) -> str:
        """Create centered text container.
        
        Args:
            text: Text content
            add_border: Whether to add a bottom border
            
        Returns:
            HTML div with centered text
        """
        border = 'border-bottom: 1px solid #eee;' if add_border else ''
        return f'<div style="text-align:center; width:100%; {border}">{text}</div>'