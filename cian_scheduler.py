import schedule
import time
import subprocess
import logging
from datetime import datetime
import os
import argparse
import json
import importlib.util
import sys

# Create necessary imports for URL library
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Helper function to load URL from library
def load_url_from_library(url_name):
    """Load a URL from the URL library by name"""
    try:
        # First, try to import the module
        spec = importlib.util.spec_from_file_location("url_library", "scrapper/url_library.py")
        if not spec:
            logger.error("Could not find scrapper/url_library.py")
            return None
            
        url_lib = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(url_lib)
        
        # Get the URL by name
        if hasattr(url_lib, 'get_url'):
            url = url_lib.get_url(url_name)
            if url:
                return url
            else:
                logger.error(f"URL name '{url_name}' not found in URL library")
                # List available URLs
                if hasattr(url_lib, 'list_available_urls'):
                    available = url_lib.list_available_urls()
                    logger.info(f"Available URL names: {', '.join(available)}")
                return None
        else:
            logger.error("URL library does not have a get_url function")
            return None
    except Exception as e:
        logger.error(f"Error loading URL from library: {e}")
        return None

# Create logs directory
os.makedirs("logs", exist_ok=True)

# Setup logging for the scheduler with rotation
logger = logging.getLogger('CianScheduler')
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent propagation to root logger

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Import logging handlers for rotation
from logging.handlers import RotatingFileHandler

# File handler for scheduler logs with rotation
file_handler = RotatingFileHandler(
    "logs/scheduler.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5  # Keep 5 backup files
)
file_handler.setFormatter(formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Function to setup rotated log files for child processes
def get_rotated_log_path(base_path):
    """Create a RotatingFileHandler and return the path to the log file"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(base_path), exist_ok=True)
    
    # Setup file rotation and get handler
    handler = RotatingFileHandler(
        base_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5  # Keep 5 backup files
    )
    
    # Initialize the log file if needed
    handler.emit(logging.LogRecord(
        name='init',
        level=logging.INFO,
        pathname='',
        lineno=0,
        msg=f"Log initialized at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        args=(),
        exc_info=None
    ))
    
    return base_path

# Create necessary directories
os.makedirs("scrapper", exist_ok=True)
os.makedirs("cian_data", exist_ok=True)

# Configuration
CONFIG = {
    # Paths
    "data_dir": "cian_data",
    "base_filename": "cian_apartments",  # Base name for all data files
    
    # Scraper parameters
    "base_url": "https://www.cian.ru/cat.php?currency=2&deal_type=rent&district%5B0%5D=13&district%5B1%5D=21&engine_version=2&maxprice=100000&metro%5B0%5D=4&metro%5B10%5D=86&metro%5B11%5D=115&metro%5B12%5D=118&metro%5B13%5D=120&metro%5B14%5D=134&metro%5B15%5D=143&metro%5B16%5D=151&metro%5B17%5D=159&metro%5B18%5D=310&metro%5B1%5D=8&metro%5B2%5D=12&metro%5B3%5D=18&metro%5B4%5D=20&metro%5B5%5D=33&metro%5B6%5D=46&metro%5B7%5D=56&metro%5B8%5D=63&metro%5B9%5D=80&offer_type=flat&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1&room9=1&sort=creation_date_desc&type=4",
    "max_pages": 100,
    "max_distance_km": 3,
    "time_filter": None,
    "headless": True,
    "reference_address": "Москва, переулок Большой Саввинский, 3",
    
    # Git parameters
    "commit_changes": True,
    
    # Scheduler parameters
    "run_interval_minutes": 30
}

# Function to get file paths based on base filename
def get_file_paths():
    """Generate file paths based on the base filename config"""
    base_dir = CONFIG["data_dir"]
    base_name = CONFIG["base_filename"]
    
    csv_file = os.path.join(base_dir, f"{base_name}.csv")
    json_file = os.path.join(base_dir, f"{base_name}.json")
    meta_file = os.path.join(base_dir, f"{base_name}.meta.json")
    
    return {
        "csv_file": csv_file,
        "json_file": json_file,
        "meta_file": meta_file
    }

# Data files to commit (update paths)
def get_data_files():
    """Get list of data files to commit based on current config"""
    paths = get_file_paths()
    return [paths["csv_file"], paths["meta_file"]]

# Run counter to control part2 frequency
run_count = 0

def save_config():
    """Save current configuration to a file"""
    with open('scrapper_config.json', 'w', encoding='utf-8') as f:
        json.dump(CONFIG, f, ensure_ascii=False, indent=4)
    logger.info("Configuration saved to scrapper_config.json")

def load_config():
    """Load configuration from file if it exists"""
    global CONFIG
    if os.path.exists('scrapper_config.json'):
        try:
            with open('scrapper_config.json', 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                CONFIG.update(loaded_config)
            logger.info("Configuration loaded from scrapper_config.json")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")

def commit_and_push(files):
    """Commit and push changes to Git repository"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    base_name = CONFIG["base_filename"]
    commit_message = f"Auto-update CIAN data for {base_name} ({timestamp})"
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

def run_scrapper_part1():
    """Run part1.py with parameters from config"""
    try:
        # Get file paths
        paths = get_file_paths()
        
        # Setup rotated log file for part1
        log_file = get_rotated_log_path("logs/part1.log")
        
        cmd = [
            "python", "scrapper/cian_scrapper_part1.py",
            "--csv_file", paths["csv_file"],
            "--json_file", paths["json_file"],
            "--base_url", CONFIG["base_url"],
            "--max_pages", str(CONFIG["max_pages"]),
            "--max_distance_km", str(CONFIG["max_distance_km"]),
            "--reference_address", CONFIG["reference_address"],
            "--log_file", log_file  # Specify log file location
        ]
        
        if CONFIG["time_filter"]:
            cmd.extend(["--time_filter", str(CONFIG["time_filter"])])
        
        if CONFIG["headless"]:
            cmd.append("--headless")
        
        logger.info(f"Running part1 with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("part1.py completed successfully")
            # Log a summary instead of full output
            last_lines = result.stdout.strip().split('\n')[-5:] if result.stdout else []
            logger.info(f"Last output lines: {'; '.join(last_lines)}")
            return True
        else:
            logger.error(f"part1.py failed with error:\n{result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error running part1.py: {e}")
        return False

def run_scrapper_part2():
    """Run part2.py with parameters from config"""
    try:
        # Get file paths
        paths = get_file_paths()
        
        # Setup rotated log file for part2
        log_file = get_rotated_log_path("logs/part2.log")
        
        cmd = [
            "python", "scrapper/cian_scrapper_part2.py",
            "--csv_file", paths["csv_file"],
            "--max_distance_km", str(CONFIG["max_distance_km"]),
            "--log_file", log_file  # Specify log file location
        ]
        
        if CONFIG["headless"]:
            cmd.append("--headless")
        
        logger.info(f"Running part2 with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("part2.py completed successfully")
            # Log a summary instead of full output
            last_lines = result.stdout.strip().split('\n')[-5:] if result.stdout else []
            logger.info(f"Last output lines: {'; '.join(last_lines)}")
            return True
        else:
            logger.error(f"part2.py failed with error:\n{result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error running part2.py: {e}")
        return False

def run_scrapper_with_optional_part2():
    """Run part1.py every time and part2.py every 3rd time"""
    global run_count
    run_count += 1
    logger.info(f"==== Scraper Cycle {run_count} Started ====")

    # Run part1
    success_part1 = run_scrapper_part1()

    # Run part2 every 3rd cycle, only if part1 succeeded
    success_part2 = False
    if success_part1 and run_count % 3 == 0:
        logger.info("Running part2.py (every 3rd cycle)")
        success_part2 = run_scrapper_part2()
    else:
        logger.info("Skipping part2.py this cycle")

    # Commit files if part1 succeeded and commit_changes is enabled
    if success_part1 and CONFIG["commit_changes"]:
        logger.info("Committing and pushing data files...")
        data_files = get_data_files()
        existing_files = [f for f in data_files if os.path.exists(f)]
        if existing_files:
            commit_and_push(existing_files)
        else:
            logger.warning("No data files found to commit.")
    elif not CONFIG["commit_changes"]:
        logger.info("Git commit skipped (disabled in config)")
    else:
        logger.warning("Skipping commit due to part1 failure.")

    logger.info(f"==== Scraper Cycle {run_count} Finished ====\n")

def start_scheduler():
    """Start the scheduler with the configured interval"""
    # Run once at startup
    run_scrapper_with_optional_part2()

    # Schedule to run at the specified interval
    schedule.every(CONFIG["run_interval_minutes"]).minutes.do(run_scrapper_with_optional_part2)
    logger.info(f"Scheduler started: part1.py every {CONFIG['run_interval_minutes']} min, "
                f"part2.py every {CONFIG['run_interval_minutes']*3} min")

    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(1)

def run_once():
    """Run the scraper once without scheduling"""
    logger.info("Running one-time scraper execution")
    
    # Run part1
    success_part1 = run_scrapper_part1()
    
    # Always run part2 for one-time executions if part1 succeeded
    if success_part1:
        logger.info("Running part2.py for one-time execution")
        run_scrapper_part2()
    
    # Commit files if part1 succeeded and commit_changes is enabled
    if success_part1 and CONFIG["commit_changes"]:
        logger.info("Committing and pushing data files...")
        data_files = get_data_files()
        existing_files = [f for f in data_files if os.path.exists(f)]
        if existing_files:
            commit_and_push(existing_files)
        else:
            logger.warning("No data files found to commit.")
    
    logger.info("One-time execution completed")

if __name__ == "__main__":
    # Load any existing configuration
    load_config()
    
    parser = argparse.ArgumentParser(description='CIAN Scheduler')
    parser.add_argument('--once', action='store_true', help='Run once and exit (no scheduling)')
    parser.add_argument('--no-commit', action='store_true', help='Disable Git commit')
    parser.add_argument('--interval', type=int, help='Scheduler interval in minutes')
    parser.add_argument('--url', type=str, help='CIAN base URL (full URL)')
    parser.add_argument('--url-name', type=str, help='Use a named URL from url_library.py')
    parser.add_argument('--list-urls', action='store_true', help='List available URL names in library')
    parser.add_argument('--max-pages', type=int, help='Maximum pages to scrape')
    parser.add_argument('--max-distance', type=float, help='Maximum distance in km')
    parser.add_argument('--base-filename', type=str, help='Base name for data files (without extension)')
    parser.add_argument('--data-dir', type=str, help='Directory for data files')
    parser.add_argument('--save-config', action='store_true', help='Save current configuration to file')
    
    args = parser.parse_args()
    
    # List available URLs if requested
    if args.list_urls:
        try:
            spec = importlib.util.spec_from_file_location("url_library", "scrapper/url_library.py")
            url_lib = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(url_lib)
            if hasattr(url_lib, 'list_available_urls'):
                available = url_lib.list_available_urls()
                print(f"Available URL names:")
                for name in available:
                    print(f"  - {name}")
                print("\nExample usage:")
                print(f"  python cian_scheduler.py --url-name {available[0]}")
                sys.exit(0)
        except Exception as e:
            print(f"Error listing URLs: {e}")
            sys.exit(1)
    
    # Handle URL from library if provided
    if args.url_name:
        url = load_url_from_library(args.url_name)
        if url:
            logger.info(f"Using URL '{args.url_name}' from library")
            CONFIG["base_url"] = url
        else:
            logger.error(f"Could not load URL '{args.url_name}' from library. Exiting.")
            sys.exit(1)
    
    # Update config based on arguments
    if args.no_commit:
        CONFIG["commit_changes"] = False
    
    if args.interval:
        CONFIG["run_interval_minutes"] = args.interval
    
    if args.url:
        CONFIG["base_url"] = args.url
    
    if args.max_pages:
        CONFIG["max_pages"] = args.max_pages
    
    if args.max_distance:
        CONFIG["max_distance_km"] = args.max_distance
    
    if args.base_filename:
        CONFIG["base_filename"] = args.base_filename
        logger.info(f"Using base filename: {args.base_filename}")
    
    if args.data_dir:
        CONFIG["data_dir"] = args.data_dir
        logger.info(f"Using data directory: {args.data_dir}")
    
    # Ensure the data directory exists
    os.makedirs(CONFIG["data_dir"], exist_ok=True)
    
    # Save configuration if requested
    if args.save_config:
        save_config()
    
    # Run once or start scheduler
    if args.once:
        run_once()
    else:
        start_scheduler()