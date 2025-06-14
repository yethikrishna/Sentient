import asyncio
import signal
import datetime
import os
import logging

from .config import MONGO_URI, MONGO_DB_NAME
from .db import PollerMongoManager
from .service import GCalendarPollingService
from .utils import GCalendarKafkaProducer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

shutdown_requested = False

def handle_signal(signum, frame):
    global shutdown_requested
    logger.info(f"Received signal {signum}. Requesting GCalendar Poller shutdown...")
    shutdown_requested = True

async def main():
    logger.info("Starting Google Calendar Polling Worker Script...")
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    db_manager = PollerMongoManager()
    polling_service = GCalendarPollingService(db_manager)
    
    scheduler_task = None
    try:
        await GCalendarKafkaProducer.get_producer()
        scheduler_task = asyncio.create_task(polling_service.run_scheduler_loop())
        
        while not shutdown_requested:
            if scheduler_task and scheduler_task.done():
                logger.error("GCalendar scheduler task ended unexpectedly.")
                try:
                    scheduler_task.result()
                except Exception as e:
                    logger.error(f"GCalendar scheduler task exception: {e}", exc_info=True)
                break
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("GCalendar main task cancelled.")
    except Exception as e:
        logger.error(f"An error occurred in GCalendar poller main: {e}", exc_info=True)
    finally:
        logger.info("Shutting down GCalendar poller...")
        if scheduler_task and not scheduler_task.done():
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                logger.info("GCalendar scheduler task successfully cancelled during shutdown.")
        
        await GCalendarKafkaProducer.close_producer()
        await db_manager.close()
        logger.info("Google Calendar Polling Worker Script finished.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())