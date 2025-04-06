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
DATA_FILES = ["cian_apartments.csv", "cian_apartments.json"]


def file_changed(file_path):
    """Check if a file has changes that need to be committed"""
    result = subprocess.run(["git", "diff", "--name-only", file_path], 
                            capture_output=True, text=True)
    return file_path in result.stdout


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
    """Run the Cian scraper script and commit changes if needed"""
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

    # If scraper was successful, check for file changes and commit
    if success:
        logger.info("Checking for changes to commit...")
        changed_files = [f for f in DATA_FILES if os.path.exists(f) and file_changed(f)]
        
        if changed_files:
            logger.info(f"Found changes in: {', '.join(changed_files)}")
            commit_and_push(changed_files)
        else:
            logger.info("No changes detected in output files. Nothing to commit.")
    
    logger.info(f"Scraper job finished at {datetime.now()}")


# Run once at startup
run_scraper()

# Schedule to run every 10 minutes (keeping your existing interval)
schedule.every(10).minutes.do(run_scraper)

logger.info("Scheduler started. Will run scraper and git operations every 10 minutes.")

# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(1)