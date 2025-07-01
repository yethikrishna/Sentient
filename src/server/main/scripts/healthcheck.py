import os
import re
import time
import requests
import logging
import redis
from dotenv import load_dotenv

# --- Configuration ---
# Load .env from the parent 'server' directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()  # Load from default .env if not found

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

    # 2. Celery Broker (Redis)
    celery_broker_url = os.getenv('CELERY_BROKER_URL')
    if celery_broker_url:
        services.append({"name": "Celery Broker (Redis)", "type": "redis", "url": celery_broker_url})

    # 3. MCP Hubs
    mcp_pattern = re.compile(r"([A-Z0-9_]+_MCP_SERVER_URL)")
    for key, value in os.environ.items():
        if mcp_pattern.match(key) and value:
            # Service name from env var: GMAIL_MCP_SERVER_URL -> mcp-gmail
            service_name = key.replace('_MCP_SERVER_URL', '').replace('_', '-').lower()
            # Most MCPs don't have a /health endpoint, so we ping the base URL/SSE endpoint
            services.append({"name": service_name, "type": "http", "url": value})
            
    return services

# --- Health Check Functions ---
def check_http_service(service):
    """Pings an HTTP endpoint."""
    url = service['url']
    try:
        # Use a short timeout
        response = requests.get(url, timeout=10)
        # Accept 2xx, 3xx, and 404 (since some MCPs might return 404 for GET) as "reachable"
        if 200 <= response.status_code < 500:
            logger.info(f"OK - Service '{service['name']}' at {url} is reachable (Status: {response.status_code}).")
        else:
            logger.warning(f"FAIL - Service '{service['name']}' at {url} is unhealthy (Status: {response.status_code}).")
    except requests.RequestException as e:
        logger.error(f"FAIL - Service '{service['name']}' at {url} is down. Error: {e}")

def check_redis_service(service):
    """Pings a Redis server as a proxy for Celery health."""
    url = service['url']
    try:
        # The redis-py client can parse the URL
        r = redis.from_url(url, socket_connect_timeout=5, decode_responses=True)
        if r.ping():
            logger.info(f"OK - Service '{service['name']}' at {url} is healthy.")
        else:
            logger.warning(f"FAIL - Service '{service['name']}' at {url} ping returned False.")
    except Exception as e:
        logger.error(f"FAIL - Service '{service['name']}' at {url} is down. Error: {e}")

def run_all_checks(services):
    """Runs health checks for all discovered services."""
    logger.info(f"Starting health check run for {len(services)} services...")
    for service in services:
        if service['type'] == 'http':
            check_http_service(service)
        elif service['type'] == 'redis':
            check_redis_service(service)
        else:
            logger.warning(f"Unknown service type '{service['type']}' for '{service['name']}'.")
        time.sleep(1) # Small delay between checks
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