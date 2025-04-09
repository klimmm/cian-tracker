import subprocess
import threading
import logging
import time
import os
import shutil

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
    try:
        # Get the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        
        # Copy the metadata file to the working directory if needed
        metadata_file = "cian_apartments.meta.json"
        source_path = os.path.join(current_dir, metadata_file)
        destination_path = os.path.join(parent_dir, metadata_file)
        
        if os.path.exists(source_path) and not os.path.exists(destination_path):
            logger.info(f"Copying metadata file to parent directory: {destination_path}")
            shutil.copy2(source_path, destination_path)
        
        # Run as a module from the parent directory
        subprocess.run(
            ["python", "-m", "app.dashboard.cian_dashboard"], 
            check=True,
            cwd=parent_dir  # Set the working directory to the parent
        )
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