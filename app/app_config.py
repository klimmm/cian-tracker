# app/app_config.py
import os
import logging
from pathlib import Path
from typing import Optional, Union
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# app/app_config.py (with fix for type error)

class AppConfig:
    """Centralized application configuration with consistent path handling."""
    
    # Class variable for the data directory path
    _DATA_DIR: Optional[Path] = None
    
    # Enhanced data source configuration with top-level type for backward compatibility
    DATA_SOURCE = {
        # Add a top-level default type for backward compatibility
        "type": "hybrid",  # Main overall type: "local", "github", or "hybrid"
        
        # Main data files - always GitHub
        "main_data": {
            "type": "github",
            "files": ["cian_apartments.csv", "cian_apartments.meta.json"]
        },
        # Apartment details - hybrid approach
        "apartment_details": {
            "type": "hybrid",  # Options: "local", "github", "hybrid" (try local first, then github)
            "files": ["price_history.csv", "stats.csv", "features.csv", 
                      "rental_terms.csv", "apartment_details.csv", "building_details.csv"]
        },
        # Images - hybrid approach
        "images": {
            "type": "hybrid"
        },
        # GitHub settings
        "github": {
            "base_url": "https://raw.githubusercontent.com/klimmm/cian-tracker/refs/heads/main/",
            "branch": "main"
        }
    }
    
    @classmethod
    def initialize(cls, data_dir: Optional[Union[str, Path]] = None) -> 'AppConfig':
        """Initialize the application configuration."""
        if data_dir:
            cls._DATA_DIR = Path(data_dir)
        else:
            # Default to the parent directory of this file
            cls._DATA_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        logger.info(f"Initialized AppConfig with data directory: {cls._DATA_DIR}")
        logger.info(f"Data source type: {cls.DATA_SOURCE.get('type', 'hybrid')} (overall)")
        logger.info(f"Main data source: {cls.DATA_SOURCE.get('main_data', {}).get('type', 'github')}")
        logger.info(f"Apartment details source: {cls.DATA_SOURCE.get('apartment_details', {}).get('type', 'hybrid')}")
        logger.info(f"Images source: {cls.DATA_SOURCE.get('images', {}).get('type', 'hybrid')}")
        
        # Ensure critical directories exist if using local files at all
        if cls.DATA_SOURCE.get('type') != 'github' or \
           cls.DATA_SOURCE.get('apartment_details', {}).get('type') != 'github' or \
           cls.DATA_SOURCE.get('images', {}).get('type') != 'github':
            cls._ensure_directory_structure()
        
        return cls
        

    
    @classmethod
    def _ensure_directory_structure(cls) -> None:
        """Ensure that important directories exist."""
        dirs_to_check = [
            "cian_data",
            "images",
            "assets"
        ]
        
        for dir_name in dirs_to_check:
            dir_path = cls._DATA_DIR / dir_name
            if not dir_path.exists():
                logger.warning(f"Creating missing directory: {dir_path}")
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    logger.error(f"Failed to create directory {dir_path}: {e}")
    
    @classmethod
    def get_data_dir(cls) -> Path:
        """Get the base data directory path.
        
        Returns:
            Path: The base data directory path
        """
        if cls._DATA_DIR is None:
            cls.initialize()
        return cls._DATA_DIR
    
    @classmethod
    def get_path(cls, *parts: str) -> Path:
        """Get a path relative to the data directory.
        
        Args:
            *parts: Path segments to append to the data directory
            
        Returns:
            Path: The complete path
        """
        return cls.get_data_dir().joinpath(*parts)
    
    @classmethod
    def get_cian_data_path(cls, *parts: str) -> Path:
        """Get a path in the cian_data directory.
        
        Args:
            *parts: Path segments to append to the cian_data directory
            
        Returns:
            Path: The complete path
        """
        return cls.get_path("cian_data", *parts)
    
    @classmethod
    def get_images_path(cls, *parts: str) -> Path:
        """Get a path in the images directory.
        
        Args:
            *parts: Path segments to append to the images directory
            
        Returns:
            Path: The complete path
        """
        return cls.get_path("images", *parts)
    
    @classmethod
    def get_assets_path(cls, *parts: str) -> Path:
        """Get a path in the assets directory.
        
        Args:
            *parts: Path segments to append to the assets directory
            
        Returns:
            Path: The complete path
        """
        return cls.get_path("assets", *parts)

    
    @classmethod
    def always_use_github_for(cls, filename: str) -> bool:
        """Check if a specific file should always be loaded from GitHub.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            bool: True if the file should always be loaded from GitHub
        """
        main_data_files = cls.DATA_SOURCE.get("main_data", {}).get("files", [])
        return filename in main_data_files
    
    @classmethod
    def should_use_hybrid_for_apartment_details(cls) -> bool:
        """Check if apartment details should use a hybrid approach.
        
        Returns:
            bool: True if apartment details should use hybrid approach
        """
        apartment_details_type = cls.DATA_SOURCE.get("apartment_details", {}).get("type")
        return apartment_details_type == "hybrid"
    
    @classmethod
    def should_use_hybrid_for_images(cls) -> bool:
        """Check if images should use a hybrid approach.
        
        Returns:
            bool: True if images should use hybrid approach
        """
        images_type = cls.DATA_SOURCE.get("images", {}).get("type")
        return images_type == "hybrid"
    
    @classmethod
    def get_github_url(cls, *parts: str) -> str:
        """Get a URL for a file in the GitHub repository.
        
        Args:
            *parts: Path segments to append to the GitHub base URL
            
        Returns:
            str: The complete GitHub URL
        """
        base_url = cls.DATA_SOURCE.get("github", {}).get("base_url", 
                   "https://raw.githubusercontent.com/klimmm/cian-tracker/refs/heads/main/")
        path = "/".join(parts)
        return f"{base_url}{path}"
        
    @classmethod
    def is_using_github(cls) -> bool:
        """Check if the application is configured to use GitHub as a data source.
        
        Returns:
            bool: True if using GitHub, False if using local files
        """
        return cls.DATA_SOURCE["type"] == "github"
    
   
    @classmethod
    def is_using_github(cls) -> bool:
        """Check if the application is configured to use GitHub as a data source.
        
        Returns:
            bool: True if main type is github, False otherwise
        """
        # For backward compatibility
        return cls.DATA_SOURCE.get("type") == "github"


        

# Legacy functions are deprecated and should be removed in future versions
# For backward compatibility only
def set_data_dir(path):
    """Set the data directory path globally (legacy function, use AppConfig.initialize).
    
    Args:
        path: The new data directory path
        
    Returns:
        Path: The data directory path
    """
    import warnings
    warnings.warn(
        "set_data_dir is deprecated, use AppConfig.initialize instead",
        DeprecationWarning,
        stacklevel=2
    )
    return AppConfig.initialize(path).get_data_dir()

def get_data_dir():
    """Get the current data directory path (legacy function, use AppConfig.get_data_dir).
    
    Returns:
        Path: The data directory path
    """
    import warnings
    warnings.warn(
        "get_data_dir is deprecated, use AppConfig.get_data_dir instead",
        DeprecationWarning,
        stacklevel=2
    )
    return AppConfig.get_data_dir()