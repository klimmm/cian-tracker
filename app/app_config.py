# app/app_config.py - Simplified
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppConfig:
    """Centralized application configuration with simplified strategy."""

    # Application data directory
    _DATA_DIR: Optional[Path] = None

    # Primary data source - set to 'github' or 'local'
    PRIMARY_SOURCE = "github"
    
    # GitHub repository information
    GITHUB_BASE_URL = "https://raw.githubusercontent.com/klimmm/cian-tracker/main/"
    # Files that must always be loaded from GitHub (even in local mode)
    GITHUB_ONLY_FILES = ["cian_apartments.csv", "cian_apartments.meta.json"]
    
    # Files that require fallback to the alternate source if primary fails
    FALLBACK_ENABLED_FILES = [
        "price_history.csv",
        "stats.csv", 
        "features.csv", 
        "rental_terms.csv", 
        "apartment_details.csv", 
        "building_details.csv"
    ]

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
        if cls.PRIMARY_SOURCE != "github":
            for dir_name in cls.SUBDIRS:
                dir_path = cls._DATA_DIR / dir_name
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory: {dir_path}")

        logger.info(f"Initialized AppConfig with data directory: {cls._DATA_DIR}")
        logger.info(f"Using primary data source: {cls.PRIMARY_SOURCE}")
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
    def get_github_url(cls, *parts: str) -> str:
        """Construct GitHub URL from path components."""
        return f"{cls.GITHUB_BASE_URL}{'/'.join(parts)}"
        
    @classmethod
    def should_use_github_for(cls, filename: str) -> bool:
        """Determine if GitHub should be used as the source for this file."""
        # Always use GitHub for specified files regardless of primary source
        if filename in cls.GITHUB_ONLY_FILES:
            return True
            
        # Use GitHub as primary if configured
        return cls.PRIMARY_SOURCE == "github"
        
    @classmethod
    def should_use_fallback(cls, filename: str) -> bool:
        """Determine if fallback to alternate source is allowed for this file."""
        # Only allow fallback for specified files
        return filename in cls.FALLBACK_ENABLED_FILES