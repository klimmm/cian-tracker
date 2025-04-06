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


def run_scheduler():
    """Run the scheduler script in a separate process"""
    logger.info("Starting scheduler process")
    try:
        subprocess.run(["python", "cian_scheduler.py"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Scheduler process failed: {e}")
    except KeyboardInterrupt:
        logger.info("Scheduler process stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error in scheduler: {e}")


def run_dashboard():
    """Run the dashboard app in a separate process"""
    logger.info("Starting dashboard process")
    try:
        subprocess.run(["python", "cian_dashboard.py"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Dashboard process failed: {e}")
    except KeyboardInterrupt:
        logger.info("Dashboard process stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error in dashboard: {e}")


def main():
    """Start both the scheduler and dashboard in separate threads"""
    logger.info("Starting Cian system")

    # Create threads
    scheduler_thread = threading.Thread(target=run_scheduler)
    dashboard_thread = threading.Thread(target=run_dashboard)

    # Set as daemon threads so they'll exit when the main program exits
    scheduler_thread.daemon = True
    dashboard_thread.daemon = True

    # Start threads
    scheduler_thread.start()
    dashboard_thread.start()

    logger.info("Both services started. Press Ctrl+C to exit.")

    try:
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("System shutdown initiated by user")
    except Exception as e:
        logger.error(f"Unexpected error in main thread: {e}")
    finally:
        logger.info("System shutting down")


if __name__ == "__main__":
    main()