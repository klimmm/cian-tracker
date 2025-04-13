# main.py - Optimized
import logging
import os
import subprocess

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/cian_system.log"), logging.StreamHandler()],
)
logger = logging.getLogger("CianSystem")

def run_dashboard():
    """Run the dashboard app"""
    logger.info("Starting dashboard process")
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")
        env["DATA_DIR"] = os.getcwd()
        subprocess.run(["python", "app/cian_dashboard.py"], check=True, env=env)
    except subprocess.CalledProcessError as e:
        logger.error(f"Dashboard process failed: {e}")
    except KeyboardInterrupt:
        logger.info("Dashboard process stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    run_dashboard()