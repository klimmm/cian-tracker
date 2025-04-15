# Modified PillFactory in components.py to remove duplicate styling
import logging
from dash import html

logger = logging.getLogger(__name__)


class ContainerFactory:
    """Factory for creating consistent container components"""

    @classmethod
    def create_section(
        cls, children, title=None, divider=True, spacing="md", custom_style=None
    ):
        """Create a section container with optional title and divider"""
        # Filter out None values
        if isinstance(children, list):
            children = [child for child in children if child is not None]
            if not children:
                return None
        elif children is None:
            return None

        # Build class name
        class_name = f"section section--spacing-{spacing}"
        if divider:
            class_name += " section--divider"

        # Build section elements
        elements = []

        # Add title if provided
        if title:
            elements.append(html.H4(title, className="section-title"))

        # Add children
        if isinstance(children, list):
            elements.extend(children)
        else:
            elements.append(children)

        # Keep only truly dynamic styles, if any
        dynamic_style = {}
        if custom_style:
            dynamic_style = custom_style

        return html.Div(elements, style=dynamic_style, className=class_name)