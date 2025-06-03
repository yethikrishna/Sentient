from polling_service.polling.base_engine import BasePollingEngine # Relative import
from polling_service.core.db_manager import DBManager # Relative import
from polling_service.core.config import GOOGLE_CLIENT_SECRET_JSON_PATH, GOOGLE_TOKEN_STORAGE_DIR # Import for token path
# Import your actual Gmail API functions and runnables
from server.agents.functions import authenticate_gmail # This will be your real auth
from server.agents.helpers import extract_email_body # Assuming this helper exists
from polling_service.polling.runnables import get_gmail_context_processing_runnable # New runnable

from datetime import datetime, timezone, timedelta
import asyncio
import os
import pickle # For loading Google tokens
from google.auth.transport.requests import Request as GoogleAuthRequest
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from typing import Optional, Any, List, Tuple, Dict

class GmailPollingEngine(BasePollingEngine):
    def __init__(self, user_id: str, db_manager: DBManager):
        super().__init__(user_id, db_manager, "gmail")
        self.gmail_service: Optional[Any] = None
        self.user_email: Optional[str] = None # Will be set during auth or from profile
        # asyncio.create_task(self._initialize_service()) # Defer initialization slightly
        print(f"[GmailEngine] Initialized for user {self.user_id}. Service will be authed on first poll.")

    async def _initialize_service(self):
        if self.gmail_service:
            return True
        
        print(f"[GmailEngine AUTH] Attempting to initialize Gmail service for user {self.user_id}...")
        
        # Get user's email if needed for token path or specific auth
        user_profile_data = await self.db_manager.get_user_profile_data(self.user_id)
        self.user_email = user_profile_data.get("email") if user_profile_data else None
        
        # Construct user-specific token path
        token_path = os.path.join(GOOGLE_TOKEN_STORAGE_DIR, f"token_gmail_{self.user_id}.pickle")
        creds = None
        if os.path.exists(token_path):
            with open(token_path, "rb") as token_file:
                try:
                    creds = pickle.load(token_file)
                except Exception as e:
                    print(f"[GmailEngine AUTH ERROR] Failed to load token for {self.user_id}: {e}")
                    creds = None
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print(f"[GmailEngine AUTH] Refreshing expired token for {self.user_id}...")
                try:
                    creds.refresh(GoogleAuthRequest())
                    with open(token_path, "wb") as token_file:
                        pickle.dump(creds, token_file)
                    print(f"[GmailEngine AUTH] Token refreshed and saved for {self.user_id}.")
                except Exception as e:
                    print(f"[GmailEngine AUTH ERROR] Failed to refresh token for {self.user_id}: {e}. User needs to re-authenticate.")
                    # Here, you might set a flag or notify that re-authentication is needed.
                    # For this sandbox, we'll prevent the service from being set.
                    self.gmail_service = None
                    return False
            else:
                # This part is tricky for a background service. 
                # The initial OAuth flow typically requires user interaction.
                # For a polling service, we assume tokens exist or can be refreshed.
                # If not, the service for this user cannot operate.
                print(f"[GmailEngine AUTH ERROR] No valid credentials for user {self.user_id}. Manual re-authentication required via frontend.")
                # You might want to update polling_state to reflect this (e.g., set a long next_poll_time or an error state)
                # For now, just don't set self.gmail_service
                return False # Indicate service not initialized

        try:
            self.gmail_service = build("gmail", "v1", credentials=creds)
            print(f"[GmailEngine AUTH] Gmail service authenticated for user {self.user_id}")
            return True
        except Exception as e:
            print(f"[GmailEngine AUTH ERROR] Failed to build Gmail service for user {self.user_id}: {e}")
            self.gmail_service = None
            return False

    async def fetch_new_data(self, current_polling_state: Dict[str, Any]) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        if not self.gmail_service:
            initialized = await self._initialize_service()
            if not initialized:
                print(f"[GmailEngine FETCH_ERROR] Gmail service not available for user {self.user_id}. Cannot fetch.")
                # Consider incrementing failure count here before returning
                return None, current_polling_state.get("last_processed_item_marker")


        last_marker = current_polling_state.get("last_processed_item_marker") # This should be historyId
        
        # Gmail API uses historyId for efficient delta syncing.
        # Start with user's full history if no marker.
        # Note: First sync might be large. Consider fetching in pages or limiting initial scope.
        start_history_id = last_marker
        print(f"[GmailEngine FETCH] User {self.user_id}. Current HistoryId: {start_history_id}")

        new_emails_content = []
        new_latest_history_id = start_history_id # Will be updated to the latest historyId from the response

        try:
            loop = asyncio.get_event_loop()
            
            history_response = await loop.run_in_executor(None, 
                lambda: self.gmail_service.users().history().list(
                    userId="me", 
                    startHistoryId=start_history_id,
                    historyTypes=['messageAdded'] # Only interested in new messages
                ).execute()
            )
            
            history_records = history_response.get('history', [])
            # print(f"[GmailEngine FETCH] Found {len(history_records)} history records.")

            message_ids_to_fetch = set()
            for record in history_records:
                if 'messagesAdded' in record:
                    for msg_added in record['messagesAdded']:
                        message_ids_to_fetch.add(msg_added['message']['id'])
            
            if not message_ids_to_fetch:
                print(f"[GmailEngine FETCH] No new messages added for user {self.user_id} since HistoryId {start_history_id}.")
                # Update marker to current historyId even if no messages, to advance it.
                # This ensures next poll starts from this point.
                new_latest_history_id = history_response.get('historyId', start_history_id)
                return [], new_latest_history_id

            print(f"[GmailEngine FETCH] Fetching details for {len(message_ids_to_fetch)} new message IDs.")
            for msg_id in message_ids_to_fetch:
                try:
                    email_detail = await loop.run_in_executor(None,
                        lambda: self.gmail_service.users().messages().get(
                            userId="me", id=msg_id, format="full" # Using 'full' for LLM processing
                        ).execute()
                    )
                    if email_detail:
                        new_emails_content.append(email_detail)
                except Exception as e_detail:
                    print(f"[GmailEngine FETCH ERROR] Failed to fetch details for email ID {msg_id} for user {self.user_id}: {e_detail}")
            
            # The new marker is the historyId from the history.list response
            new_latest_history_id = history_response.get('historyId', new_latest_history_id)
            
            print(f"[GmailEngine FETCH] Fetched {len(new_emails_content)} full emails for {self.user_id}. New HistoryId: {new_latest_history_id}")
            return new_emails_content, new_latest_history_id

        except Exception as e_list:
            print(f"[GmailEngine FETCH ERROR] User {self.user_id}: {e_list}")
            traceback.print_exc()
            return None, last_marker

    async def process_new_data(self, new_emails: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Formats new emails for further LLM processing or direct Kafka push."""
        processed_emails_for_llm = []
        for email in new_emails:
            snippet = email.get("snippet", "N/A")
            headers = {h["name"]: h["value"] for h in email.get("payload", {}).get("headers", [])}
            subject = headers.get("Subject", "No Subject")
            from_ = headers.get("From", "Unknown Sender")
            date_str = headers.get("Date", datetime.now(timezone.utc).isoformat())
            body = extract_email_body(email.get("payload", {})) # Use your helper

            processed_emails_for_llm.append({
                "email_id": email.get("id"),
                "from": from_,
                "subject": subject,
                "snippet": snippet,
                "body": body, # Include full body for LLM
                "received_at_iso": date_str, # Original date string for reference
                "internal_date_ms": email.get("internalDate")
            })
        print(f"[GmailEngine PROCESS] Processed {len(processed_emails_for_llm)} emails for LLM/Kafka for user {self.user_id}")
        return processed_emails_for_llm

    async def get_llm_runnable_for_processing(self) -> Any:
        """Returns the LLM runnable for processing Gmail content."""
        return get_gmail_context_processing_runnable() # From polling.runnables