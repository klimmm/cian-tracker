import schedule
import time
import subprocess
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CianScheduler')


def run_scraper():
    """Run the Cian scraper script"""
    logger.info(f"Starting scraper job at {datetime.now()}")
    try:
        # Run the scraper script
        result = subprocess.run(
            ["python", "cian_parser.py"],  # Update this to your script filename
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("Scraper job completed successfully")
        else:
            logger.error(f"Scraper job failed with error: {result.stderr}")

    except Exception as e:
        logger.error(f"Error running scraper: {e}")

    logger.info(f"Scraper job finished at {datetime.now()}")


# Run once at startup
run_scraper()

# Schedule to run every 30 minutes
schedule.every(10).minutes.do(run_scraper)

logger.info("Scheduler started. Will run scraper every 30 minutes.")

# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(1)