# src/server/main/service.py
# This file would wrap the main logic for running the server as a service.
# For a FastAPI app, this typically involves uvicorn.run().

import uvicorn
import os
import datetime

# Import config from the current 'main' directory
from .config import APP_SERVER_PORT, IS_DEV_ENVIRONMENT
from .app import app # Import the FastAPI app instance

def run_main_server():
    """
    Runs the main FastAPI server using Uvicorn.
    """
    log_config = uvicorn.config.LOGGING_CONFIG.copy()
    log_config["formatters"]["access"]["fmt"] = '%(asctime)s %(levelname)s %(client_addr)s - "[MAIN_SERVER] %(request_line)s" %(status_code)s'
    log_config["formatters"]["default"]["fmt"] = '%(asctime)s %(levelname)s [%(name)s] [MAIN_SERVER] %(message)s'
    
    print(f"[{datetime.datetime.now()}] [MainServer_Service] Attempting to start Main Server on host 0.0.0.0, port {APP_SERVER_PORT}...")
    
    uvicorn.run(
        app, # Use the imported app instance directly
        host="0.0.0.0",
        port=APP_SERVER_PORT,
        lifespan="on", # Ensure lifespan events are handled
        reload=IS_DEV_ENVIRONMENT, # Enable reload in dev mode
        workers=1, # Typically 1 worker for dev, adjust for prod if needed (behind a reverse proxy)
        log_config=log_config
    )

if __name__ == "__main__":
    # This allows running the server directly using: python -m server.main.service
    # Ensure your PYTHONPATH is set up correctly if you run this way,
    # or run from the 'src' directory as: python -m server.main.service
    run_main_server()