# app/apartment_card.py
from dash import html, dcc
import logging
import os
import base64
import requests
from app.app_config import AppConfig
from app.components import ContainerFactory

logger = logging.getLogger(__name__)


class ImageHandler:
    """Efficient apartment image processing with enhanced presentation."""

    @staticmethod
    def get_apartment_images(offer_id):
        """Get images for apartment with optimized fallback strategies."""
        try:
            # Cache for found images
            image_cache = getattr(ImageHandler, "_image_cache", {})
            if offer_id in image_cache:
                return image_cache[offer_id]

            # Try local first in hybrid mode
            if AppConfig.should_use_hybrid_for_images():
                local_images = ImageHandler._get_images_from_local(offer_id)
                if local_images:
                    image_cache[offer_id] = local_images
                    return local_images

                github_images = ImageHandler._get_images_from_github(offer_id)
                if github_images:
                    image_cache[offer_id] = github_images
                    return github_images
                return []

            # Use configured source
            images = (
                ImageHandler._get_images_from_github(offer_id)
                if AppConfig.is_using_github()
                else ImageHandler._get_images_from_local(offer_id)
            )

            # Cache results
            if not hasattr(ImageHandler, "_image_cache"):
                ImageHandler._image_cache = {}
            image_cache[offer_id] = images
            return images
        except Exception as e:
            logger.error(f"Error getting images: {e}")
            return []

    @staticmethod
    def _get_images_from_local(offer_id):
        """Get images from local filesystem efficiently."""
        image_dir = AppConfig.get_images_path(str(offer_id))
        if not os.path.exists(image_dir):
            return []

        # Find and encode jpg files
        image_paths = []
        jpg_files = sorted(
            f for f in os.listdir(image_dir) if f.lower().endswith(".jpg")
        )

        for file in jpg_files:
            try:
                file_path = os.path.join(image_dir, file)
                # Only read if file exists and is not empty
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    with open(file_path, "rb") as image_file:
                        encoded = base64.b64encode(image_file.read()).decode()
                        image_paths.append(f"data:image/jpeg;base64,{encoded}")
            except Exception as e:
                logger.error(f"Error encoding image {file}: {e}")

        return image_paths

    @staticmethod
    def _get_images_from_github(offer_id):
        """Get images from GitHub repository with optimized requests."""
        github_base = AppConfig.DATA_SOURCE["github"]["base_url"]
        image_dir_url = f"{github_base}images/{offer_id}/"
        image_paths = []

        # Check for existence pattern first to reduce request overhead
        try:
            # Try first image to check if directory exists
            first_image_url = f"{image_dir_url}1.jpg"
            response = requests.head(first_image_url)

            if response.status_code != 200:
                return []

            # If first image exists, try the rest
            for i in range(1, 11):
                try:
                    image_url = f"{image_dir_url}{i}.jpg"
                    img_response = requests.get(image_url)
                    if img_response.status_code == 200:
                        encoded = base64.b64encode(img_response.content).decode()
                        image_paths.append(f"data:image/jpeg;base64,{encoded}")
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error fetching GitHub images: {e}")

        return image_paths

    # Update this method in apartment_card.py to remove the loading attribute

    @staticmethod
    def create_slideshow(offer_id):
        """Create responsive slideshow component for images with improved styling."""
        image_paths = ImageHandler.get_apartment_images(offer_id)
        if not image_paths:
            return html.Div(
                [
                    html.Div("No images available", className="no-photo-placeholder"),
                    html.P("Фотографии недоступны"),
                ],
                className="slideshow-container no-photos",
            )

        # Create slideshow with improved responsive design
        return ContainerFactory.create_section(
            [
                # Image container with nav arrows and touch support
                html.Div(
                    [
                        html.Img(
                            id={"type": "slideshow-img", "offer_id": offer_id},
                            src=image_paths[0],
                            className="slideshow-img",
                            # Specifically avoid using loading="lazy" which can cause issues
                        ),
                        html.Button(
                            "❮",
                            id={"type": "prev-btn", "offer_id": offer_id},
                            className="slideshow-nav-btn slideshow-nav-btn--prev",
                            # Add aria-label for accessibility
                            **{"aria-label": "Previous image"},
                        ),
                        html.Button(
                            "❯",
                            id={"type": "next-btn", "offer_id": offer_id},
                            className="slideshow-nav-btn slideshow-nav-btn--next",
                            **{"aria-label": "Next image"},
                        ),
                        html.Div(
                            f"1/{len(image_paths)}",
                            id={"type": "counter", "offer_id": offer_id},
                            className="slideshow-counter",
                        ),
                    ],
                    className="slideshow-container",
                    # Add data attribute for identifying total images
                    **{"data-total": str(len(image_paths))},
                ),
                dcc.Store(
                    id={"type": "slideshow-data", "offer_id": offer_id},
                    data={"current_index": 0, "image_paths": image_paths},
                ),
                html.Div(
                    f"Фотографии ({len(image_paths)})", className="slideshow-title"
                ),
            ],
            divider=True,
        )