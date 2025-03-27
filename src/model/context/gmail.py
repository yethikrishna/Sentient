from model.context.base_context_engine import BaseContextEngine
from model.auth.helpers import authenticate_gmail
from model.agents.runnables import get_gmail_context_runnable
from datetime import datetime

class GmailContextEngine(BaseContextEngine):
    """Context Engine for processing Gmail data."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gmail_service = authenticate_gmail()
        self.category = "gmail"

    async def fetch_new_data(self):
        """Fetch new emails from Gmail since the last check."""
        results = self.gmail_service.users().messages().list(userId="me", maxResults=5, q="in:inbox").execute()
        messages = results.get("messages", [])
        current_top_5_ids = [msg["id"] for msg in messages]
        gmail_context = self.context.get("gmail", {})
        previous_top_5_ids = gmail_context.get("emails", {}).get("last_email_ids", [])
        new_email_ids = [eid for eid in current_top_5_ids if eid not in previous_top_5_ids]
        new_emails = []
        for email_id in new_email_ids:
            email = self.gmail_service.users().messages().get(userId="me", id=email_id).execute()
            new_emails.append(email)
        # Update context with the latest email IDs
        self.context["gmail"] = {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "emails": {"last_email_ids": current_top_5_ids}
        }
        self.save_context()
        return new_emails

    def process_new_data(self, new_emails):
        """Process new emails into summaries."""
        summaries = [self.generate_email_summary(email) for email in new_emails]
        return "\n".join(summaries)

    def get_runnable(self):
        """Return the Gmail-specific runnable."""
        return get_gmail_context_runnable()

    def get_category(self):
        """Return the memory category for Gmail."""
        return self.category

    def generate_email_summary(self, email):
        """Generate a summary for a single email."""
        snippet = email.get("snippet", "")
        subject = next((header["value"] for header in email["payload"]["headers"] if header["name"] == "Subject"), "No Subject")
        from_ = next((header["value"] for header in email["payload"]["headers"] if header["name"] == "From"), "Unknown Sender")
        return f"You have an email from {from_} with subject '{subject}' and snippet '{snippet}'"