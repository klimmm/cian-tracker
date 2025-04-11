# app/app_config.py
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Global variable for data directory path
DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def set_data_dir(path):
    """Set the data directory path globally"""
    global DATA_DIR
    DATA_DIR = path
    logger.info(f"Set data directory to: {DATA_DIR}")
    return DATA_DIR

def get_data_dir():
    """Get the current data directory path"""
    global DATA_DIR
    return DATA_DIR