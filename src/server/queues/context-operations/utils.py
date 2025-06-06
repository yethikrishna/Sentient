# src/server/queues/context-operations/utils.py
import json
import asyncio
import datetime
from kafka.consumer.fetcher import ConsumerRecord # For type hinting Kafka messages
from aiokafka import AIOKafkaConsumer # Using aiokafka for async consumption
from typing import Optional, AsyncGenerator, Dict

from .config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_CONSUMER_GROUP_ID, KAFKA_CONSUME_TOPIC

class ContextKafkaConsumer:
    _consumer: Optional[AIOKafkaConsumer] = None
    _lock = asyncio.Lock()

    @staticmethod
    async def get_consumer() -> Optional[AIOKafkaConsumer]:
        async with ContextKafkaConsumer._lock:
            if ContextKafkaConsumer._consumer is None:
                print(f"[{datetime.datetime.now()}] [ContextQueue_Kafka] Initializing Kafka Consumer for {KAFKA_BOOTSTRAP_SERVERS}...")
                try:
                    loop = asyncio.get_event_loop()
                    ContextKafkaConsumer._consumer = AIOKafkaConsumer(
                        KAFKA_CONSUME_TOPIC,
                        loop=loop,
                        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                        group_id=KAFKA_CONSUMER_GROUP_ID,
                        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                        key_deserializer=lambda k: k.decode('utf-8') if k else None,
                        auto_offset_reset='earliest', # Or 'latest'
                        enable_auto_commit=True, # Auto commit offsets
                        auto_commit_interval_ms=5000 # Commit every 5 seconds
                    )
                    await ContextKafkaConsumer._consumer.start()
                    print(f"[{datetime.datetime.now()}] [ContextQueue_Kafka] Kafka Consumer started for topic '{KAFKA_CONSUME_TOPIC}'.")
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] [ContextQueue_Kafka_ERROR] Failed to init Kafka Consumer: {e}")
                    ContextKafkaConsumer._consumer = None
        return ContextKafkaConsumer._consumer

    @staticmethod
    async def consume_messages() -> AsyncGenerator[Dict, None]:
        consumer = await ContextKafkaConsumer.get_consumer()
        if not consumer:
            print(f"[{datetime.datetime.now()}] [ContextQueue_Kafka_ERROR] Consumer not available. Cannot consume messages.")
            return

        try:
            async for msg in consumer:
                # print(f"Consumed msg: offset={msg.offset}, key={msg.key}, value={msg.value}, topic={msg.topic}, partition={msg.partition}")
                yield {
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                    "key": msg.key,
                    "value": msg.value # This is already deserialized by AIOKafkaConsumer
                }
        except asyncio.CancelledError:
            print(f"[{datetime.datetime.now()}] [ContextQueue_Kafka] Consume messages task cancelled.")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [ContextQueue_Kafka_ERROR] Error during message consumption: {e}")
        # `finally` block for consumer.stop() is in the main service script

    @staticmethod
    async def close_consumer():
        async with ContextKafkaConsumer._lock:
            if ContextKafkaConsumer._consumer:
                print(f"[{datetime.datetime.now()}] [ContextQueue_Kafka] Stopping Kafka Consumer...")
                try:
                    await ContextKafkaConsumer._consumer.stop()
                    ContextKafkaConsumer._consumer = None
                    print(f"[{datetime.datetime.now()}] [ContextQueue_Kafka] Kafka Consumer stopped.")
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] [ContextQueue_Kafka_ERROR] Error stopping Kafka Consumer: {e}")