# src/server/workers/extractor/kafka_clients.py
import json
import asyncio
import logging
from typing import Optional
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from . import config

logger = logging.getLogger(__name__)

class KafkaManager:
    """Manages Kafka Consumer and Producer for the Extractor worker."""
    _consumer: Optional[AIOKafkaConsumer] = None
    _producer: Optional[AIOKafkaProducer] = None
    _lock = asyncio.Lock()

    @staticmethod
    async def get_consumer() -> AIOKafkaConsumer:
        async with KafkaManager._lock:
            if KafkaManager._consumer is None:
                logger.info(f"Initializing Kafka Consumer for group '{config.KAFKA_CONSUMER_GROUP_ID}'...")
                loop = asyncio.get_event_loop()
                KafkaManager._consumer = AIOKafkaConsumer(
                    config.CONTEXT_EVENTS_TOPIC,
                    loop=loop,
                    bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                    group_id=config.KAFKA_CONSUMER_GROUP_ID,
                    value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                )
                await KafkaManager._consumer.start()
                logger.info("Kafka Consumer started.")
            return KafkaManager._consumer

    @staticmethod
    async def get_producer() -> AIOKafkaProducer:
        async with KafkaManager._lock:
            if KafkaManager._producer is None:
                logger.info("Initializing Kafka Producer...")
                loop = asyncio.get_event_loop()
                KafkaManager._producer = AIOKafkaProducer(
                    loop=loop,
                    bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
                await KafkaManager._producer.start()
                logger.info("Kafka Producer started.")
            return KafkaManager._producer

    @staticmethod
    async def produce_memories(user_id: str, memories: list):
        producer = await KafkaManager.get_producer()
        payload = {"user_id": user_id, "memories": memories}
        await producer.send_and_wait(config.MEMORY_OPERATIONS_TOPIC, value=payload)
        logger.info(f"Produced {len(memories)} memory items for user {user_id} to topic '{config.MEMORY_OPERATIONS_TOPIC}'.")

    @staticmethod
    async def produce_actions(user_id: str, actions: list):
        producer = await KafkaManager.get_producer()
        payload = {"user_id": user_id, "actions": actions}
        await producer.send_and_wait(config.ACTION_ITEMS_TOPIC, value=payload)
        logger.info(f"Produced {len(actions)} action items for user {user_id} to topic '{config.ACTION_ITEMS_TOPIC}'.")

    @staticmethod
    async def close_all():
        async with KafkaManager._lock:
            if KafkaManager._consumer:
                await KafkaManager._consumer.stop()
                KafkaManager._consumer = None
                logger.info("Kafka Consumer stopped.")
            if KafkaManager._producer:
                await KafkaManager._producer.stop()
                KafkaManager._producer = None
                logger.info("Kafka Producer stopped.")