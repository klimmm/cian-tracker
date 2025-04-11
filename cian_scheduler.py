import schedule
import time
import subprocess
import logging
from datetime import datetime
import os

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CianScheduler')

# Data files to commit
DATA_FILES = ["cian_apartments.csv", "cian_apartments.meta.json"]

# Run counter to control part2 frequency
run_count = 0

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

def run_scraper_with_optional_part2():
    """Run part1.py every 10 minutes and part2.py every 30 minutes"""
    global run_count
    run_count += 1
    logger.info(f"==== Scraper Cycle {run_count} Started ====")

    # Run part1
    success_part1 = False
    try:
        result1 = subprocess.run(
            ["python", "cian_scraper_part1.py"],
            capture_output=True,
            text=True
        )
        if result1.returncode == 0:
            logger.info("part1.py completed successfully")
            success_part1 = True
        else:
            logger.error(f"part1.py failed with error:\n{result1.stderr}")
    except Exception as e:
        logger.error(f"Error running part1.py: {e}")

    # Run part2 every 3rd cycle, only if part1 succeeded
    success_part2 = False
    if success_part1 and run_count % 3 == 0:
        logger.info("Running part2.py (every 3rd cycle)")
        try:
            result2 = subprocess.run(
                ["python", "cian_scraper_part2.py"],
                capture_output=True,
                text=True
            )
            if result2.returncode == 0:
                logger.info("part2.py completed successfully")
                success_part2 = True
            else:
                logger.error(f"part2.py failed with error:\n{result2.stderr}")
        except Exception as e:
            logger.error(f"Error running part2.py: {e}")
    else:
        logger.info("Skipping part2.py this cycle")

    # Commit files if part1 succeeded
    if success_part1:
        logger.info("Committing and pushing data files...")
        existing_files = [f for f in DATA_FILES if os.path.exists(f)]
        if existing_files:
            commit_and_push(existing_files)
        else:
            logger.warning("No data files found to commit.")
    else:
        logger.warning("Skipping commit due to part1 failure.")

    logger.info(f"==== Scraper Cycle {run_count} Finished ====\n")

# Run once at startup
run_scraper_with_optional_part2()

# Schedule to run every 10 minutes
schedule.every(30).minutes.do(run_scraper_with_optional_part2)
logger.info("Scheduler started: part1.py every 10 min, part2.py every 30 min")

# Keep the scheduler running
while True:
    schedule.run_pending()
    time.sleep(1)
