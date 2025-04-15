# app/button_factory.py
import logging
from dash import html

logger = logging.getLogger(__name__)
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
        "label": "Акт.",
        "value": "activity_date_sort",
        "default_direction": "desc",
    },
    {
        "id": "btn-sort-distance",
        "label": "Расст.",
        "value": "distance_sort",
        "default": True,
        "default_direction": "asc",
    },
]

# Default configuration values
DEFAULT_PRICE = next(
    (btn["value"] for btn in PRICE_BUTTONS if btn.get("default", False)), 80000
)
DEFAULT_PRICE_BTN = next(
    (btn["id"] for btn in PRICE_BUTTONS if btn.get("default", False)), "btn-price-80k"
)
DEFAULT_DISTANCE = next(
    (btn["value"] for btn in DISTANCE_BUTTONS if btn.get("default", False)), 3.0
)
DEFAULT_DISTANCE_BTN = next(
    (btn["id"] for btn in DISTANCE_BUTTONS if btn.get("default", False)), "btn-dist-3km"
)


class ButtonFactory:
    """Factory for creating consistent button components"""

    @classmethod
    def create_button(
        cls,
        label,
        button_id,
        variant="default",
        size="md",
        is_active=False,
        icon=None,
        custom_style=None,
        **kwargs,
    ):
        """Create a button with consistent styling"""
        # Build class name based on variant, size, and state
        class_name = f"btn btn--{variant} btn--{size}"

        if is_active:
            class_name += " btn--active"

        # Allow passing custom style
        dynamic_style = custom_style if custom_style else {}

        # Create the button content with optional icon
        if icon:
            content = html.Div(
                [
                    html.I(className=icon, style={"marginRight": "0.5rem"}),
                    html.Span(label, id=f"{button_id}-text" if label else None),
                ],
                className="flex-container flex-container--align-center flex-container--gap-xs",
            )
        else:
            content = html.Span(label, id=f"{button_id}-text" if label else None)

        return html.Button(
            content, id=button_id, style=dynamic_style, className=class_name, **kwargs
        )

    @classmethod
    def create_button_group(
        cls,
        buttons,
        label_text=None,
        active_button_id=None,
        direction="horizontal",
        inline=True,
        label_width=None,
        responsive=True,
    ):
        """Create a group of related buttons with optional inline label and layout."""
        # Build button elements
        button_elements = []
        for btn in buttons:
            is_active = btn.get("default", False) or btn["id"] == active_button_id

            button = cls.create_button(
                label=btn.get("label", ""),
                button_id=btn["id"],
                variant=btn.get("variant", "default"),
                size="md",
                is_active=is_active,
            )
            button_elements.append(button)

        # Wrap buttons in container
        button_container = html.Div(
            button_elements,
            className=f"button-group button-group--{direction}",
            style={"flexGrow": "1"},
        )

        # If no label, return just the button container
        if not label_text:
            return button_container

        # Create label element
        label = html.Label(label_text, className="dash-label")

        # Return combined container with inline styling to ensure alignment
        return html.Div([label, button_container], className="button-group-container")


def create_filter_buttons(inline=True):
    """Create improved quick filter toggle buttons with modern styling."""
    filter_buttons = [
        {"id": "btn-updated-today", "label": "За сутки", "variant": "default"},
        {"id": "btn-nearest", "label": "Рядом", "variant": "default"},
        {"id": "btn-below-estimate", "label": "Ниже оценки", "variant": "default"},
        {"id": "btn-inactive", "label": "Активные", "variant": "default", 'default': True},
    ]

    # Create button group using modernized components
    return ButtonFactory.create_button_group(
        filter_buttons, label_text="Фильтры", direction="horizontal", inline=inline
    )


# Example usage:
price_buttons = ButtonFactory.create_button_group(
    PRICE_BUTTONS, "Макс. цена (₽):", DEFAULT_PRICE_BTN, inline=True, responsive=True
)
distance_buttons = ButtonFactory.create_button_group(
    DISTANCE_BUTTONS,
    "Макс. расстояние (км):",
    DEFAULT_DISTANCE_BTN,
    inline=True,
    responsive=True,
)
sort_buttons = ButtonFactory.create_button_group(
    SORT_BUTTONS, "Сортировать:", "btn-sort-time", inline=True, responsive=True
)
filter_buttons = create_filter_buttons(inline=True)
