from kafka import KafkaProducer
import json
import os
import asyncio
import datetime # For logging timestamp

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')

class KafkaProducerManager:
    _producer = None
    _lock = asyncio.Lock() # To ensure producer is initialized only once

    @staticmethod
    async def get_producer():
        async with KafkaProducerManager._lock:
            if KafkaProducerManager._producer is None:
                print(f"[{datetime.datetime.now()}] [KafkaProducerManager] Initializing Kafka Producer for servers: {KAFKA_BOOTSTRAP_SERVERS}...")
                try:
                    # For kafka-python, the producer initialization is synchronous.
                    # If using an async library like aiokafka, the init would be `await`.
                    KafkaProducerManager._producer = KafkaProducer(
                        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                        # Basic error handling and retry configurations:
                        retries=3,  # Retry sending a message up to 3 times
                        acks='all', # Wait for all in-sync replicas to acknowledge
                        # request_timeout_ms=30000, # Timeout for broker acknowledgement
                    )
                    print(f"[{datetime.datetime.now()}] [KafkaProducerManager] Kafka Producer initialized successfully.")
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] [KafkaProducerManager_ERROR] Failed to initialize Kafka Producer: {e}")
                    KafkaProducerManager._producer = None # Ensure it remains None on failure
        return KafkaProducerManager._producer

    @staticmethod
    async def send_message(topic: str, message_dict: dict, key: Optional[str] = None):
        producer = await KafkaProducerManager.get_producer()
        if not producer:
            print(f"[{datetime.datetime.now()}] [KafkaProducerManager_ERROR] Cannot send message to topic '{topic}', producer not available.")
            return False
        
        try:
            # kafka-python's send is asynchronous but returns a Future.
            # We use run_in_executor to make it awaitable in an asyncio context.
            loop = asyncio.get_event_loop()
            future = producer.send(topic, value=message_dict, key=key.encode('utf-8') if key else None)
            
            # Wait for the send to complete (or timeout)
            # The Future's get() method blocks until the message is acknowledged or an error occurs.
            await loop.run_in_executor(None, future.get, 30) # Timeout after 30 seconds for acknowledgement
            
            # print(f"[{datetime.datetime.now()}] [KafkaProducerManager] Message sent to topic '{topic}'. Key: {key}, Payload: {str(message_dict)[:150]}...")
            return True
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [KafkaProducerManager_ERROR] Failed to send message to Kafka topic '{topic}': {e}")
            return False

    @staticmethod
    async def close_producer():
        async with KafkaProducerManager._lock:
            if KafkaProducerManager._producer:
                print(f"[{datetime.datetime.now()}] [KafkaProducerManager] Closing Kafka Producer...")
                try:
                    # kafka-python's close is synchronous
                    KafkaProducerManager._producer.flush(timeout=10) # Attempt to send any buffered messages
                    KafkaProducerManager._producer.close(timeout=10)
                    KafkaProducerManager._producer = None
                    print(f"[{datetime.datetime.now()}] [KafkaProducerManager] Kafka Producer closed.")
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] [KafkaProducerManager_ERROR] Error closing Kafka Producer: {e}")

# Example usage (optional, for testing this module directly)
# async def main():
#     if await KafkaProducerManager.send_message("test_topic", {"hello": "world from producer.py"}):
#         print("Test message sent.")
#     else:
#         print("Failed to send test message.")
#     await KafkaProducerManager.close_producer()

# if __name__ == "__main__":
#     asyncio.run(main())