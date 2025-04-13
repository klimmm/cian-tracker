# app/app_config.py - Optimized
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppConfig:
    """Centralized application configuration"""
    _DATA_DIR = None
    
    # Data source configuration
    DATA_SOURCE = {
        "type": "hybrid",
        "main_data": {"type": "github", "files": ["cian_apartments.csv", "cian_apartments.meta.json"]},
        "apartment_details": {"type": "hybrid"},
        "images": {"type": "hybrid"},
        "github": {"base_url": "https://raw.githubusercontent.com/klimmm/cian-tracker/refs/heads/main/"}
    }
    
    @classmethod
    def initialize(cls, data_dir=None):
        """Initialize configuration"""
        cls._DATA_DIR = Path(data_dir) if data_dir else Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Create directories if needed
        if cls.DATA_SOURCE.get('type') != 'github':
            for dir_name in ["cian_data", "images", "assets"]:
                dir_path = cls._DATA_DIR / dir_name
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
        return cls
    
    @classmethod
    def get_data_dir(cls):
        """Get data directory"""
        if cls._DATA_DIR is None:
            cls.initialize()
        return cls._DATA_DIR
    
    @classmethod
    def get_path(cls, *parts):
        """Get a path relative to data dir"""
        return cls.get_data_dir().joinpath(*parts)
    
    @classmethod
    def get_cian_data_path(cls, *parts):
        """Get cian_data path"""
        return cls.get_path("cian_data", *parts)
    
    @classmethod
    def get_images_path(cls, *parts):
        """Get images path"""
        return cls.get_path("images", *parts)
    
    @classmethod
    def get_assets_path(cls, *parts):
        """Get assets path"""
        return cls.get_path("assets", *parts)
    
    @classmethod
    def always_use_github_for(cls, filename):
        """Check if file should use GitHub"""
        return filename in cls.DATA_SOURCE.get("main_data", {}).get("files", [])
    
    @classmethod
    def should_use_hybrid_for_apartment_details(cls):
        """Check hybrid mode for apartment details"""
        return cls.DATA_SOURCE.get("apartment_details", {}).get("type") == "hybrid"
    
    @classmethod
    def should_use_hybrid_for_images(cls):
        """Check hybrid mode for images"""
        return cls.DATA_SOURCE.get("images", {}).get("type") == "hybrid"
    
    @classmethod
    def get_github_url(cls, *parts):
        """Get GitHub URL"""
        base_url = cls.DATA_SOURCE.get("github", {}).get("base_url", 
                   "https://raw.githubusercontent.com/klimmm/cian-tracker/refs/heads/main/")
        return f"{base_url}{'/'.join(parts)}"
    
    @classmethod
    def is_using_github(cls):
        """Check if using GitHub"""
        return cls.DATA_SOURCE.get("type") == "github"