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
            "address_title": "Адрес",
            "update_title": "Обновлено",
            "neighborhood": "Район",
            "price_text": "Цена",
            "property_tags": "Квартира",
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
}

# Font definition (for reference only)
FONT = "Arial,sans-serif"
# Button styles with classes
BUTTON_STYLES = {
    "nearest": {"className": "dashboard-button"},
    "below_estimate": {"className": "dashboard-button"},
    "updated_today": {"className": "dashboard-button"},
    "inactive": {"className": "dashboard-button"},
    "price": {"className": "dashboard-button"},
    "distance": {"className": "dashboard-button"},
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
