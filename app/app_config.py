# app/app_config.py - Optimized
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppConfig:
    """Centralized application configuration with improved path handling."""

    # Application data directory
    _DATA_DIR: Optional[Path] = None

    # Data source configuration
    DATA_SOURCE: Dict[str, Any] = {
        "type": "hybrid",
        "main_data": {
            "type": "github",
            "files": ["cian_apartments.csv", "cian_apartments.meta.json"],
        },
        "apartment_details": {"type": "hybrid"},
        "images": {"type": "hybrid"},
        "github": {
            "base_url": "https://raw.githubusercontent.com/klimmm/cian-tracker/refs/heads/main/"
        },
    }

    # Default subdirectories
    SUBDIRS = ["cian_data", "images", "assets"]

    @classmethod
    def initialize(cls, data_dir: Optional[Union[str, Path]] = None) -> "AppConfig":
        """Initialize configuration with data directory."""
        # Set data directory
        cls._DATA_DIR = (
            Path(data_dir)
            if data_dir
            else Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )

        # Create directories if needed and we're not using GitHub exclusively
        if cls.DATA_SOURCE.get("type") != "github":
            for dir_name in cls.SUBDIRS:
                dir_path = cls._DATA_DIR / dir_name
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory: {dir_path}")

        logger.info(f"Initialized AppConfig with data directory: {cls._DATA_DIR}")
        return cls

    @classmethod
    def get_data_dir(cls) -> Path:
        """Get data directory, initializing if necessary."""
        if cls._DATA_DIR is None:
            cls.initialize()
        return cls._DATA_DIR

    @classmethod
    def get_path(cls, *parts: str) -> Path:
        """Get a path relative to data dir."""
        return cls.get_data_dir().joinpath(*parts)

    @classmethod
    def get_cian_data_path(cls, *parts: str) -> Path:
        """Get cian_data path."""
        return cls.get_path("cian_data", *parts)

    @classmethod
    def get_images_path(cls, *parts: str) -> Path:
        """Get images path."""
        return cls.get_path("images", *parts)

    @classmethod
    def get_assets_path(cls, *parts: str) -> Path:
        """Get assets path."""
        return cls.get_path("assets", *parts)

    @classmethod
    def always_use_github_for(cls, filename: str) -> bool:
        """Check if file should always use GitHub regardless of mode."""
        return filename in cls.DATA_SOURCE.get("main_data", {}).get("files", [])

    @classmethod
    def should_use_hybrid_for_apartment_details(cls) -> bool:
        """Check if hybrid mode is enabled for apartment details."""
        return cls.DATA_SOURCE.get("apartment_details", {}).get("type") == "hybrid"

    @classmethod
    def should_use_hybrid_for_images(cls) -> bool:
        """Check if hybrid mode is enabled for images."""
        return cls.DATA_SOURCE.get("images", {}).get("type") == "hybrid"

    @classmethod
    def get_github_url(cls, *parts: str) -> str:
        """Construct GitHub URL from path components."""
        base_url = cls.DATA_SOURCE.get("github", {}).get(
            "base_url",
            "https://raw.githubusercontent.com/klimmm/cian-tracker/refs/heads/main/",
        )
        return f"{base_url}{'/'.join(parts)}"

    @classmethod
    def is_using_github(cls) -> bool:
        """Check if using GitHub as primary data source."""
        return cls.DATA_SOURCE.get("type") == "github"
