import subprocess
import threading
import logging
import time
import os

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/cian_system.log"), logging.StreamHandler()],
)
logger = logging.getLogger("CianSystem")

def run_dashboard():
    """Run the dashboard app in a separate process"""
    logger.info("Starting dashboard process")
    
    # Log the current working directory for debugging
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Check if images directory exists
    if os.path.exists("images"):
        logger.info(f"Images directory exists at: {os.path.abspath('images')}")
        # List some example directories
        try:
            dirs = os.listdir("images")
            logger.info(f"Found {len(dirs)} items in images directory")
            for item in dirs[:5]:  # List up to 5 items
                item_path = os.path.join("images", item)
                if os.path.isdir(item_path):
                    files = os.listdir(item_path)
                    logger.info(f"Directory {item} contains {len(files)} files")
        except Exception as e:
            logger.error(f"Error inspecting images directory: {e}")
    else:
        logger.warning(f"Images directory does not exist at: {os.path.abspath('images')}")
    
    try:
        # Use the same environment variables for the subprocess
        env = os.environ.copy()
        # Add the current directory to PYTHONPATH to ensure imports work
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = os.getcwd() + os.pathsep + env["PYTHONPATH"]
        else:
            env["PYTHONPATH"] = os.getcwd()
            
        # Run the dashboard passing through all environment variables
        subprocess.run(["python", "cian_dashboard.py"], check=True, env=env)
    except subprocess.CalledProcessError as e:
        logger.error(f"Dashboard process failed: {e}")
    except KeyboardInterrupt:
        logger.info("Dashboard process stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error in dashboard: {e}")

def main():
    """Start only the dashboard app"""
    logger.info("Starting Cian dashboard only")
    # Run the dashboard directly (not in a thread)
    run_dashboard()

if __name__ == "__main__":
    main()