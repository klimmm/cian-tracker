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
DATA_FILES = ["cian_apartments.csv"]

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

def run_scraper():
    """Run the Cian scraper script and commit changes regardless if needed"""
    logger.info(f"Starting scraper job at {datetime.now()}")
    success = False
    
    try:
        # Run the scraper script
        result = subprocess.run(
            ["python", "cian_parser.py"],  # Update this to your script filename
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info("Scraper job completed successfully")
            success = True
        else:
            logger.error(f"Scraper job failed with error: {result.stderr}")
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
    
    # If scraper was successful, commit and push regardless of changes
    if success:
        logger.info("Committing and pushing data files...")
        existing_files = [f for f in DATA_FILES if os.path.exists(f)]
        
        if existing_files:
            commit_and_push(existing_files)
        else:
            logger.warning("None of the specified data files exist. Nothing to commit.")
    
    logger.info(f"Scraper job finished at {datetime.now()}")

# Run once at startup
run_scraper()

# Schedule to run every 10 minutes
schedule.every(10).minutes.do(run_scraper)
logger.info("Scheduler started. Will run scraper and git operations every 10 minutes.")

# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(1)