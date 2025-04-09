import subprocess
import threading
import logging
import time
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
        subprocess.run(["python", "dashboard/cian_dashboard.py"], check=True)
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