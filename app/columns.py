# app/columns.py
import pandas as pd
import logging
from app.pill_factory import PillFactory

logger = logging.getLogger(__name__)


class ColumnFormatter:
    """Centralized column formatting for consistent display using PillFactory."""

    @staticmethod
    def format_price_column(row):
        """Format price column with consistent pills."""
        pills = []

        # Get status from row
        status = row.get("status", "active")

        price_formatted = row.get("price_value_formatted", "--")

        # Determine if it's a 'good price'
        is_good_price = (
            row.get("price_difference_value", 0) > 0 and status != "non active"
        )

        if price_formatted and price_formatted != "--":
            # Use centralized PillFactory logic for styling
            pills.append(
                PillFactory.create_price_pill(
                    price_formatted, is_good_price=is_good_price, status=status
                )
            )


        # Price change pill
        price_change = row.get("price_change_value", 0)
        if price_change:
            pills.append(
                PillFactory.create_price_change_pill(price_change, status=status)
            )


        
        return PillFactory.create_pill_container(
            pills,
            wrap=False,  # disable flex-wrap so it stays columnar
            align="flex-start",
            custom_style={
                "flexDirection": "column",
                "gap": "4px",         # adjust vertical spacing as you like
            },
            return_as_html=True,
            status=status,
        )

    @staticmethod
    def format_update_title(row):
        """Format update title column with activity date if available."""
        pills = []

        # Get status from row
        status = row.get("status", "active")

        # Time string as a pill
        time_str = row.get("updated_time_display", "--")
        if time_str and time_str != "--":
            pills.append(PillFactory.create_time_pill(time_str, status=status))


        # Activity date formatting
        should_add_activity_date = "activity_date_display" in row and pd.notnull(
            row["activity_date_display"]
        )

        # Skip if same as updated time
        if (
            should_add_activity_date
            and pd.notnull(row.get("updated_time_sort"))
            and pd.notnull(row.get("activity_date_sort"))
        ):
            time_diff = abs(
                (row["activity_date_sort"] - row["updated_time_sort"]).total_seconds()
            )
            if time_diff < 60:
                should_add_activity_date = False

        if should_add_activity_date:
            activity_date = row["activity_date_display"]
            pills.append(
                PillFactory.create_activity_date_pill(activity_date, status=status)
            )

        return PillFactory.create_pill_container(
            pills,
            wrap=False,  # disable flex-wrap so it stays columnar
            align="flex-start",
            custom_style={
                "flexDirection": "column",
                "gap": "4px",         # adjust vertical spacing as you like
            },
            return_as_html=True,
            status=status,
        )
        
    @staticmethod
    def format_combined_price_update(row):
        """Format combined price and update column for small displays.
        Shows price on first line (using create_price_pill),
        price change on second line, updated time on third line,
        and activity date on fourth line.
        """
        status = row.get("status", "active")
        
        # Create container div with class for styling
        html = f'<div class="combined-column-container {status}">'
        
        # Line 1: Price value with special styling
        line1_parts = []
        price_formatted = row.get("price_value_formatted", "--")
        is_good_price = (
            row.get("price_difference_value", 0) > 0 and status != "non active"
        )
        
        if price_formatted and price_formatted != "--":
            line1_parts.append(
                PillFactory.create_price_pill(
                    price_formatted, is_good_price=is_good_price, status=status
                )
            )
        
        if line1_parts:
            # Create price container with a special data attribute we can target in CSS
            line1_html = PillFactory.create_pill_container(
                line1_parts,
                wrap=False,
                align="flex-start",
                custom_style={"flexDirection": "row"},
                return_as_html=True,
                status=status,
            )
            # Add data attribute to help with CSS targeting
            line1_html = line1_html.replace('<div class="pill-container', '<div data-price-line="true" class="pill-container')
            html += line1_html
        
        # Line 2: Price change
        line2_parts = []
        price_change = row.get("price_change_value", 0)
        if price_change:
            line2_parts.append(
                PillFactory.create_price_change_pill(price_change, status=status)
            )
        
        if line2_parts:
            line2_html = PillFactory.create_pill_container(
                line2_parts,
                wrap=False,
                align="flex-start",
                custom_style={"flexDirection": "row"},
                return_as_html=True,
                status=status,
            )
            html += line2_html
        
        # Line 3: Updated time
        line3_parts = []
        time_str = row.get("updated_time_display", "--")
        if time_str and time_str != "--":
            line3_parts.append(PillFactory.create_time_pill(time_str, status=status))
        
        if line3_parts:
            line3_html = PillFactory.create_pill_container(
                line3_parts,
                wrap=False,
                align="flex-start",
                custom_style={"flexDirection": "row"},
                return_as_html=True,
                status=status,
            )
            html += line3_html
        
        # Line 4: Activity date
        line4_parts = []
        should_add_activity_date = "activity_date_display" in row and pd.notnull(
            row["activity_date_display"]
        )
        
        # Skip if same as updated time (using the same logic as in format_update_title)
        if (
            should_add_activity_date
            and pd.notnull(row.get("updated_time_sort"))
            and pd.notnull(row.get("activity_date_sort"))
        ):
            time_diff = abs(
                (row["activity_date_sort"] - row["updated_time_sort"]).total_seconds()
            )
            if time_diff < 60:
                should_add_activity_date = False
        
        if should_add_activity_date:
            activity_date = row["activity_date_display"]
            line4_parts.append(
                PillFactory.create_activity_date_pill(activity_date, status=status)
            )
        
        if line4_parts:
            line4_html = PillFactory.create_pill_container(
                line4_parts,
                wrap=False,
                align="flex-start",
                custom_style={"flexDirection": "row"},
                return_as_html=True,
                status=status,
            )
            html += line4_html
        
        html += '</div>'
        return html

    @staticmethod
    def format_property_tags(row):
        """Format property pills column consistently."""
        pills = []
        status = row.get("status", "active")

        # room count
        room_count = row.get("room_count")
        if pd.notnull(room_count):
            pill = PillFactory.create_room_pill(room_count, status=status)
            if pill:
                pills.append(pill)

        # area
        area = row.get("area")
        if pd.notnull(area):
            pill = PillFactory.create_area_pill(area, status=status)
            if pill:
                pills.append(pill)

        # floor
        floor = row.get("floor")
        total_floors = row.get("total_floors")
        if pd.notnull(floor) and pd.notnull(total_floors):
            pill = PillFactory.create_floor_pill(floor, total_floors, status=status)
            if pill:
                pills.append(pill)

        return PillFactory.create_pill_container(
            pills, wrap=True, return_as_html=True, status=status
        )

    def format_address_title(row, base_url):
        """Format address with distance, neighborhood, metro, property and extra info pills."""
        status = row.get("status", "active")

        # --- existing address‐related pills ---
        address_related = []
        distance_value = row.get("distance_sort")
        if pd.notnull(distance_value):
            address_related.append(
                PillFactory.create_walking_time_pill(distance_value, status=status)
            )

        neighborhood = str(row.get("neighborhood", ""))
        if neighborhood and neighborhood.lower() not in ("nan", "none"):
            address_related.append(
                PillFactory.create_neighborhood_pill(neighborhood, status=status)
            )

        address_pills_html = (
            PillFactory.create_pill_container(
                address_related, wrap=True, return_as_html=True, status=status
            )
            if address_related
            else ""
        )

        # --- existing property pills (rooms, area, floor, etc.) ---
        property_pills_html = ColumnFormatter.format_property_tags(row)

        # --- NEW: apartment specifics & amenities pills ---
        info_pills = []

        # Ceiling height
        '''ceiling = row.get("ceiling_height")
        if pd.notnull(ceiling) and ceiling not in ("nan", ""):
            info_pills.append(
                PillFactory.create_pill(f"Потолки: {ceiling}", status=status)
            )

        # View
        view = row.get("view")
        if pd.notnull(view) and view not in ("nan", ""):
            info_pills.append(
                PillFactory.create_pill(f"Вид: {view}", status=status)
            )

        # Amenities: only if explicitly True
        if row.get("features_has_air_conditioner") is True:
            info_pills.append(
                PillFactory.create_amenity_pill("Кондиционер", status=status)
            )
        if row.get("features_has_bathtub") is True:
            info_pills.append(
                PillFactory.create_amenity_pill("Ванна", status=status)
            )
        if row.get("features_has_shower_cabin") is True:
            info_pills.append(
                PillFactory.create_amenity_pill("Душевая кабина", status=status)
            )'''

        info_pills_html = (
            PillFactory.create_pill_container(
                info_pills, wrap=True, return_as_html=True, status=status
            )
            if info_pills
            else ""
        )

        # --- build the address link ---
        address = row.get("address", "")
        offer_id = row.get("offer_id", "")
        address_html = (
            f'<div class="pill pill--default address-pill">'
            f'<a href="{base_url}{offer_id}/" class="address-link">{address}</a>'
            f'</div>'
        )

        # --- stitch all parts together ---
        # Order: link → property pills → info pills → address‐related pills
        parts = [
            address_html,
            property_pills_html,
            info_pills_html,
            address_pills_html,
        ]
        # Filter out empty strings and join
        return " ".join(p for p in parts if p)


    
    @staticmethod
    def format_distance(distance_value):
        """Format distance value for display."""
        return f"{distance_value:.2f} km" if pd.notnull(distance_value) else ""
    
    @staticmethod
    def format_active_time(days_value, hours_value):
        """Format active time for display (days or hours)."""
        # Show hours for recent listings (less than a day old)
        if pd.notnull(days_value) and days_value == 0 and pd.notnull(hours_value):
            return f"{int(hours_value)} ч."
            
        # Show days for older listings
        if pd.notnull(days_value) and days_value >= 0:
            return f"{int(days_value)} дн."
            
        # Default case
        return "--"
        
    
    @staticmethod
    def format_condition_text_column(row):
        status = row.get("status", "active")
        pills = []
        
        # Define pill configurations as data structures
        pill_configs = {
            "features": {
                "features_has_air_conditioner": {"text": "❄️ Кондиционер", "variant": "primary"},
                "features_has_bathtub": {"text": "🛁 Ванна", "variant": "primary"},
                "features_has_shower_cabin": {"text": "🚿 Душевая кабина", "variant": "neutral"}
            },
            "view": {
                "Во двор": {"text": "🏡 Окна во двор", "variant": "primary"},
                "На улицу": {"text": "🌇 Окна на улицу", "variant": "error"},
                "На улицу и двор": {"text": "🏘️ Окна на улицу и двор", "variant": "warning"}
            },
            "renovation": {
                "Косметический": {"text": "🎨 Косметический ремонт", "variant": "warning"},
                "Евроремонт": {"text": "🛠️ Евроремонт", "variant": "success"},
                "Дизайнерский": {"text": "🖼️ Дизайнерский ремонт", "variant": "primary"},
                "Без ремонта": {"text": "🚧 Без ремонта", "variant": "error"}
            },

            "ceiling_height": {
                "ranges": [
                    {"max": 2.5, "variant": "error"},
                    {"max": 2.7, "variant": "neutral"},
                    {"max": 3.0, "variant": "success"},
                    {"max": float('inf'), "variant": "primary"}
                ]
            }
        }
        
        # 1) Process boolean features
        for feature, config in pill_configs["features"].items():
            if row.get(feature) is True:
                pills.append(
                    PillFactory.create_pill(
                        config["text"],
                        variant=config["variant"],
                        custom_class="pill--condition",
                        status=status
                    )
                )
        
        # 2) Process view
        view = row.get("view")
        if pd.notnull(view) and view in pill_configs["view"]:
            config = pill_configs["view"][view]
            pills.append(
                PillFactory.create_pill(
                    config["text"],
                    variant=config["variant"],
                    custom_class="pill--condition",
                    status=status
                )
            )
        
        # 3) Process ceiling height
        ch = row.get("ceiling_height")
        if pd.notnull(ch):
            try:
                num = float(ch.replace("м", "").replace(",", ".").strip())
                for range_config in pill_configs["ceiling_height"]["ranges"]:
                    if num <= range_config["max"]:
                        pills.append(
                            PillFactory.create_pill(
                                f"📏 Потолки: {ch}",
                                variant=range_config["variant"],
                                custom_class="pill--condition",
                                status=status
                            )
                        )
                        break
            except (ValueError, TypeError):
                pass

        renovation = row.get("renovation")
        if pd.notnull(renovation) and renovation in pill_configs["renovation"]:
            config = pill_configs["renovation"][renovation]
            pills.append(
                PillFactory.create_pill(
                    config["text"],
                    variant=config["variant"],
                    custom_class="pill--condition",
                    status=status
                )
            )




        
        if not pills:
            return ""
            
        return PillFactory.create_pill_container(
            pills,
            wrap=True,
            return_as_html=True,
            status=status
        )

    @staticmethod
    def apply_display_formatting(df, base_url):
        """Apply display formatting to dataframe columns."""

        # AFTER everything else, add our new column:



        # Format address_title column
        df["address_title"] = df.apply(
            lambda r: ColumnFormatter.format_address_title(r, base_url), axis=1
        )
        
        # Create combined display columns
        if all(
            col in df.columns for col in ["price_value_formatted", "price_change_value"]
        ):
            df["price_text"] = df.apply(ColumnFormatter.format_price_column, axis=1)

        df["property_tags"] = df.apply(ColumnFormatter.format_property_tags, axis=1)

        if "price_change_formatted" in df.columns:
            df["price_change"] = df["price_change_formatted"]

        df["update_title"] = df.apply(ColumnFormatter.format_update_title, axis=1)
        df["condition_summary"] = df.apply(
            ColumnFormatter.format_condition_text_column, axis=1
        )  

        df['price_update_combined'] = df.apply(ColumnFormatter.format_combined_price_update, axis=1)

        logger.info(f"DataFrame columns: {df.columns.tolist()}")
        
        return df