# app/utils.py
import pandas as pd
import json
import os
import logging
import traceback
from typing import Tuple, Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import requests
from urllib.parse import urljoin
from app.config import CONFIG, MOSCOW_TZ
from app.app_config import AppConfig

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Standardized error handling and logging."""
    @staticmethod
    def try_operation(logger, operation_name, operation_func, *args, default_return=None, **kwargs):
        """Execute operation with error handling."""
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {operation_name}: {str(e)}")
            return default_return

    @staticmethod
    def fallback_chain(logger, operation_name, operations):
        """Try operations in sequence until one succeeds."""
        for i, (func, args, kwargs) in enumerate(operations):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Fallback {i+1}/{len(operations)} failed: {e}")
                if i == len(operations) - 1:
                    logger.error(f"All fallbacks failed")
        return None

# Metro station data
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
    'Новослободская': 5, 'Проспект Мира': 5, 'Добрынинская': 5, 'Краснопресненская': 5,
    
    # Line 6 (Калужско-Рижская)
    'Медведково': 6, 'Бабушкинская': 6, 'Свиблово': 6, 'Ботанический сад': 6, 
    'ВДНХ': 6, 'Алексеевская': 6, 'Рижская': 6, 'Сухаревская': 6, 
    'Тургеневская': 6, 'Китай-город': 6, 'Третьяковская': 6, 'Шаболовская': 6, 
    'Ленинский проспект': 6, 'Академическая': 6, 'Профсоюзная': 6, 'Новые Черемушки': 6, 
    'Калужская': 6, 'Беляево': 6, 'Коньково': 6, 'Теплый Стан': 6, 
    'Ясенево': 6, 'Новоясеневская': 6, 'Октябрьская': 5,
    
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


class DataManager:
    """Centralized data management."""
    @staticmethod
    def load_csv_from_url(url):
        """Load CSV from URL."""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return pd.read_csv(pd.io.common.StringIO(response.text), encoding="utf-8")
            else:
                logger.error(f"Failed to fetch CSV: {url}, Status: {response.status_code}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading CSV from URL: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def load_csv_safely(file_path):
        """Load CSV with fallback strategies."""
        filename = os.path.basename(file_path)
        
        # Check for GitHub first if needed
        if AppConfig.always_use_github_for(filename):
            github_url = AppConfig.get_github_url("cian_data", filename)
            return DataManager.load_csv_from_url(github_url)
        
        # Try hybrid approach if configured
        if AppConfig.should_use_hybrid_for_apartment_details():
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
                    if not df.empty:
                        return df
                except Exception:
                    pass
                    
            # Fall back to GitHub
            github_url = AppConfig.get_github_url("cian_data", filename)
            return DataManager.load_csv_from_url(github_url)
        
        # Local file as last resort
        if not os.path.exists(file_path):
            return pd.DataFrame()

        try:
            return pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
        except Exception:
            try:
                return pd.read_csv(file_path, encoding="utf-8", error_bad_lines=False)
            except Exception:
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
        """Extract update time from metadata with proper timezone."""
        try:
            meta_url = AppConfig.get_github_url("cian_data", "cian_apartments.meta.json")
            response = requests.get(meta_url)
            
            if response.status_code == 200:
                metadata = response.json()
                update_time_str = metadata.get("last_updated", "Unknown")
                try:
                    # Apply Moscow timezone
                    dt = pd.to_datetime(update_time_str).tz_localize('UTC').tz_convert(MOSCOW_TZ)
                    return dt.strftime("%d.%m.%Y %H:%M:%S")
                except:
                    return update_time_str
            return "Unknown"
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return "Unknown"

    @staticmethod
    def process_data(df):
        """Process dataframe into display format."""
        if df.empty:
            return df

        df["offer_id"] = df["offer_id"].astype(str)

        # Process data transformations
        DataManager._process_links(df)
        DataManager._process_metrics(df)
        DataManager._process_dates(df)
        DataManager._process_financial_info(df)
        DataManager._create_display_columns(df)

        df["tags"] = df.apply(generate_tags_for_row, axis=1)

        # Sort by status and distance
        df["sort_key"] = df["status"].apply(lambda x: 1)
        df = df.sort_values(["sort_key", "distance_sort"], ascending=[True, True]).drop(columns="sort_key")

        return df

    @staticmethod
    def _process_links(df):
        """Process address and offer links."""
        base_url = CONFIG["base_url"]
        df["address"] = df.apply(lambda r: f"[{r['address']}]({base_url}{r['offer_id']}/)", axis=1)
        df["offer_link"] = df["offer_id"].apply(lambda x: f"[View]({base_url}{x}/)")
        df["address_title"] = df.apply(lambda r: f"[{r['address']}]({base_url}{r['offer_id']}/)<br>{r['title']}", axis=1)

    @staticmethod
    def _process_metrics(df):
        """Process distance and other metrics."""
        df["distance_sort"] = pd.to_numeric(df["distance"], errors="coerce")
        df["distance"] = df["distance_sort"].apply(lambda x: f"{x:.2f} km" if pd.notnull(x) else "")

    @staticmethod
    def _process_dates(df):
        """Process dates and timestamps with Moscow timezone."""
        # Use Moscow timezone for now
        now = pd.Timestamp.now(tz=MOSCOW_TZ)
        
        # Convert datetime columns with timezone handling
        for col in ["updated_time", "unpublished_date", "activity_date"]:
            # Convert to datetime and apply timezone
            df[f"{col}_sort"] = pd.to_datetime(df[col], errors="coerce")
            # If timezone info is missing, assume UTC and convert to Moscow
            df[f"{col}_sort"] = df[f"{col}_sort"].apply(
                lambda x: x.tz_localize('UTC').tz_convert(MOSCOW_TZ) 
                if pd.notnull(x) and x.tzinfo is None else x
            )
            # Format for display
            df[col] = df[f"{col}_sort"].apply(
                lambda x: format_date(x, MOSCOW_TZ) if pd.notnull(x) else "--"
            )
        
        # Rest of the method remains unchanged but will now use timezone-aware datetimes
        df["days_active_value"] = df.apply(
            lambda r: (now - r["updated_time_sort"]).days if r["status"] == "active" and pd.notnull(r["updated_time_sort"])
            else (r["unpublished_date_sort"] - r["updated_time_sort"]).days if r["status"] == "non active" 
            and pd.notnull(r["unpublished_date_sort"]) and pd.notnull(r["updated_time_sort"]) else None, axis=1)
                
        # Calculate hours for entries where days = 0
        df["hours_active_value"] = df.apply(
            lambda r: int((now - r["updated_time_sort"]).total_seconds() // 3600) 
            if r["status"] == "active" and pd.notnull(r["updated_time_sort"]) and (now - r["updated_time_sort"]).days == 0
            else int((r["unpublished_date_sort"] - r["updated_time_sort"]).total_seconds() // 3600) 
            if r["status"] == "non active" and pd.notnull(r["unpublished_date_sort"]) 
            and pd.notnull(r["updated_time_sort"]) and (r["unpublished_date_sort"] - r["updated_time_sort"]).days == 0
            else None, axis=1)
        
        # Format days active
        df["days_active"] = df.apply(
            lambda r: f"{int(r['hours_active_value'])} ч." if pd.notnull(r['days_active_value']) and r['days_active_value'] == 0 
            and pd.notnull(r['hours_active_value']) else f"{int(r['days_active_value'])} дн." 
            if pd.notnull(r['days_active_value']) and r['days_active_value'] >= 0 else "--", axis=1)
                    
        # Combined date for sorting
        df["date_sort_combined"] = df["updated_time_sort"]

    @staticmethod
    def _process_financial_info(df):
        """Process financial information."""
        # Format price columns
        for col in ["price_value", "cian_estimation_value"]:
            df[f"{col}_formatted"] = df[col].apply(lambda x: format_number(x) if is_numeric(x) else "--")
            
        df["price_difference_formatted"] = df["price_difference_value"].apply(
            lambda x: format_number(x, abbreviate=True) if is_numeric(x) else "")
            
        df["price_change_formatted"] = df["price_change_value"].apply(format_price_change)

        # Format period and utilities
        df["rental_period_abbr"] = df["rental_period"].apply(format_rental_period)
        df["utilities_type_abbr"] = df["utilities_type"].apply(format_utilities)

        # Process commission and deposit
        df["commission_value"] = df["commission_info"].apply(extract_commission_value)
        df["commission_info_abbr"] = df["commission_value"].apply(format_commission)
        df["deposit_value"] = df["deposit_info"].apply(extract_deposit_value)
        df["deposit_info_abbr"] = df["deposit_value"].apply(format_deposit)

        # Calculate monthly burden
        df["monthly_burden"] = df.apply(calculate_monthly_burden, axis=1)
        df["monthly_burden_formatted"] = df.apply(format_burden, axis=1)

    @staticmethod
    def _create_display_columns(df):
        """Create combined display columns."""
        # Price text with highlighting
        df["price_text"] = df.apply(
            lambda r: f'<div style="display:block; text-align:center; margin:0; padding:0;">'
            f'<strong style="margin:0; padding:0;">{r["price_value_formatted"]}</strong>'
            + (f'<br><span style="display:inline-block; padding:1px 4px; border-radius:6px; margin-top:2px; '
               f'background-color:#fcf3cd; color:#856404;">хорошая цена</span>'
               if r.get("price_difference_value", 0) > 0 and r.get("status") != "non active" else "")
            + "</div>", axis=1)

        # Financial info
        df["commission_text"] = df.apply(lambda r: f'комиссия {r["commission_info_abbr"]}', axis=1)
        df["deposit_text"] = df.apply(lambda r: f'залог {r["deposit_info_abbr"]}', axis=1)
        df["price_info"] = df.apply(
            lambda r: f"{r['price_text']}<br>{r['commission_text']}<br> {r['deposit_text']}", axis=1)

        # Update info
        df["update_title"] = df.apply(format_update_title, axis=1)
        df["property_tags"] = df.apply(format_property_tags, axis=1)
        df["update_time"] = df.apply(lambda r: f'<strong>{r["updated_time"]}</strong>', axis=1)
        df["price_change"] = df["price_change_formatted"]
        df["activity_date"] = df.apply(format_activity_date, axis=1)
        df["days_active"] = df.apply(format_active_days, axis=1)
        
        # Combine update title with activity date
        df["update_title"] = df.apply(
            lambda r: f"{r['update_title']}{r['activity_date']}" if pd.notnull(r['activity_date']) 
            and r['activity_date'] != "" else r['update_title'], axis=1)

    @staticmethod
    def filter_data(df, filters=None):
        """Filter data based on user filters."""
        if df.empty or not filters:
            return df

        filtered_df = df.copy()

        # Apply price filter
        if (price_value := filters.get("price_value")) and price_value != float("inf") and "price_value" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["price_value"] <= price_value]

        # Apply distance filter
        if (distance_value := filters.get("distance_value")) and distance_value != float("inf") and "distance_sort" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["distance_sort"] <= distance_value]

        # Apply feature filters
        if filters.get("nearest") and "distance_sort" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["distance_sort"] < 1.5]

        if filters.get("below_estimate") and "price_difference_value" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["price_difference_value"] >= 5000]

        if filters.get("inactive") and "status" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["status"] == "active"]

        if filters.get("updated_today") and "updated_time_sort" in filtered_df.columns:
            recent_time = pd.Timestamp.now() - pd.Timedelta(hours=24)
            filtered_df = filtered_df[filtered_df["updated_time_sort"] > recent_time]
        
        return filtered_df

    @staticmethod
    def filter_and_sort_data(df, filters=None, sort_by=None):
        """Filter and sort data in a single function."""
        df = DataManager.filter_data(df, filters)
        if df.empty:
            return df

        # Apply sorting
        if filters and "sort_column" in filters and "sort_direction" in filters:
            sort_column = filters["sort_column"]
            if sort_column in df.columns:
                df = df.sort_values(sort_column, ascending=filters["sort_direction"] == "asc")
            elif "price_value" in df.columns:
                df = df.sort_values("price_value", ascending=True)
        elif sort_by:
            for item in sort_by:
                col = CONFIG["columns"]["sort_map"].get(item["column_id"], item["column_id"])
                if col in df.columns:
                    df = df.sort_values(col, ascending=item["direction"] == "asc")

        return df

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
                    apartment_data[group_name] = filtered_df.to_dict("records") if group_name == "price_history" else filtered_df.iloc[0].to_dict()
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")

    return apartment_data

# Utility functions
def is_numeric(value):
    """Check if value can be converted to a number."""
    if value is None:
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

def format_date(dt, timezone=MOSCOW_TZ, threshold_hours=24):
    """Format date with relative time for recent dates using Moscow timezone."""
    if dt is None or pd.isna(dt):
        return "--"
        
    # Russian month abbreviations
    month_names = {1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
                   7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек"}
    
    # Ensure timezone is applied
    now = datetime.now(timezone)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone)
    
    delta = now - dt
    today = now.date()
    yesterday = today - timedelta(days=1)

    if delta < timedelta(minutes=1):
        return "только что"
    elif delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() // 60)
        return f"{minutes} {'минуту' if minutes == 1 else 'минуты' if 2 <= minutes <= 4 else 'минут'} назад"
    elif delta < timedelta(hours=6):
        hours = int(delta.total_seconds() // 3600)
        return f"{hours} {'час' if hours == 1 else 'часа' if 2 <= hours <= 4 else 'часов'} назад"
    elif dt.date() == today:
        return f"сегодня, {dt.hour:02}:{dt.minute:02}"
    elif dt.date() == yesterday:
        return f"вчера, {dt.hour:02}:{dt.minute:02}"
    else:
        return f"{dt.day} {month_names[dt.month]}"

def format_price_change(value, decimal_places=0):
    """Format price changes with styling hints."""
    if value is None or pd.isna(value) or (isinstance(value, str) and value.lower() == "new"):
        return ""
            
    try:
        value = float(value)
    except:
        return ""
            
    if abs(value) < 1:
        return ""

    # Colors and formatting
    color = "#2a9d8f" if value < 0 else "#d62828"
    bg_color = "#e6f7f5" if value < 0 else "#fbe9e7"
    arrow = "↓" if value < 0 else "↑"
    
    # Abbreviate large numbers
    if abs(value) >= 1000:
        display = f"{abs(int(value))//1000}K"
    else:
        display = f"{abs(int(value))}"

    return (f'<span style="color:{color}; font-weight:bold; background-color:{bg_color}; '
            f'padding:2px 4px; font-size:0.5rem !important; border-radius:4px; display:inline-block; margin-top:2px;">'
            f"{arrow} {display}</span>")

def extract_commission_value(value):
    """Extract commission percentage from text."""
    if value is None or pd.isna(value):
        return None
    value = str(value).lower()
    if "без комиссии" in value:
        return 0.0
    elif "комиссия" in value:
        import re
        match = re.search(r"(\d+)%", value)
        if match:
            return float(match.group(1))
    return None

def extract_deposit_value(deposit_info):
    """Extract numeric deposit value from text."""
    if deposit_info is None or pd.isna(deposit_info) or deposit_info == "--":
        return None

    if "без залога" in deposit_info.lower():
        return 0

    import re
    match = re.search(r"залог\s+([\d\s\xa0]+)\s*₽", deposit_info, re.IGNORECASE)
    if match:
        amount_str = match.group(1)
        clean_amount = re.sub(r"\s", "", amount_str)
        try:
            return int(clean_amount)
        except ValueError:
            return None
    return None

def format_commission(value):
    """Format commission value."""
    if value == 0:
        return "0%"
    elif isinstance(value, (int, float)):
        return f"{int(value)}%" if value.is_integer() else f"{value}%"
    return "--"

def format_deposit(value):
    """Format deposit value."""
    if value is None or pd.isna(value) or value == "--":
        return "--"
    if value == 0:
        return "0₽"
    elif isinstance(value, (int, float)):
        return format_number(value, include_currency=False, abbreviate=True) + "₽"
    return "--"

def calculate_monthly_burden(row):
    """Calculate average monthly financial burden."""
    try:
        price = pd.to_numeric(row["price_value"], errors="coerce")
        comm = pd.to_numeric(row["commission_value"], errors="coerce")
        dep = pd.to_numeric(row["deposit_value"], errors="coerce")
        
        if pd.isna(price) or price <= 0:
            return None
            
        comm = 0 if pd.isna(comm) else comm
        dep = 0 if pd.isna(dep) else dep
        
        annual_rent = price * 12
        commission_fee = price * (comm / 100)
        total_burden = (annual_rent + commission_fee + dep) / 12
        
        return total_burden
    except Exception as e:
        logger.error(f"Error calculating burden: {e}")
        return None

def format_burden(row):
    """Format burden value with comparison to price."""
    try:
        if pd.isna(row["monthly_burden"]) or pd.isna(row["price_value"]) or row["price_value"] <= 0:
            return "--"

        burden = float(row["monthly_burden"])
        price = float(row["price_value"])
        burden_formatted = f"{'{:,}'.format(int(burden)).replace(',', ' ')} ₽"
        diff_percent = int(((burden / price) - 1) * 100)

        return f"{burden_formatted}/мес." if diff_percent > 2 else burden_formatted
    except Exception:
        return "--"

def format_rental_period(value):
    """Format rental period."""
    if value == "От года":
        return "год+"
    elif value == "На несколько месяцев":
        return "мес+"
    return "--"

def format_utilities(value):
    """Format utilities info."""
    if value is None:
        return "--"
    if "без счётчиков" in value:
        return "+счет"
    elif "счётчики включены" in value:
        return "-"
    return "--"

def generate_tags_for_row(row):
    """Generate tags for row conditions."""
    tags = {
        "below_estimate": row.get("price_difference_value", 0) > 0 and row.get("status") != "non active",
        "nearby": row.get("distance_sort", 999) < 1.5 and row.get("status") != "non active",
        "updated_today": False,
        "neighborhood": None,
        "is_hamovniki": False,
        "is_arbat": False
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
        logger.error(f"Error processing timestamp: {e}")

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

def create_tag_span(text, bg_color, text_color):
    """Create HTML span tag for a pill."""
    style = "display:inline-block; padding:1px 4px; border-radius:3px; margin-right:1px; white-space:nowrap;"
    return f'<span style="{style} background-color:{bg_color}; color:{text_color};">{text}</span>'

def create_flex_container(content):
    """Wrap content in a flex container."""
    return f'<div style="display:flex; flex-wrap:wrap; gap:1px; justify-content:flex-start; padding:0;">{content}</div>'

def format_update_title(row):
    """Format update title with all elements on the same line."""
    time_str = row["updated_time"]
    html = f'<span style="font-size:0.9rem; font-weight:bold; line-height:1.2;">{time_str}</span> '
    
    # Add price change
    if row.get("price_change_formatted"):
        html += f'{row["price_change_formatted"]} '
    
    # Add days active tag
    if pd.notnull(row.get("days_active")) and row["days_active"] != "--":
        days_value = row.get("days_active_value", 0)
        
        # Set colors based on status and age
        if row.get("status") == "non active":
            bg_color, text_color = "#f0f0f0", "#707070"  # Grey for inactive
        elif days_value == 0:
            bg_color, text_color = "#e8f5e9", "#2e7d32"  # Green for today
        elif days_value <= 3:
            bg_color, text_color = "#e3f2fd", "#1565c0"  # Blue for recent
        elif days_value <= 14:
            bg_color, text_color = "#fff3e0", "#e65100"  # Orange for 2 weeks
        else:
            bg_color, text_color = "#ffebee", "#c62828"  # Red for older
            
        html += f'<span style="display:inline-block; padding:1px 4px; border-radius:6px; margin-left:1px; background-color:{bg_color}; color:{text_color};">{row["days_active"]}</span>'
    
    return f'<div style="text-align:center; width:100%;">{html}</div>'

def format_activity_date(row):
    """Format activity date info."""
    if "activity_date" not in row or pd.isna(row["activity_date"]):
        return ""
    
    # Skip if same as updated time
    if pd.notnull(row.get("updated_time_sort")) and pd.notnull(row.get("activity_date_sort")):
        time_diff = abs((row["activity_date_sort"] - row["updated_time_sort"]).total_seconds())
        if time_diff < 60:
            return ""
        
    activity_date = row["activity_date"]
    
    # Format based on status
    if row["status"] == "active":
        html = f'<span style="color:#1976d2; font-size:0.7rem;">🔄</span><span style="font-size:0.9rem; font-weight:normal; line-height:1.2;">{activity_date}</span>'
    else:
        html = f'<span style="display:inline-block; padding:1px 4px; border-radius:6px; margin-left:3px; background-color:#f5f5f5; color:#666;">📦</span><span style="font-size:0.9rem; font-weight:normal; line-height:1.2;">{activity_date}</span> '

    return f'<div style="text-align:center; width:100%;">{html}</div>'

def format_active_days(row):
    """Format active days with styling."""
    if not pd.notnull(row.get("days_active")) or row["days_active"] == "--":
        return ""
        
    days_value = row.get("days_active_value", 0)
    
    # Set colors based on age
    if days_value == 0:
        bg_color, text_color = "#e8f5e9", "#2e7d32"  # Green for today
    elif days_value <= 3:
        bg_color, text_color = "#e3f2fd", "#1565c0"  # Blue for recent
    elif days_value <= 14:
        bg_color, text_color = "#fff3e0", "#e65100"  # Orange for 2 weeks
    else:
        bg_color, text_color = "#ffebee", "#c62828"  # Red for older
        
    html = f'<span style="display:inline-block; padding:1px 4px; border-radius:6px; margin-left:3px; background-color:{bg_color}; color:{text_color};">{row["days_active"]}</span>'
    return f'<div style="text-align:center; width:100%;">{html}</div>'

def format_property_tags(row):
    """Format property tags."""
    tags = []
    tag_flags = generate_tags_for_row(row)
    
    # Format distance tag
    distance_value = row.get("distance_sort")
    if distance_value is not None and not pd.isna(distance_value):
        walking_minutes = (distance_value / 5) * 60
        
        # Format walking time
        if walking_minutes < 60:
            time_text = f"{int(walking_minutes)}м"
        else:
            hours = int(walking_minutes // 60)
            minutes = int(walking_minutes % 60)
            time_text = f"{hours}ч{minutes}м" if minutes > 0 else f"{hours}ч"

        # Set colors based on walking time
        if walking_minutes < 12:
            bg_color, text_color = "#4285f4", "#ffffff"
        elif walking_minutes < 20:
            bg_color, text_color = "#aecbfa", "#174ea6"
        else:
            bg_color, text_color = "#dadce0", "#3c4043"

        tags.append(create_tag_span(time_text, bg_color, text_color))

    # Add neighborhood tag
    if neighborhood := tag_flags.get("neighborhood"):
        if tag_flags["is_hamovniki"]:
            bg_color, text_color = "#e0f7f7", "#0c5460"
        elif tag_flags["is_arbat"]:
            bg_color, text_color = "#d0d1ff", "#3f3fa3"
        else:
            bg_color, text_color = "#dadce0", "#3c4043"

        tags.append(create_tag_span(neighborhood, bg_color, text_color))
        
    # Add metro station tag
    if metro_station := row.get("metro_station"):
        if isinstance(metro_station, str) and metro_station.strip():
            import re
            # Clean station name
            clean_station = re.sub(r'\s*\([^)]*\)', '', metro_station).strip()
            
            # Find matching station
            line_number = None
            for station, line in METRO_STATIONS_TO_LINE.items():
                if station in clean_station or clean_station in station:
                    line_number = line
                    break
            
            if line_number:
                bg_color = LINE_TO_COLOR.get(line_number, "#dadce0")
                
                if line_number == 14:  # MCC line
                    text_color = "#000000"
                    station_display = clean_station
                    tag_style = f"display:inline-block; padding:1px 4px; border-radius:3px; margin-right:1px; white-space:nowrap; border:1px solid #EF161E;"
                    tags.append(f'<span style="{tag_style} background-color:{bg_color}; color:{text_color};">{station_display}</span>')
                else:
                    text_color = "#ffffff"
                    tags.append(create_tag_span(clean_station, bg_color, text_color))

    return create_flex_container("".join(tags)) if tags else ""