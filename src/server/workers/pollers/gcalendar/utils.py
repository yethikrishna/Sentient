import os
import datetime
import json
import asyncio
import base64
from datetime import timezone
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

from kafka import KafkaProducer
from kafka.errors import KafkaError

from .config import KAFKA_BOOTSTRAP_SERVERS, GCALENDAR_POLL_KAFKA_TOPIC, AES_SECRET_KEY, AES_IV
from .db import PollerMongoManager
from typing import Optional, List, Dict, Tuple

class GCalendarKafkaProducer:
    _producer: Optional[KafkaProducer] = None
    _lock = asyncio.Lock()

    @staticmethod
    async def get_producer() -> Optional[KafkaProducer]:
        async with GCalendarKafkaProducer._lock:
            if GCalendarKafkaProducer._producer is None:
                print(f"[{datetime.datetime.now()}] [GCalendarPoller_Kafka] Initializing Kafka Producer...")
                try:
                    loop = asyncio.get_event_loop()
                    GCalendarKafkaProducer._producer = await loop.run_in_executor(
                        None, lambda: KafkaProducer(
                            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                            key_serializer=lambda k: k.encode('utf-8') if k else None,
                            retries=3, acks='all'
                        ))
                    print(f"[{datetime.datetime.now()}] [GCalendarPoller_Kafka] Kafka Producer initialized.")
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] [GCalendarPoller_Kafka_ERROR] Failed to init Kafka Producer: {e}")
                    GCalendarKafkaProducer._producer = None
        return GCalendarKafkaProducer._producer

    @staticmethod
    async def send_gcalendar_data(data_payload: dict, user_id: str):
        producer = await GCalendarKafkaProducer.get_producer()
        if not producer:
            print(f"[{datetime.datetime.now()}] [GCalendarPoller_Kafka_ERROR] Producer not available for user {user_id}.")
            return False
        try:
            loop = asyncio.get_event_loop()
            future = producer.send(GCALENDAR_POLL_KAFKA_TOPIC, value=data_payload, key=user_id)
            await loop.run_in_executor(None, future.get, 30)
            return True
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [GCalendarPoller_Kafka_ERROR] Failed to send to Kafka for user {user_id}: {e}")
            return False
    
    @staticmethod
    async def close_producer():
        async with GCalendarKafkaProducer._lock:
            if GCalendarKafkaProducer._producer:
                print(f"[{datetime.datetime.now()}] [GCalendarPoller_Kafka] Closing Kafka Producer...")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, GCalendarKafkaProducer._producer.flush)
                await loop.run_in_executor(None, GCalendarKafkaProducer._producer.close)
                GCalendarKafkaProducer._producer = None
                print(f"[{datetime.datetime.now()}] [GCalendarPoller_Kafka] Kafka Producer closed.")

def aes_decrypt(encrypted_data_b64: str) -> str:
    if not AES_SECRET_KEY or not AES_IV:
        print(f"[{datetime.datetime.now()}] [GCalendarPoller_AES_ERROR] AES keys not configured.")
        raise ValueError("AES encryption keys not configured in poller.")
    try:
        backend = default_backend()
        cipher = Cipher(algorithms.AES(AES_SECRET_KEY), modes.CBC(AES_IV), backend=backend)
        decryptor = cipher.decryptor()
        encrypted_bytes = base64.b64decode(encrypted_data_b64)
        decrypted_padded = decryptor.update(encrypted_bytes) + decryptor.finalize()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        unpadded_data = unpadder.update(decrypted_padded) + unpadder.finalize()
        return unpadded_data.decode('utf-8')
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [GCalendarPoller_AES_ERROR] Decryption failed: {str(e)}")
        raise ValueError(f"Decryption failed: {str(e)}")

async def get_gcalendar_credentials(user_id: str, db_manager: PollerMongoManager) -> Optional[Credentials]:
    user_profile = await db_manager.get_user_profile(user_id)
    if not user_profile or "userData" not in user_profile:
        return None

    gcal_data = user_profile.get("userData", {}).get("integrations", {}).get("gcalendar")
    if not gcal_data or not gcal_data.get("connected") or "credentials" not in gcal_data:
        return None
    
    try:
        decrypted_creds_str = aes_decrypt(gcal_data["credentials"])
        token_info = json.loads(decrypted_creds_str)
        creds = Credentials.from_authorized_user_info(token_info)

        if creds.expired and creds.refresh_token:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, creds.refresh, GoogleAuthRequest())
            
            refreshed_token_info = json.loads(creds.to_json())
            encrypted_refreshed_creds = aes_encrypt(json.dumps(refreshed_token_info))
            await db_manager.user_profiles_collection.update_one(
                {"user_id": user_id},
                {"$set": {"userData.integrations.gcalendar.credentials": encrypted_refreshed_creds}}
            )
        
        return creds if creds.valid else None
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [GCalendarPoller_Auth_ERROR] Failed to get credentials for {user_id}: {e}")
        return None

async def fetch_events(creds: Credentials, last_updated_iso: Optional[str] = None, max_results: int = 50) -> Tuple[List[Dict], str]:
    try:
        loop = asyncio.get_event_loop()
        service = await loop.run_in_executor(None, lambda: build('calendar', 'v3', credentials=creds))
        
        now = datetime.datetime.now(timezone.utc)
        
        list_params = {
            'calendarId': 'primary',
            'maxResults': max_results,
            'singleEvents': True,
            'orderBy': 'updated',
            'showDeleted': True # Important to capture cancellations
        }
        if last_updated_iso:
            list_params['updatedMin'] = last_updated_iso

        results = await loop.run_in_executor(None, 
            lambda: service.events().list(**list_params).execute()
        )
        events_data = results.get('items', [])
        
        # The new "last updated" time is now, to ensure we don't miss anything between polls.
        new_last_updated_iso = now.isoformat()

        if not events_data:
            return [], new_last_updated_iso

        print(f"[{datetime.datetime.now()}] [GCalendarPoller_Fetch] Found {len(events_data)} updated events.")
        
        return events_data, new_last_updated_iso
        
    except HttpError as error:
        print(f"[{datetime.datetime.now()}] [GCalendarPoller_Fetch_ERROR] An API error occurred: {error}")
        raise error
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [GCalendarPoller_Fetch_ERROR] Unexpected error fetching events: {e}")
        return [], datetime.datetime.now(timezone.utc).isoformat()