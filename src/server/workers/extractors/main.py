# src/server/workers/extractor/main.py
import asyncio
import signal
import logging
import os

from .service import ExtractorService
from .kafka_clients import KafkaManager
from .db import ExtractorMongoManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

shutdown_event = asyncio.Event()

def handle_signal(signum, frame):
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    shutdown_event.set()

async def main():
    logger.info("Starting Extractor Worker...")
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    service_task = None
    try:
        db_manager = ExtractorMongoManager()
        await db_manager.initialize_db()

        extractor_service = ExtractorService(db_manager)
        service_task = asyncio.create_task(extractor_service.run(shutdown_event))
        
        await service_task

    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in main: {e}", exc_info=True)
    finally:
        logger.info("Shutting down resources...")
        if service_task and not service_task.done():
            service_task.cancel()
            await asyncio.sleep(1) # Give it a moment to cancel
        
        await KafkaManager.close_all()
        if 'db_manager' in locals() and db_manager:
            await db_manager.close()
        logger.info("Extractor Worker has finished.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())