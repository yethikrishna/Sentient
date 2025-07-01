import os
import re
import time
import requests
import logging

# --- Configuration ---

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s")
logger = logging.getLogger("HealthCheck")

INTERVAL_SECONDS = 300  # 5 minutes

# --- Service Discovery ---
def get_services_from_env():
    """Dynamically discovers service URLs from environment variables."""
    services = []

    # 1. WAHA
    waha_url = os.getenv('WAHA_URL')
    if waha_url:
        services.append({"name": "WAHA", "type": "http", "url": f"{waha_url}/health"})

    # 2. MCP Hubs
    mcp_pattern = re.compile(r"([A-Z0-9_]+_MCP_SERVER_URL)")
    for key, value in os.environ.items():
        if mcp_pattern.match(key) and value:
            # Service name from env var: GMAIL_MCP_SERVER_URL -> mcp-gmail
            service_name = key.replace('_MCP_SERVER_URL', '').replace('_', '-').lower()
            services.append({"name": service_name, "type": "http", "url": value})

    return services

# --- Health Check Functions ---
def check_http_service(service):
    """Pings an HTTP endpoint."""
    url = service['url']
    try:
        response = requests.get(url, timeout=10)
        if 200 <= response.status_code < 500:
            logger.info(f"OK - Service '{service['name']}' at {url} is reachable (Status: {response.status_code}).")
        else:
            logger.warning(f"FAIL - Service '{service['name']}' at {url} is unhealthy (Status: {response.status_code}).")
    except requests.RequestException as e:
        logger.error(f"FAIL - Service '{service['name']}' at {url} is down. Error: {e}")

def run_all_checks(services):
    """Runs health checks for all discovered services."""
    logger.info(f"Starting health check run for {len(services)} services...")
    for service in services:
        if service['type'] == 'http':
            check_http_service(service)
        else:
            logger.warning(f"Unknown service type '{service['type']}' for '{service['name']}'.")
        time.sleep(1)
    logger.info("Health check run finished.")

# --- Main Loop ---
def main():
    services = get_services_from_env()
    if not services:
        logger.warning("No services found in environment variables to health check. Exiting.")
        return

    logger.info(f"Starting continuous health check loop. Interval: {INTERVAL_SECONDS}s")
    while True:
        run_all_checks(services)
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
