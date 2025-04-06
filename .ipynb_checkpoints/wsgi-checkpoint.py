import os
import sys
import logging
from pathlib import Path

# Ensure logs directory exists
Path("logs").mkdir(exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/wsgi.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("WSGI")

# Import the app
try:
    from cian_dashboard import app
    logger.info("Successfully imported Dash app")
except Exception as e:
    logger.error(f"Error importing app: {e}")
    raise

# For Gunicorn
application = app.server
app = application