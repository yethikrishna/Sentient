from server.context.polling.base import BasePollingEngine
from server.db.mongo_manager import MongoManager 
from server.utils.config import GOOGLE_TOKEN_STORAGE_DIR # Using utils.config for paths
# Assuming gmail_tools.py is in the same directory or accessible via Python path
from server.agents.functions import authenticate_gmail_service # Use your actual Gmail auth function
from server.agents.helpers import extract_email_body # If used for basic processing

import os
import pickle
from datetime import datetime, timezone, timedelta
import asyncio
from typing import Optional, Any, List, Tuple, Dict

# For Google API calls
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build

class GmailPollingEngine(BasePollingEngine):
    def __init__(self, user_id: str, db_manager: MongoManager): # Corrected type hint for db_manager
        super().__init__(user_id, db_manager, "gmail")
        self.gmail_service: Optional[Any] = None
        # User email might be useful for logging or if API calls need it, but not strictly for auth here
        # self.user_email: Optional[str] = None 
        print(f"[{datetime.now()}] [GmailPollingEngine] Initialized for user {self.user_id}. Service will be authed on first poll.")

    async def _initialize_service(self) -> bool:
        """Initializes the Gmail API service for the user."""
        if self.gmail_service:
            return True # Already initialized
        
        print(f"[{datetime.now()}] [GmailPollingEngine AUTH] Attempting to initialize Gmail service for user {self.user_id}...")
        
        # Path to the user's token file
        token_path = os.path.join(GOOGLE_TOKEN_STORAGE_DIR, f"token_gmail_{self.user_id}.pickle")
        creds = None

        if os.path.exists(token_path):
            with open(token_path, "rb") as token_file:
                try:
                    creds = pickle.load(token_file)
                except Exception as e:
                    print(f"[{datetime.now()}] [GmailPollingEngine AUTH_ERROR] Failed to load token for {self.user_id}: {e}")
                    creds = None
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print(f"[{datetime.now()}] [GmailPollingEngine AUTH] Refreshing expired token for {self.user_id}...")
                try:
                    creds.refresh(GoogleAuthRequest()) # Synchronous, might block
                    with open(token_path, "wb") as token_file:
                        pickle.dump(creds, token_file)
                    print(f"[{datetime.now()}] [GmailPollingEngine AUTH] Token refreshed and saved for {self.user_id}.")
                except Exception as e:
                    print(f"[{datetime.now()}] [GmailPollingEngine AUTH_ERROR] Failed to refresh token for {self.user_id}: {e}. User needs to re-authenticate.")
                    self.gmail_service = None
                    return False # Indicate service not initialized
            else:
                print(f"[{datetime.now()}] [GmailPollingEngine AUTH_ERROR] No valid credentials for user {self.user_id}. Manual re-authentication required via frontend.")
                return False 

        try:
            # Build the Gmail service object
            self.gmail_service = build("gmail", "v1", credentials=creds)
            print(f"[{datetime.now()}] [GmailPollingEngine AUTH] Gmail service authenticated successfully for user {self.user_id}")
            return True
        except Exception as e:
            print(f"[{datetime.now()}] [GmailPollingEngine AUTH_ERROR] Failed to build Gmail service for user {self.user_id}: {e}")
            self.gmail_service = None
            return False

    async def fetch_new_data(self, current_polling_state: Dict[str, Any]) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """Fetches new emails since the last poll using Gmail API history."""
        if not self.gmail_service:
            initialized = await self._initialize_service()
            if not initialized:
                print(f"[{datetime.now()}] [GmailEngine FETCH_ERROR] Gmail service not available for user {self.user_id}. Cannot fetch.")
                return None, current_polling_state.get("last_processed_item_marker")

        last_history_id = current_polling_state.get("last_processed_item_marker")
        print(f"[{datetime.now()}] [GmailEngine FETCH] User {self.user_id}. Current HistoryId: {last_history_id}")

        new_emails_data = []
        new_latest_history_id = last_history_id 
        
        try:
            loop = asyncio.get_event_loop()
            
            # Call Gmail API's history.list method
            history_response = await loop.run_in_executor(None, 
                lambda: self.gmail_service.users().history().list(
                    userId="me", 
                    startHistoryId=last_history_id,
                    historyTypes=['messageAdded'] # Only interested in new messages
                ).execute()
            )
            
            history_records = history_response.get('history', [])
            
            message_ids_to_fetch = set()
            for record in history_records:
                if 'messagesAdded' in record:
                    for msg_added in record['messagesAdded']:
                        message_ids_to_fetch.add(msg_added['message']['id'])
            
            if not message_ids_to_fetch:
                print(f"[{datetime.now()}] [GmailEngine FETCH] No new messages added for user {self.user_id} since HistoryId {last_history_id}.")
                new_latest_history_id = history_response.get('historyId', last_history_id)
                return [], new_latest_history_id # Return empty list, but update marker

            print(f"[{datetime.now()}] [GmailEngine FETCH] Fetching details for {len(message_ids_to_fetch)} new message IDs for user {self.user_id}.")
            for msg_id in message_ids_to_fetch:
                try:
                    # Fetch full email detail
                    email_detail = await loop.run_in_executor(None,
                        lambda: self.gmail_service.users().messages().get(
                            userId="me", id=msg_id, format="full" 
                        ).execute()
                    )
                    if email_detail:
                        # Perform basic processing/formatting here
                        processed_email = self._process_single_email(email_detail)
                        new_emails_data.append(processed_email)
                except Exception as e_detail:
                    print(f"[{datetime.now()}] [GmailEngine FETCH_ERROR] Failed to fetch/process details for email ID {msg_id} for user {self.user_id}: {e_detail}")
            
            new_latest_history_id = history_response.get('historyId', new_latest_history_id)
            
            print(f"[{datetime.now()}] [GmailEngine FETCH] Fetched and processed {len(new_emails_data)} emails for {self.user_id}. New HistoryId: {new_latest_history_id}")
            return new_emails_data, new_latest_history_id

        except Exception as e_list:
            print(f"[{datetime.now()}] [GmailEngine FETCH_ERROR] User {self.user_id}: {e_list}")
            traceback.print_exc()
            return None, last_history_id # Return None for data on error, keep old marker

    def _process_single_email(self, email_detail: Dict[str, Any]) -> Dict[str, Any]:
        """Processes a single raw email detail from Gmail API into a simpler format for Kafka."""
        headers = {h["name"].lower(): h["value"] for h in email_detail.get("payload", {}).get("headers", [])}
        
        # Basic information extraction
        return {
            "email_id": email_detail.get("id"),
            "thread_id": email_detail.get("threadId"),
            "history_id": email_detail.get("historyId"),
            "snippet": email_detail.get("snippet", "N/A")[:250], # Limit snippet length
            "from": headers.get("from", "Unknown Sender"),
            "to": headers.get("to"),
            "cc": headers.get("cc"),
            "bcc": headers.get("bcc"),
            "subject": headers.get("subject", "No Subject"),
            "date_iso": headers.get("date"), # This is a string, might need parsing for consistent ISO
            "internal_date_ms": email_detail.get("internalDate"), # Timestamp from Gmail
            "label_ids": email_detail.get("labelIds", []),
            "body_preview": extract_email_body(email_detail.get("payload", {}))[:500] # Limit body preview
            # Add more fields if needed for Kafka consumer, but keep it concise for this example
        }

    # generate_kafka_payload is inherited from BasePollingEngine and should work as is
    # if _process_single_email formats the data sufficiently for the Kafka message.
    # No LLM processing is done here before sending to Kafka.