# src/server/workers/memory/kafka_clients.py
import json
import asyncio
import logging
from typing import Optional
from aiokafka import AIOKafkaConsumer

from . import config

logger = logging.getLogger(__name__)

class KafkaManager:
    """Manages the Kafka Consumer for the Memory worker."""
    _consumer: Optional[AIOKafkaConsumer] = None
    _lock = asyncio.Lock()

    @staticmethod
    async def get_consumer() -> AIOKafkaConsumer:
        async with KafkaManager._lock:
            if KafkaManager._consumer is None:
                logger.info(f"Initializing Kafka Consumer for group '{config.KAFKA_CONSUMER_GROUP_ID}'...")
                loop = asyncio.get_event_loop()
                KafkaManager._consumer = AIOKafkaConsumer(
                    config.MEMORY_OPERATIONS_TOPIC,
                    loop=loop,
                    bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                    group_id=config.KAFKA_CONSUMER_GROUP_ID,
                    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    session_timeout_ms=30000,
                    request_timeout_ms=40000,
                    retry_backoff_ms=500
                )
                await KafkaManager._consumer.start()
                logger.info("Kafka Consumer for memory operations started.")
            return KafkaManager._consumer

    @staticmethod
    async def close():
        async with KafkaManager._lock:
            if KafkaManager._consumer:
                await KafkaManager._consumer.stop()
                KafkaManager._consumer = None
                logger.info("Kafka Consumer for memory operations stopped.")