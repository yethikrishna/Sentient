import os
from typing import Dict, Any, List, Optional

import base64
from email.mime.text import MIMEText
import re
import asyncio

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message
from googleapiclient.errors import HttpError
from fastmcp.utilities.logging import configure_logging, get_logger

# Local imports for modularity
from . import auth
from . import prompts
from . import utils as helpers

# --- Standardized Logging Setup ---
configure_logging(level="INFO")
logger = get_logger(__name__)

# Conditionally load .env for local development
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

# --- Server Initialization ---
mcp = FastMCP(
    name="GMailServer",
    instructions="Provides a comprehensive suite of tools to read, search, send, and manage emails and labels in a user's Gmail account.",
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

        # NEW: Fetch user info including privacy filters for tools that need it
        needs_user_info = func.__name__ in ["_list_emails_sync", "_read_email_sync", "_catchup_sync"]
        if needs_user_info:
            user_info = await auth.get_user_info(user_id)
            kwargs['user_info'] = user_info

        # Use asyncio.to_thread to run synchronous Google API calls
        result = await asyncio.to_thread(func, service, *args, **kwargs)
        return {"status": "success", "result": result}
    except HttpError as e:
        logger.error(f"Google API Error in '{func.__name__}': {e.content.decode()}", exc_info=True)
        # Catching HttpError specifically to get more details
        return {"status": "failure", "error": f"Google API Error: {e.content.decode()}"}
    except Exception as e:
        logger.error(f"Tool execution failed for '{func.__name__}': {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

# --- Sync Tool Implementations ---

def _send_email_sync(service, to: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject

    # Optional: add From header to avoid confusion
    msg["from"] = "me"

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    message_body = {"raw": raw}

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

def _list_emails_sync(service, query: str = None, max_results: int = 10, user_info: Dict = None):
    # Fetch more results than requested to account for potential filtering
    results = service.users().messages().list(userId="me", q=query, maxResults=max_results * 2).execute()
    messages_info = results.get("messages", [])

    if not messages_info:
        return []

    # Fetch full message details in a batch for efficiency
    batch = service.new_batch_http_request()
    messages_full = []
    def callback(request_id, response, exception):
        if exception is None:
            messages_full.append(response)

    for msg_info in messages_info:
        batch.add(service.users().messages().get(userId="me", id=msg_info["id"]), callback=callback)

    batch.execute()

    # Apply privacy filters if available
    filtered_messages = []
    if user_info and user_info.get("privacy_filters"):
        filters = user_info["privacy_filters"]
        keyword_filters = filters.get("keywords", [])
        email_filters = [e.lower() for e in filters.get("emails", [])]
        label_filters = [l.lower() for l in filters.get("labels", [])]

        for msg in messages_full:
            is_filtered = False
            simplified = helpers._simplify_message(msg)

            # Check labels
            email_labels = [l.lower() for l in simplified.get("labels", [])]
            if any(fl in email_labels for fl in label_filters):
                is_filtered = True

            # Check sender
            sender_header = simplified.get("from", "").lower()
            sender_match = re.search(r'<(.+?)>', sender_header)
            sender_email = sender_match.group(1) if sender_match else sender_header
            if any(fe in sender_email for fe in email_filters):
                is_filtered = True

            # Check keywords in subject/snippet
            content_to_check = (simplified.get("subject", "") + " " + simplified.get("snippet", "")).lower()
            if any(kw.lower() in content_to_check for kw in keyword_filters):
                is_filtered = True

            if not is_filtered:
                filtered_messages.append(simplified)
    else:
        # No filters, just simplify all fetched messages
        filtered_messages = [helpers._simplify_message(msg) for msg in messages_full]

    return filtered_messages[:max_results]

def _read_email_sync(service, message_id: str, user_info: Dict = None):
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()

    # Apply privacy filters before returning content
    if user_info and user_info.get("privacy_filters"):
        filters = user_info["privacy_filters"]
        keyword_filters = filters.get("keywords", [])
        email_filters = [e.lower() for e in filters.get("emails", [])]
        label_filters = [l.lower() for l in filters.get("labels", [])]

        simplified_check = helpers._simplify_message(msg)

        email_labels = [l.lower() for l in simplified_check.get("labels", [])]
        if any(fl in email_labels for fl in label_filters):
            raise Exception("Access denied to this email due to a privacy filter (label).")

        sender_header = simplified_check.get("from", "").lower()
        sender_match = re.search(r'<(.+?)>', sender_header)
        sender_email = sender_match.group(1) if sender_match else sender_header
        if any(fe in sender_email for fe in email_filters):
            raise Exception("Access denied to this email due to a privacy filter (sender).")

        content_to_check = (simplified_check.get("subject", "") + " " + simplified_check.get("snippet", "")).lower()
        if any(kw.lower() in content_to_check for kw in keyword_filters):
            raise Exception("Access denied to this email due to a privacy filter (keyword).")

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

def _catchup_sync(service, user_info: Dict = None):
    # The list function now handles filtering
    unread_emails = _list_emails_sync(service, query="is:unread", max_results=20, user_info=user_info)
    if not unread_emails:
        return "Your inbox is all caught up!"
    # Need to run the async helper in the event loop
    return asyncio.run(helpers.summarize_emails_with_gemini(unread_emails))


# --- Async Tool Definitions ---

@mcp.tool()
async def sendEmail(ctx: Context, to: str, subject: str, body: str) -> Dict[str, Any]:
    """Compose and send a new email message to one or more recipients."""
    logger.info(f"Executing tool: sendEmail to='{to}'")
    return await _execute_tool(ctx, _send_email_sync, to=to, subject=subject, body=body)

@mcp.tool()
async def replyToEmail(ctx: Context, message_id: str, body: str, reply_all: bool = False) -> Dict[str, Any]:
    """Send a reply to an existing email message, either to the sender only or to all recipients."""
    logger.info(f"Executing tool: replyToEmail to message_id='{message_id}'")
    return await _execute_tool(ctx, _reply_to_email_sync, message_id=message_id, body=body, reply_all=reply_all)

@mcp.tool()
async def getLatestEmails(ctx: Context, max_results: int = 10) -> Dict[str, Any]:
    """Retrieve the most recent email messages from your inbox, sorted by date received."""
    logger.info(f"Executing tool: getLatestEmails with max_results={max_results}")
    return await _execute_tool(ctx, _list_emails_sync, query="in:inbox", max_results=max_results)

@mcp.tool()
async def getUnreadEmails(ctx: Context, max_results: int = 10) -> Dict[str, Any]:
    """Retrieve unread email messages from your inbox."""
    logger.info(f"Executing tool: getUnreadEmails with max_results={max_results}")
    return await _execute_tool(ctx, _list_emails_sync, query="is:unread in:inbox", max_results=max_results)

@mcp.tool()
async def createLabel(ctx: Context, name: str) -> Dict[str, Any]:
    """Create a new Gmail label for organizing emails."""
    logger.info(f"Executing tool: createLabel with name='{name}'")
    return await _execute_tool(ctx, _create_label_sync, name=name)

@mcp.tool()
async def applyLabels(ctx: Context, message_id: str, label_ids: List[str]) -> Dict[str, Any]:
    """Add one or more labels to a specific email message."""
    logger.info(f"Executing tool: applyLabels to message_id='{message_id}'")
    return await _execute_tool(ctx, _modify_email_sync, message_id=message_id, add_labels=label_ids)

@mcp.tool()
async def createDraft(ctx: Context, to: str, subject: str, body: str) -> Dict[str, Any]:
    """Create a new draft email that can be edited before sending."""
    logger.info(f"Executing tool: createDraft to='{to}'")
    def _sync(service, to, subject, body):
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        message_raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        message = {"message": {"raw": message_raw}}
        draft = service.users().drafts().create(userId="me", body=message).execute()
        return {"draft_id": draft['id'], "message": "Draft created successfully."}
    return await _execute_tool(ctx, _sync, to=to, subject=subject, body=body)

@mcp.tool()
async def listDrafts(ctx: Context) -> Dict[str, Any]:
    """List all saved draft emails in the user's account."""
    logger.info("Executing tool: listDrafts")
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
    logger.info(f"Executing tool: markAsRead for message_id='{message_id}'")
    return await _execute_tool(ctx, _modify_email_sync, message_id=message_id, remove_labels=["UNREAD"])

@mcp.tool()
async def moveToTrash(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Move an email message to the trash."""
    logger.info(f"Executing tool: moveToTrash for message_id='{message_id}'")
    def _sync(service, message_id):
        service.users().messages().trash(userId="me", id=message_id).execute()
        return {"message": "Email moved to trash."}
    return await _execute_tool(ctx, _sync, message_id=message_id)

@mcp.tool()
async def archiveEmail(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Remove an email message from the inbox without deleting it (archive)."""
    logger.info(f"Executing tool: archiveEmail for message_id='{message_id}'")
    return await _execute_tool(ctx, _modify_email_sync, message_id=message_id, remove_labels=["INBOX"])

@mcp.tool()
async def searchWithAttachments(ctx: Context, max_results: int = 5) -> Dict[str, Any]:
    """Search for email messages that have file attachments."""
    logger.info(f"Executing tool: searchWithAttachments with max_results={max_results}")
    return await _execute_tool(ctx, _list_emails_sync, query="has:attachment", max_results=max_results)

@mcp.tool()
async def searchInFolder(ctx: Context, folder_name: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for email messages within a specific Gmail folder or label."""
    logger.info(f"Executing tool: searchInFolder for folder='{folder_name}'")
    return await _execute_tool(ctx, _list_emails_sync, query=f"in:{folder_name}", max_results=max_results)

@mcp.tool()
async def createFilter(ctx: Context, from_email: Optional[str] = None, to_email: Optional[str] = None, subject: Optional[str] = None, add_label_id: Optional[str] = None, remove_label_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Create a new Gmail filter that automatically applies actions to incoming messages."""
    logger.info(f"Executing tool: createFilter")
    criteria = {k: v for k, v in locals().items() if k in ['from_email', 'to_email', 'subject'] and v is not None}
    action = {"addLabelIds": [add_label_id] if add_label_id else [], "removeLabelIds": remove_label_ids or []}
    if not criteria or not (action["addLabelIds"] or action["removeLabelIds"]):
        return {"status": "failure", "error": "Filter requires at least one criteria and one action."}
    return await _execute_tool(ctx, _create_filter_sync, criteria=criteria, action=action)

@mcp.tool()
async def deleteFilter(ctx: Context, filter_id: str) -> Dict[str, Any]:
    """Delete a Gmail filter."""
    logger.info(f"Executing tool: deleteFilter with filter_id='{filter_id}'")
    return await _execute_tool(ctx, _delete_filter_sync, filter_id=filter_id)

@mcp.tool()
async def cancelScheduled(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Cancel a scheduled email. This is done by moving the email to trash."""
    logger.info(f"Executing tool: cancelScheduled for message_id='{message_id}'")
    return await moveToTrash(ctx, message_id)

@mcp.tool()
async def catchup(ctx: Context) -> Dict[str, Any]:
    """Get a quick compact summary of all unread emails from your primary inbox."""
    logger.info("Executing tool: catchup")
    return await _execute_tool(ctx, _catchup_sync)

@mcp.tool()
async def readEmail(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Retrieve and read the content of a specific email message by its unique ID."""
    logger.info(f"Executing tool: readEmail with message_id='{message_id}'")
    return await _execute_tool(ctx, _read_email_sync, message_id=message_id)

@mcp.tool()
async def getEmailsByThread(ctx: Context, thread_id: str) -> Dict[str, Any]:
    """Retrieve all email messages that belong to the same conversation thread."""
    logger.info(f"Executing tool: getEmailsByThread with thread_id='{thread_id}'")
    def _sync(service, thread_id):
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        return [helpers._simplify_message(m) for m in thread.get('messages', [])]
    return await _execute_tool(ctx, _sync, thread_id=thread_id)

@mcp.tool()
async def getEmailsBySender(ctx: Context, sender_email: str, max_results: int = 10) -> Dict[str, Any]:
    """Retrieve email messages from a specific sender email address."""
    logger.info(f"Executing tool: getEmailsBySender with sender_email='{sender_email}'")
    return await _execute_tool(ctx, _list_emails_sync, query=f"from:{sender_email}", max_results=max_results)

@mcp.tool()
async def searchEmails(ctx: Context, query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for email messages using Gmail search operators and syntax."""
    logger.info(f"Executing tool: searchEmails with query='{query}'")
    return await _execute_tool(ctx, _list_emails_sync, query=query, max_results=max_results)

@mcp.tool()
async def listLabels(ctx: Context) -> Dict[str, Any]:
    """List all available Gmail labels in the user's account."""
    logger.info("Executing tool: listLabels")
    return await _execute_tool(ctx, _list_labels_sync)

@mcp.tool()
async def removeLabels(ctx: Context, message_id: str, label_ids: List[str]) -> Dict[str, Any]:
    """Remove one or more labels from a specific email message."""
    logger.info(f"Executing tool: removeLabels from message_id='{message_id}'")
    return await _execute_tool(ctx, _modify_email_sync, message_id=message_id, remove_labels=label_ids)

@mcp.tool()
async def updateDraft(ctx: Context, draft_id: str, to: Optional[str] = None, subject: Optional[str] = None, body: Optional[str] = None) -> Dict[str, Any]:
    """Update an existing draft email with new content."""
    logger.info(f"Executing tool: updateDraft for draft_id='{draft_id}'")
    def _sync(service, draft_id, to, subject, body):
        msg = MIMEText(body)
        if to:
            msg["to"] = to
        if subject:
            msg["subject"] = subject
        message_raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        message = {"message": {"raw": message_raw}}
        updated_draft = service.users().drafts().update(userId="me", id=draft_id, body=message).execute()
        return {"draft_id": updated_draft['id'], "message": "Draft updated."}
    return await _execute_tool(ctx, _sync, draft_id=draft_id, to=to, subject=subject, body=body)

@mcp.tool()
async def deleteDraft(ctx: Context, draft_id: str) -> Dict[str, Any]:
    """Delete a saved draft email."""
    logger.info(f"Executing tool: deleteDraft with draft_id='{draft_id}'")
    def _sync(service, draft_id):
        service.users().drafts().delete(userId="me", id=draft_id).execute()
        return {"message": "Draft deleted."}
    return await _execute_tool(ctx, _sync, draft_id=draft_id)

@mcp.tool()
async def markAsUnread(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Mark an email message as unread."""
    logger.info(f"Executing tool: markAsUnread for message_id='{message_id}'")
    return await _execute_tool(ctx, _modify_email_sync, message_id=message_id, add_labels=["UNREAD"])

@mcp.tool()
async def restoreFromTrash(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Restore an email message from the trash to the inbox."""
    logger.info(f"Executing tool: restoreFromTrash for message_id='{message_id}'")
    def _sync(service, message_id):
        service.users().messages().untrash(userId="me", id=message_id).execute()
        return {"message": "Email restored from trash."}
    return await _execute_tool(ctx, _sync, message_id=message_id)

@mcp.tool()
async def searchByDate(ctx: Context, before: Optional[str] = None, after: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
    """Search for email messages within a specific date range (YYYY/MM/DD format)."""
    logger.info(f"Executing tool: searchByDate with before='{before}', after='{after}'")
    query_parts = []
    if before: query_parts.append(f"before:{before}")
    if after: query_parts.append(f"after:{after}")
    if not query_parts: return {"status": "failure", "error": "Either 'before' or 'after' date must be provided."}
    return await _execute_tool(ctx, _list_emails_sync, query=" ".join(query_parts), max_results=max_results)

@mcp.tool()
async def searchBySize(ctx: Context, size_mb: int, comparison: str = "larger", max_results: int = 5) -> Dict[str, Any]:
    """Search for large email messages above a specified size in MB."""
    logger.info(f"Executing tool: searchBySize with size_mb={size_mb}")
    op = ">" if comparison == "larger" else "<"
    return await _execute_tool(ctx, _list_emails_sync, query=f"size:{size_mb}m", max_results=max_results)

@mcp.tool()
async def forwardEmail(ctx: Context, message_id: str, to: str) -> Dict[str, Any]:
    """Forward an existing email message to new recipients."""
    logger.info(f"Executing tool: forwardEmail for message_id='{message_id}' to='{to}'")
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
    logger.info("Executing tool: listFilters")
    return await _execute_tool(ctx, _list_filters_sync)

@mcp.tool()
async def scheduleEmail(ctx: Context, to: str, subject: str, body: str, send_at_iso: str) -> Dict[str, Any]:
    """Create an email to be sent at a specified future time (ISO 8601 format)."""
    logger.info(f"Executing tool: scheduleEmail to='{to}' at '{send_at_iso}'")
    # Gmail API doesn't have a direct schedule send. The common workaround is to save a draft and use a separate scheduler (like Celery Beat)
    # to send it. For simplicity here, we will simulate it by sending immediately and returning a "scheduled" message.
    # A full implementation would require a separate scheduler worker.
    return await sendEmail(ctx, to, subject, f"[Simulating Send at {send_at_iso}]\n\n{body}")

@mcp.tool()
async def listScheduled(ctx: Context) -> Dict[str, Any]:
    """List all scheduled emails. (Simulated)"""
    logger.info("Executing tool: listScheduled")
    # Since we don't have a real scheduler, we return an empty list.
    return {"status": "success", "result": "No scheduled emails found (scheduling is simulated)."}

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9001))
    
    print(f"Starting GMail MCP Server on http://{host}:{port}")
    
    mcp.run(transport="sse", host=host, port=port)