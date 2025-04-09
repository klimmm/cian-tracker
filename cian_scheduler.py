import schedule
import time
import subprocess
import logging
from datetime import datetime
import os

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

# Define the data files that need to be committed
DATA_FILES = ["cian_apartments.csv", "cian_apartments.meta.json"]

def commit_and_push(files):
    """Commit and push changes to Git repository"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_message = f"Auto-update CIAN data ({timestamp})"
    try:
        for file in files:
            logger.info(f"Staging {file}...")
            subprocess.run(["git", "add", file], check=True)
        logger.info("Committing changes...")
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        logger.info("Pushing to remote repository...")
        subprocess.run(["git", "push"], check=True)
        logger.info("Git push completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during Git operations: {e}")

def run_scraper(script_name):
    """Run a scraper script and commit changes if successful"""
    logger.info(f"Starting {script_name} at {datetime.now()}")
    success = False
    
    try:
        result = subprocess.run(
            ["python", script_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info(f"{script_name} completed successfully")
            success = True
        else:
            logger.error(f"{script_name} failed with error:\n{result.stderr}")
    except Exception as e:
        logger.error(f"Error running {script_name}: {e}")
    
    if success:
        logger.info("Committing and pushing data files...")
        existing_files = [f for f in DATA_FILES if os.path.exists(f)]
        if existing_files:
            commit_and_push(existing_files)
        else:
            logger.warning("None of the specified data files exist. Nothing to commit.")
    
    logger.info(f"{script_name} job finished at {datetime.now()}")

# Run both at startup
run_scraper("cian_scraper_part1.py")
run_scraper("cian_scraper_part2.py")

# Schedule scraper jobs
schedule.every(10).minutes.do(run_scraper, "cian_scraper_part1.py")
schedule.every(30).minutes.do(run_scraper, "cian_scraper_part2.py")

logger.info("Scheduler started. part1.py every 10 minutes, part2.py every 30 minutes.")

# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(1)
