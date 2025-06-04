# src/server/polling_server/app.py
import time
import datetime
from datetime import timezone
START_TIME = time.time()
print(f"[{datetime.datetime.now()}] [STARTUP] Polling Server application script execution started.")

import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware # Keep for potential internal health checks

from dotenv import load_dotenv
import nest_asyncio
import uvicorn

# --- Core Dependencies ---
from server.common.dependencies import (
    mongo_manager,
    polling_scheduler_loop,  # The core logic of this server
    polling_scheduler_task_handle, # To manage the task
    initialize_kafka_producer_on_startup # Kafka producer
)

print(f"[{datetime.datetime.now()}] [STARTUP] Polling Server: Basic imports completed.")

# --- Environment Loading ---
print(f"[{datetime.datetime.now()}] [STARTUP] Polling Server: Loading environment variables from server/.env...")
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=dotenv_path)
print(f"[{datetime.datetime.now()}] [STARTUP] Polling Server: Environment variables loaded.")

IS_DEV_ENVIRONMENT = os.getenv("IS_DEV_ENVIRONMENT", "false").lower() in ("true", "1", "t", "y")
print(f"[{datetime.datetime.now()}] [STARTUP] Polling Server: IS_DEV_ENVIRONMENT: {IS_DEV_ENVIRONMENT}")

nest_asyncio.apply()
print(f"[{datetime.datetime.now()}] [STARTUP] Polling Server: nest_asyncio applied.")

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global polling_scheduler_task_handle
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [POLLING_SERVER_LIFECYCLE] App startup...")

    # Initialize MongoDB (collections and indexes) if not already done by another service
    # or if this service requires direct specific initializations.
    # For polling, MongoManager needs to be ready for polling_state_store.
    await mongo_manager.initialize_db() 
    
    # Initialize Kafka Producer (used by GmailPollingEngine when sending results)
    await initialize_kafka_producer_on_startup()

    # Start the central polling scheduler loop
    # Ensure polling_scheduler_task_handle is managed correctly for this server instance
    if polling_scheduler_task_handle is None or polling_scheduler_task_handle.done():
        polling_scheduler_task_handle = asyncio.create_task(polling_scheduler_loop())
        print(f"[{datetime.datetime.now()}] [POLLING_SERVER_LIFECYCLE] Central polling scheduler started.")
    else:
        print(f"[{datetime.datetime.now()}] [POLLING_SERVER_LIFECYCLE] Polling scheduler task already running or initiated.")

    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [POLLING_SERVER_LIFECYCLE] App startup complete.")
    yield 

    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [POLLING_SERVER_LIFECYCLE] App shutdown sequence initiated...")
    if polling_scheduler_task_handle and not polling_scheduler_task_handle.done():
        print(f"[{datetime.datetime.now()}] [POLLING_SERVER_LIFECYCLE] Cancelling polling scheduler task...")
        polling_scheduler_task_handle.cancel()
        try:
            await polling_scheduler_task_handle
        except asyncio.CancelledError:
            print(f"[{datetime.datetime.now()}] [POLLING_SERVER_LIFECYCLE] Polling scheduler task successfully cancelled.")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [POLLING_SERVER_LIFECYCLE_ERROR] Error during polling scheduler shutdown: {e}")
    
    # Close Kafka Producer (if this server instance owns it exclusively)
    # await KafkaProducerManager.close_producer() # Usually shared, closed by last service or main

    if mongo_manager and mongo_manager.client:
        mongo_manager.client.close()
        print(f"[{datetime.datetime.now()}] [POLLING_SERVER_LIFECYCLE] MongoManager client closed.")
    
    print(f"[{datetime.datetime.now(timezone.utc).isoformat()}] [POLLING_SERVER_LIFECYCLE] App shutdown complete.")

# --- FastAPI Application Setup ---
print(f"[{datetime.datetime.now()}] [POLLING_SERVER_FASTAPI] Initializing FastAPI app...")
app = FastAPI(
    title="Sentient Polling Server", 
    description="Handles background polling for data sources like Gmail and sends data to Kafka.", 
    version="1.0.0_microservice",
    docs_url=None, # No public docs needed
    redoc_url=None, 
    lifespan=lifespan
)
print(f"[{datetime.datetime.now()}] [POLLING_SERVER_FASTAPI] FastAPI app initialized.")

# Optional: Add CORS if you plan to have an internal dashboard or health check endpoint accessible from other origins
# app.add_middleware(
#     CORSMiddleware, 
#     allow_origins=["http://localhost:YOUR_MAIN_SERVER_PORT_OR_ADMIN_UI"], # Example
#     allow_credentials=True, 
#     allow_methods=["GET"], 
#     allow_headers=["*"]
# )

# --- Root Endpoint (Health Check) ---
@app.get("/health", status_code=status.HTTP_200_OK, summary="Polling Server Health Check", tags=["Health"])
async def polling_server_health():
    scheduler_status = "Not running"
    if polling_scheduler_task_handle:
        if polling_scheduler_task_handle.done():
            try:
                polling_scheduler_task_handle.result() # Check for exceptions if done
                scheduler_status = "Finished (unexpectedly)"
            except asyncio.CancelledError:
                scheduler_status = "Cancelled"
            except Exception as e:
                scheduler_status = f"Crashed: {e}"
        else:
            scheduler_status = "Running"
            
    return {"message": "Sentient Polling Server is running.", "scheduler_status": scheduler_status}

# --- Main Execution Block ---
if __name__ == "__main__":
    # Note: multiprocessing.freeze_support() usually not needed for non-GUI, non-packaged scripts directly.
    
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = '%(asctime)s %(levelname)s %(client_addr)s - "%(request_line)s" %(status_code)s'
    log_config["formatters"]["default"]["fmt"] = '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    
    polling_server_port = int(os.getenv("POLLING_SERVER_PORT", 5001)) # Use a different port
    print(f"[{datetime.datetime.now()}] [UVICORN] Starting Polling Server on host 0.0.0.0, port {polling_server_port}...")
    
    uvicorn.run(
        "server.polling_server.app:app", # Correct path to this app
        host="0.0.0.0",
        port=polling_server_port,
        lifespan="on",
        reload=IS_DEV_ENVIRONMENT,
        workers=1, # Polling is often fine with 1 worker
        log_config=log_config
    )

END_TIME = time.time()
print(f"[{datetime.datetime.now()}] [STARTUP_COMPLETE] Polling Server script execution and Uvicorn setup took {END_TIME - START_TIME:.2f} seconds.")