# app/app_config.py
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

class AppConfig:
    """Centralized application configuration with consistent path handling."""
    
    # Class variable for the data directory path
    _DATA_DIR = None
    
    @classmethod
    def initialize(cls, data_dir=None):
        """Initialize the application configuration.
        
        Args:
            data_dir: Optional custom data directory path
        """
        if data_dir:
            cls._DATA_DIR = Path(data_dir)
        else:
            # Default to the parent directory of this file
            cls._DATA_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        logger.info(f"Initialized AppConfig with data directory: {cls._DATA_DIR}")
        
        # Ensure critical directories exist
        cls._ensure_directory_structure()
        
        return cls
    
    @classmethod
    def _ensure_directory_structure(cls):
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
                dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_data_dir(cls):
        """Get the base data directory path.
        
        Returns:
            Path: The base data directory path
        """
        if cls._DATA_DIR is None:
            cls.initialize()
        return cls._DATA_DIR
    
    @classmethod
    def get_path(cls, *parts):
        """Get a path relative to the data directory.
        
        Args:
            *parts: Path segments to append to the data directory
            
        Returns:
            Path: The complete path
        """
        return cls.get_data_dir().joinpath(*parts)
    
    @classmethod
    def get_cian_data_path(cls, *parts):
        """Get a path in the cian_data directory.
        
        Args:
            *parts: Path segments to append to the cian_data directory
            
        Returns:
            Path: The complete path
        """
        return cls.get_path("cian_data", *parts)
    
    @classmethod
    def get_images_path(cls, *parts):
        """Get a path in the images directory.
        
        Args:
            *parts: Path segments to append to the images directory
            
        Returns:
            Path: The complete path
        """
        return cls.get_path("images", *parts)
    
    @classmethod
    def get_assets_path(cls, *parts):
        """Get a path in the assets directory.
        
        Args:
            *parts: Path segments to append to the assets directory
            
        Returns:
            Path: The complete path
        """
        return cls.get_path("assets", *parts)


# For backward compatibility
def set_data_dir(path):
    """Set the data directory path globally (legacy function).
    
    Args:
        path: The new data directory path
        
    Returns:
        Path: The data directory path
    """
    AppConfig.initialize(path)
    return AppConfig.get_data_dir()


def get_data_dir():
    """Get the current data directory path (legacy function).
    
    Returns:
        Path: The data directory path
    """
    return AppConfig.get_data_dir()