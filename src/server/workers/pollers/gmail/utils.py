# src/server/workers/pollers/gmail/utils.py
import os
import datetime
import json
import asyncio
import base64 # For AES
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# Google imports (will need to be installed in poller's env)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build, Resource # Added Resource
from googleapiclient.errors import HttpError

from kafka import KafkaProducer
from kafka.errors import KafkaError

from .config import (
    KAFKA_BOOTSTRAP_SERVERS, GMAIL_POLL_KAFKA_TOPIC,
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_PROJECT_ID, GOOGLE_TOKEN_STORAGE_DIR_POLLER,
    AES_SECRET_KEY, AES_IV, POLLING_INTERVALS_WORKER
)
from .db_utils import PollerMongoManager

# --- Kafka Producer Utility (Replicated) ---
class GmailKafkaProducer:
    _producer: Optional[KafkaProducer] = None
    _lock = asyncio.Lock()

    @staticmethod
    async def get_producer() -> Optional[KafkaProducer]:
        async with GmailKafkaProducer._lock:
            if GmailKafkaProducer._producer is None:
                print(f"[{datetime.datetime.now()}] [GmailPoller_Kafka] Initializing Kafka Producer for {KAFKA_BOOTSTRAP_SERVERS}...")
                try:
                    loop = asyncio.get_event_loop()
                    GmailKafkaProducer._producer = await loop.run_in_executor(
                        None, lambda: KafkaProducer(
                            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                            key_serializer=lambda k: k.encode('utf-8') if k else None,
                            retries=3, acks='all'
                        ))
                    print(f"[{datetime.datetime.now()}] [GmailPoller_Kafka] Kafka Producer initialized.")
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] [GmailPoller_Kafka_ERROR] Failed to init Kafka Producer: {e}")
                    GmailKafkaProducer._producer = None
        return GmailKafkaProducer._producer

    @staticmethod
    async def send_gmail_data(data_payload: dict, user_id: str):
        producer = await GmailKafkaProducer.get_producer()
        if not producer:
            print(f"[{datetime.datetime.now()}] [GmailPoller_Kafka_ERROR] Producer not available. Cannot send Gmail data for user {user_id}.")
            return False
        try:
            loop = asyncio.get_event_loop()
            future = producer.send(GMAIL_POLL_KAFKA_TOPIC, value=data_payload, key=user_id)
            await loop.run_in_executor(None, future.get, 30) # Wait for send
            # print(f"[{datetime.datetime.now()}] [GmailPoller_Kafka] Sent data to {GMAIL_POLL_KAFKA_TOPIC} for user {user_id}")
            return True
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [GmailPoller_Kafka_ERROR] Failed to send to Kafka for user {user_id}: {e}")
            return False
    
    @staticmethod
    async def close_producer():
        async with GmailKafkaProducer._lock:
            if GmailKafkaProducer._producer:
                print(f"[{datetime.datetime.now()}] [GmailPoller_Kafka] Closing Kafka Producer...")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, GmailKafkaProducer._producer.flush)
                await loop.run_in_executor(None, GmailKafkaProducer._producer.close)
                GmailKafkaProducer._producer = None
                print(f"[{datetime.datetime.now()}] [GmailPoller_Kafka] Kafka Producer closed.")

# --- AES Decryption Utility (Replicated) ---
def aes_decrypt_for_poller(encrypted_data_b64: str) -> str:
    if not AES_SECRET_KEY or not AES_IV:
        print(f"[{datetime.datetime.now()}] [GmailPoller_AES_ERROR] AES keys not configured for poller.")
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
        print(f"[{datetime.datetime.now()}] [GmailPoller_AES_ERROR] Decryption failed: {str(e)}")
        raise ValueError(f"Decryption failed: {str(e)}")


# --- Gmail API Utilities ---
SCOPES_GMAIL = ["https://www.googleapis.com/auth/gmail.readonly"]

async def get_gmail_credentials(user_id: str, db_manager: PollerMongoManager) -> Optional[Credentials]:
    """
    Retrieves stored Google credentials for a user. If they exist and are valid or refreshable,
    returns them. Otherwise, indicates that re-authentication is needed (handled by main server).
    """
    token_path = os.path.join(GOOGLE_TOKEN_STORAGE_DIR_POLLER, f"token_gmail_{user_id}.pickle")
    
    user_profile = await db_manager.get_user_profile(user_id)
    if not user_profile or "userData" not in user_profile:
        print(f"[{datetime.datetime.now()}] [GmailPoller_Auth] No user profile found for {user_id} to get Google token.")
        return None

    encrypted_refresh_token = user_profile["userData"].get("encrypted_google_refresh_token")
    
    creds = None
    # Try loading from pickle file first (if poller manages its own tokens)
    if os.path.exists(token_path):
        try:
            with open(token_path, "rb") as token_file:
                creds = pickle.load(token_file)
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [GmailPoller_Auth_ERROR] Error loading token from pickle for {user_id}: {e}")
            creds = None # Proceed to try refresh token from DB

    # If pickle load failed or token invalid, try using refresh token from DB
    if not creds or not creds.valid:
        if encrypted_refresh_token:
            try:
                decrypted_refresh_token = aes_decrypt_for_poller(encrypted_refresh_token)
                creds_data = {
                    "token": None, # Access token will be fetched by refresh
                    "refresh_token": decrypted_refresh_token,
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "scopes": SCOPES_GMAIL
                }
                creds = Credentials.from_authorized_user_info(creds_data)
            except Exception as e:
                print(f"[{datetime.datetime.now()}] [GmailPoller_Auth_ERROR] Failed to construct creds from DB refresh token for {user_id}: {e}")
                return None # Cannot proceed without valid refresh token
        else: # No pickle and no refresh token in DB
            print(f"[{datetime.datetime.now()}] [GmailPoller_Auth] No stored token or refresh token in DB for user {user_id}.")
            return None

    # If credentials exist (either from pickle or DB refresh token), try to refresh if expired
    if creds and creds.expired and creds.refresh_token:
        print(f"[{datetime.datetime.now()}] [GmailPoller_Auth] Google token for {user_id} expired, attempting refresh.")
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, creds.refresh, GoogleAuthRequest())
            # Save refreshed token (important if poller manages its own token file)
            with open(token_path, "wb") as token_file:
                pickle.dump(creds, token_file)
            print(f"[{datetime.datetime.now()}] [GmailPoller_Auth] Google token refreshed and saved for {user_id}.")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] [GmailPoller_Auth_ERROR] Failed to refresh Google token for {user_id}: {e}. User may need to re-auth.")
            return None # Refresh failed
    
    if creds and creds.valid:
        return creds
    
    print(f"[{datetime.datetime.now()}] [GmailPoller_Auth] No valid Google credentials for user {user_id}.")
    return None


async def fetch_emails(creds: Credentials, last_processed_timestamp_unix: Optional[int] = None, max_results: int = 10) -> List[Dict]:
    """Fetches new emails since the last processed timestamp."""
    try:
        loop = asyncio.get_event_loop()
        service = await loop.run_in_executor(None, lambda: build('gmail', 'v1', credentials=creds))
        
        query = 'is:unread'
        if last_processed_timestamp_unix:
            # Gmail API requires 'after' in seconds since epoch
            query += f' after:{last_processed_timestamp_unix}'
            
        # print(f"[{datetime.datetime.now()}] [GmailPoller_Fetch] Querying Gmail with: '{query}'")

        # List messages
        results = await loop.run_in_executor(None, 
            lambda: service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        )
        messages_info = results.get('messages', [])
        
        emails_data = []
        if not messages_info:
            # print(f"[{datetime.datetime.now()}] [GmailPoller_Fetch] No new messages found with query: '{query}'.")
            return []

        print(f"[{datetime.datetime.now()}] [GmailPoller_Fetch] Found {len(messages_info)} new message(s). Fetching details...")

        for msg_info in messages_info:
            msg_id = msg_info['id']
            # Get full message details
            msg_full = await loop.run_in_executor(None, 
                lambda: service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            )
            
            headers = {h['name']: h['value'] for h in msg_full.get('payload', {}).get('headers', [])}
            email_data = {
                "id": msg_full.get('id'),
                "threadId": msg_full.get('threadId'),
                "snippet": msg_full.get('snippet', ''),
                "timestamp_ms": int(msg_full.get('internalDate', '0')), # internalDate is in ms
                "subject": headers.get('Subject', ''),
                "from": headers.get('From', ''),
                "to": headers.get('To', ''),
                "body": "", # Body needs to be extracted
                "labels": msg_full.get('labelIds', [])
            }

            # Extract body (simplified, can be complex due to multipart messages)
            payload = msg_full.get('payload', {})
            if payload.get('mimeType') == 'text/plain' and payload.get('body', {}).get('data'):
                email_data["body"] = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            elif payload.get('parts'):
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                        email_data["body"] = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
            emails_data.append(email_data)
        
        return emails_data
    except HttpError as error:
        print(f"[{datetime.datetime.now()}] [GmailPoller_Fetch_ERROR] An API error occurred: {error}")
        if error.resp.status == 401 or error.resp.status == 403: # Token invalid or expired
            print(f"[{datetime.datetime.now()}] [GmailPoller_Fetch_ERROR] Gmail token error. User may need to re-authenticate.")
            # Signal to main poller loop to handle token refresh or disable polling for user.
            raise error # Re-raise to be caught by the main polling loop for this user
        return [] # Other errors
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [GmailPoller_Fetch_ERROR] Unexpected error fetching emails: {e}")
        return []