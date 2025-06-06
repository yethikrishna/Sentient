# src/server/queues/context-operations/main.py
import asyncio
import signal
import datetime
import os

from .config import KAFKA_BOOTSTRAP_SERVERS # To ensure config is loaded
from .db_utils import ContextQueueMongoManager
from .service import ContextOperationsService
from .utils import ContextKafkaConsumer # For graceful shutdown

shutdown_requested = False

def handle_signal(signum, frame):
    global shutdown_requested
    print(f"[{datetime.datetime.now()}] [ContextQueue_Main] Received signal {signum}. Requesting shutdown...")
    shutdown_requested = True

async def main():
    print(f"[{datetime.datetime.now()}] [ContextQueue_Main] Starting Context Operations Queue Worker Script...")
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    db_manager = ContextQueueMongoManager()
    context_service = ContextOperationsService(db_manager)
    
    consumer_loop_task = None
    try:
        # Consumer starts itself via get_consumer -> start()
        consumer_loop_task = asyncio.create_task(context_service.run_consumer_loop())
        
        while not shutdown_requested:
            if consumer_loop_task and consumer_loop_task.done():
                print(f"[{datetime.datetime.now()}] [ContextQueue_Main_ERROR] Consumer loop task ended unexpectedly.")
                try:
                    consumer_loop_task.result()
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] [ContextQueue_Main_ERROR] Consumer loop task exception: {e}")
                break 
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        print(f"[{datetime.datetime.now()}] [ContextQueue_Main] Main task cancelled.")
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [ContextQueue_Main_ERROR] An error occurred in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"[{datetime.datetime.now()}] [ContextQueue_Main] Shutting down...")
        if consumer_loop_task and not consumer_loop_task.done():
            consumer_loop_task.cancel()
            try:
                await consumer_loop_task
            except asyncio.CancelledError:
                print(f"[{datetime.datetime.now()}] [ContextQueue_Main] Consumer loop task successfully cancelled.")
        
        await ContextKafkaConsumer.close_consumer()
        await db_manager.close()
        print(f"[{datetime.datetime.now()}] [ContextQueue_Main] Context Operations Queue Worker Script finished.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())