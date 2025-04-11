# config.py
from zoneinfo import ZoneInfo
import pandas as pd

# Timezone configuration
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

# Column definitions and display settings
CONFIG = {
    "columns": {
        "display": [
            "offer_id",
            "title",
            'description',
            "updated_time",
            "updated_time_sort",
            "price_value_formatted",
            "price_value",
            "cian_estimation_formatted",
            "price_difference_formatted",
            "address",
            "metro_station",
            "neighborhood",
            "offer_link",
            "distance",
            "distance_sort",
            "price_change_formatted",
            "status",
            "unpublished_date",
            "unpublished_date_sort",
            "price_difference_value",
            "rental_period_abbr",
            "utilities_type_abbr",
            "commission_info_abbr",
            "deposit_info_abbr",
            "monthly_burden",
            "monthly_burden_formatted",
            "address_title",
            "price_info",
            "update_title",
            "price_text",
            "property_tags",
            'price_change'
            #"tags"  # Add the new tags column
            
            
        ],
        "visible": [
            #"address",
            #"updated_time",
            "update_title",
            "address_title",  # Add the combined column
            #"distance",
            #"price_info",
            #"price_value_formatted",
            "price_text",
            "property_tags",
            #"neighborhood",
            #"commission_info_abbr",
            #"deposit_info_abbr",
            #"monthly_burden_formatted",
            #"cian_estimation_formatted"
            #"price_change_formatted",
            #"title",
            # "rental_period_abbr", "utilities_type_abbr",
            #"metro_station",
            #"unpublished_date",
            #"tags"
            #'price_change'
        ],
        "headers": {
            "offer_id": "ID",
            "distance": "Расст.",
            "price_change_formatted": "Изм.",
            "title": "Описание",
            "updated_time": "Обновлено",
            "price_value_formatted": "Цена",
            "cian_estimation_formatted": "Оценка",
            "price_difference_formatted": "Разница",
            "address": "Адрес",
            "metro_station": "Метро",
            "offer_link": "Ссылка",
            "status": "Статус",
            "unpublished_date": "Снято",
            "rental_period_abbr": "Срок",
            "utilities_type_abbr": "ЖКХ",
            "commission_info_abbr": "Коммис",
            "deposit_info_abbr": "Залог",
            "monthly_burden_formatted": "Нагрузка/мес",
            "address_title": "Квартира",
            "price_info": "Цена",
            "update_title": "Посл. обновление",
            "neighborhood": "Район",
            "price_text": "Цена",
            "property_tags": "Пешком"  # Add header for tags
            
        },
        "sort_map": {
            "updated_time": "date_sort_combined",
            "price_value_formatted": "price_value",
            'price_text': 'price_value',
            "property_tags": "distance_sort",
            "price_change_formatted": "price_change_value",
            "cian_estimation_formatted": "cian_estimation_value",
            "price_difference_formatted": "price_difference_value",
            "distance": "distance_sort",
            "monthly_burden_formatted": "monthly_burden",
        },
    },
    "months": {
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
    },
    "base_url": "https://www.cian.ru/rent/flat/",
    "hidden_cols": [
        "price_value",
        "distance_sort",
        "updated_time_sort",
        "cian_estimation_value",
        "price_difference_value",
        "unpublished_date_sort",
        "monthly_burden",
    ],
}

# Style definitions
FONT = "Arial,sans-serif"
STYLE = {
    "container": {"fontFamily": FONT, "padding": "5px", "maxWidth": "100%"},
    "header": {
        "fontFamily": FONT,
        "textAlign": "center",
        "fontSize": "8px",
        "borderBottom": "1px solid #ddd",
    },
    "update_time": {"fontFamily": FONT, "fontStyle": "bold", "fontSize": "12px"},
    "table": {"overflowX": "auto", "width": "auto"},
    "cell": {
        "fontFamily": FONT,
        "textAlign": "center",
        "padding": "3px",
        "maxWidth": "auto",
        "fontSize": "8px",
        "whiteSpace": "nowrap",
    },
    "header_cell": {
        "fontFamily": FONT,
        "backgroundColor": "#4682B4",
        "color": "white",
        "fontSize": "9.5px",
    },



    
    "filter": {"display": "none"},
    "data": {"lineHeight": "14px"},
    "input": {"marginRight": "5px", "width": "110px", "height": "15px"},
    "input_number": {"width": "110px", "height": "15px"},
    "label": {"fontSize": "11px", "marginRight": "3px", "display": "block"},
    "button_base": {
        "display": "inline-block",
        "padding": "3px 8px",
        "fontSize": "10px",
        "border": "1px solid #ccc",
        "margin": "0 5px 5px 0",
        "cursor": "pointer",
    },
    "cell_conditional": [
        
        {"if": {"column_id": "update_title"}, 
         "whiteSpace": "normal", 
         "height": "auto",
         "minHeight": "60px",
         "width": "75px",
         "maxWidth": "85px",  # Uncomment and set this value
         "overflow": "visible",
         "padding": "3px 4px",
         "lineHeight": "1.2"},
        {"if": {"column_id": "details"}, 
         "whiteSpace": "normal", 
         "height": "auto",
         "minHeight": "60px",
         "width": "75px",
         "maxWidth": "85px",  # Uncomment and set this value
         "overflow": "visible",
         "padding": "3px 4px",
         "lineHeight": "1.2"},

        
        {"if": {"column_id": "address_title"}, 
         "whiteSpace": "normal", 
         "height": "auto",
         #"width": "120px",
         #"maxWidth": "120px",
         "overflow": "hidden",
         "textOverflow": "ellipsis"},

        {"if": {"column_id": "tags"}, 
         "whiteSpace": "normal", 
         "height": "auto",
         "width": "120px", 
         "overflow": "visible",
         "textOverflow": "clip"},
        {"if": {"column_id": "details_button"}, "maxWidth": "80px", "textAlign": "center"}
    ]
}
# Button styles
BUTTON_STYLES = {
    "nearest": {"backgroundColor": "#d9edf7", **STYLE["button_base"]},
    "below_estimate": {"backgroundColor": "#fef3d5", **STYLE["button_base"]},
    "updated_today": {"backgroundColor": "#dff0d8", **STYLE["button_base"]},
    "inactive": {"backgroundColor": "#f4f4f4", **STYLE["button_base"]},  # Keep the key the same for compatibility
    "price": {"backgroundColor": "#e8e8e0", **STYLE["button_base"]},
    "distance": {"backgroundColor": "#e0e4e8", **STYLE["button_base"]},
}
# In config.py, update the styling for the update_title column:

# Find in COLUMN_STYLES:

# Update to:


# In config.py, update the COLUMN_STYLES list:

# In config.py, update the COLUMN_STYLES list:

# In config.py, update the COLUMN_STYLES list:

# In config.py, update the COLUMN_STYLES list to restore non-active background:

COLUMN_STYLES = [
    # Keep some background color conditions
    # {
    #     "if": {
    #         "filter_query": '{price_difference_value} > 0 && {status} ne "non active"'
    #     },
    #     "backgroundColor": "#fef3d5",
    # },
    # {
    #     "if": {
    #         "filter_query": '{updated_time_sort} > "'
    #         + (pd.Timestamp.now() - pd.Timedelta(hours=24)).isoformat()
    #         + '"'
    #     },
    #     "backgroundColor": "#e6f3e0",
    #     "fontWeight": "normal",
    # },
    # {
    #     "if": {"filter_query": '{distance_sort} < 1.5 && {status} ne "non active"'},
    #     "backgroundColor": "#d9edf7",
    # },
    
    # Restore background color for non-active listings
    {
        "if": {"filter_query": '{status} contains "non active"'},
        "backgroundColor": "#f4f4f4",
        "color": "#888",
    },
    
    # Keep specific column styles
    {"if": {"column_id": "tags"}, "textAlign": "left", "whiteSpace": "normal"},
    {"if": {"column_id": "price_change_formatted"}, "textAlign": "center"},
    {
        "if": {"column_id": "price_text"},
        "textAlign": "center",
        "padding": "0 4px",
        "whiteSpace": "normal",  # allow line breaks
        "lineHeight": "1.2"
    },
    {
        "if": {"column_id": "update_title"},
        "textAlign": "center",
        "whiteSpace": "normal",
        "padding": "2px 4px",
        "lineHeight": "1.2"
    },

    
    {"if": {"column_id": "updated_time"}, "fontWeight": "bold", "textAlign": "center"},
    {
        "if": {"column_id": "price_value_formatted"},
        "fontWeight": "bold",
        "textAlign": "center",
        #"maxWidth": "60px"
    },
    {
        "if": {"column_id": "update_title"},
        "textAlign": "center",
        "whiteSpace": "normal",
        "padding": "2px 4px",
        "lineHeight": "1.2",
        "height": "auto",
        "minHeight": "60px",
    },
    {
        "if": {"column_id": "property_tags"},
        "padding": "1px", 
        "textAlign": "left",
        "lineHeight": "1.2"
    },    
        
    {
        "if": {"column_id": "monthly_burden_formatted"},
        "fontWeight": "bold",
        "textAlign": "center",
    },
    {"if": {"column_id": "address"}, "textAlign": "left"},
    {"if": {"column_id": "distance"}, "maxWidth": "40px"},
    {"if": {"column_id": "metro_station"}, "textAlign": "left"},
    #{"if": {"column_id": "address_title"}, "maxWidth": "140px"},
    #{"if": {"column_id": "update_title"}, "maxWidth": "75px", "whiteSpace": "normal", "height": "auto", "minHeight": "65px"},
    {"if": {"column_id": "title"}, "textAlign": "left"},
    
    # Keep other styling
    {
        "if": {"column_id": "address_title"}, 
        "textAlign": "left",
        "whiteSpace": "normal", 
        "height": "auto"
    },
    {"if": {"column_id": "details_button"}, "textAlign": "center", "maxWidth": "60px"}
]

HEADER_STYLES = [
    {"if": {"column_id": col}, "textAlign": "center"}
    for col in [
        "distance",
        "updated_time",
        "unpublished_date",
        "price_value_formatted",
        "cian_estimation_formatted",
        "price_change_formatted",
        "price_text",

        "status",
        "monthly_burden_formatted",
    ]
] + [{"if": {"column_id": col}, "textAlign": "left"} for col in ["address_title", "metro_station"]]



# First, define button configurations in config.py
PRICE_BUTTONS = [
    {"id": "btn-price-60k", "label": "65K", "value": 65000},
    {"id": "btn-price-70k", "label": "75K", "value": 75000},
    {"id": "btn-price-80k", "label": "85K", "value": 85000, "default": True},
    {"id": "btn-price-90k-plus", "label": "любая", "value": float('inf')}
]

DISTANCE_BUTTONS = [
    #{"id": "btn-dist-1km", "label": "1km", "value": 1.0},
    {"id": "btn-dist-2km", "label": "2", "value": 2.0},
    {"id": "btn-dist-3km", "label": "3", "value": 3.0, "default": True},
    #{"id": "btn-dist-4km", "label": "4km", "value": 4.0},
    {"id": "btn-dist-5km", "label": "5", "value": 5.0},
    {"id": "btn-dist-5km-plus", "label": "любое", "value": float('inf')}
]
# Add this to config.py alongside the existing button definitions
# Modify the SORT_BUTTONS definition in config.py
SORT_BUTTONS = [
    {"id": "btn-sort-price", "label": "По цене", "value": "price_value", "default_direction": "asc"},
    {"id": "btn-sort-time", "label": "По дате", "value": "updated_time_sort", "default_direction": "desc"},
    {"id": "btn-sort-distance", "label": "По расстоянию", "value": "distance_sort", "default": True, "default_direction": "asc"},  # Make this the default
]
# Add a style for sort buttons
BUTTON_STYLES["sort"] = {"backgroundColor": "#e0e0e8", **STYLE["button_base"]}