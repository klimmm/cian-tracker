# app/utils.py - Refactored
import pandas as pd
import json
import os
import logging
import traceback
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime, timedelta
import requests
from app.config import CONFIG, MOSCOW_TZ
from app.app_config import AppConfig
from zoneinfo import ZoneInfo
from app.metro import LINE_COLORS, METRO_TO_LINE

logger = logging.getLogger(__name__)

# Styling constants - centralized tag styles
TAG_STYLES = {
    "default": {
        "display": "inline-block",
        "font-size": "10px", 
        "background-color": "#f0f0f0",
        "color": "#333333",
        "border-radius": "4px",
        "padding": "2px 6px",
        "white-space": "nowrap",
        "margin": "0px"
    },
    "price": {
        "background-color": "#f0f7ff", 
        "fontSize": "12px", 
        "color": "#2271b1",
        "font-weight": "bold"
    },
    "price_down": {
        "backgroundColor": "#e6f7f5", 
        "color": "#2a9d8f"
    },
    "price_up": {
        "backgroundColor": "#fbe9e7", 
        "color": "#d62828"
    },
    "good_price": {
        "backgroundColor": "#fcf3cd", 
        "color": "#856404"
    },
    "cian_estimate": {
        "backgroundColor": "#f5f5f5", 
        "color": "#555555",
        "fontSize": "0.9rem"
    },
    "days_new": {
        "backgroundColor": "#e8f5e9", 
        "color": "#2e7d32"
    },
    "days_recent": {
        "backgroundColor": "#e3f2fd", 
        "color": "#1565c0"
    },
    "days_medium": {
        "backgroundColor": "#fff3e0", 
        "color": "#e65100"
    },
    "days_old": {
        "backgroundColor": "#ffebee", 
        "color": "#c62828"
    },
    "days_inactive": {
        "backgroundColor": "#f0f0f0", 
        "color": "#707070"
    },
    "walk_close": {
        "backgroundColor": "#4285f4", 
        "color": "#ffffff"
    },
    "walk_medium": {
        "backgroundColor": "#aecbfa", 
        "color": "#174ea6"
    },
    "walk_far": {
        "backgroundColor": "#dadce0", 
        "color": "#3c4043"
    },
    "neighborhood_hamovniki": {
        "backgroundColor": "#e0f7f7", 
        "color": "#0c5460"
    },
    "neighborhood_arbat": {
        "backgroundColor": "#d0d1ff", 
        "color": "#3f3fa3"
    },
    "neighborhood_other": {
        "backgroundColor": "#dadce0", 
        "color": "#3c4043"
    }
}


class ErrorHandler:
    """Error handling utilities."""

    @staticmethod
    def try_operation(
        logger, operation_name, func, *args, default_return=None, **kwargs
    ):
        """Execute operation with error handling."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {operation_name}: {str(e)}")
            return default_return


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


def is_numeric(value):
    if value is None or pd.isna(value):
        return False
    try:
        float(str(value).replace(" ", "").replace("₽", ""))
        return True
    except (ValueError, TypeError):
        return False



def format_number(value, include_currency=True, abbreviate=False, default="--"):
    """Format numbers with options."""
    if not is_numeric(value):
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


import re

def camel_to_kebab(s: str) -> str:
    """
    Convert a camelCase string to kebab-case.
    Example: "backgroundColor" -> "background-color"
    """
    return re.sub(r'(?<!^)(?=[A-Z])', '-', s).lower()

class TagCreator:
    """Centralized tag creation system"""
    
    @staticmethod
    def create_tag(text, tag_type="default", custom_styles=None):
        """Create an HTML tag with consistent styling."""
        # Get base styles for this tag type
        base_styles = TAG_STYLES.get(tag_type, TAG_STYLES["default"]).copy()
        
        # Add any custom styles
        if custom_styles:
            base_styles.update(custom_styles)
        
        # Build style string converting camelCase keys to kebab-case
        style_str = "; ".join([f"{camel_to_kebab(k)}:{v}" for k, v in base_styles.items()])
        
        # Create the span tag
        return f'<span style="{style_str}">{text}</span>'

    
    @staticmethod
    def create_container(tags, layout="flex"):
        """Create a container for tags with specified layout."""
        if not tags:
            return ""
            
        # Filter out empty tags
        tags = [tag for tag in tags if tag]
        if not tags:
            return ""
        
        # Different layout options
        layouts = {
            "flex": "display:flex; flex-wrap:wrap; gap:0px; justify-content:flex-start; padding:0;",
            "center": "display:flex; flex-wrap:wrap; gap:0px; justify-content:center; padding:0;",
            "column": "display:flex; flex-direction:column; align-items:center; justify-content:center; padding:0;"
        }
        
        style_str = layouts.get(layout, layouts["flex"])
        return f'<div style="{style_str}">{"".join(tags)}</div>'


class TagFormatter:
    """Specialized tag formatters"""
    
    @staticmethod
    def format_price_tag(price):
        """Format price as tag."""
        if not price or pd.isna(price) or price == "--":
            return ""
        return TagCreator.create_tag(price, "price")
    
    @staticmethod
    def format_price_change_tag(value):
        """Format price change with appropriate styling."""
        if not value or pd.isna(value) or value == 0 or value == "new":
            return ""
        
        try:
            value = float(value)
            if abs(value) < 1:
                return ""
                
            tag_type = "price_down" if value < 0 else "price_up"
            arrow = "↓" if value < 0 else "↑"
            display = f"{format_number(value)}"
            
            return TagCreator.create_tag(f"{arrow} {display}", tag_type)
        except:
            return ""
    
    @staticmethod
    def format_days_active_tag(days_value, status="active"):
        """Create days active tag with appropriate styling."""
        if pd.isna(days_value) or days_value == "--":
            return ""
            
        # Convert days to integer if possible
        try:
            days = int(days_value) if not isinstance(days_value, str) else 0
        except:
            days = 0
            
        # Determine tag type based on age and status
        if status == "non active":
            tag_type = "days_inactive"
        elif days == 0:
            tag_type = "days_new"
        elif days <= 3:
            tag_type = "days_recent"
        elif days <= 14:
            tag_type = "days_medium"
        else:
            tag_type = "days_old"
            
        # Format display text
        if isinstance(days_value, str):
            display_text = days_value
        else:
            display_text = f"{days} дн."
            
        return TagCreator.create_tag(display_text, tag_type)
    
    @staticmethod
    def format_walking_time_tag(distance_value):
        """Create walking time tag based on distance."""
        if distance_value is None or pd.isna(distance_value):
            return ""
            
        # Calculate walking time (5 km/h)
        walking_minutes = (distance_value / 5) * 60
        
        # Format time text
        if walking_minutes < 60:
            time_text = f"{int(walking_minutes)}м"
        else:
            hours = int(walking_minutes // 60)
            minutes = int(walking_minutes % 60)
            time_text = f"{hours}ч{minutes}м" if minutes > 0 else f"{hours}ч"
            
        # Set tag type based on walking time
        if walking_minutes < 12:
            tag_type = "walk_close"
        elif walking_minutes < 20:
            tag_type = "walk_medium"
        else:
            tag_type = "walk_far"
            
        return TagCreator.create_tag(time_text, tag_type)
    
    @staticmethod
    def format_neighborhood_tag(neighborhood, is_hamovniki=False, is_arbat=False):
        """Format neighborhood tag with appropriate styling."""
        if not neighborhood or neighborhood == "nan" or neighborhood == "None":
            return ""
            
        # Determine tag type based on neighborhood
        if is_hamovniki:
            tag_type = "neighborhood_hamovniki"
        elif is_arbat:
            tag_type = "neighborhood_arbat"
        else:
            tag_type = "neighborhood_other"
            
        return TagCreator.create_tag(neighborhood, tag_type)
    
    @staticmethod
    def format_metro_tag(metro_station):
        """Create metro station tag with line color."""
        if not metro_station or not isinstance(metro_station, str) or not metro_station.strip():
            return ""
            
        import re
        # Clean station name
        clean_station = re.sub(r"\s*\([^)]*\)", "", metro_station).strip()
        
        # Find matching line
        line_number = None
        for station, line in METRO_TO_LINE.items():
            if station in clean_station or clean_station in station:
                line_number = line
                break
                
        if not line_number:
            return TagCreator.create_tag(clean_station, "default")
            
        # Get line color and create tag
        bg_color = LINE_COLORS.get(line_number, "#dadce0")
        
        # Special case for MCC line
        if line_number == 14:
            return TagCreator.create_tag(
                clean_station, 
                "default", 
                {
                    "backgroundColor": bg_color,
                    "color": "#000000",
                    "border": "1px solid #EF161E"
                }
            )
        else:
            return TagCreator.create_tag(
                clean_station, 
                "default", 
                {
                    "backgroundColor": bg_color,
                    "color": "#ffffff"
                }
            )


class ColumnFormatter:
    """Centralized column formatting."""
    
    @staticmethod
    def format_price_column(row):
        """Format price column with consistent tags."""
        tags = []
        
        # Main price tag
        price_formatted = row.get("price_value_formatted", "--")
        tags.append(TagFormatter.format_price_tag(price_formatted))
        
        # Price change tag
        price_change = row.get("price_change_value", 0)
        if price_change:
            tags.append(TagFormatter.format_price_change_tag(price_change))
        
        # Good price tag
        if row.get("price_difference_value", 0) > 0 and row.get("status") != "non active":
            tags.append(TagCreator.create_tag("хорошая цена", "good_price"))
        
        # CIAN estimation tag
        cian_est = row.get("cian_estimation_formatted")
        if (pd.notnull(cian_est) and cian_est != "--" and 
            cian_est != row.get("price_value_formatted")):
            tags.append(TagCreator.create_tag(f"оценка: {cian_est}", "cian_estimate"))
        
        return TagCreator.create_container(tags, "center")
    
    @staticmethod
    def format_update_title(row):
        """Format update title column consistently."""
        tags = []
        
        # Time string with special styling
        time_str = row.get("updated_time", "--")
        time_tag = f'<span style="font-size:0.9rem; font-weight:bold; line-height:1.2;">{time_str}</span>'
        tags.append(time_tag)
        
        # Days active tag
        days_active = row.get("days_active")
        days_value = row.get("days_active_value", 0)
        if pd.notnull(days_active) and days_active != "--":
            tags.append(TagFormatter.format_days_active_tag(days_value, row.get("status", "active")))
        
        return TagCreator.create_container(tags, "column")
    
    @staticmethod
    def format_property_tags(row):
        """Format property tags column consistently."""
        tags = []
        
        # Walking time tag
        distance_value = row.get("distance_sort")
        if distance_value is not None and not pd.isna(distance_value):
            tags.append(TagFormatter.format_walking_time_tag(distance_value))
        
        # Neighborhood tag
        tag_flags = DataManager.generate_tags_for_row(row)
        if neighborhood := tag_flags.get("neighborhood"):
            tags.append(TagFormatter.format_neighborhood_tag(
                neighborhood, 
                tag_flags.get("is_hamovniki", False), 
                tag_flags.get("is_arbat", False)
            ))
        
        # Metro station tag
        if metro_station := row.get("metro_station"):
            tags.append(TagFormatter.format_metro_tag(metro_station))
        
        return TagCreator.create_container(tags)
    
    @staticmethod
    def format_activity_date(row):
        """Format activity date column consistently."""
        if "activity_date" not in row or pd.isna(row["activity_date"]):
            return ""
        
        # Skip if same as updated time
        if pd.notnull(row.get("updated_time_sort")) and pd.notnull(row.get("activity_date_sort")):
            time_diff = abs((row["activity_date_sort"] - row["updated_time_sort"]).total_seconds())
            if time_diff < 60:
                return ""
        
        activity_date = row["activity_date"]
        
        # Format based on status
        if row.get("status") == "active":
            html = f'<span style="color:#1976d2; font-size:0.7rem;">🔄</span><span style="font-size:0.9rem; font-weight:normal; line-height:1.2;">{activity_date}</span>'
        else:
            html = f'<span style="display:inline-block; padding:1px 4px; border-radius:6px; margin-left:0px; background-color:#f5f5f5; color:#666;">📦</span><span style="font-size:0.9rem; font-weight:normal; line-height:1.2;">{activity_date}</span> '
        
        return f'<div style="text-align:center; width:100%;">{html}</div>'
    
    @staticmethod
    def format_active_days(row):
        """Format active days column consistently."""
        if not pd.notnull(row.get("days_active")) or row["days_active"] == "--":
            return ""
        
        days_value = row.get("days_active_value", 0)
        tag = TagFormatter.format_days_active_tag(days_value, row.get("status", "active"))
        
        return TagCreator.create_container([tag], "center")
    
    @staticmethod
    def format_price_change(value):
        """Format price change using standardized tag system."""
        # Direct replacement for the old format_price_change function
        return TagFormatter.format_price_change_tag(value)


def format_date(dt, threshold_hours=24):
    """Format date with timezone awareness."""
    if dt is None or pd.isna(dt):
        return "--"

    # Ensure dt has Moscow timezone
    dt = ensure_timezone(dt, MOSCOW_TZ)

    # Get current time in Moscow
    now = datetime.now(MOSCOW_TZ)

    # Calculate delta
    delta = now - dt
    seconds_ago = delta.total_seconds()

    # Russian month abbreviations
    month_names = {
        i: m
        for i, m in enumerate(
            [
                "янв",
                "фев",
                "мар",
                "апр",
                "май",
                "июн",
                "июл",
                "авг",
                "сен",
                "окт",
                "ноя",
                "дек",
            ],
            1,
        )
    }

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


class DataManager:
    """Centralized data management."""
    @staticmethod
    def load_csv_safely(file_path):
        """Load CSV file safely with fallback to GitHub if needed."""
        try:
            # Try to load from local file first
            if os.path.exists(file_path):
                logger.info(f"Loading CSV from local file: {file_path}")
                return pd.read_csv(file_path, encoding='utf-8')
            
            # If local file doesn't exist and we're using hybrid mode for apartment details
            elif AppConfig.should_use_hybrid_for_apartment_details():
                # Extract filename from path
                file_name = os.path.basename(file_path)
                # Try to load from GitHub
                github_url = AppConfig.get_github_url("cian_data", file_name)
                logger.info(f"Local file not found, trying GitHub: {github_url}")
                return DataManager.load_csv_from_url(github_url)
            
            # If we're not using hybrid mode and file doesn't exist locally
            logger.warning(f"CSV file not found: {file_path} and not using hybrid mode")
            return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Error loading CSV {file_path}: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
        
    @staticmethod
    def load_csv_from_url(url):
        """Load CSV from URL."""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return pd.read_csv(
                    pd.io.common.StringIO(response.text), encoding="utf-8"
                )
            logger.error(f"Failed to fetch CSV: {url}, Status: {response.status_code}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading CSV from URL: {e}")
            return pd.DataFrame()

    @staticmethod
    def load_data():
        """Load main apartment data."""
        try:
            url = AppConfig.get_github_url("cian_data", "cian_apartments.csv")
            df = DataManager.load_csv_from_url(url)
            if df.empty:
                return pd.DataFrame(), "Data file not found"

            # Get update time
            update_time = DataManager._extract_update_time()

            return df, update_time
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return pd.DataFrame(), f"Error: {e}"

    @staticmethod
    def _extract_update_time():
        """Extract update time from metadata."""
        try:
            meta_url = AppConfig.get_github_url(
                "cian_data", "cian_apartments.meta.json"
            )
            response = requests.get(meta_url)

            if response.status_code == 200:
                metadata = response.json()
                update_time_str = metadata.get("last_updated", "Unknown")
                try:
                    dt = pd.to_datetime(update_time_str)
                    dt = dt.replace(tzinfo=MOSCOW_TZ)
                    return dt.strftime("%d.%m.%Y %H:%M:%S") + " (МСК)"
                except:
                    return update_time_str
            return "Unknown"
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return "Unknown"

    @staticmethod
    def process_data(df):
        """Process dataframe with all transformations."""
        if df.empty:
            return df

        df["offer_id"] = df["offer_id"].astype(str)

        # Apply all transformations
        DataManager._apply_transformations(df)

        # Sort by status and distance
        df["sort_key"] = df["status"].apply(lambda x: 1)
        df = df.sort_values(["sort_key", "distance_sort"], ascending=[True, True]).drop(
            columns="sort_key"
        )

        return df

    @staticmethod
    def _apply_transformations(df):
        """Apply all data transformations."""
        # Process links
        base_url = CONFIG["base_url"]
        df["address"] = df.apply(
            lambda r: f"[{r['address']}]({base_url}{r['offer_id']}/)", axis=1
        )
        df["offer_link"] = df["offer_id"].apply(lambda x: f"[View]({base_url}{x}/)")
        df["address_title"] = df.apply(
            lambda r: f"[{r['address']}]({base_url}{r['offer_id']}/)<br>{r['title']}",
            axis=1,
        )

        # Process metrics
        df["distance_sort"] = pd.to_numeric(df["distance"], errors="coerce")
        df["distance"] = df["distance_sort"].apply(
            lambda x: f"{x:.2f} km" if pd.notnull(x) else ""
        )

        # Process dates
        now = datetime.now(MOSCOW_TZ)
        for col in ["updated_time", "unpublished_date", "activity_date"]:
            df[f"{col}_sort"] = pd.to_datetime(df[col], errors="coerce")
            df[f"{col}_sort"] = df[f"{col}_sort"].apply(
                lambda x: ensure_timezone(x) if pd.notnull(x) else None
            )

            df[col] = df[f"{col}_sort"].apply(
                lambda x: format_date(x) if pd.notnull(x) else "--"
            )

        # Calculate days active
        df["days_active_value"] = df.apply(
            lambda r: (
                (now - ensure_timezone(r["updated_time_sort"])).days
                if r["status"] == "active" and pd.notnull(r["updated_time_sort"])
                else (
                    (
                        ensure_timezone(r["unpublished_date_sort"])
                        - ensure_timezone(r["updated_time_sort"])
                    ).days
                    if r["status"] == "non active"
                    and pd.notnull(r["unpublished_date_sort"])
                    and pd.notnull(r["updated_time_sort"])
                    else None
                )
            ),
            axis=1,
        )

        # Hours for entries where days = 0
        df["hours_active_value"] = df.apply(
            lambda r: (
                int(
                    (now - ensure_timezone(r["updated_time_sort"])).total_seconds()
                    // 3600
                )
                if r["status"] == "active"
                and pd.notnull(r["updated_time_sort"])
                and (now - ensure_timezone(r["updated_time_sort"])).days == 0
                else (
                    int(
                        (
                            ensure_timezone(r["unpublished_date_sort"])
                            - ensure_timezone(r["updated_time_sort"])
                        ).total_seconds()
                        // 3600
                    )
                    if r["status"] == "non active"
                    and pd.notnull(r["unpublished_date_sort"])
                    and pd.notnull(r["updated_time_sort"])
                    and (
                        ensure_timezone(r["unpublished_date_sort"])
                        - ensure_timezone(r["updated_time_sort"])
                    ).days
                    == 0
                    else None
                )
            ),
            axis=1,
        )

        # Format days active
        df["days_active"] = df.apply(
            lambda r: (
                f"{int(r['hours_active_value'])} ч."
                if pd.notnull(r["days_active_value"])
                and r["days_active_value"] == 0
                and pd.notnull(r["hours_active_value"])
                else (
                    f"{int(r['days_active_value'])} дн."
                    if pd.notnull(r["days_active_value"])
                    and r["days_active_value"] >= 0
                    else "--"
                )
            ),
            axis=1,
        )

        # Combined date for sorting
        df["date_sort_combined"] = df["updated_time_sort"]

        # Format financial info
        DataManager._process_financial_info(df)

        # Create display columns - using consistent column formatters
        DataManager._create_display_columns(df)

    @staticmethod
    def _process_financial_info(df):
        """Process financial information."""
        # Format price columns
        for col in ["price_value", "cian_estimation_value"]:
            df[f"{col}_formatted"] = df[col].apply(
                lambda x: format_number(x) if is_numeric(x) else "--"
            )

        # Calculate price difference
        if "price_value" in df.columns and "cian_estimation_value" in df.columns:
            df["price_difference_value"] = df.apply(
                lambda r: (
                    int(r["cian_estimation_value"]) - int(r["price_value"])
                    if (is_numeric(r["price_value"]) and is_numeric(r["cian_estimation_value"])
                        and not pd.isna(r["price_value"]) and not pd.isna(r["cian_estimation_value"]))
                    else 0
                ),
                axis=1,
            )



        # Format price changes
        df["price_change_formatted"] = df["price_change_value"].apply(
            ColumnFormatter.format_price_change
        )

    @staticmethod
    def _create_display_columns(df):
        """Create combined display columns using consistent formatters."""
        # Use consistent column formatters
        df["price_text"] = df.apply(ColumnFormatter.format_price_column, axis=1)
        df["update_title"] = df.apply(ColumnFormatter.format_update_title, axis=1)
        df["property_tags"] = df.apply(ColumnFormatter.format_property_tags, axis=1)
        df["price_change"] = df["price_change_formatted"]
        df["activity_date"] = df.apply(ColumnFormatter.format_activity_date, axis=1)
        df["days_active"] = df.apply(ColumnFormatter.format_active_days, axis=1)
    
        # Combine update title with activity date if needed
        df["update_title"] = df.apply(
            lambda r: (
                f"{r['update_title']}{r['activity_date']}"
                if pd.notnull(r["activity_date"]) and r["activity_date"] != ""
                else r["update_title"]
            ),
            axis=1,
        )

    @staticmethod
    def filter_and_sort_data(df, filters=None, sort_by=None):
        """Filter and sort data in a single function."""
        if df.empty:
            return df

        # Apply filters
        if filters:
            # Price filter
            if (
                (price_value := filters.get("price_value"))
                and price_value != float("inf")
                and "price_value" in df.columns
            ):
                df = df[df["price_value"] <= price_value]

            # Distance filter
            if (
                (distance_value := filters.get("distance_value"))
                and distance_value != float("inf")
                and "distance_sort" in df.columns
            ):
                df = df[df["distance_sort"] <= distance_value]

            # Special filters
            if filters.get("nearest") and "distance_sort" in df.columns:
                df = df[df["distance_sort"] < 1.5]

            if filters.get("below_estimate") and "price_difference_value" in df.columns:
                df = df[df["price_difference_value"] >= 5000]

            if filters.get("inactive") and "status" in df.columns:
                df = df[df["status"] == "active"]

            if filters.get("updated_today") and "updated_time_sort" in df.columns:
                df["updated_time_sort"] = pd.to_datetime(df["updated_time_sort"], errors="coerce")
                recent_time = pd.Timestamp.now(MOSCOW_TZ) - pd.Timedelta(hours=24)
                df = df[df["updated_time_sort"] > recent_time]


            # Apply sorting from filters
            if "sort_column" in filters and "sort_direction" in filters:
                sort_column = filters["sort_column"]
                if sort_column in df.columns:
                    df = df.sort_values(
                        sort_column, ascending=filters["sort_direction"] == "asc"
                    )
                elif "price_value" in df.columns:
                    df = df.sort_values("price_value", ascending=True)

        # Apply sorting from sort_by parameter
        elif sort_by:
            for item in sort_by:
                col = CONFIG["columns"]["sort_map"].get(
                    item["column_id"], item["column_id"]
                )
                if col in df.columns:
                    df = df.sort_values(col, ascending=item["direction"] == "asc")

        return df

    @staticmethod
    def generate_tags_for_row(row):
        """Generate tags for row conditions."""
        tags = {
            "below_estimate": row.get("price_difference_value", 0) > 0
            and row.get("status") != "non active",
            "nearby": row.get("distance_sort", 999) < 1.5
            and row.get("status") != "non active",
            "updated_today": False,
            "neighborhood": None,
            "is_hamovniki": False,
            "is_arbat": False,
        }

        # Check for recent updates
        try:
            recent_time = pd.Timestamp.now() - pd.Timedelta(hours=24)
            row_time = row.get("updated_time_sort")
            if row_time and not pd.isna(row_time):
                row_dt = pd.to_datetime(row_time)
                if row_dt.date() == pd.Timestamp.now().date():
                    tags["updated_today"] = True
        except Exception as e:
            logger.warning(f"Error processing timestamp: {e}")

        # Check neighborhood
        neighborhood = str(row.get("neighborhood", ""))
        if neighborhood and neighborhood != "nan" and neighborhood != "None":
            # Extract neighborhood name
            if "р-н " in neighborhood:
                neighborhood_name = neighborhood.split("р-н ")[1].strip()
            else:
                neighborhood_name = neighborhood.strip()

            tags["neighborhood"] = neighborhood_name
            tags["is_hamovniki"] = "Хамовники" in neighborhood
            tags["is_arbat"] = "Арбат" in neighborhood

        return tags


def load_apartment_details(offer_id):
    """Load details for a specific apartment."""
    data_dir = AppConfig.get_cian_data_path()
    apartment_data = {"offer_id": offer_id}

    # Define files to check
    files_to_check = [
        ("price_history.csv", "price_history"),
        ("stats.csv", "stats"),
        ("features.csv", "features"),
        ("rental_terms.csv", "terms"),
        ("apartment_details.csv", "apartment"),
        ("building_details.csv", "building"),
    ]

    for filename, group_name in files_to_check:
        try:
            filepath = os.path.join(data_dir, filename)
            df = DataManager.load_csv_safely(filepath)

            if not df.empty and "offer_id" in df.columns:
                df["offer_id"] = df["offer_id"].astype(str)
                filtered_df = df[df["offer_id"] == str(offer_id)]

                if not filtered_df.empty:
                    apartment_data[group_name] = (
                        filtered_df.to_dict("records")
                        if group_name == "price_history"
                        else filtered_df.iloc[0].to_dict()
                    )
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")

    return apartment_data