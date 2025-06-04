from kafka import KafkaProducer # Using kafka-python
from kafka.errors import KafkaError
import json
import os
import asyncio
import datetime
from typing import Optional

from server.common_lib.utils.config import KAFKA_BOOTSTRAP_SERVERS

class KafkaProducerManager:
    _producer: Optional[KafkaProducer] = None
    _lock = asyncio.Lock() # asyncio.Lock for async context

    @staticmethod
    async def get_producer() -> Optional[KafkaProducer]:
        async with KafkaProducerManager._lock:
            if KafkaProducerManager._producer is None:
                print(f"[{datetime.datetime.now()}] [KafkaProducerManager] Initializing Kafka Producer for servers: {KAFKA_BOOTSTRAP_SERVERS}...")
                try:
                    loop = asyncio.get_event_loop()
                    KafkaProducerManager._producer = await loop.run_in_executor(
                        None, 
                        lambda: KafkaProducer(
                            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'), # Add default=str for datetime
                            key_serializer=lambda k: k.encode('utf-8') if k else None,
                            retries=3,
                            acks='all',
                            api_version=(0, 10, 1) # Common version, adjust if needed
                        )
                    )
                    print(f"[{datetime.datetime.now()}] [KafkaProducerManager] Kafka Producer initialized successfully.")
                except KafkaError as ke:
                    print(f"[{datetime.datetime.now()}] [KafkaProducerManager_ERROR] Kafka-specific error initializing producer: {ke}")
                    KafkaProducerManager._producer = None
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] [KafkaProducerManager_ERROR] Failed to initialize Kafka Producer: {e}")
                    KafkaProducerManager._producer = None
        return KafkaProducerManager._producer

    @staticmethod
    async def send_message(topic: str, message_dict: dict, key: Optional[str] = None) -> bool:
        producer = await KafkaProducerManager.get_producer()
        if not producer:
            print(f"[{datetime.datetime.now()}] [KafkaProducerManager_ERROR] Cannot send message to topic '{topic}', producer not available.")
            return False
        
        try:
            loop = asyncio.get_event_loop()
            # The send method is asynchronous in kafka-python when called from an async context
            # but it returns a Future. We need to await its result or handle it appropriately.
            # For simplicity in an async function, we can run the blocking part in an executor.
            future = producer.send(topic, value=message_dict, key=key)
            # future.get() is blocking, so run it in an executor
            await loop.run_in_executor(None, future.get, 30) # Timeout for acknowledgement
            
            # print(f"[{datetime.datetime.now()}] [KafkaProducerManager] Message sent to topic '{topic}'. Key: {key if key else 'N/A'}")
            return True
        except KafkaError as ke:
            print(f"[{datetime.datetime.now()}] [KafkaProducerManager_ERROR] Kafka-specific error sending message to topic '{topic}': {ke}")
            return False
        except Exception as e: # Includes KafkaTimeoutError
            print(f"[{datetime.datetime.now()}] [KafkaProducerManager_ERROR] Failed to send message to Kafka topic '{topic}': {e}")
            return False

    @staticmethod
    async def close_producer():
        async with KafkaProducerManager._lock:
            if KafkaProducerManager._producer:
                print(f"[{datetime.datetime.now()}] [KafkaProducerManager] Closing Kafka Producer...")
                try:
                    loop = asyncio.get_event_loop()
                    # producer.flush() and producer.close() are blocking
                    await loop.run_in_executor(None, KafkaProducerManager._producer.flush, 10) 
                    await loop.run_in_executor(None, KafkaProducerManager._producer.close, 10)
                    KafkaProducerManager._producer = None
                    print(f"[{datetime.datetime.now()}] [KafkaProducerManager] Kafka Producer closed.")
                except KafkaError as ke:
                    print(f"[{datetime.datetime.now()}] [KafkaProducerManager_ERROR] Kafka-specific error closing producer: {ke}")
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] [KafkaProducerManager_ERROR] Error closing Kafka Producer: {e}")