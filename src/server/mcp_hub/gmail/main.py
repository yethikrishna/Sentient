import os
from typing import Dict, Any, List, Optional

import base64
from email.mime.text import MIMEText
import asyncio

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message
from googleapiclient.errors import HttpError

# Local imports for modularity
from . import auth
from . import prompts
from . import utils as helpers

# Conditionally load .env for local development
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

# --- Server Initialization ---
mcp = FastMCP(
    name="GMailServer",
    instructions="This server provides tools to interact with the GMail API for sending, searching, and managing emails.",
)


# --- Prompt Registration ---
@mcp.resource("prompt://gmail-agent-system")
def get_gmail_system_prompt() -> str:
    """Provides the system prompt for the GMail agent."""
    return prompts.gmail_agent_system_prompt

@mcp.prompt(name="gmail_user_prompt_builder")
def build_gmail_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    """Builds a formatted user prompt for the GMail agent."""
    content = prompts.gmail_agent_user_prompt.format(
        query=query,
        username=username,
        previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)


# --- Tool Helper ---
async def _execute_tool(ctx: Context, func, *args, **kwargs) -> Dict[str, Any]:
    """Helper to handle auth and execution for all tools."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gmail(creds)
        
        # Use asyncio.to_thread to run synchronous Google API calls
        result = await asyncio.to_thread(func, service, *args, **kwargs)
        return {"status": "success", "result": result}
    except HttpError as e:
        return {"status": "failure", "error": f"Google API Error: {e.content.decode()}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Sync Tool Implementations ---

def _send_email_sync(service, to: str, subject: str, body: str):
    message_raw = base64.urlsafe_b64encode(MIMEText(body).as_bytes()).decode()
    message_body = {"raw": message_raw, "to": to, "subject": subject}
    service.users().messages().send(userId="me", body=message_body).execute()
    return {"message": "Email sent successfully."}

def _reply_to_email_sync(service, message_id: str, body: str, reply_all: bool = False):
    original_msg = service.users().messages().get(userId="me", id=message_id, format="metadata", metadataHeaders=["subject", "from", "to", "cc", "message-id", "references"]).execute()
    headers = {h['name'].lower(): h['value'] for h in original_msg['payload']['headers']}

    thread_id = original_msg['threadId']
    subject = headers.get('subject', '')
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    msg = MIMEText(body)
    msg["subject"] = subject
    msg["In-Reply-To"] = headers['message-id']
    msg["References"] = headers.get('references', headers['message-id'])

    if reply_all:
        to_recipients = headers.get('to', '') + ',' + headers.get('cc', '')
        msg["to"] = to_recipients
        msg["cc"] = headers.get('from')
    else:
        msg["to"] = headers.get('from')

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw_message, "threadId": thread_id}).execute()
    return {"message": "Reply sent successfully."}

def _list_emails_sync(service, query: str = None, max_results: int = 10):
    results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = results.get("messages", [])
    return [helpers._simplify_message(service.users().messages().get(userId="me", id=m["id"]).execute()) for m in messages]

def _read_email_sync(service, message_id: str):
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    simplified = helpers._simplify_message(msg)
    simplified["body"] = helpers.extract_email_body(msg.get("payload", {}))
    return simplified

def _modify_email_sync(service, message_id: str, add_labels: Optional[List[str]] = None, remove_labels: Optional[List[str]] = None):
    body = {"addLabelIds": add_labels or [], "removeLabelIds": remove_labels or []}
    service.users().messages().modify(userId="me", id=message_id, body=body).execute()
    return {"message": f"Email {message_id} modified."}

def _list_labels_sync(service):
    results = service.users().labels().list(userId="me").execute()
    return [helpers._simplify_label(l) for l in results.get("labels", [])]

def _create_label_sync(service, name: str):
    label = {"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
    created_label = service.users().labels().create(userId="me", body=label).execute()
    return helpers._simplify_label(created_label)

def _list_filters_sync(service):
    results = service.users().settings().filters().list(userId="me").execute()
    return [helpers._simplify_filter(f) for f in results.get("filter", [])]

def _create_filter_sync(service, criteria: Dict, action: Dict):
    filter_body = {"criteria": criteria, "action": action}
    created_filter = service.users().settings().filters().create(userId="me", body=filter_body).execute()
    return helpers._simplify_filter(created_filter)

def _delete_filter_sync(service, filter_id: str):
    service.users().settings().filters().delete(userId="me", id=filter_id).execute()
    return {"message": f"Filter {filter_id} deleted."}

def _catchup_sync(service):
    unread_emails = _list_emails_sync(service, query="is:unread", max_results=20)
    if not unread_emails:
        return "Your inbox is all caught up!"
    # Need to run the async helper in the event loop
    return asyncio.run(helpers.summarize_emails_with_gemini(unread_emails))


# --- Async Tool Definitions ---

@mcp.tool()
async def sendEmail(ctx: Context, to: str, subject: str, body: str) -> Dict[str, Any]:
    """Compose and send a new email message to one or more recipients."""
    return await _execute_tool(ctx, _send_email_sync, to=to, subject=subject, body=body)

@mcp.tool()
async def replyToEmail(ctx: Context, message_id: str, body: str, reply_all: bool = False) -> Dict[str, Any]:
    """Send a reply to an existing email message, either to the sender only or to all recipients."""
    return await _execute_tool(ctx, _reply_to_email_sync, message_id=message_id, body=body, reply_all=reply_all)

@mcp.tool()
async def getLatestEmails(ctx: Context, max_results: int = 10) -> Dict[str, Any]:
    """Retrieve the most recent email messages from your inbox, sorted by date received."""
    return await _execute_tool(ctx, _list_emails_sync, query="in:inbox", max_results=max_results)

@mcp.tool()
async def getUnreadEmails(ctx: Context, max_results: int = 10) -> Dict[str, Any]:
    """Retrieve unread email messages from your inbox."""
    return await _execute_tool(ctx, _list_emails_sync, query="is:unread in:inbox", max_results=max_results)

@mcp.tool()
async def createLabel(ctx: Context, name: str) -> Dict[str, Any]:
    """Create a new Gmail label for organizing emails."""
    return await _execute_tool(ctx, _create_label_sync, name=name)

@mcp.tool()
async def applyLabels(ctx: Context, message_id: str, label_ids: List[str]) -> Dict[str, Any]:
    """Add one or more labels to a specific email message."""
    return await _execute_tool(ctx, _modify_email_sync, message_id=message_id, add_labels=label_ids)

@mcp.tool()
async def createDraft(ctx: Context, to: str, subject: str, body: str) -> Dict[str, Any]:
    """Create a new draft email that can be edited before sending."""
    def _sync(service, to, subject, body):
        message_raw = base64.urlsafe_b64encode(MIMEText(body).as_bytes()).decode()
        message = {"message": {"raw": message_raw, "to": to, "subject": subject}}
        draft = service.users().drafts().create(userId="me", body=message).execute()
        return {"draft_id": draft['id'], "message": "Draft created successfully."}
    return await _execute_tool(ctx, _sync, to=to, subject=subject, body=body)

@mcp.tool()
async def listDrafts(ctx: Context) -> Dict[str, Any]:
    """List all saved draft emails in the user's account."""
    def _sync(service):
        drafts = service.users().drafts().list(userId="me").execute().get('drafts', [])
        # Fetch details for each draft to show subject/to
        detailed_drafts = []
        for d in drafts[:10]: # Limit to 10 to avoid too many API calls
            draft_details = service.users().drafts().get(userId="me", id=d['id']).execute()
            headers = {h['name'].lower(): h['value'] for h in draft_details['message']['payload']['headers']}
            detailed_drafts.append({"id": d['id'], "to": headers.get('to'), "subject": headers.get('subject')})
        return detailed_drafts
    return await _execute_tool(ctx, _sync)

@mcp.tool()
async def markAsRead(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Mark an email message as read."""
    return await _execute_tool(ctx, _modify_email_sync, message_id=message_id, remove_labels=["UNREAD"])

@mcp.tool()
async def moveToTrash(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Move an email message to the trash."""
    def _sync(service, message_id):
        service.users().messages().trash(userId="me", id=message_id).execute()
        return {"message": "Email moved to trash."}
    return await _execute_tool(ctx, _sync, message_id=message_id)

@mcp.tool()
async def archiveEmail(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Remove an email message from the inbox without deleting it (archive)."""
    return await _execute_tool(ctx, _modify_email_sync, message_id=message_id, remove_labels=["INBOX"])

@mcp.tool()
async def searchWithAttachments(ctx: Context, max_results: int = 5) -> Dict[str, Any]:
    """Search for email messages that have file attachments."""
    return await _execute_tool(ctx, _list_emails_sync, query="has:attachment", max_results=max_results)

@mcp.tool()
async def searchInFolder(ctx: Context, folder_name: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for email messages within a specific Gmail folder or label."""
    return await _execute_tool(ctx, _list_emails_sync, query=f"in:{folder_name}", max_results=max_results)

@mcp.tool()
async def createFilter(ctx: Context, from_email: Optional[str] = None, to_email: Optional[str] = None, subject: Optional[str] = None, add_label_id: Optional[str] = None, remove_label_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Create a new Gmail filter that automatically applies actions to incoming messages."""
    criteria = {k: v for k, v in locals().items() if k in ['from_email', 'to_email', 'subject'] and v is not None}
    action = {"addLabelIds": [add_label_id] if add_label_id else [], "removeLabelIds": remove_label_ids or []}
    if not criteria or not (action["addLabelIds"] or action["removeLabelIds"]):
        return {"status": "failure", "error": "Filter requires at least one criteria and one action."}
    return await _execute_tool(ctx, _create_filter_sync, criteria=criteria, action=action)

@mcp.tool()
async def deleteFilter(ctx: Context, filter_id: str) -> Dict[str, Any]:
    """Delete a Gmail filter."""
    return await _execute_tool(ctx, _delete_filter_sync, filter_id=filter_id)

@mcp.tool()
async def cancelScheduled(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Cancel a scheduled email. This is done by moving the email to trash."""
    return await moveToTrash(ctx, message_id)

@mcp.tool()
async def catchup(ctx: Context) -> Dict[str, Any]:
    """Get a quick compact summary of all unread emails from your primary inbox."""
    return await _execute_tool(ctx, _catchup_sync)

@mcp.tool()
async def readEmail(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Retrieve and read the content of a specific email message by its unique ID."""
    return await _execute_tool(ctx, _read_email_sync, message_id=message_id)

@mcp.tool()
async def getEmailsByThread(ctx: Context, thread_id: str) -> Dict[str, Any]:
    """Retrieve all email messages that belong to the same conversation thread."""
    def _sync(service, thread_id):
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        return [helpers._simplify_message(m) for m in thread.get('messages', [])]
    return await _execute_tool(ctx, _sync, thread_id=thread_id)

@mcp.tool()
async def getEmailsBySender(ctx: Context, sender_email: str, max_results: int = 10) -> Dict[str, Any]:
    """Retrieve email messages from a specific sender email address."""
    return await _execute_tool(ctx, _list_emails_sync, query=f"from:{sender_email}", max_results=max_results)

@mcp.tool()
async def searchEmails(ctx: Context, query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for email messages using Gmail search operators and syntax."""
    return await _execute_tool(ctx, _list_emails_sync, query=query, max_results=max_results)

@mcp.tool()
async def listLabels(ctx: Context) -> Dict[str, Any]:
    """List all available Gmail labels in the user's account."""
    return await _execute_tool(ctx, _list_labels_sync)

@mcp.tool()
async def removeLabels(ctx: Context, message_id: str, label_ids: List[str]) -> Dict[str, Any]:
    """Remove one or more labels from a specific email message."""
    return await _execute_tool(ctx, _modify_email_sync, message_id=message_id, remove_labels=label_ids)

@mcp.tool()
async def updateDraft(ctx: Context, draft_id: str, to: Optional[str] = None, subject: Optional[str] = None, body: Optional[str] = None) -> Dict[str, Any]:
    """Update an existing draft email with new content."""
    def _sync(service, draft_id, to, subject, body):
        message_raw = base64.urlsafe_b64encode(MIMEText(body).as_bytes()).decode()
        message = {"message": {"raw": message_raw, "to": to, "subject": subject}}
        updated_draft = service.users().drafts().update(userId="me", id=draft_id, body=message).execute()
        return {"draft_id": updated_draft['id'], "message": "Draft updated."}
    return await _execute_tool(ctx, _sync, draft_id=draft_id, to=to, subject=subject, body=body)

@mcp.tool()
async def deleteDraft(ctx: Context, draft_id: str) -> Dict[str, Any]:
    """Delete a saved draft email."""
    def _sync(service, draft_id):
        service.users().drafts().delete(userId="me", id=draft_id).execute()
        return {"message": "Draft deleted."}
    return await _execute_tool(ctx, _sync, draft_id=draft_id)

@mcp.tool()
async def markAsUnread(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Mark an email message as unread."""
    return await _execute_tool(ctx, _modify_email_sync, message_id=message_id, add_labels=["UNREAD"])

@mcp.tool()
async def restoreFromTrash(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Restore an email message from the trash to the inbox."""
    def _sync(service, message_id):
        service.users().messages().untrash(userId="me", id=message_id).execute()
        return {"message": "Email restored from trash."}
    return await _execute_tool(ctx, _sync, message_id=message_id)

@mcp.tool()
async def searchByDate(ctx: Context, before: Optional[str] = None, after: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
    """Search for email messages within a specific date range (YYYY/MM/DD format)."""
    query_parts = []
    if before: query_parts.append(f"before:{before}")
    if after: query_parts.append(f"after:{after}")
    if not query_parts: return {"status": "failure", "error": "Either 'before' or 'after' date must be provided."}
    return await _execute_tool(ctx, _list_emails_sync, query=" ".join(query_parts), max_results=max_results)

@mcp.tool()
async def searchBySize(ctx: Context, size_mb: int, comparison: str = "larger", max_results: int = 5) -> Dict[str, Any]:
    """Search for large email messages above a specified size in MB."""
    op = ">" if comparison == "larger" else "<"
    return await _execute_tool(ctx, _list_emails_sync, query=f"size:{size_mb}m", max_results=max_results)

@mcp.tool()
async def forwardEmail(ctx: Context, message_id: str, to: str) -> Dict[str, Any]:
    """Forward an existing email message to new recipients."""
    def _sync(service, message_id, to):
        original_msg = service.users().messages().get(userId="me", id=message_id, format='full').execute()
        headers = {h['name'].lower(): h['value'] for h in original_msg['payload']['headers']}
        body = helpers.extract_email_body(original_msg['payload'])

        fwd_subject = f"Fwd: {headers.get('subject', '')}"
        fwd_body = f"-------- Forwarded message --------\nFrom: {headers.get('from')}\nDate: {headers.get('date')}\nSubject: {headers.get('subject')}\nTo: {headers.get('to')}\n\n{body}"

        message_raw = base64.urlsafe_b64encode(MIMEText(fwd_body).as_bytes()).decode()
        message = {"raw": message_raw, "to": to, "subject": fwd_subject}
        service.users().messages().send(userId="me", body=message).execute()
        return {"message": "Email forwarded successfully."}
    return await _execute_tool(ctx, _sync, message_id=message_id, to=to)

@mcp.tool()
async def listFilters(ctx: Context) -> Dict[str, Any]:
    """List all Gmail filters in the user's account."""
    return await _execute_tool(ctx, _list_filters_sync)

@mcp.tool()
async def scheduleEmail(ctx: Context, to: str, subject: str, body: str, send_at_iso: str) -> Dict[str, Any]:
    """Create an email to be sent at a specified future time (ISO 8601 format)."""
    # Gmail API doesn't have a direct schedule send. The common workaround is to save a draft and use a separate scheduler (like Celery Beat)
    # to send it. For simplicity here, we will simulate it by sending immediately and returning a "scheduled" message.
    # A full implementation would require a separate scheduler worker.
    return await sendEmail(ctx, to, subject, f"[Simulating Send at {send_at_iso}]\n\n{body}")

@mcp.tool()
async def listScheduled(ctx: Context) -> Dict[str, Any]:
    """List all scheduled emails. (Simulated)"""
    # Since we don't have a real scheduler, we return an empty list.
    return {"status": "success", "result": "No scheduled emails found (scheduling is simulated)."}

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9001))
    
    print(f"Starting GMail MCP Server on http://{host}:{port}")
    
    mcp.run(transport="sse", host=host, port=port)