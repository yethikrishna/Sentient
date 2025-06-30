# healthcheck.py

import os
import time
import requests
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

URL = f"{os.getenv('WAHA_API_URL')}/health"
INTERVAL = 300  # seconds between checks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def check_health():
    try:
        response = requests.get(URL, timeout=5)
        if response.status_code == 200:
            logging.info("Health check passed.")
        else:
            logging.warning(f"Health check failed with status code: {response.status_code}")
    except requests.RequestException as e:
        logging.error(f"Health check error: {e}")

def main():
    logging.info(f"Starting health check loop for {URL}")
    while True:
        check_health()
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
