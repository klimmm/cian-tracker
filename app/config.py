# app/config.py
from zoneinfo import ZoneInfo

# Timezone configuration
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

# Column configuration
CONFIG = {
    "columns": {
        "display": [
            "offer_id",
            "title",
            "description",
            "updated_time",
            "updated_time_sort",
            "activity_date",
            "activity_date_sort",
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
            "address_title",
            "update_title",
            "price_text",
            "property_tags",
            "price_change",
            "days_active",
            "days_active_value",
        ],
        "visible": ["update_title", "address_title", "price_text", "property_tags"],
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
            "address_title": "Квартира",
            "update_title": "Обновл.",
            "neighborhood": "Район",
            "price_text": "Цена",
            "property_tags": "Пешком",
            "activity_date": "Посл. активность",
            "days_active": "С обновления",
        },
        "sort_map": {
            "updated_time": "date_sort_combined",
            "update_title": "date_sort_combined",
            "activity_date": "activity_date_sort",
            "activity_date_formatted": "activity_date_sort",
            "price_value_formatted": "price_value",
            "price_text": "price_value",
            "property_tags": "distance_sort",
            "price_change_formatted": "price_change_value",
            "price_change": "price_change_value",
            "cian_estimation_formatted": "cian_estimation_value",
            "price_difference_formatted": "price_difference_value",
            "distance": "distance_sort",
            "days_active": "days_active_value",
            "address_title": "address",
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
    ],
}

# Font definition (for reference only)
FONT = "Arial,sans-serif"
# Button styles with classes
BUTTON_STYLES = {
    "nearest": {"className": "dashboard-button button-nearest"},
    "below_estimate": {"className": "dashboard-button button-below-estimate"},
    "updated_today": {"className": "dashboard-button button-updated-today"},
    "inactive": {"className": "dashboard-button button-inactive"},
    "price": {"className": "dashboard-button button-price"},
    "distance": {"className": "dashboard-button button-distance"},
    "sort": {"className": "dashboard-button button-sort"},
}

# Style definitions - using CSS classes instead of inline styles
STYLE = {
    "container": {"className": "main-container"},
    "header": {"className": "dashboard-header"},
    "update_time": {"className": "update-time"},
    "table": {"className": "apartment-table"},
    "cell": {"className": "dash-cell"},
    "header_cell": {"className": "dash-header-cell"},
    "filter": {"display": "none"},  # keep this one as it's an override
    "input": {"className": "dashboard-input"},
    "input_number": {"className": "dashboard-input dashboard-input-number"},
    "label": {"className": "dashboard-label"},
}


# Only keep conditional styles (data-dependent styling)
COLUMN_STYLES = [
    {
        "if": {"filter_query": '{status} contains "non active"'},
        "backgroundColor": "#f4f4f4",
        "color": "#888",
    },
    # Only kept special conditions that can't be handled with CSS
    {"if": {"column_id": "price_change_formatted"}, "textAlign": "center"},
    {"if": {"column_id": "updated_time"}, "fontWeight": "bold", "textAlign": "center"},
    {"if": {"column_id": "price_value_formatted"}, "fontWeight": "bold", "textAlign": "center"},
]

# Using CSS for header styling instead
HEADER_STYLES = []

# Button definitions
PRICE_BUTTONS = [
    {"id": "btn-price-60k", "label": "65K", "value": 65000},
    {"id": "btn-price-70k", "label": "75K", "value": 75000},
    {"id": "btn-price-80k", "label": "85K", "value": 85000, "default": True},
    {"id": "btn-price-90k-plus", "label": "любая", "value": float("inf")},
]

DISTANCE_BUTTONS = [
    {"id": "btn-dist-2km", "label": "2", "value": 2.0},
    {"id": "btn-dist-3km", "label": "3", "value": 3.0, "default": True},
    {"id": "btn-dist-5km", "label": "5", "value": 5.0},
    {"id": "btn-dist-5km-plus", "label": "любое", "value": float("inf")},
]

SORT_BUTTONS = [
    {
        "id": "btn-sort-price",
        "label": "Цена",
        "value": "price_value",
        "default_direction": "asc",
    },
    {
        "id": "btn-sort-time",
        "label": "Дата",
        "value": "updated_time_sort",
        "default_direction": "desc",
    },
    {
        "id": "btn-sort-activity",
        "label": "Актуальность",
        "value": "activity_date_sort",
        "default_direction": "desc",
    },
    {
        "id": "btn-sort-distance",
        "label": "Расстояние",
        "value": "distance_sort",
        "default": True,
        "default_direction": "asc",
    },
]