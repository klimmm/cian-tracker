# app/utils.py
import pandas as pd
import json
import os
import logging
import traceback
from typing import Tuple, Dict, List, Optional, Any, Callable
from app.config import CONFIG, MOSCOW_TZ
from app.formatters import (
    PriceFormatter,
    TimeFormatter,
    DataExtractor,
    FormatUtils,
    HtmlFormatter,
)
from app.app_config import AppConfig

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Standardized error handling and logging."""

    @staticmethod
    def log_and_return(
        logger,
        operation_name: str,
        error: Exception,
        default_return: Any = None,
        log_level: str = "error",
    ) -> Any:
        """Log an error and return a default value."""
        getattr(logger, log_level)(f"Error in {operation_name}: {str(error)}")
        if log_level == "error":
            logger.debug(f"Traceback: {traceback.format_exc()}")
        return default_return

    @staticmethod
    def try_operation(
        logger,
        operation_name: str,
        operation_func: Callable,
        *args,
        default_return: Any = None,
        **kwargs,
    ) -> Any:
        """Try to execute an operation with standardized error handling."""
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            return ErrorHandler.log_and_return(
                logger, operation_name, e, default_return
            )

    @staticmethod
    def fallback_chain(
        logger, operation_name: str, operations: List[Tuple[Callable, List, Dict]]
    ) -> Any:
        """Try a sequence of operations until one succeeds."""
        for i, (func, args, kwargs) in enumerate(operations):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Fallback {i+1}/{len(operations)} for {operation_name} failed: {e}"
                )
                if i == len(operations) - 1:
                    logger.error(f"All fallbacks for {operation_name} failed")
        return None


# Add these imports to the top of utils.py
import requests
from urllib.parse import urljoin

# Add this to the DataManager class in utils.py
# Add to utils.py
import requests
from urllib.parse import urljoin

class DataManager:
    """Centralized manager for all data operations with improved error handling."""


    @staticmethod
    def _load_with_csv_module(file_path: str) -> pd.DataFrame:
        """Load CSV using Python's CSV module for better error tolerance."""
        import csv

        with open(file_path, "r", encoding="utf-8") as f:
            sample = f.read(1000)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample)
                reader = csv.reader(f, dialect)
            except:
                reader = csv.reader(
                    f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
                )

            rows = list(reader)

        if not rows:
            return pd.DataFrame()

        max_fields = max(len(row) for row in rows)
        header = rows[0]

        if len(header) < max_fields:
            header = header + [f"unnamed_{i}" for i in range(len(header), max_fields)]

        unique_header = DataManager._create_unique_header(header)

        data = []
        for row in rows[1:]:
            if len(row) < max_fields:
                row = row + [""] * (max_fields - len(row))
            data.append(row[:max_fields])

        return pd.DataFrame(data, columns=unique_header)

    @staticmethod
    def _create_unique_header(header: List[str]) -> List[str]:
        """Create unique header names from potentially duplicate names."""
        unique_header = []
        seen = set()

        for col in header:
            if col in seen or not col:
                count = 1
                new_col = f"column_{count}" if not col else f"{col}_{count}"
                while new_col in seen:
                    count += 1
                    new_col = f"column_{count}" if not col else f"{col}_{count}"
                unique_header.append(new_col)
            else:
                unique_header.append(col)
            seen.add(unique_header[-1])

        return unique_header

    @staticmethod
    def _load_with_pandas_fallback(file_path: str) -> pd.DataFrame:
        """Fallback method to load CSV with pandas."""
        try:
            return pd.read_csv(
                file_path,
                encoding="utf-8",
                on_bad_lines="skip",
                escapechar="\\",
                quotechar='"',
                low_memory=False,
            )
        except Exception as e2:
            try:
                return pd.read_csv(
                    file_path,
                    encoding="utf-8",
                    error_bad_lines=False,
                    warn_bad_lines=True,
                    low_memory=False,
                )
            except Exception as e3:
                logger.error(f"All loading methods failed for {file_path}: {str(e3)}")
                return pd.DataFrame()
    
    @staticmethod
    def load_csv_from_url(url: str) -> pd.DataFrame:
        """Load a CSV file from a URL with error handling."""
        try:
            logger.info(f"Loading CSV from URL: {url}")
            response = requests.get(url)
            
            # Check if the request was successful
            if response.status_code == 200:
                # Use pandas to read the CSV from the content
                return pd.read_csv(pd.io.common.StringIO(response.text), encoding="utf-8")
            else:
                logger.error(f"Failed to fetch CSV from URL: {url}, Status code: {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error loading CSV from URL {url}: {str(e)}")
            return pd.DataFrame()
    
    @staticmethod
    def load_csv_safely(file_path: str) -> pd.DataFrame:
        """Load a CSV file with robust error handling for malformed files."""
        filename = os.path.basename(file_path)
        
        # Always use GitHub for main data files
        if AppConfig.always_use_github_for(filename):
            github_url = AppConfig.get_github_url("cian_data", filename)
            return DataManager.load_csv_from_url(github_url)
        
        # For apartment details files, use hybrid approach if configured
        if AppConfig.should_use_hybrid_for_apartment_details():
            # Try local file first
            if os.path.exists(file_path):
                try:
                    df = DataManager._load_with_csv_module(file_path)
                    if not df.empty:
                        logger.info(f"Successfully loaded {filename} from local file")
                        return df
                except Exception as e:
                    logger.warning(f"Error loading local file {filename}: {e}")
                    
            # Fall back to GitHub
            github_url = AppConfig.get_github_url("cian_data", filename)
            logger.info(f"Trying to load {filename} from GitHub at {github_url}")
            df = DataManager.load_csv_from_url(github_url)
            if not df.empty:
                logger.info(f"Successfully loaded {filename} from GitHub")
                return df
            else:
                logger.warning(f"Failed to load {filename} from GitHub")
                return pd.DataFrame()
        
        # Default to local file loading
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return pd.DataFrame()

        try:
            return DataManager._load_with_csv_module(file_path)
        except Exception as e:
            logger.error(f"Error in CSV module parsing for {file_path}: {str(e)}")
            return DataManager._load_with_pandas_fallback(file_path)
    
    @staticmethod
    def load_data() -> Tuple[pd.DataFrame, str]:
        """Load main apartment data from CSV files."""
        try:
            # Always use GitHub for the main data file
            url = AppConfig.get_github_url("cian_data", "cian_apartments.csv")
            logger.info(f"Loading main data from GitHub: {url}")
            
            df = DataManager.load_csv_from_url(url)
            if df.empty:
                logger.error("Loaded DataFrame from GitHub is empty!")
                return pd.DataFrame(), "Data file not found on GitHub"
                
            logger.info(f"Successfully loaded {len(df)} rows from GitHub")
            
            # Get update time
            update_time = DataManager._extract_update_time_from_github()
            
            return df, update_time
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return pd.DataFrame(), f"Error: {e}"
    
    @staticmethod
    def _extract_update_time_from_github() -> str:
        """Extract update time from GitHub metadata file."""
        try:
            # Try to load the metadata file from GitHub
            meta_url = AppConfig.get_github_url("cian_data", "cian_apartments.meta.json")
            response = requests.get(meta_url)
            
            if response.status_code == 200:
                metadata = response.json()
                update_time_str = metadata.get("last_updated", "Unknown")
                try:
                    dt = pd.to_datetime(update_time_str)
                    return dt.strftime("%d.%m.%Y %H:%M:%S")
                except:
                    return update_time_str
            else:
                # Fallback to CSV header approach
                return DataManager._extract_update_time_from_csv_header_github()
                
        except Exception as e:
            logger.error(f"Error reading metadata from GitHub: {e}")
            return "Unknown (GitHub)"
    
    @staticmethod
    def _extract_update_time_from_csv_header_github() -> str:
        """Extract update time from CSV header as fallback when using GitHub."""
        try:
            # Get first few lines of the CSV to check for header comments
            url = AppConfig.get_github_url("cian_data", "cian_apartments.csv")
            response = requests.get(url, headers={"Range": "bytes=0-1000"})
            
            if response.status_code in [200, 206]:  # 200 OK or 206 Partial Content
                first_line = response.text.split('\n')[0]
                if "last_updated=" in first_line:
                    parts = first_line.split("last_updated=")
                    if len(parts) > 1:
                        return parts[1].split(",")[0].strip()
            return "Unknown (GitHub)"
                
        except Exception as e:
            logger.error(f"Error reading CSV header from GitHub: {e}")
            return "Unknown (GitHub)"

    @staticmethod
    def process_data(df: pd.DataFrame) -> pd.DataFrame:
        """Process and transform raw dataframe into display-ready format."""
        if df.empty:
            return df

        df["offer_id"] = df["offer_id"].astype(str)

        DataManager._process_links(df)
        DataManager._process_metrics(df)
        DataManager._process_dates(df)
        DataManager._process_financial_info(df)
        DataManager._create_display_columns(df)

        df["tags"] = df.apply(generate_tags_for_row, axis=1)

        df["sort_key"] = df["status"].apply(lambda x: 1)
        df = df.sort_values(["sort_key", "distance_sort"], ascending=[True, True]).drop(
            columns="sort_key"
        )

        return df

    @staticmethod
    def _process_links(df: pd.DataFrame) -> None:
        """Process address and offer links."""
        base_url = CONFIG["base_url"]
        df["address"] = df.apply(
            lambda r: f"[{r['address']}]({base_url}{r['offer_id']}/)", axis=1
        )
        df["offer_link"] = df["offer_id"].apply(lambda x: f"[View]({base_url}{x}/)")
        df["address_title"] = df.apply(
            lambda r: f"[{r['address']}]({base_url}{r['offer_id']}/)<br>{r['title']}",
            axis=1,
        )

    @staticmethod
    def _process_metrics(df: pd.DataFrame) -> None:
        """Process distance and other metrics."""
        df["distance_sort"] = pd.to_numeric(df["distance"], errors="coerce")
        df["distance"] = df["distance_sort"].apply(
            lambda x: f"{x:.2f} km" if pd.notnull(x) else ""
        )

    @staticmethod
    def _process_dates(df: pd.DataFrame) -> None:
        """Process dates and timestamps."""
        # Process existing date columns
        df["updated_time_sort"] = pd.to_datetime(df["updated_time"], errors="coerce")
        df["updated_time"] = df["updated_time_sort"].apply(
            lambda x: FormatUtils.format_text(x, lambda dt: TimeFormatter.format_date(dt, MOSCOW_TZ), "")
        )
    
        df["unpublished_date_sort"] = pd.to_datetime(
            df["unpublished_date"], format="%Y-%m-%d %H:%M:%S", errors="coerce"
        )
        df["unpublished_date"] = df["unpublished_date_sort"].apply(
            lambda x: FormatUtils.format_text(x, lambda dt: TimeFormatter.format_date(dt, MOSCOW_TZ), "--")
        )
        
        df["activity_date_sort"] = pd.to_datetime(df["activity_date"], errors="coerce")
        df["activity_date"] = df["activity_date_sort"].apply(
            lambda x: FormatUtils.format_text(x, lambda dt: TimeFormatter.format_date(dt, MOSCOW_TZ), "--")
        )
        
        # Calculate days_active
        now = pd.Timestamp.now()

        # In utils.py, modify the DataManager._process_dates method where days_active is calculated:
        
        # Calculate days_active and hours when days is 0
        df["days_active_value"] = df.apply(
            lambda r: (now - r["updated_time_sort"]).days 
                      if r["status"] == "active" and pd.notnull(r["updated_time_sort"])
                      else (r["unpublished_date_sort"] - r["updated_time_sort"]).days 
                      if r["status"] == "non active" and pd.notnull(r["unpublished_date_sort"]) and pd.notnull(r["updated_time_sort"]) 
                      else None,
            axis=1
        )
        
        # Calculate hours for entries where days = 0
        df["hours_active_value"] = df.apply(
            lambda r: int((now - r["updated_time_sort"]).total_seconds() // 3600) 
                      if r["status"] == "active" and pd.notnull(r["updated_time_sort"]) and (now - r["updated_time_sort"]).days == 0
                      else int((r["unpublished_date_sort"] - r["updated_time_sort"]).total_seconds() // 3600) 
                      if r["status"] == "non active" and pd.notnull(r["unpublished_date_sort"]) and pd.notnull(r["updated_time_sort"]) 
                      and (r["unpublished_date_sort"] - r["updated_time_sort"]).days == 0
                      else None,
            axis=1
        )
        
        # Format days_active for display, showing hours when days = 0
        df["days_active"] = df.apply(
            lambda r: f"{int(r['hours_active_value'])} ч." if pd.notnull(r['days_active_value']) and r['days_active_value'] == 0 and pd.notnull(r['hours_active_value'])
                      else f"{int(r['days_active_value'])} дн." if pd.notnull(r['days_active_value']) and r['days_active_value'] >= 0 
                      else "--",
            axis=1
        )
                    


        
        # Combined date for sorting
        df["date_sort_combined"] = df.apply(
            lambda r: r["updated_time_sort"],
            axis=1
        )

    @staticmethod
    def _process_financial_info(df: pd.DataFrame) -> None:
        """Process price, commission, deposit and other financial information."""
        df["price_value_formatted"] = df["price_value"].apply(
            lambda x: FormatUtils.format_text(
                x, lambda v: PriceFormatter.format_price(v), "--"
            )
        )
        df["cian_estimation_formatted"] = df["cian_estimation_value"].apply(
            lambda x: FormatUtils.format_text(
                x, lambda v: PriceFormatter.format_price(v), "--"
            )
        )
        df["price_difference_formatted"] = df["price_difference_value"].apply(
            lambda x: FormatUtils.format_text(
                x, lambda v: PriceFormatter.format_price(v, abbreviate=True), ""
            )
        )
        df["price_change_formatted"] = df["price_change_value"].apply(
            PriceFormatter.format_price_change
        )

        df["rental_period_abbr"] = df["rental_period"].apply(format_rental_period)
        df["utilities_type_abbr"] = df["utilities_type"].apply(format_utilities)

        df["commission_value"] = df["commission_info"].apply(
            DataExtractor.extract_commission_value
        )
        df["commission_info_abbr"] = df["commission_value"].apply(
            PriceFormatter.format_commission
        )
        df["deposit_value"] = df["deposit_info"].apply(
            DataExtractor.extract_deposit_value
        )
        df["deposit_info_abbr"] = df["deposit_value"].apply(
            PriceFormatter.format_deposit
        )

        df["monthly_burden"] = df.apply(calculate_monthly_burden, axis=1)
        df["monthly_burden_formatted"] = df.apply(format_burden, axis=1)

    @staticmethod
    def _create_display_columns(df: pd.DataFrame) -> None:
        """Create combined display columns for the UI."""
        df["price_text"] = df.apply(
            lambda r: (
                f'<div style="display:block; text-align:center; margin:0; padding:0;">'
                f'<strong style="margin:0; padding:0;">{r["price_value_formatted"]}</strong>'
                + (
                    f'<br><span style="display:inline-block; padding:1px 4px; border-radius:6px; margin-top:2px; background-color:#fcf3cd; color:#856404;">хорошая цена</span>'
                    if r.get("price_difference_value", 0) > 0
                    and r.get("status") != "non active"
                    else ""
                )
                + "</div>"
            ),
            axis=1,
        )

        df["commission_text"] = df.apply(
            lambda r: f'комиссия {r["commission_info_abbr"]}', axis=1
        )
        df["deposit_text"] = df.apply(
            lambda r: f'залог {r["deposit_info_abbr"]}', axis=1
        )
        df["price_info"] = df.apply(
            lambda r: f"{r['price_text']}<br>{r['commission_text']}<br> {r['deposit_text']}",
            axis=1,
        )

        df["update_title"] = df.apply(format_update_title, axis=1)
        df["property_tags"] = df.apply(format_property_tags, axis=1)
        df["update_time"] = df.apply(
            lambda r: f'<strong>{r["updated_time"]}</strong>',
            axis=1,
        )
        df["price_change"] = df["price_change_formatted"]

        df["activity_date"] = df.apply(format_activity_date, axis=1)
   
        df["days_active"] = df.apply(format_active_days, axis=1)
        # Create a combined update_title and activity_date column
        df["update_title"] = df.apply(
            lambda r: f"{r['update_title']}{r['activity_date']}" 
            if pd.notnull(r['activity_date']) and r['activity_date'] != ""
            else r['update_title'],
            axis=1
        )


    
    @staticmethod
    def filter_data(
        df: pd.DataFrame, filters: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """Filter data based on user-selected filters with cumulative filtering."""
        if df.empty or not filters:
            return df

        filtered_df = df.copy()

        if (
            (price_value := filters.get("price_value"))
            and price_value != float("inf")
            and "price_value" in filtered_df.columns
        ):
            filtered_df = filtered_df[filtered_df["price_value"] <= price_value]

        if (
            (distance_value := filters.get("distance_value"))
            and distance_value != float("inf")
            and "distance_sort" in filtered_df.columns
        ):
            filtered_df = filtered_df[filtered_df["distance_sort"] <= distance_value]

        if filters.get("nearest") and "distance_sort" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["distance_sort"] < 1.5]

        if (
            filters.get("below_estimate")
            and "price_difference_value" in filtered_df.columns
        ):
            filtered_df = filtered_df[filtered_df["price_difference_value"] >= 5000]

        if filters.get("inactive") and "status" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["status"] == "active"]

        if filters.get("updated_today") and "updated_time_sort" in filtered_df.columns:
            filtered_df["updated_time_sort"] = pd.to_datetime(
                filtered_df["updated_time_sort"], errors="coerce"
            )
            recent_time = pd.Timestamp.now() - pd.Timedelta(hours=24)
            filtered_df = filtered_df[filtered_df["updated_time_sort"] > recent_time]



        
        return filtered_df

    @staticmethod
    def filter_and_sort_data(
        df: pd.DataFrame,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[List[Dict[str, Any]]] = None,
    ) -> pd.DataFrame:
        """Filter and sort data in a single function."""
        df = DataManager.filter_data(df, filters)

        if df.empty:
            return df

        if filters and "sort_column" in filters and "sort_direction" in filters:
            sort_column = filters["sort_column"]

            if sort_column in df.columns:
                df = df.sort_values(
                    sort_column, ascending=filters["sort_direction"] == "asc"
                )
            elif "price_value" in df.columns:
                df = df.sort_values("price_value", ascending=True)
        elif sort_by:
            for item in sort_by:
                col = CONFIG["columns"]["sort_map"].get(
                    item["column_id"], item["column_id"]
                )
                if col in df.columns:
                    df = df.sort_values(col, ascending=item["direction"] == "asc")

        return df


def load_apartment_details(offer_id: str) -> Dict[str, Any]:
    """Load all details for a specific apartment by offer_id."""
    data_dir = AppConfig.get_cian_data_path()
    logger.info(f"Loading apartment details for offer_id {offer_id}")

    apartment_data = {"offer_id": offer_id}
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
            # Use the DataManager's load_csv_safely method which already supports the hybrid approach
            filepath = os.path.join(data_dir, filename)
            df = DataManager.load_csv_safely(filepath)
                
            if df.empty or "offer_id" not in df.columns:
                continue

            df["offer_id"] = df["offer_id"].astype(str)
            filtered_df = df[df["offer_id"] == str(offer_id)]

            if not filtered_df.empty:
                if group_name == "price_history":
                    apartment_data[group_name] = filtered_df.to_dict("records")
                else:
                    apartment_data[group_name] = filtered_df.iloc[0].to_dict()
                logger.info(f"Loaded {group_name} data for offer_id {offer_id}")
            else:
                logger.warning(f"No data found for offer_id {offer_id} in {filename}")
        except Exception as e:
            logger.error(f"Error processing data from {filename}: {e}")

    return apartment_data
    
def generate_tags_for_row(row: pd.Series) -> Dict[str, Any]:
    """Generate tag flags for various row conditions."""
    tags = {
        "below_estimate": False,
        "nearby": False,
        "updated_today": False,
        "neighborhood": None,
        "is_hamovniki": False,
        "is_arbat": False,
    }

    if row.get("price_difference_value", 0) > 0 and row.get("status") != "non active":
        tags["below_estimate"] = True

    if row.get("distance_sort", 999) < 1.5 and row.get("status") != "non active":
        tags["nearby"] = True

    try:
        recent_time = pd.Timestamp.now() - pd.Timedelta(hours=24)
        row_time = row.get("updated_time_sort")
        if row_time and not pd.isna(row_time):
            row_dt = pd.to_datetime(row_time)
            if row_dt.date() == pd.Timestamp.now().date():
                tags["updated_today"] = True
    except Exception as e:
        logger.error(f"Error processing timestamp: {e}")

    neighborhood = str(row.get("neighborhood", ""))
    if neighborhood and neighborhood != "nan" and neighborhood != "None":
        neighborhood_name = DataExtractor.extract_neighborhood(neighborhood)
        tags["neighborhood"] = neighborhood_name
        tags["is_hamovniki"] = "Хамовники" in neighborhood
        tags["is_arbat"] = "Арбат" in neighborhood

    return tags

def format_update_title(row: pd.Series) -> str:
    """Format update_title showing all elements on the same line."""
    time_str = row["updated_time"]
    # Start with the date
    html = f'<span style="font-size:0.9rem; font-weight:bold; line-height:1.2;">{time_str}</span> '
    # Add price change or new indicator
    if row.get("price_change_formatted"):
        html += f'{row["price_change_formatted"]} '
    
    # Add days_active as a tag if it exists - on the same line
    if pd.notnull(row.get("days_active")) and row["days_active"] != "--":
        # Style based on the age - different colors for different age ranges
        days_value = row.get("days_active_value", 0)
        
        # Check if status is non active
        if row.get("status") == "non active":
            # Use grey colors for non-active items
            bg_color, text_color = "#f0f0f0", "#707070"  # Light grey background, dark grey text
        else:
            # Define colors based on age for active items
            if days_value == 0:  # Today
                bg_color, text_color = "#e8f5e9", "#2e7d32"  # Light green
            elif days_value <= 3:  # Recent
                bg_color, text_color = "#e3f2fd", "#1565c0"  # Light blue
            elif days_value <= 14:  # Within 2 weeks
                bg_color, text_color = "#fff3e0", "#e65100"  # Light orange
            else:  # Older
                bg_color, text_color = "#ffebee", "#c62828"  # Light red
            
        html += f'<span style="display:inline-block; padding:1px 4px; border-radius:6px; margin-left:1px; background-color:{bg_color}; color:{text_color};">{row["days_active"]}</span>'
    return HtmlFormatter.create_centered_text(html)




def format_activity_date(row: pd.Series) -> str:
    """Format activity_date showing when owner was last active with no material changes."""
    if "activity_date" not in row or pd.isna(row["activity_date"]):
        return ""
    
    # Check if activity_date is the same as updated_time, if so return empty string
    if pd.notnull(row.get("updated_time_sort")) and pd.notnull(row.get("activity_date_sort")):
        # Compare the dates to see if they're on the same day and time (within a minute tolerance)
        time_diff = abs((row["activity_date_sort"] - row["updated_time_sort"]).total_seconds())
        if time_diff < 60:  # If they're within a minute of each other
            return ""
        
    activity_date = row["activity_date"]
    
    # Add a refresh/update icon only for activity updates
    if row["status"] == "active":
        html = f'<span style="color:#1976d2; font-size:0.7rem;">🔄</span><span style="font-size:0.9rem; font-weight:normal; line-height:1.2;">{activity_date}</span>'
    else:
        # For archived listings, just show the date and archive tag
        html = f'<span style="display:inline-block; padding:1px 4px; border-radius:6px; margin-left:3px; background-color:#f5f5f5; color:#666;">📦</span><span style="font-size:0.9rem; font-weight:naormal; line-height:1.2;">{activity_date}</span> '

    return HtmlFormatter.create_centered_text(html)


def format_active_days(row: pd.Series) -> str:
    html = ''
    # Add days_active as a tag if it exists - on the same line
    if pd.notnull(row.get("days_active")) and row["days_active"] != "--":
        # Style based on the age - different colors for different age ranges
        days_value = row.get("days_active_value", 0)
        
        # Define colors based on age
        if days_value == 0:  # Today
            bg_color, text_color = "#e8f5e9", "#2e7d32"  # Light green
        elif days_value <= 3:  # Recent
            bg_color, text_color = "#e3f2fd", "#1565c0"  # Light blue
        elif days_value <= 14:  # Within 2 weeks
            bg_color, text_color = "#fff3e0", "#e65100"  # Light orange
        else:  # Older
            bg_color, text_color = "#ffebee", "#c62828"  # Light red
            
        html = f'<span style="display:inline-block; padding:1px 4px; border-radius:6px; margin-left:3px; background-color:{bg_color}; color:{text_color};">{row["days_active"]}</span>'

    return HtmlFormatter.create_centered_text(html)

    
# Add these constants to utils.py
# Mapping of metro stations to line numbers
METRO_STATIONS_TO_LINE = {
    # Line 1 (Сокольническая)
    'Бульвар Рокоссовского': 1, 'Черкизовская': 1, 'Преображенская площадь': 1, 'Сокольники': 1, 
    'Красносельская': 1, 'Комсомольская': 1, 'Красные ворота': 1, 'Чистые пруды': 1, 
    'Лубянка': 1, 'Охотный ряд': 1, 'Библиотека им. Ленина': 1, 'Кропоткинская': 1, 
    'Парк Культуры': 1, 'Фрунзенская': 1, 'Спортивная': 1, 'Воробьёвы горы': 1, 
    'Университет': 1, 'Проспект Вернадского': 1, 'Юго-Западная': 1, 'Тропарёво': 1,
    
    # Line 2 (Замоскворецкая)
    'Алма-Атинская': 2, 'Красногвардейская': 2, 'Домодедовская': 2, 'Орехово': 2, 
    'Царицыно': 2, 'Кантемировская': 2, 'Каширская': 2, 'Коломенская': 2, 
    'Автозаводская': 2, 'Павелецкая': 2, 'Новокузнецкая': 2, 'Театральная': 2, 
    'Тверская': 2, 'Маяковская': 2, 'Белорусская': 2, 'Динамо': 2, 
    'Аэропорт': 2, 'Сокол': 2, 'Войковская': 2, 'Водный стадион': 2, 'Речной вокзал': 2,
    
    # Line 3 (Арбатско-Покровская)
    'Пятницкое шоссе': 3, 'Митино': 3, 'Волоколамская': 3, 'Мякинино': 3, 
    'Строгино': 3, 'Крылатское': 3, 'Молодежная': 3, 'Кунцевская': 3, 
    'Славянский бульвар': 3, 'Парк Победы': 3, 'Киевская': 3, 'Смоленская': 3, 
    'Арбатская': 3, 'Площадь Революции': 3, 'Курская': 3, 'Бауманская': 3, 
    'Электрозаводская': 3, 'Семеновская': 3, 'Партизанская': 3, 'Измайловская': 3, 
    'Первомайская': 3, 'Щелковская': 3,
    
    # Line 4 (Филевская)
    'Александровский сад': 4, 'Выставочная': 4, 'Международная': 4, 'Студенческая': 4, 
    'Кутузовская': 4, 'Фили': 4, 'Багратионовская': 4, 'Филёвский парк': 4, 'Пионерская': 4,
    
    # Line 5 (Кольцевая)
    'Новослободская': 5, 'Проспект Мира': 5, 'Добрынинская': 5, 'Октябрьская': 5, 'Краснопресненская': 5,
    
    # Line 6 (Калужско-Рижская)
    'Медведково': 6, 'Бабушкинская': 6, 'Свиблово': 6, 'Ботанический сад': 6, 
    'ВДНХ': 6, 'Алексеевская': 6, 'Рижская': 6, 'Сухаревская': 6, 
    'Тургеневская': 6, 'Китай-город': 6, 'Третьяковская': 6, 'Шаболовская': 6, 
    'Ленинский проспект': 6, 'Академическая': 6, 'Профсоюзная': 6, 'Новые Черемушки': 6, 
    'Калужская': 6, 'Беляево': 6, 'Коньково': 6, 'Теплый Стан': 6, 
    'Ясенево': 6, 'Новоясеневская': 6,
    
    # Line 7 (Таганско-Краснопресненская)
    'Жулебино': 7, 'Лермонтовский проспект': 7, 'Выхино': 7, 'Рязанский проспект': 7, 
    'Кузьминки': 7, 'Текстильщики': 7, 'Волгоградский проспект': 7, 'Пролетарская': 7, 
    'Таганская': 7, 'Кузнецкий мост': 7, 'Пушкинская': 7, 'Баррикадная': 7, 
    'Улица 1905 года': 7, 'Беговая': 7, 'Полежаевская': 7, 'Октябрьское поле': 7, 
    'Щукинская': 7, 'Спартак': 7, 'Тушинская': 7, 'Сходненская': 7, 'Планерная': 7,
    
    # Line 8 (Калининская)
    'Новокосино': 8, 'Новогиреево': 8, 'Перово': 8, 'Шоссе Энтузиастов': 8, 
    'Авиамоторная': 8, 'Площадь Ильича': 8, 'Марксистская': 8, 'Деловой центр': 8,
    
    # Line 9 (Серпуховско-Тимирязевская)
    'Алтуфьево': 9, 'Бибирево': 9, 'Отрадное': 9, 'Владыкино': 9, 
    'Петровско-Разумовская': 9, 'Тимирязевская': 9, 'Дмитровская': 9, 'Савеловская': 9, 
    'Менделеевская': 9, 'Цветной бульвар': 9, 'Чеховская': 9, 'Боровицкая': 9, 
    'Полянка': 9, 'Серпуховская': 9, 'Тульская': 9, 'Нагатинская': 9, 
    'Нагорная': 9, 'Нахимовский проспект': 9, 'Севастопольская': 9, 'Чертановская': 9, 
    'Южная': 9, 'Пражская': 9, 'Улица Академика Янгеля': 9, 'Аннино': 9, 'Бульвар Дмитрия Донского': 9,
    
    # Line 10 (Люблинско-Дмитровская)
    'Марьина Роща': 10, 'Достоевская': 10, 'Трубная': 10, 'Сретенский бульвар': 10, 
    'Чкаловская': 10, 'Римская': 10, 'Крестьянская застава': 10, 'Дубровка': 10, 
    'Кожуховская': 10, 'Печатники': 10, 'Волжская': 10, 'Люблино': 10, 
    'Братиславская': 10, 'Марьино': 10, 'Борисово': 10, 'Шипиловская': 10, 'Зябликово': 10,
    
    # Line 11 (Каховская)
    'Варшавская': 11, 'Каховская': 11,
    
    # Line 12 (Бутовская)
    'Битцевский парк': 12, 'Лесопарковая': 12, 'Улица Старокачаловская': 12, 
    'Улица Скобелевская': 12, 'Бульвар адмирала Ушакова': 12, 'Улица Горчакова': 12, 'Бунинская аллея': 12,
    
    # Line 14 (Московское центральное кольцо / MCC / МЦК)
    'Окружная': 14, 'Владыкино МЦК': 14, 'Ботанический сад МЦК': 14, 'Ростокино': 14,
    'Белокаменная': 14, 'Бульвар Рокоссовского МЦК': 14, 'Локомотив': 14, 'Измайлово': 14,
    'Соколиная Гора': 14, 'Шоссе Энтузиастов МЦК': 14, 'Андроновка': 14, 'Нижегородская': 14,
    'Новохохловская': 14, 'Угрешская': 14, 'Дубровка МЦК': 14, 'Автозаводская МЦК': 14,
    'ЗИЛ': 14, 'Верхние Котлы': 14, 'Крымская': 14, 'Гагаринский тоннель': 14,
    'Площадь Гагарина': 14, 'Лужники': 14, 'Кутузовская МЦК': 14, 'Москва-Сити': 14,
    'Шелепиха': 14, 'Хорошёво': 14, 'Зорге': 14, 'Панфиловская': 14,
    'Стрешнево': 14, 'Балтийская': 14, 'Коптево': 14, 'Лихоборы': 14,
    'МЦК': 14, 'МЦД': 14  # Add common abbreviations that might appear
}

# Line colors mapped from the provided color codes
LINE_TO_COLOR = {
    1: '#EF161E',  # Сокольническая линия
    2: '#2DBE2C',  # Замоскворецкая линия
    3: '#0078BE',  # Арбатско-Покровская линия
    4: '#00BFFF',  # Филёвская линия
    5: '#8D5B2D',  # Кольцевая линия
    6: '#ED9121',  # Калужско-Рижская линия
    7: '#800080',  # Таганско-Краснопресненская линия
    8: '#FFD702',  # Калининская/Солнцевская линия
    9: '#999999',  # Серпуховско-Тимирязевская линия
    10: '#99CC00',  # Люблинско-Дмитровская линия
    11: '#82C0C0',  # Большая кольцевая/Каховская линия
    12: '#A1B3D4',  # Бутовская линия
    13: '#B9C8E7',  # Московский монорельс
    14: '#FFFFFF',  # Московское центральное кольцо
    15: '#DE64A1',  # Некрасовская линия
    16: '#03795F',  # Троицкая линия
    17: '#27303F',  # Рублёво-Архангельская линия
    18: '#AC1753',  # Бирюлёвская линия
}

# Add these methods to the HtmlFormatter class in formatters.py
def create_tag_span_with_border(text, bg_color, text_color, border_color, border_width):
    """Create an HTML span tag with styling for a tag/pill that includes a border.
    
    Args:
        text: Text content
        bg_color: Background color
        text_color: Text color
        border_color: Border color
        border_width: Border width
        
    Returns:
        HTML span tag string with border
    """
    tag_style = f"display:inline-block; padding:1px 4px; border-radius:3px; margin-right:1px; white-space:nowrap; border:{border_width} solid {border_color};"
    return f'<span style="{tag_style} background-color:{bg_color}; color:{text_color};">{text}</span>'

# Modified format_property_tags function in utils.py
def format_property_tags(row: pd.Series) -> str:
    """Format property tags with reduced padding."""
    import re  # Make sure re is imported
    
    tags = []
    tag_flags = generate_tags_for_row(row)
    distance_value = row.get("distance_sort")
    # Existing code for distance tags
    if distance_value is not None and not pd.isna(distance_value):
        walking_minutes = (distance_value / 5) * 60
        time_text = TimeFormatter.format_walking_time(distance_value)

        if walking_minutes < 12:
            bg_color, text_color = "#4285f4", "#ffffff"
        elif walking_minutes < 20:
            bg_color, text_color = "#aecbfa", "#174ea6"
        elif walking_minutes < 30:
            bg_color, text_color = "#aecbfa", "#174ea6"
        else:
            bg_color, text_color = "#dadce0", "#3c4043"

        tags.append(HtmlFormatter.create_tag_span(time_text, bg_color, text_color))

    # Existing code for neighborhood tags
    if neighborhood := tag_flags.get("neighborhood"):
        if tag_flags["is_hamovniki"]:
            bg_color, text_color = "#e0f7f7", "#0c5460"
        elif tag_flags["is_arbat"]:
            bg_color, text_color = "#d0d1ff", "#3f3fa3"
        else:
            bg_color, text_color = "#dadce0", "#3c4043"

        tags.append(HtmlFormatter.create_tag_span(neighborhood, bg_color, text_color))
    # Add metro station tag if available
    if metro_station := row.get("metro_station"):
        if isinstance(metro_station, str) and metro_station.strip():
            # Clean the metro station name (remove parentheses, etc.)
            clean_station = re.sub(r'\s*\([^)]*\)', '', metro_station).strip()
            
            # Try to find a matching station
            line_number = None
            for station, line in METRO_STATIONS_TO_LINE.items():
                if station in clean_station or clean_station in station:
                    line_number = line
                    break
            
            if line_number:
                # Get the color for this line
                bg_color = LINE_TO_COLOR.get(line_number, "#dadce0")  # Default gray if line not found
                
                # Special styling for MCC (Line 14) with red border
                if line_number == 14:
                    text_color = "#000000"  # Black text for better visibility on white
                    # Add MCC prefix if not in the name already
                    if "МЦК" not in clean_station and "MCC" not in clean_station and "мцк" not in clean_station.lower():
                        station_display = f"{clean_station}"
                    else:
                        station_display = clean_station
                    
                    # Create special tag with red border for MCC
                    # Using HtmlFormatter.create_tag_span_with_border directly at first
                    tag_style = f"display:inline-block; padding:1px 4px; border-radius:3px; margin-right:1px; white-space:nowrap; border:1px solid #EF161E;"
                    tags.append(f'<span style="{tag_style} background-color:{bg_color}; color:{text_color};">{station_display}</span>')
                else:
                    text_color = "#ffffff"  # White text for all other lines
                    # Create the standard tag with station name and line color
                    tags.append(HtmlFormatter.create_tag_span(clean_station, bg_color, text_color))



    return HtmlFormatter.create_flex_container("".join(tags)) if tags else ""

    

def format_rental_period(value: Optional[str]) -> str:
    """Format rental period with more intuitive abbreviation."""
    if value == "От года":
        return "год+"
    elif value == "На несколько месяцев":
        return "мес+"
    return "--"


def format_utilities(value: Optional[str]) -> str:
    """Format utilities info with clearer abbreviation."""
    if value is None:
        return "--"
    if "без счётчиков" in value:
        return "+счет"
    elif "счётчики включены" in value:
        return "-"
    return "--"


def calculate_monthly_burden(row: pd.Series) -> Optional[float]:
    """Calculate average monthly financial burden over 12 months."""
    try:
        price = pd.to_numeric(row["price_value"], errors="coerce")
        comm = pd.to_numeric(row["commission_value"], errors="coerce")
        dep = pd.to_numeric(row["deposit_value"], errors="coerce")
        return PriceFormatter.calculate_monthly_burden(price, comm, dep)
    except Exception as e:
        logger.error(f"Error calculating burden: {e}")
        return None


def format_burden(row: pd.Series) -> str:
    """Format the burden value with comparison to price."""
    try:
        if (
            pd.isna(row["monthly_burden"])
            or pd.isna(row["price_value"])
            or row["price_value"] <= 0
        ):
            return "--"

        burden = float(row["monthly_burden"])
        price = float(row["price_value"])
        burden_formatted = f"{'{:,}'.format(int(burden)).replace(',', ' ')} ₽"
        diff_percent = int(((burden / price) - 1) * 100)

        return f"{burden_formatted}/мес." if diff_percent > 2 else burden_formatted
    except Exception as e:
        logger.error(f"Error formatting burden: {e}")
        return "--"
