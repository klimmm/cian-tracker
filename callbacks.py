# callbacks.py
import dash
from dash.dependencies import Input, Output, State
from dash import callback, html

from config import BUTTON_STYLES, PRICE_BUTTONS, DISTANCE_BUTTONS
from layout import default_price, default_price_btn, default_distance, default_distance_btn

# Base layout styles for buttons that should be preserved
PRICE_BUTTON_LAYOUT = {
    "flex": "1",  # Take full width
    "margin": "0",  # No margin
    "padding": "2px 0",  # Reduced vertical padding
    "fontSize": "10px",  # Smaller font size
    "lineHeight": "1",  # Tighter line height
    "borderRadius": "0",  # No rounded corners
}

DISTANCE_BUTTON_LAYOUT = {
    "flex": "1",  # Take full width
    "margin": "0",  # No margin
    "padding": "2px 0",  # Reduced vertical padding
    "fontSize": "10px",  # Smaller font size
    "lineHeight": "1",  # Tighter line height
    "borderRadius": "0",  # No rounded corners
}

# Callback to handle price button clicks
@callback(
    [Output(btn["id"], "style") for btn in PRICE_BUTTONS]
    + [Output("filter-store", "data", allow_duplicate=True)],
    [Input(btn["id"], "n_clicks") for btn in PRICE_BUTTONS],
    [State("filter-store", "data")],
    prevent_initial_call=True,
)
def update_price_buttons(*args):
    n_buttons = len(PRICE_BUTTONS)
    clicks = args[:n_buttons]
    current_filters = args[n_buttons]

    ctx = dash.callback_context
    if not ctx.triggered:
        # Default button
        button_id = default_price_btn
        price_value = default_price
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        price_value = next(
            (btn["value"] for btn in PRICE_BUTTONS if btn["id"] == button_id),
            default_price,
        )

    # Update the filter store
    current_filters["price_value"] = price_value
    current_filters["active_price_btn"] = button_id

    # Create button styles
    styles = []
    for i, btn in enumerate(PRICE_BUTTONS):
        # Base style with layout preserved
        base_style = {
            **BUTTON_STYLES["price"],
            **PRICE_BUTTON_LAYOUT,
        }
        
        # Add buttongroup-specific styling
        if i > 0:
            base_style["borderLeft"] = "none"
        
        # Add active/inactive styling
        if btn["id"] == button_id:
            base_style.update({
                "opacity": 1.0,
                "boxShadow": "0 0 5px #4682B4",
                "position": "relative",
                "zIndex": "1",
            })
        else:
            base_style.update({
                "opacity": 0.6,
                "position": "relative",
                "zIndex": "0",
            })
            
        styles.append(base_style)

    return *styles, current_filters


# Callback to handle distance button clicks
@callback(
    [Output(btn["id"], "style") for btn in DISTANCE_BUTTONS]
    + [Output("filter-store", "data", allow_duplicate=True)],
    [Input(btn["id"], "n_clicks") for btn in DISTANCE_BUTTONS],
    [State("filter-store", "data")],
    prevent_initial_call=True,
)
def update_distance_buttons(*args):
    n_buttons = len(DISTANCE_BUTTONS)
    clicks = args[:n_buttons]
    current_filters = args[n_buttons]

    ctx = dash.callback_context
    if not ctx.triggered:
        # Default button
        button_id = default_distance_btn
        distance_value = default_distance
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        distance_value = next(
            (btn["value"] for btn in DISTANCE_BUTTONS if btn["id"] == button_id),
            default_distance,
        )

    # Update the filter store
    current_filters["distance_value"] = distance_value
    current_filters["active_dist_btn"] = button_id

    # Create button styles
    styles = []
    for i, btn in enumerate(DISTANCE_BUTTONS):
        # Base style with layout preserved
        base_style = {
            **BUTTON_STYLES["distance"],
            **DISTANCE_BUTTON_LAYOUT,
        }
        
        # Add buttongroup-specific styling
        if i > 0:
            base_style["borderLeft"] = "none"
            
        # Add active/inactive styling
        if btn["id"] == button_id:
            base_style.update({
                "opacity": 1.0,
                "boxShadow": "0 0 5px #4682B4",
                "position": "relative",
                "zIndex": "1",
            })
        else:
            base_style.update({
                "opacity": 0.6,
                "position": "relative",
                "zIndex": "0",
            })
            
        styles.append(base_style)

    return *styles, current_filters


# Callback to handle filter button clicks
@callback(
    [
        Output("btn-nearest", "style"),
        Output("btn-below-estimate", "style"),
        Output("btn-inactive", "style"),
        Output("btn-updated-today", "style"),
        Output("filter-store", "data", allow_duplicate=True),
    ],
    [
        Input("btn-nearest", "n_clicks"),
        Input("btn-below-estimate", "n_clicks"),
        Input("btn-inactive", "n_clicks"),
        Input("btn-updated-today", "n_clicks"),
    ],
    [State("filter-store", "data")],
    prevent_initial_call=True,
)
def update_filters(
    nearest_clicks,
    below_est_clicks,
    inactive_clicks,
    updated_today_clicks,
    current_filters,
):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [
            {**BUTTON_STYLES["nearest"], "opacity": 0.6},
            {**BUTTON_STYLES["below_estimate"], "opacity": 0.6},
            {**BUTTON_STYLES["inactive"], "opacity": 0.6},
            {**BUTTON_STYLES["updated_today"], "opacity": 0.6},
            current_filters,
        ]

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    filter_map = {
        "btn-nearest": "nearest",
        "btn-below-estimate": "below_estimate",
        "btn-inactive": "inactive",
        "btn-updated-today": "updated_today",
    }

    if button_id in filter_map:
        current_filters[filter_map[button_id]] = not current_filters[
            filter_map[button_id]
        ]

    # Create button styles
    styles = []
    for key in ["nearest", "below_estimate", "inactive", "updated_today"]:
        filter_style = {**BUTTON_STYLES[key], "flex": "1"}  # Add flex for full width
        
        if current_filters[key]:
            filter_style.update({"opacity": 1.0, "boxShadow": "0 0 5px #4682B4"})
        else:
            filter_style.update({"opacity": 0.6})
            
        styles.append(filter_style)

    return *styles, current_filters


    # Add to callbacks.py

def create_apartment_details_card(apartment_data):
    """Create a card layout with all apartment details"""
    if not apartment_data:
        return html.Div("Нет данных для этой квартиры.")
    
    offer_id = apartment_data.get("offer_id", "ID неизвестен")
    
    # Helper function to create a section 
    def create_section(title, content):
        return html.Div(
            className="details-section",
            style={
                "marginBottom": "15px",
                "border": "1px solid #ddd",
                "borderRadius": "5px",
                "padding": "10px",
                "backgroundColor": "#f9f9f9"
            },
            children=[
                html.H4(title, style={
                    "marginBottom": "8px", 
                    "fontSize": "14px",
                    "color": "#4682B4",
                    "borderBottom": "1px solid #ddd",
                    "paddingBottom": "5px"
                }),
                content
            ]
        )
    
    # Helper function to create a detail item
    def create_detail_item(label, value):
        return html.Div(
            style={"marginBottom": "5px", "display": "flex"},
            children=[
                html.Span(
                    f"{label}: ", 
                    style={"fontWeight": "bold", "marginRight": "5px", "fontSize": "12px", "minWidth": "140px"}
                ),
                html.Span(value, style={"fontSize": "12px"})
            ]
        )
    
    # Create specific sections based on available data
    sections = []
    
    # Basic information section
    basic_info = []
    if "apartment" in apartment_data:
        apt_data = apartment_data["apartment"]
        
        # Add apartment type if available
        if apt_data.get("apartment_type"):
            basic_info.append(create_detail_item(
                "Тип жилья", apt_data.get("apartment_type", "")
            ))
        
        # Add layout if available
        if apt_data.get("layout"):
            basic_info.append(create_detail_item(
                "Планировка", apt_data.get("layout", "")
            ))
        
        # Add areas
        if apt_data.get("total_area"):
            basic_info.append(create_detail_item(
                "Общая площадь", apt_data.get("total_area", "")
            ))
        if apt_data.get("living_area"):
            basic_info.append(create_detail_item(
                "Жилая площадь", apt_data.get("living_area", "")
            ))
        if apt_data.get("kitchen_area"):
            basic_info.append(create_detail_item(
                "Площадь кухни", apt_data.get("kitchen_area", "")
            ))
        
        # Add other apartment details
        if apt_data.get("ceiling_height"):
            basic_info.append(create_detail_item(
                "Высота потолков", apt_data.get("ceiling_height", "")
            ))
        if apt_data.get("bathroom"):
            basic_info.append(create_detail_item(
                "Санузел", apt_data.get("bathroom", "")
            ))
        if apt_data.get("balcony"):
            basic_info.append(create_detail_item(
                "Балкон/лоджия", apt_data.get("balcony", "")
            ))
        if apt_data.get("sleeping_places"):
            basic_info.append(create_detail_item(
                "Спальных мест", apt_data.get("sleeping_places", "")
            ))
        if apt_data.get("renovation"):
            basic_info.append(create_detail_item(
                "Ремонт", apt_data.get("renovation", "")
            ))
        if apt_data.get("view"):
            basic_info.append(create_detail_item(
                "Вид из окон", apt_data.get("view", "")
            ))
        
        if basic_info:
            sections.append(create_section("Основная информация", html.Div(basic_info)))
    
    # Rental terms section
    if "terms" in apartment_data:
        terms_data = apartment_data["terms"]
        terms_info = []
        
        term_mapping = {
            'utilities_payment': 'Оплата ЖКХ',
            'security_deposit': 'Залог',
            'commission': 'Комиссия',
            'prepayment': 'Предоплата',
            'rental_period': 'Срок аренды',
            'living_conditions': 'Условия проживания',
            'negotiable': 'Торг'
        }
        
        for field, label in term_mapping.items():
            if terms_data.get(field):
                terms_info.append(create_detail_item(
                    label, terms_data.get(field, "")
                ))
        
        if terms_info:
            sections.append(create_section("Условия аренды", html.Div(terms_info)))
    
    # Features section (appliances, furniture, etc.)
    if "features" in apartment_data:
        features_data = apartment_data["features"]
        feature_info = []
        
        feature_mapping = {
            'has_refrigerator': 'Холодильник',
            'has_dishwasher': 'Посудомоечная машина',
            'has_washing_machine': 'Стиральная машина',
            'has_air_conditioner': 'Кондиционер',
            'has_tv': 'Телевизор',
            'has_internet': 'Интернет',
            'has_kitchen_furniture': 'Мебель на кухне',
            'has_room_furniture': 'Мебель в комнатах',
            'has_bathtub': 'Ванна',
            'has_shower_cabin': 'Душевая кабина'
        }
        
        # Group features that are present
        present_features = []
        for field, label in feature_mapping.items():
            # Check for either True as a string or True as a boolean
            if str(features_data.get(field)).lower() == "true":
                present_features.append(label)
        
        if present_features:
            feature_info.append(html.Div(
                [
                    html.Span("В квартире есть:", style={"fontWeight": "bold", "fontSize": "12px"}),
                    html.Ul([
                        html.Li(feature, style={"fontSize": "12px"}) 
                        for feature in present_features
                    ], style={"marginTop": "5px"})
                ]
            ))
        
        if feature_info:
            sections.append(create_section("Оснащение", html.Div(feature_info)))
    
    # Building information section
    if "building" in apartment_data:
        building_data = apartment_data["building"]
        building_info = []
        
        building_mapping = {
            'year_built': 'Год постройки',
            'building_series': 'Строительная серия',
            'garbage_chute': 'Мусоропровод',
            'elevators': 'Количество лифтов',
            'building_type': 'Тип дома',
            'ceiling_type': 'Тип перекрытий',
            'parking': 'Парковка',
            'entrances': 'Подъезды',
            'heating': 'Отопление',
            'emergency': 'Аварийность',
            'gas_supply': 'Газоснабжение'
        }
        
        for field, label in building_mapping.items():
            if building_data.get(field):
                building_info.append(create_detail_item(
                    label, building_data.get(field, "")
                ))
        
        if building_info:
            sections.append(create_section("Информация о доме", html.Div(building_info)))
    
    # Price history section
    if "price_history" in apartment_data and apartment_data["price_history"]:
        price_history_data = apartment_data["price_history"]
        
        # Sort price history by date (newest first)
        try:
            from datetime import datetime
            price_history_data = sorted(
                price_history_data, 
                key=lambda x: datetime.strptime(x.get("date_iso", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S"),
                reverse=True
            )
        except:
            # If sorting fails, proceed with original order
            pass
        
        # Create table for price history
        price_history_table = html.Table(
            style={"width": "100%", "borderCollapse": "collapse"},
            children=[
                html.Thead(
                    style={"backgroundColor": "#e8e8e8"},
                    children=[
                        html.Tr([
                            html.Th("Дата", style={"padding": "5px", "fontSize": "12px", "textAlign": "left", "fontWeight": "bold"}),
                            html.Th("Цена", style={"padding": "5px", "fontSize": "12px", "textAlign": "right", "fontWeight": "bold"}),
                            html.Th("Изменение", style={"padding": "5px", "fontSize": "12px", "textAlign": "right", "fontWeight": "bold"})
                        ])
                    ]
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(entry.get("date", ""), style={"padding": "5px", "fontSize": "12px", "borderTop": "1px solid #ddd"}),
                        html.Td(entry.get("price", ""), style={"padding": "5px", "fontSize": "12px", "textAlign": "right", "borderTop": "1px solid #ddd"}),
                        html.Td(entry.get("change", ""), style={"padding": "5px", "fontSize": "12px", "textAlign": "right", "borderTop": "1px solid #ddd"})
                    ]) for entry in price_history_data
                ])
            ]
        )
        
        sections.append(create_section("История цен", price_history_table))
    
    # Statistics section
    if "stats" in apartment_data:
        stats_data = apartment_data["stats"]
        stats_info = []
        
        if stats_data.get("creation_date"):
            stats_info.append(create_detail_item(
                "Дата создания объявления", stats_data.get("creation_date", "")
            ))
        if stats_data.get("total_views"):
            stats_info.append(create_detail_item(
                "Всего просмотров", stats_data.get("total_views", "")
            ))
        if stats_data.get("recent_views"):
            stats_info.append(create_detail_item(
                "Недавние просмотры", stats_data.get("recent_views", "")
            ))
        if stats_data.get("unique_views"):
            stats_info.append(create_detail_item(
                "Уникальные просмотры", stats_data.get("unique_views", "")
            ))
        
        if stats_info:
            sections.append(create_section("Статистика объявления", html.Div(stats_info)))
    
    # Return the complete card
    header = html.Div(
        style={
            "marginBottom": "15px",
            "padding": "10px",
            "backgroundColor": "#4682B4",
            "color": "white",
            "borderRadius": "5px"
        },
        children=[
            html.H3(f"Информация об объявлении №{offer_id}", style={"fontSize": "16px", "margin": "0"})
        ]
    )
    
    return html.Div([header] + sections, style={"maxWidth": "800px", "margin": "0 auto"})