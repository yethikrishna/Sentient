import asyncio
import signal
import logging
import os

from .service import PlannerService
from .kafka_clients import KafkaManager
from .db import PlannerMongoManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

shutdown_event = asyncio.Event()

def handle_signal(signum, frame):
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    shutdown_event.set()

async def main():
    logger.info("Starting Planner Worker...")
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    service_task = None
    db_manager = None
    try:
        db_manager = PlannerMongoManager()
        
        planner_service = PlannerService(db_manager)
        service_task = asyncio.create_task(planner_service.run(shutdown_event))
        
        await service_task

    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in main: {e}", exc_info=True)
    finally:
        logger.info("Shutting down resources...")
        if service_task and not service_task.done():
            service_task.cancel()
            await asyncio.sleep(1)
        
        await KafkaManager.close()
        if db_manager:
            await db_manager.close()
        logger.info("Planner Worker has finished.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())