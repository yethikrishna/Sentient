# src/server/queues/context-operations/service.py
import asyncio
import datetime
import traceback

from .utils import ContextKafkaConsumer
from .db_utils import ContextQueueMongoManager

class ContextOperationsService:
    def __init__(self, db_manager: ContextQueueMongoManager):
        self.db_manager = db_manager
        print(f"[{datetime.datetime.now()}] [ContextQueue_Service] Initialized.")

    async def process_kafka_message(self, message_payload: dict):
        """
        Processes a single message received from Kafka.
        For this workflow: stores in MongoDB and prints to terminal.
        """
        try:
            user_id = message_payload.get("value", {}).get("user_id")
            service_name = message_payload.get("value", {}).get("service_name")
            event_id = message_payload.get("value", {}).get("event_id")
            data = message_payload.get("value", {}).get("data")
            
            print(f"--- Kafka Message Received ({message_payload.get('topic')}) ---")
            print(f"  User ID: {user_id}")
            print(f"  Service: {service_name}")
            print(f"  Event ID: {event_id}")
            print(f"  Data: {json.dumps(data, indent=2, default=str)[:500]}...") # Print snippet of data
            print(f"----------------------------------------------------")

            # Log the consumed message (optional, but good for tracking)
            await self.db_manager.log_consumed_message(message_payload)

            # Store/process the actual data (e.g., email content)
            if user_id and service_name and event_id and data:
                # Example: store the raw data or extracted context into a specific collection
                # This part depends heavily on how you want to use the context.
                # For now, let's assume a generic context storage.
                await self.db_manager.store_user_context_data(user_id, service_name, event_id, data)
            else:
                print(f"[{datetime.datetime.now()}] [ContextQueue_Service_WARN] Message missing key fields, cannot fully process: {message_payload.get('key')}")

        except Exception as e:
            print(f"[{datetime.datetime.now()}] [ContextQueue_Service_ERROR] Processing Kafka message: {e}")
            traceback.print_exc()

    async def run_consumer_loop(self):
        print(f"[{datetime.datetime.now()}] [ContextQueue_Service] Starting Kafka consumer loop...")
        await self.db_manager.initialize_indices_if_needed()
        
        consumer = await ContextKafkaConsumer.get_consumer()
        if not consumer:
            print(f"[{datetime.datetime.now()}] [ContextQueue_Service_ERROR] Kafka consumer not available. Exiting loop.")
            return

        try:
            async for message in ContextKafkaConsumer.consume_messages():
                if message: # Ensure message is not None (e.g., if generator yields None on error)
                    await self.process_kafka_message(message)
        except asyncio.CancelledError:
            print(f"[{datetime.datetime.now()}] [ContextQueue_Service] Consumer loop cancelled.")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [ContextQueue_Service_ERROR] Critical error in consumer loop: {e}")
            traceback.print_exc()
        finally:
            print(f"[{datetime.datetime.now()}] [ContextQueue_Service] Consumer loop finished or terminated.")
            # Consumer stop is handled in main.py's finally block