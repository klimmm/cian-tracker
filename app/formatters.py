# app/formatters.py
import re
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class FormatUtils:
    """Utility functions for text and value formatting."""
    
    @staticmethod
    def is_numeric(value):
        """Check if a value can be converted to a number."""
        if value is None:
            return False
        try:
            float(str(value).replace(" ", "").replace("₽", ""))
            return True
        except (ValueError, TypeError):
            return False
            
    @staticmethod
    def format_number(value):
        """Format numbers with thousand separators and currency symbol."""
        if not FormatUtils.is_numeric(value):
            return value

        clean_value = re.sub(r"[^\d.]", "", str(value))
        try:
            num = int(float(clean_value))
            formatted = "{:,}".format(num).replace(",", " ")
            return f"{formatted} ₽"
        except (ValueError, TypeError):
            return value


class PriceFormatter:
    """Unified price and financial value formatting functions."""
    
    @staticmethod
    def format_price(value, include_currency=True, abbreviate=False, default="--"):
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
    def format_price_change(value, decimal_places=0):
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
            f'padding:2px 4px; border-radius:4px; display:inline-block; margin-top:2px;">'
            f"{arrow} {display}</span>"
        )
    
    @staticmethod
    def format_commission(value):
        """Format commission value as percentage or default if unknown."""
        if value == 0:
            return "0%"
        elif isinstance(value, (int, float)):
            return f"{int(value)}%" if value.is_integer() else f"{value}%"
        else:
            return "--"
    
    @staticmethod
    def format_deposit(value):
        """Format deposit values with appropriate abbreviations."""
        if value is None or pd.isna(value) or value == "--":
            return "--"
        if value == 0:
            return "0₽"
        elif isinstance(value, (int, float)):
            return PriceFormatter.format_price(value, include_currency=False, abbreviate=True) + "₽"
        return "--"
    
    @staticmethod
    def calculate_monthly_burden(rent, commission_pct, deposit):
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
    def format_date(dt, timezone=None, relative_threshold_hours=24):
        """Format date with relative time for recent dates.
        
        Args:
            dt: Datetime to format
            timezone: Timezone to use (optional)
            relative_threshold_hours: Hours threshold for relative time
            
        Returns:
            Formatted date/time string
        """
        if dt is None or pd.isna(dt):
            return "--"
            
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
            return f"{minutes} {TimeFormatter.pluralize_ru(minutes, 'минут', 'минута', 'минуты', 'минут')} назад"
        elif delta < timedelta(hours=relative_threshold_hours):
            hours = int(delta.total_seconds() // 3600)
            return f"{hours} {TimeFormatter.pluralize_ru(hours, 'час', 'час', 'часа', 'часов')} назад"
        elif dt.date() == today:
            return f"сегодня, {dt.hour:02}:{dt.minute:02}"
        elif dt.date() == yesterday:
            return f"вчера, {dt.hour:02}:{dt.minute:02}"
        else:
            # Format with month name (requires month_names dict to be passed or defined elsewhere)
            # For example: f"{dt.day} {month_names[dt.month]}, {dt.hour:02}:{dt.minute:02}"
            return f"{dt.day:02}.{dt.month:02}, {dt.hour:02}:{dt.minute:02}"
    
    @staticmethod
    def pluralize_ru(number, default_form, acc_one_form, acc_few_form, acc_many_form):
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
    
    @staticmethod
    def format_walking_time(distance_km):
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
    def extract_deposit_value(deposit_info):
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
    def extract_commission_value(value):
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
    def extract_neighborhood(text):
        """Extract neighborhood name from address or district text."""
        if text is None or pd.isna(text) or text in ("nan", "None"):
            return None
            
        # Extract just the neighborhood name if it follows a pattern like "р-н Хамовники"
        if "р-н " in text:
            return text.split("р-н ")[1].strip()
        else:
            return text.strip()