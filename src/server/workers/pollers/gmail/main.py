# src/server/workers/pollers/gmail/main.py
import asyncio
import signal
import datetime
import os

# Import from local modules
from .config import MONGO_URI, MONGO_DB_NAME # To ensure config is loaded
from .db import PollerMongoManager
from .service import GmailPollingService
from .utils import GmailKafkaProducer # For graceful shutdown

# Global flag to handle shutdown
shutdown_requested = False

def handle_signal(signum, frame):
    global shutdown_requested
    print(f"[{datetime.datetime.now()}] [GmailPoller_Main] Received signal {signum}. Requesting shutdown...")
    shutdown_requested = True

async def main():
    print(f"[{datetime.datetime.now()}] [GmailPoller_Main] Starting Gmail Polling Worker Script...")
    
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
                print(f"[{datetime.datetime.now()}] [GmailPoller_Main_ERROR] Scheduler task ended unexpectedly.")
                try:
                    scheduler_task.result() # To raise exception if any
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] [GmailPoller_Main_ERROR] Scheduler task exception: {e}")
                break # Exit main loop if scheduler crashes
            await asyncio.sleep(1) # Check for shutdown every second

    except asyncio.CancelledError:
        print(f"[{datetime.datetime.now()}] [GmailPoller_Main] Main task cancelled.")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [GmailPoller_Main_ERROR] An error occurred in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"[{datetime.datetime.now()}] [GmailPoller_Main] Shutting down...")
        if scheduler_task and not scheduler_task.done():
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                print(f"[{datetime.datetime.now()}] [GmailPoller_Main] Scheduler task successfully cancelled during shutdown.")
        
        await GmailKafkaProducer.close_producer()
        await db_manager.close()
        print(f"[{datetime.datetime.now()}] [GmailPoller_Main] Gmail Polling Worker Script finished.")

if __name__ == "__main__":
    # This allows running the script directly
    # e.g., python -m server.workers.pollers.gmail.main
    # Ensure PYTHONPATH includes the 'src' directory or run from 'src'
    if os.name == 'nt': # Windows specific for asyncio event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())