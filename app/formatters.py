# app/formatters.py
import pandas as pd
import logging
import re
from app.config import CONFIG, MOSCOW_TZ

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

    def get_minute_word(minutes: int) -> str:
        """
        Returns the correct form of the word 'минута' for a given number of minutes.

        Examples:
            1 -> "минута"
            2 -> "минуты"
            5 -> "минут"
            21 -> "минута"
            22 -> "минуты"
            25 -> "минут"
        """
        last_two = minutes % 100
        # For numbers 11-14, always use the plural form "минут"
        if 11 <= last_two <= 14:
            return "мин."

        last_digit = minutes % 10
        if last_digit == 1:
            return "мин."
        elif last_digit in {2, 3, 4}:
            return "мин."
        else:
            return "мин."

    def format_date(dt, threshold_hours=24):
        """Format date with timezone awareness."""
        import pandas as pd  # Ensure you have pandas imported
        from datetime import datetime, timedelta

        # Assuming MOSCOW_TZ, DateFormatter, and CONFIG are defined elsewhere in your code.

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
            minute_word = DateFormatter.get_minute_word(minutes)
            
            return f"{minutes} {minute_word} назад"
            print(f"{minutes} {minute_word} назад")

            
        elif seconds_ago < 21600:  # 6 hours
            hours = int(seconds_ago // 3600)
            hour_word = "час" if hours == 1 else "часа" if 2 <= hours <= 4 else "часов"
            return f"{hours} {hour_word} назад"

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
