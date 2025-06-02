from server.context.base import BaseContextEngine, POLLING_INTERVALS # Import POLLING_INTERVALS
from server.agents.functions import authenticate_gmail
from server.context.runnables import get_gmail_context_runnable
from datetime import datetime, timezone, timedelta # Ensure all are imported
import asyncio
from server.agents.helpers import extract_email_body # Make sure this is available or defined
from typing import Optional, Any, Tuple # For type hinting

class GmailContextEngine(BaseContextEngine):
    """Context Engine for processing Gmail data, with dynamic polling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = "gmail"
        print(f"[GMAIL_ENGINE_INIT] Initializing for user: {self.user_id}")
        try:
            self.gmail_service = authenticate_gmail()
            print(f"[GMAIL_ENGINE_INIT] Gmail service authenticated for user: {self.user_id}")
        except Exception as e:
            print(f"[GMAIL_ENGINE_ERROR] Failed to authenticate Gmail for user {self.user_id}: {e}")
            self.gmail_service = None # Ensure it's None if auth fails
        print(f"[GMAIL_ENGINE_INIT] Initialization complete for user: {self.user_id}")

    # The start() method is removed as polling is now driven by the central scheduler
    # async def start(self):
    #    pass 

    async def fetch_new_data(self) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetch new emails from Gmail since the last processed marker.
        Returns a tuple: (list_of_new_emails, new_marker).
        The marker can be the ID or internalDate of the latest processed email.
        """
        if not self.gmail_service:
            print(f"[GMAIL_ENGINE_FETCH_ERROR] Gmail service not available for user {self.user_id}.")
            return None, None

        print(f"[GMAIL_ENGINE_FETCH] Fetching new data for user: {self.user_id}")
        polling_state = await self.mongo_manager.get_polling_state(self.user_id, self.category)
        
        last_marker = polling_state.get("last_processed_item_marker") if polling_state else None
        
        query = "in:inbox is:unread" # Start with unread, can be refined
        if last_marker:
            # Assuming last_marker is an email's internalDate (timestamp in ms string) or historyId
            # For simplicity, let's use 'after' with a timestamp. Gmail API expects Unix timestamp (seconds).
            # If last_marker was an email ID, more complex logic for "newer than this ID" is needed.
            # Let's assume last_marker is an ISO timestamp of the last *successful* poll.
            # If `last_processed_item_marker` is indeed the `internalDate` of the last email:
            if last_marker and last_marker.isdigit(): # If it's a timestamp like internalDate
                 query += f" after:{int(int(last_marker) / 1000)}" # Convert ms to s
                 print(f"[GMAIL_ENGINE_FETCH] Querying emails after internalDate marker: {last_marker}")
            elif polling_state and polling_state.get("last_successful_poll_timestamp"):
                last_poll_dt = polling_state["last_successful_poll_timestamp"]
                if isinstance(last_poll_dt, str): # If stored as ISO string
                    last_poll_dt = datetime.fromisoformat(last_poll_dt.replace("Z", "+00:00"))
                
                if last_poll_dt.tzinfo is None: # Ensure timezone aware
                    last_poll_dt = last_poll_dt.replace(tzinfo=timezone.utc)

                last_poll_unix_ts = int(last_poll_dt.timestamp())
                query += f" after:{last_poll_unix_ts}"
                print(f"[GMAIL_ENGINE_FETCH] Querying emails after last successful poll: {last_poll_dt.isoformat()}")
            else:
                print(f"[GMAIL_ENGINE_FETCH] No valid last_marker or last_successful_poll_timestamp. Fetching all unread.")
        else:
            print(f"[GMAIL_ENGINE_FETCH] No last_marker. Fetching all unread emails.")

        new_emails_content = []
        new_latest_marker = last_marker # Start with the old marker
        
        try:
            results = self.gmail_service.users().messages().list(userId="me", q=query, maxResults=10, includeSpamTrash=False).execute()
            messages_metadata = results.get("messages", [])
            print(f"[GMAIL_ENGINE_FETCH] Found {len(messages_metadata)} potentially new/unread messages metadata for user {self.user_id}.")

            if not messages_metadata:
                return [], last_marker # No new messages, return current marker

            # Process messages, typically from newest to oldest if not specified by API
            # It's often better to process in chronological order to update marker correctly.
            # Gmail API list might return newest first. Let's assume this for marker update.

            for msg_meta in reversed(messages_metadata): # Process oldest of the new batch first
                msg_id = msg_meta["id"]
                try:
                    # Consider fetching 'metadata' format with 'internalDate' first to avoid full fetch if not needed by LLM
                    email_detail = self.gmail_service.users().messages().get(userId="me", id=msg_id, format="full").execute()
                    new_emails_content.append(email_detail)
                    
                    # Update new_latest_marker with the internalDate of this email
                    # Gmail's internalDate is a string of milliseconds since epoch
                    current_email_internal_date_str = email_detail.get("internalDate")
                    if current_email_internal_date_str:
                        # If we are processing from oldest to newest, the last one will be the newest marker
                        new_latest_marker = current_email_internal_date_str 
                        
                except Exception as e_detail:
                    print(f"[GMAIL_ENGINE_ERROR] Failed to fetch details for email ID {msg_id} for user {self.user_id}: {e_detail}")
            
            # If we processed messages, new_latest_marker should be the internalDate of the newest one processed.
            # If no messages processed but messages_metadata was not empty, something is wrong, but marker stays.
            if not new_emails_content and messages_metadata:
                 print(f"[GMAIL_ENGINE_WARN] Had metadata but no content fetched for user {self.user_id}")


        except Exception as e_list:
            print(f"[GMAIL_ENGINE_ERROR] Failed to list Gmail messages for user {self.user_id}: {e_list}")
            return None, last_marker # Error, return None for data, keep old marker

        print(f"[GMAIL_ENGINE_FETCH] Returning {len(new_emails_content)} new emails for user {self.user_id}. New marker: {new_latest_marker}")
        return new_emails_content, new_latest_marker


    async def process_new_data(self, new_emails: List[Dict[str, Any]]) -> str:
        """Process new emails into a single string summary."""
        print(f"[GMAIL_ENGINE_PROCESS] Processing {len(new_emails)} new emails for user: {self.user_id}")
        summaries = []
        for email in new_emails:
            snippet = email.get("snippet", "")
            headers = {h["name"]: h["value"] for h in email.get("payload", {}).get("headers", [])}
            subject = headers.get("Subject", "No Subject")
            from_ = headers.get("From", "Unknown Sender")
            # Example: simple concatenation. LLM could do better.
            summaries.append(f"Email from: {from_}. Subject: '{subject}'. Snippet: '{snippet}'")
        
        joined_summaries = "\n---\n".join(summaries) # Separate emails clearly
        print(f"[GMAIL_ENGINE_PROCESS] Processed data for user {self.user_id}: {joined_summaries[:200]}...")
        return joined_summaries

    async def get_runnable(self):
        """Return the Gmail-specific context runnable."""
        print(f"[GMAIL_ENGINE_RUNNABLE] Getting runnable for user: {self.user_id}")
        return get_gmail_context_runnable()