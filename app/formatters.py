# app/formatters.py
import re
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Any, Optional, Callable, Dict

logger = logging.getLogger(__name__)

class FormatUtils:
    """Utilities for text and value formatting."""
    
    @staticmethod
    def is_numeric(value):
        """Check if value can be converted to a number."""
        if value is None:
            return False
        try:
            float(str(value).replace(" ", "").replace("₽", ""))
            return True
        except (ValueError, TypeError):
            return False
            
    @staticmethod
    def format_number(value, include_currency=True, abbreviate=False, default="--"):
        """Format numbers with flexible options."""
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
                
            return f"{result} ₽" if include_currency else result
        except (ValueError, TypeError):
            return default
            
    @staticmethod
    def format_text(value, formatter, default=""):
        """Apply formatter with default handling."""
        if value is None or pd.isna(value):
            return default
        return formatter(value)
    
    @staticmethod
    def pluralize_ru(number, default_form, acc_one_form, acc_few_form, acc_many_form):
        """Return correct Russian word form based on number."""
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
    """Price and financial value formatting."""
    
    @staticmethod
    def format_price(value, include_currency=True, abbreviate=False, default="--"):
        """Format price with options."""
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
                
            return f"{result} ₽" if include_currency else result
            
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def format_price_change(value, decimal_places=0):
        """Format price changes with styling hints."""
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

        # Format with appropriate styling
        color = "#2a9d8f" if value < 0 else "#d62828"
        bg_color = "#e6f7f5" if value < 0 else "#fbe9e7"
        arrow = "↓" if value < 0 else "↑"
        
        # Abbreviate large numbers
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
    def format_commission(value):
        """Format commission value."""
        if value == 0:
            return "0%"
        elif isinstance(value, (int, float)):
            return f"{int(value)}%" if value.is_integer() else f"{value}%"
        return "--"
    
    @staticmethod
    def format_deposit(value):
        """Format deposit value."""
        if value is None or pd.isna(value) or value == "--":
            return "--"
        if value == 0:
            return "0₽"
        elif isinstance(value, (int, float)):
            return PriceFormatter.format_price(value, include_currency=False, abbreviate=True) + "₽"
        return "--"
    
    @staticmethod
    def calculate_monthly_burden(rent, commission_pct, deposit):
        """Calculate monthly burden over 12 months."""
        try:
            if pd.isna(rent) or rent <= 0:
                return None

            comm = 0 if pd.isna(commission_pct) else commission_pct
            dep = 0 if pd.isna(deposit) else deposit

            annual_rent = rent * 12
            commission_fee = rent * (comm / 100)
            
            return (annual_rent + commission_fee + deposit) / 12
        except Exception as e:
            logger.error(f"Error calculating burden: {e}")
            return None


class TimeFormatter:
    """Time and date formatting utilities."""
    
    @staticmethod
    def format_date(dt, timezone=None, relative_threshold_hours=24):
        """Format date with relative time for recent dates."""
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
        elif delta < timedelta(hours=6):
            hours = int(delta.total_seconds() // 3600)
            return f"{hours} {FormatUtils.pluralize_ru(hours, 'час', 'час', 'часа', 'часов')} назад"
        elif dt.date() == today:
            return f"сегодня, {dt.hour:02}:{dt.minute:02}"
        elif dt.date() == yesterday:
            return f"вчера, {dt.hour:02}:{dt.minute:02}"
        else:
            return f"{dt.day} {month_names[dt.month]}"
    
    @staticmethod
    def format_walking_time(distance_km):
        """Format walking distance into time."""
        if distance_km is None or pd.isna(distance_km):
            return ""
            
        # Calculate walking time (5 km/h)
        walking_minutes = (distance_km / 5) * 60

        if walking_minutes < 60:
            return f"{int(walking_minutes)}м"
        else:
            hours = int(walking_minutes // 60)
            minutes = int(walking_minutes % 60)
            return f"{hours}ч{minutes}м" if minutes > 0 else f"{hours}ч"


class DataExtractor:
    """Utilities for extracting structured data from text."""
    
    @staticmethod
    def extract_deposit_value(deposit_info):
        """Extract numeric deposit value."""
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
        """Extract commission percentage from text."""
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
        """Extract neighborhood name from text."""
        if text is None or pd.isna(text) or text in ("nan", "None"):
            return None
            
        if "р-н " in text:
            return text.split("р-н ")[1].strip()
        return text.strip()


class HtmlFormatter:
    """Utilities for HTML formatting."""
    
    @staticmethod
    def create_tag_span(text, bg_color, text_color):
        """Create HTML tag span."""
        tag_style = "display:inline-block; padding:1px 4px; border-radius:3px; margin-right:1px; white-space:nowrap;"
        return f'<span style="{tag_style} background-color:{bg_color}; color:{text_color};">{text}</span>'
    
    @staticmethod
    def create_flex_container(content):
        """Create flex container for content."""
        return f'<div style="display:flex; flex-wrap:wrap; gap:1px; justify-content:flex-start; padding:0;">{content}</div>'
    
    @staticmethod
    def create_centered_text(text, add_border=False):
        """Create centered text container."""
        border = 'border-bottom: 1px solid #eee;' if add_border else ''
        return f'<div style="text-align:center; width:100%; {border}">{text}</div>'