# app/app_config.py
import os
import logging
from pathlib import Path
from typing import Optional, Union, List

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
    _DATA_DIR: Optional[Path] = None
    
    @classmethod
    def initialize(cls, data_dir: Optional[Union[str, Path]] = None) -> 'AppConfig':
        """Initialize the application configuration.
        
        Args:
            data_dir: Optional custom data directory path
        
        Returns:
            The AppConfig class for method chaining
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