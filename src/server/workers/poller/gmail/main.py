# src/server/workers/pollers/gmail/main.py
import asyncio
import signal
import datetime
import os
import logging # Add logging

# Import from local modules
from .config import MONGO_URI, MONGO_DB_NAME # To ensure config is loaded
from .db import PollerMongoManager
from .service import GmailPollingService
from .utils import GmailKafkaProducer # For graceful shutdown

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global flag to handle shutdown
shutdown_requested = False

def handle_signal(signum, frame):
    global shutdown_requested
    logger.info(f"Received signal {signum}. Requesting shutdown...")
    shutdown_requested = True

async def main():
    logger.info("Starting Gmail Polling Worker Script...")
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    db_manager = PollerMongoManager()
    polling_service = GmailPollingService(db_manager)
    
    scheduler_task = None
    try:
        # Initialize Kafka producer early if desired, or let it init lazily
        await GmailKafkaProducer.get_producer()

        scheduler_task = asyncio.create_task(polling_service.run_scheduler_loop())
        
        while not shutdown_requested:
            # Keep the main coroutine alive, checking for shutdown request
            if scheduler_task and scheduler_task.done():
                logger.error("Scheduler task ended unexpectedly.")
                try:
                    scheduler_task.result() # To raise exception if any
                except Exception as e:
                    logger.error(f"Scheduler task exception: {e}", exc_info=True)
                break # Exit main loop if scheduler crashes
            await asyncio.sleep(1) # Check for shutdown every second

    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    except Exception as e:
        logger.error(f"An error occurred in main: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Shutting down...")
        if scheduler_task and not scheduler_task.done():
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                logger.info("Scheduler task successfully cancelled during shutdown.")
        
        await GmailKafkaProducer.close_producer()
        await db_manager.close()
        logger.info("Gmail Polling Worker Script finished.")

if __name__ == "__main__":
    # This allows running the script directly
    # e.g., python -m server.workers.pollers.gmail.main
    # Ensure PYTHONPATH includes the 'src' directory or run from 'src'
    if os.name == 'nt': # Windows specific for asyncio event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())