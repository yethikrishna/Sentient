import datetime
import json
import base64

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from workers.utils.crypto import aes_decrypt, aes_encrypt
from workers.poller.gmail.db import PollerMongoManager
from typing import Optional, List, Dict

async def get_gmail_credentials(user_id: str, db_manager: PollerMongoManager) -> Optional[Credentials]:
    import asyncio
    import json
    user_profile = await db_manager.get_user_profile(user_id)
    if not user_profile or "userData" not in user_profile:
        print(f"[{datetime.datetime.now()}] [GmailPoller_Auth] No user profile found for {user_id} to get Google token.")
        return None

    gmail_data = user_profile.get("userData", {}).get("integrations", {}).get("gmail")

    if not gmail_data or not gmail_data.get("connected") or "credentials" not in gmail_data:
        print(f"[{datetime.datetime.now()}] [GmailPoller_Auth] Gmail not connected or credentials missing for {user_id}.")
        return None
    
    try:
        decrypted_creds_str = aes_decrypt(gmail_data["credentials"])
        token_info = json.loads(decrypted_creds_str)
        creds = Credentials.from_authorized_user_info(token_info)

        if creds.expired and creds.refresh_token:
            print(f"[{datetime.datetime.now()}] [GmailPoller_Auth] Gmail token for {user_id} expired, attempting refresh.")
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, creds.refresh, GoogleAuthRequest())
                
                refreshed_token_info = json.loads(creds.to_json())
                encrypted_refreshed_creds = aes_encrypt(json.dumps(refreshed_token_info))
                await db_manager.user_profiles_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"userData.integrations.gmail.credentials": encrypted_refreshed_creds}}
                )
                print(f"[{datetime.datetime.now()}] [GmailPoller_Auth] Gmail token refreshed and saved for {user_id}.")
            except Exception as e:
                print(f"[{datetime.datetime.now()}] [GmailPoller_Auth_ERROR] Failed to refresh Google token for {user_id}: {e}. User may need to re-auth.")
                return None
        
        if creds.valid:
            return creds
        
        print(f"[{datetime.datetime.now()}] [GmailPoller_Auth] No valid Google credentials for user {user_id}.")
        return None
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [GmailPoller_Auth_ERROR] Failed to get credentials for {user_id}: {e}")
        return None

async def fetch_emails(creds: Credentials, last_processed_timestamp_unix: Optional[int] = None, max_results: int = 10) -> List[Dict]: # noqa
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        service = await loop.run_in_executor(None, lambda: build('gmail', 'v1', credentials=creds))
        
        query = 'is:unread'
        if last_processed_timestamp_unix:
            query += f' after:{last_processed_timestamp_unix}'
        else:
            # For the first run, only look at the last 2 weeks to avoid a huge backlog.
            query += ' newer_than:14d'
            
        results = await loop.run_in_executor(None, 
            lambda: service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        )
        messages_info = results.get('messages', [])
        
        emails_data = []
        if not messages_info:
            return []

        print(f"[{datetime.datetime.now()}] [GmailPoller_Fetch] Found {len(messages_info)} new message(s). Fetching details...")

        for msg_info in messages_info:
            msg_id = msg_info['id']
            msg_full = await loop.run_in_executor(None, 
                lambda: service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            )
            
            headers = {h['name']: h['value'] for h in msg_full.get('payload', {}).get('headers', [])}
            email_data = {
                "id": msg_full.get('id'),
                "threadId": msg_full.get('threadId'),
                "snippet": msg_full.get('snippet', ''),
                "timestamp_ms": int(msg_full.get('internalDate', '0')),
                "subject": headers.get('Subject', ''),
                "from": headers.get('From', ''),
                "to": headers.get('To', ''),
                "body": "",
                "labels": msg_full.get('labelIds', [])
            }

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
        if error.resp.status in [401, 403]:
            print(f"[{datetime.datetime.now()}] [GmailPoller_Fetch_ERROR] Gmail token error. User may need to re-authenticate.")
            raise error
        return []
    except Exception as e:
        print(f"[{datetime.datetime.now()}] [GmailPoller_Fetch_ERROR] Unexpected error fetching emails: {e}")
        return []