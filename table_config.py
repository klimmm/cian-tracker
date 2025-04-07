import pandas as pd
import os
from datetime import datetime

display_columns = [
    "offer_id",
    "title",
    "updated_time",
    "updated_time_sort",
    "price",
    "price_sort",
    "cian_estimation",
    "cian_estimation_sort",
    "price_difference",
    "price_difference_sort",
    "address",
    "metro_station",
    "offer_link",
    "distance",
    "price_change_value",
    "price_change_formatted",
]
visible_columns = [
    "title",
    "updated_time",
    "price_change_formatted",
    #"price_change",
    "price",
    "cian_estimation",
    # "price_difference",
    "distance",
    "address",
    "metro_station",
    "offer_link",
]
 



# Function to load data
def load_data():
    csv = "cian_apartments.csv"

    try:
        # Load data from URL
        df = pd.read_csv(csv, encoding="utf-8", comment="#")
        
        with open("cian_apartments.csv", "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        
        update_time = "Unknown"
        metadata_parts = first_line.replace("# ", "").split(",")
        for part in metadata_parts:
            if part.startswith("last_updated="):
                update_time = part.split("=")[1].strip()
        
        # Rest of your processing code...
        if "offer_id" in df.columns:
            df["offer_id"] = df["offer_id"].astype(str)

        # In load_data function
        if "distance" in df.columns:
            # Convert to numeric first
            df["distance_sort"] = pd.to_numeric(df["distance"], errors="coerce")

            # Format with exactly 2 decimal places and add km unit
            df["distance"] = df["distance_sort"].apply(
                lambda x: f"{x:.2f} km" if pd.notnull(x) else ""
            )
        if "price_change_value" in df.columns:
            df["price_change_sort"] = pd.to_numeric(df["price_change_value"], errors="coerce")
            
            def format_price_change(value):
                if pd.isna(value):
                    return "—"
                try:
                    value = float(value)
                    if value < 0:
                        return f"↓ {abs(value):,.0f} ₽/мес."  # Unicode arrow
                    elif value > 0:
                        return f"↑ {value:,.0f} ₽/мес."
                    else:
                        return "—"
                except Exception as e:
                    print("Formatting error:", e)
                    return "—"

            
            df["price_change_formatted"] = df["price_change_sort"].apply(format_price_change)

        
        # Define Russian month mapping
        months = {
            1: "янв",
            2: "фев",
            3: "мар",
            4: "апр",
            5: "май",
            6: "июн",
            7: "июл",
            8: "авг",
            9: "сен",
            10: "окт",
            11: "ноя",
            12: "дек",
        }

        # Process price columns (extraction from {XX XXX ₽/мес.} format)
        for col in ["price", "cian_estimation", "price_difference"]:
            if col in df.columns:

                df[f"{col}_sort"] = (
                    df[col].astype(str).str.extract(r"(\d+[\s\d]*)", expand=False)
                )
                df[f"{col}_sort"] = (
                    df[f"{col}_sort"]
                    .str.replace(" ", "")
                    .astype(float, errors="ignore")
                )

        # Convert updated_time to datetime for sorting
        if "updated_time" in df.columns:
            # Save sortable datetime value
            df["updated_time_sort"] = pd.to_datetime(
                df["updated_time"], errors="coerce"
            )
            df = df.sort_values("updated_time_sort", ascending=False)

            # Format dates in Russian format: "5 апр, 16:19"
            df["updated_time"] = df["updated_time_sort"].apply(
                lambda x: (
                    f"{x.day} {months[x.month]}, {x.hour:02d}:{x.minute:02d}"
                    if pd.notnull(x)
                    else ""
                )
            )

        if "days_active" in df.columns:
            df["days_active"] = pd.to_numeric(
                df["days_active"].fillna(0), errors="coerce"
            ).astype(int)

        # Link to the offer
        if "offer_url" in df.columns and "offer_id" in df.columns:
            df["offer_link"] = df.apply(
                lambda row: f"[View](https://www.cian.ru/rent/flat/{row['offer_id']}/)",
                axis=1,
            )

        return df, update_time
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame(), f"Error: {e}"
# Define the column configurations and sorting functions
def get_table_config():
    """
    Function to define the DataTable columns, data, and sorting configurations.
    Returns a tuple containing (columns, data, display_columns, sort_map)
    """
    # Define visible and display columns

    df, _ = load_data()
    # Filter columns that exist in the DataFrame
    display_cols = [col for col in display_columns if col in df.columns]
    visible_cols = [col for col in visible_columns if col in df.columns]

    # Define column configurations
    columns = []
    for col in visible_cols:
        if col == "offer_id":
            columns.append({"name": "ID", "id": "offer_id", "type": "text"})
        elif col == "distance":
            columns.append({"name": "расст.", "id": "distance", "type": "numeric"})
        elif col == "price_change_formatted":
            columns.append(
                {
                    "name": "изм.цены",
                    "id": "price_change_formatted",
                    "type": "text",  # ✅ Must be text to show emoji
                }
            )

        elif col == "title":
            columns.append({"name": "квартира", "id": "title", "type": "text"})
        elif col == "updated_time":
            columns.append({"name": "обновлено", "id": "updated_time", "type": "text"})
        elif col == "days_active":
            columns.append({"name": "Days", "id": "days_active", "type": "numeric"})
        elif col == "price":
            columns.append({"name": "цена", "id": "price", "type": "numeric"})
        elif col == "cian_estimation":
            columns.append(
                {"name": "оценка ЦИАН", "id": "cian_estimation", "type": "numeric"}
            )
        elif col == "price_difference":
            columns.append(
                {"name": "разн.", "id": "price_difference", "type": "numeric"}
            )
        elif col == "address":
            columns.append(
                {
                    "name": "адрес",
                    "id": "address",
                    "type": "text",
                    # Add presentation property for the address column
                    "presentation": "markdown",
                }
            )

        elif col == "metro_station":
            columns.append({"name": "метро", "id": "metro_station", "type": "text"})
        elif col == "offer_link":
            columns.append(
                {
                    "name": "Link",
                    "id": "offer_link",
                    "presentation": "markdown",
                    "type": "text",
                }
            )
        else:
            columns.append({"name": col, "id": col, "type": "text"})

    # Define the mapping for sorting
    sort_map = {
        "updated_time": "updated_time_sort",
        "price": "price_sort",
        "cian_estimation": "cian_estimation_sort",
        "price_difference": "price_difference_sort",
    }

    # Create the data dictionary for the table
    data = df[display_cols].to_dict("records")

    hidden_columns = [col for col in display_cols if col.endswith("_sort")]

    return columns, data, display_cols, sort_map, hidden_columns


def sort_table_data(sort_by):
    """
    Function to sort the table data based on sort_by parameters
    Returns the sorted dataframe as records
    """
    df, _ = load_data()
    display_cols = [col for col in display_columns if col in df.columns]

    if not sort_by or df.empty:
        # Default sorting - by updated time, descending
        if "updated_time_sort" in df.columns:
            df = df.sort_values("updated_time_sort", ascending=False)
        return df[display_cols].to_dict("records")

    # Map visible columns to their sorting counterparts
    sort_map = {
        "updated_time": "updated_time_sort",
        "price": "price_sort",
        "cian_estimation": "cian_estimation_sort",
        "price_difference": "price_difference_sort",
    }

    # Apply sorting based on sort_by parameter
    for sort_item in sort_by:
        col_id = sort_item["column_id"]
        ascending = sort_item["direction"] == "asc"

        # Use the mapping for special columns
        if col_id in sort_map:
            sort_col = sort_map[col_id]
        else:
            sort_col = col_id

        df = df.sort_values(sort_col, ascending=ascending)

    return df[display_cols].to_dict("records")