import asyncio
import json
from typing import Optional
from aiokafka import AIOKafkaProducer

from . import config

class KafkaTaskProducer:
    _producer: Optional[AIOKafkaProducer] = None
    _lock = asyncio.Lock()

    @staticmethod
    async def get_producer() -> AIOKafkaProducer:
        async with KafkaTaskProducer._lock:
            if KafkaTaskProducer._producer is None:
                loop = asyncio.get_event_loop()
                KafkaTaskProducer._producer = AIOKafkaProducer(
                    loop=loop,
                    bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8')
                )
                await KafkaTaskProducer._producer.start()
        return KafkaTaskProducer._producer

    @staticmethod
    async def close_producer():
        async with KafkaTaskProducer._lock:
            if KafkaTaskProducer._producer:
                await KafkaTaskProducer._producer.stop()
                KafkaTaskProducer._producer = None