# app/utils.py
import pandas as pd
import json
import os
import logging
from pathlib import Path
from app.config import CONFIG, MOSCOW_TZ
from app.formatters import PriceFormatter, TimeFormatter, DataExtractor, FormatUtils
from app.app_config import AppConfig

logger = logging.getLogger(__name__)

class DataManager:
    """Centralized manager for all data operations with improved error handling."""
    
    @staticmethod
    def load_csv_safely(file_path):
        """Load a CSV file with robust error handling for malformed files."""
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return pd.DataFrame()

        try:
            # First try using Python's built-in CSV module which is more forgiving
            import csv

            # Read raw data while auto-detecting dialect
            with open(file_path, "r", encoding="utf-8") as f:
                # Sample first 1000 chars to detect format
                sample = f.read(1000)
                f.seek(0)

                # Try to detect the dialect
                try:
                    dialect = csv.Sniffer().sniff(sample)
                    reader = csv.reader(f, dialect)
                except:
                    # If detection fails, use most permissive settings
                    reader = csv.reader(
                        f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
                    )

                rows = list(reader)

            if not rows:
                return pd.DataFrame()

            # Find maximum field count
            max_fields = max(len(row) for row in rows)

            # Use header as column names, padded if needed
            header = rows[0]

            # Pad header if it has fewer columns than data rows
            if len(header) < max_fields:
                header = header + [f"unnamed_{i}" for i in range(len(header), max_fields)]

            # Fix possible duplicate column names
            unique_header = []
            seen = set()

            for col in header:
                if col in seen or not col:  # Also handle empty column names
                    # Add suffix to make the column name unique
                    count = 1
                    new_col = f"column_{count}" if not col else f"{col}_{count}"
                    while new_col in seen:
                        count += 1
                        new_col = f"column_{count}" if not col else f"{col}_{count}"
                    unique_header.append(new_col)
                else:
                    unique_header.append(col)
                seen.add(unique_header[-1])

            # Create DataFrame, padding rows that have fewer fields
            data = []
            for row in rows[1:]:  # Skip header
                # Pad row if needed
                if len(row) < max_fields:
                    row = row + [""] * (max_fields - len(row))
                # Truncate if longer (shouldn't happen with max_fields)
                data.append(row[:max_fields])

            df = pd.DataFrame(data, columns=unique_header)
            return df

        except Exception as e:
            logger.error(f"Error in CSV module parsing for {file_path}: {str(e)}")

            # Fallback to pandas with error handling options
            try:
                # Try with some common settings that might help with malformed files
                return pd.read_csv(
                    file_path,
                    encoding="utf-8",
                    on_bad_lines="skip",  # For newer pandas versions
                    escapechar="\\",
                    quotechar='"',
                    low_memory=False,
                )
            except Exception as e2:
                try:
                    # For older pandas versions
                    return pd.read_csv(
                        file_path,
                        encoding="utf-8",
                        error_bad_lines=False,  # Deprecated but works in older pandas
                        warn_bad_lines=True,
                        low_memory=False,
                    )
                except Exception as e3:
                    logger.error(f"All loading methods failed for {file_path}: {str(e3)}")
                    return pd.DataFrame()  # Return empty DataFrame
    
    @staticmethod
    def load_data():
        """Load main apartment data from CSV files."""
        try:
            # Use AppConfig for consistent path management
            data_path = AppConfig.get_cian_data_path("cian_apartments.csv")
            logger.info(f"Loading data from: {data_path}")
            
            if not os.path.exists(data_path):
                logger.error(f"Data file not found: {data_path}")
                return pd.DataFrame(), "Data file not found"
                
            df = pd.read_csv(data_path, encoding="utf-8", comment="#")
            logger.info(f"Successfully loaded {len(df)} rows")
            
            # Load metadata
            update_time = DataManager._extract_update_time()
            
            return df, update_time
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return pd.DataFrame(), f"Error: {e}"
    
    @staticmethod
    def _extract_update_time():
        """Extract update time from metadata file."""
        try:
            meta_path = AppConfig.get_cian_data_path("cian_apartments.meta.json")
            logger.info(f"Reading metadata from: {meta_path}")
            
            if not os.path.exists(meta_path):
                logger.warning(f"Metadata file not found: {meta_path}")
                return "Unknown"
                
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                update_time_str = metadata.get("last_updated", "Unknown")
                try:
                    dt = pd.to_datetime(update_time_str)
                    return dt.strftime("%d.%m.%Y %H:%M:%S")
                except:
                    return update_time_str
        except Exception as e:
            logger.error(f"Error reading metadata file: {e}")
            
            # Fall back to reading metadata from the CSV header
            try:
                data_path = AppConfig.get_cian_data_path("cian_apartments.csv")
                with open(data_path, encoding="utf-8") as f:
                    first_line = f.readline()
                    if "last_updated=" in first_line:
                        parts = first_line.split("last_updated=")
                        if len(parts) > 1:
                            return parts[1].split(",")[0].strip()
            except Exception as e2:
                logger.error(f"Error reading CSV header: {e2}")
            
            return "Unknown"
    
    @staticmethod
    def process_data(df):
        """Process and transform raw dataframe into display-ready format."""
        if df.empty:
            return df
            
        # Convert types
        df["offer_id"] = df["offer_id"].astype(str)
        
        # Create derived columns through specialized methods
        df = DataManager._process_links(df)
        df = DataManager._process_metrics(df)
        df = DataManager._process_dates(df)
        df = DataManager._process_financial_info(df)
        df = DataManager._create_display_columns(df)
        
        # Generate tags and sort
        df["tags"] = df.apply(generate_tags_for_row, axis=1)
        df = DataManager._apply_default_sorting(df)
        
        return df
    
    @staticmethod
    def _process_links(df):
        """Process address and offer links."""
        base_url = CONFIG['base_url']
        
        df["address"] = df.apply(
            lambda r: f"[{r['address']}]({base_url}{r['offer_id']}/)", axis=1
        )
        df["offer_link"] = df["offer_id"].apply(
            lambda x: f"[View]({base_url}{x}/)"
        )
        df["address_title"] = df.apply(
            lambda r: f"[{r['address']}]({base_url}{r['offer_id']}/)<br>{r['title']}",
            axis=1,
        )
        return df
    
    @staticmethod
    def _process_metrics(df):
        """Process distance and other metrics."""
        df["distance_sort"] = pd.to_numeric(df["distance"], errors="coerce")
        df["distance"] = df["distance_sort"].apply(
            lambda x: f"{x:.2f} km" if pd.notnull(x) else ""
        )
        return df
    
    @staticmethod
    def _process_dates(df):
        """Process dates and timestamps."""
        # Regular updated_time field
        df["updated_time_sort"] = pd.to_datetime(df["updated_time"], errors="coerce")
        df["updated_time"] = df["updated_time_sort"].apply(
            lambda x: format_text(x, lambda dt: TimeFormatter.format_date(dt, MOSCOW_TZ), "")
        )

        # Process unpublished_date fields with explicit format
        df["unpublished_date_sort"] = pd.to_datetime(
            df["unpublished_date"],
            format="%Y-%m-%d %H:%M:%S",  # Format matching "2025-04-10 00:04:00"
            errors="coerce",
        )
        df["unpublished_date"] = df["unpublished_date_sort"].apply(
            lambda x: format_text(x, lambda dt: TimeFormatter.format_date(dt, MOSCOW_TZ), "--")
        )
        
        # Combined date for sorting
        df["date_sort_combined"] = df.apply(
            lambda r: (
                r["updated_time_sort"]
                if r["status"] == "active"
                else r["unpublished_date_sort"]
            ),
            axis=1,
        )
        
        return df
    
    @staticmethod
    def _process_financial_info(df):
        """Process price, commission, deposit and other financial information."""
        # Price value formatting
        df["price_value_formatted"] = df["price_value"].apply(
            lambda x: format_text(x, lambda v: PriceFormatter.format_price(v), "--")
        )
        
        # Cian estimation formatting
        df["cian_estimation_formatted"] = df["cian_estimation_value"].apply(
            lambda x: format_text(x, lambda v: PriceFormatter.format_price(v), "--")
        )
        
        # Price difference formatting
        df["price_difference_formatted"] = df["price_difference_value"].apply(
            lambda x: format_text(x, lambda v: PriceFormatter.format_price(v, abbreviate=True), "")
        )
        
        # Price change formatting
        df["price_change_formatted"] = df["price_change_value"].apply(
            PriceFormatter.format_price_change
        )
        
        # Process rental details with improved abbreviations
        df["rental_period_abbr"] = df["rental_period"].apply(format_rental_period)
        df["utilities_type_abbr"] = df["utilities_type"].apply(format_utilities)
        
        # Extract and format commission values
        df["commission_value"] = df["commission_info"].apply(DataExtractor.extract_commission_value)
        df["commission_info_abbr"] = df["commission_value"].apply(PriceFormatter.format_commission)
        
        # Extract and format deposit values
        df["deposit_value"] = df["deposit_info"].apply(DataExtractor.extract_deposit_value)
        df["deposit_info_abbr"] = df["deposit_value"].apply(PriceFormatter.format_deposit)
        
        # Calculate financial burden
        df["monthly_burden"] = df.apply(calculate_monthly_burden, axis=1)
        df["monthly_burden_formatted"] = df.apply(format_burden, axis=1)
        
        return df
    
    @staticmethod
    def _create_display_columns(df):
        """Create combined display columns for the UI."""
        # Price text with formatted style
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
        
        # Price info with commission and deposit
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
        
        # Update title with status information
        df["update_title"] = df.apply(format_update_title, axis=1)
        
        # Property tags for distance and neighborhood
        df["property_tags"] = df.apply(format_property_tags, axis=1)
        
        # Simple update time display
        df["update_time"] = df.apply(
            lambda r: f'<strong>{r["updated_time" if r["status"] == "active" else "unpublished_date"]}</strong>',
            axis=1,
        )
        
        # Basic price change display
        df["price_change"] = df["price_change_formatted"]
        
        return df
    
    @staticmethod
    def _apply_default_sorting(df):
        """Apply default sorting to the dataframe."""
        # Create a sort key column (active first, then by distance)
        df["sort_key"] = df["status"].apply(lambda x: 1)  # All items have same priority now
        
        # Sort by sort_key and distance
        df = df.sort_values(["sort_key", "distance_sort"], ascending=[True, True]).drop(
            columns="sort_key"
        )
        
        return df
    
    # Updated filter method in utils.py - DataManager class
    
    @staticmethod
    def filter_data(df, filters=None):
        """Filter data based on user-selected filters with cumulative filtering."""
        if df.empty or not filters:
            return df
    
        filtered_df = df.copy()
    
        # Apply price filter
        price_value = filters.get("price_value")
        if price_value and price_value != float("inf") and "price_value" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["price_value"] <= price_value]
            
        # Apply distance filter
        distance_value = filters.get("distance_value") 
        if distance_value and distance_value != float("inf") and "distance_sort" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["distance_sort"] <= distance_value]
            
        # Apply each toggle filter individually (AND logic)
        # Nearby filter (within 1.5km)
        if filters.get("nearest") and "distance_sort" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["distance_sort"] < 1.5]
            
        # Below estimate filter (price difference > 5000)
        if filters.get("below_estimate") and "price_difference_value" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["price_difference_value"] >= 5000]
            
        # Active listings filter
        if filters.get("inactive") and "status" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["status"] == "active"]
            
        # Updated today filter
        if filters.get("updated_today") and "updated_time_sort" in filtered_df.columns:
            filtered_df["updated_time_sort"] = pd.to_datetime(
                filtered_df["updated_time_sort"], errors="coerce"
            )
            recent_time = pd.Timestamp.now() - pd.Timedelta(hours=24)
            filtered_df = filtered_df[filtered_df["updated_time_sort"] > recent_time]
    
        return filtered_df
        
    @staticmethod
    def filter_and_sort_data(df, filters=None, sort_by=None):
        """Filter and sort data in a single function."""
        # Apply filtering
        df = DataManager.filter_data(df, filters)
        
        if df.empty:
            return df
            
        # Apply sorting from filter store
        if filters and "sort_column" in filters and "sort_direction" in filters:
            sort_column = filters["sort_column"]
            
            # Make sure the sort column exists in the DataFrame
            if sort_column in df.columns:
                sort_ascending = filters["sort_direction"] == "asc"
                df = df.sort_values(sort_column, ascending=sort_ascending)
            else:
                logger.warning(f"Sort column '{sort_column}' not found in DataFrame")
                # Fallback to default sort if column doesn't exist
                if "price_value" in df.columns:
                    df = df.sort_values("price_value", ascending=True)

        # Backward compatibility for table sort_by parameter
        elif sort_by:
            for item in sort_by:
                col = CONFIG["columns"]["sort_map"].get(
                    item["column_id"], item["column_id"]
                )
                if col in df.columns:
                    df = df.sort_values(col, ascending=item["direction"] == "asc")

        return df


def load_apartment_details(offer_id):
    """
    Load all details for a specific apartment by offer_id,
    combining data from multiple CSV files with robust error handling.
    """
    # Get the data directory path using AppConfig
    data_dir = AppConfig.get_cian_data_path()
    
    logger.info(f"Loading apartment details from: {data_dir}")

    # Initialize the result dictionary
    apartment_data = {"offer_id": offer_id}

    # List of files to check and their corresponding field groups
    files_to_check = [
        ("price_history.csv", "price_history"),
        ("stats.csv", "stats"),
        ("features.csv", "features"),
        ("rental_terms.csv", "terms"),
        ("apartment_details.csv", "apartment"),
        ("building_details.csv", "building"),
    ]

    for filename, group_name in files_to_check:
        filepath = os.path.join(data_dir, filename)

        if not os.path.exists(filepath):
            continue

        try:
            # Use the safer CSV loading approach from DataManager
            df = DataManager.load_csv_safely(filepath)

            if df.empty:
                continue

            if "offer_id" not in df.columns:
                logger.warning(f"Warning: 'offer_id' column missing in {filepath}")
                continue

            # Convert offer_id to string for safer comparison
            df["offer_id"] = df["offer_id"].astype(str)
            offer_id_str = str(offer_id)

            # Filter for the specific offer_id
            filtered_df = df[df["offer_id"] == offer_id_str]

            if not filtered_df.empty:
                if group_name == "price_history":
                    # For price history, we may have multiple rows
                    apartment_data[group_name] = filtered_df.to_dict("records")
                else:
                    # For other files, we expect just one row per offer_id
                    apartment_data[group_name] = filtered_df.iloc[0].to_dict()

                logger.info(f"Successfully loaded {group_name} data for offer_id {offer_id}")
            else:
                logger.warning(f"No data found for offer_id {offer_id} in {filepath}")
        except Exception as e:
            logger.error(f"Error processing data from {filepath}: {e}")

    return apartment_data


def generate_tags_for_row(row):
    """Generate tag flags for various row conditions."""
    # Initialize tag dictionary
    tags = {
        "below_estimate": False,
        "nearby": False,
        "updated_today": False,
        "neighborhood": None,  # Store the neighborhood name
        "is_hamovniki": False,  # Special flag for Хамовники
        "is_arbat": False,  # Special flag for Арбат
    }

    # Check for "below estimate" condition
    if row.get("price_difference_value", 0) > 0 and row.get("status") != "non active":
        tags["below_estimate"] = True

    # Check for "nearby" condition (within 1.5km)
    if row.get("distance_sort", 999) < 1.5 and row.get("status") != "non active":
        tags["nearby"] = True

    # Check for "updated today" condition
    try:
        # Get the timestamp from 24 hours ago
        recent_time = pd.Timestamp.now() - pd.Timedelta(hours=24)

        # Get the row's timestamp (or a default far past date if not available)
        row_time = row.get("updated_time_sort")
        if row_time and not pd.isna(row_time):
            row_dt = pd.to_datetime(row_time)
            if row_dt.date() == pd.Timestamp.now().date():
                tags["updated_today"] = True
    except Exception as e:
        # Add error handling to prevent crashes
        logger.error(f"Error processing timestamp: {e}")

    # Extract neighborhood if available
    neighborhood = str(row.get("neighborhood", ""))
    if neighborhood and neighborhood != "nan" and neighborhood != "None":
        # Extract just the neighborhood name if it follows a pattern like "р-н Хамовники"
        if "р-н " in neighborhood:
            neighborhood_name = neighborhood.split("р-н ")[1].strip()
        else:
            neighborhood_name = neighborhood.strip()

        tags["neighborhood"] = neighborhood_name

        # Check if this is Хамовники
        if "Хамовники" in neighborhood:
            tags["is_hamovniki"] = True

        # Check if this is Арбат
        if "Арбат" in neighborhood:
            tags["is_arbat"] = True

    return tags


def format_update_title(row):
    """Format the update_title column with enhanced responsive design."""
    tag_style = "display:inline-block; padding:1px 4px; border-radius:6px; margin:0; white-space:nowrap;"
    tag_flags = generate_tags_for_row(row)

    # Showing date
    if row["status"] == "active":
        time_str = row["updated_time"]
    else:
        time_str = row["unpublished_date"] or row["updated_time"]

    # Use a more compact layout with better centering
    html = f'<div style="text-align:center; width:100%; display:block; padding:0; margin:0;">'
    html += f"<strong>{time_str}</strong>"

    # Show price change only if status is active
    if row["status"] == "active" and row.get("price_change_formatted"):
        html += f'<br>{row["price_change_formatted"]}'

    # Tags with improved styling
    tags = []
    if row["status"] != "active":
        tags.append(
            f'<span style="{tag_style} background-color:#f5f5f5; color:#666;">📦 архив</span>'
        )

    if tags:
        html += "<br>" + "".join(tags)

    html += "</div>"
    return html


def format_property_tags(row):
    """Format property tags with reduced padding."""
    # Reduce padding in tag style
    tag_style = "display:inline-block; padding:1px 4px; border-radius:3px; margin-right:1px; white-space:nowrap;"
    tags = []
    tag_flags = generate_tags_for_row(row)
    distance_value = row.get("distance_sort")

    if distance_value is not None and not pd.isna(distance_value):
        # Calculate walking time in minutes
        walking_minutes = (distance_value / 5) * 60

        # Format time display using the TimeFormatter
        time_text = TimeFormatter.format_walking_time(distance_value)

        # Different background colors based on time
        if walking_minutes < 12:  # Less than 12 minutes (1km)
            bg_color = "#4285f4"  # Bright blue for very close
            text_color = "#ffffff"  # White text for contrast
        elif walking_minutes < 20:  # Less than 20 minutes (1.67km)
            bg_color = "#aecbfa"  # Medium blue for nearby
            text_color = "#174ea6"  # Dark blue text
        elif walking_minutes < 30:  # Less than 40 minutes (3.33km)
            bg_color = "#aecbfa"  # Light blue for moderate distance
            text_color = "#174ea6"  # Dark blue text
        else:
            bg_color = "#dadce0"  # Gray for farther distances
            text_color = "#3c4043"  # Dark gray text

        tags.append(
            f'<span style="{tag_style} background-color:{bg_color}; color:{text_color};">{time_text}</span>'
        )

    # Add neighborhood tag if available
    if tag_flags.get("neighborhood"):
        neighborhood = tag_flags["neighborhood"]

        # Special style for Хамовники
        if tag_flags["is_hamovniki"]:
            bg_color = "#e0f7f7"  # Teal
            text_color = "#0c5460"  # Dark teal
        # Special style for Арбат
        elif tag_flags["is_arbat"]:
            bg_color = "#d0d1ff"  # Light indigo/purple
            text_color = "#3f3fa3"  # Dark indigo/purple
        else:
            # Default style for all other neighborhoods
            bg_color = "#dadce0"  # Gray
            text_color = "#3c4043"  # Dark gray

        tags.append(
            f'<span style="{tag_style} background-color:{bg_color}; color:{text_color};">{neighborhood}</span>'
        )

    # Use minimal padding and gap in the container
    return (
        f'<div style="display:flex; flex-wrap:wrap; gap:1px; justify-content:flex-start; padding:0;">{"".join(tags)}</div>'
        if tags
        else ""
    )


# Helper function to apply formatters safely
def format_text(value, formatter, default=""):
    """Generic formatter with default handling."""
    if value is None or pd.isna(value):
        return default
    return formatter(value)


# Rental period formatting
def format_rental_period(value):
    """Format rental period with more intuitive abbreviation."""
    if value == "От года":
        return "год+"
    elif value == "На несколько месяцев":
        return "мес+"
    return "--"


# Utilities formatting
def format_utilities(value):
    """Format utilities info with clearer abbreviation."""
    if "без счётчиков" in value:
        return "+счет"
    elif "счётчики включены" in value:
        return "-"
    return "--"


# Calculate financial burden
def calculate_monthly_burden(row):
    """Calculate average monthly financial burden over 12 months."""
    try:
        price = pd.to_numeric(row["price_value"], errors="coerce")
        comm = pd.to_numeric(row["commission_value"], errors="coerce")
        dep = pd.to_numeric(row["deposit_value"], errors="coerce")

        return PriceFormatter.calculate_monthly_burden(price, comm, dep)
    except Exception as e:
        logger.error(f"Error calculating burden: {e}")
        return None


# Format burden value
def format_burden(row):
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

        if diff_percent > 2:
            return f"{burden_formatted}/мес."
        else:
            return burden_formatted
    except Exception as e:
        logger.error(f"Error formatting burden: {e}")
        return "--"