import os
from typing import Dict, Any, List, Optional

import re
import asyncio

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message
from fastmcp.utilities.logging import configure_logging, get_logger
from composio import Composio
from main.config import COMPOSIO_API_KEY

# Local imports for modularity
from . import auth
from . import prompts
from . import utils as helpers

# --- Standardized Logging Setup ---
configure_logging(level="INFO")
logger = get_logger(__name__)

# --- Composio Client ---
composio = Composio(api_key=COMPOSIO_API_KEY)

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
async def _execute_tool(ctx: Context, action_name: str, **kwargs) -> Dict[str, Any]:
    """Helper to handle auth and execution for all tools using Composio."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        connection_id = await auth.get_composio_connection_id(user_id, "gmail")
        
        # Composio's execute method is synchronous, so we use asyncio.to_thread
        result = await asyncio.to_thread(
            composio.tools.execute,
            action_name,
            arguments=kwargs, # Changed from params to arguments
            connected_account_id=connection_id
        )
        
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Tool execution failed for action '{action_name}': {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}


# --- Async Tool Definitions ---

@mcp.tool()
async def sendEmail(ctx: Context, to: str, subject: str, body: str) -> Dict[str, Any]:
    """Compose and send a new email message to one or more recipients."""
    logger.info(f"Executing tool: sendEmail to='{to}'")
    return await _execute_tool(ctx, "GMAIL_SEND_EMAIL", recipient_email=to, subject=subject, body=body)

@mcp.tool()
async def replyToEmail(ctx: Context, message_id: str, body: str, reply_all: bool = False) -> Dict[str, Any]:
    """Send a reply to an existing email message, either to the sender only or to all recipients."""
    logger.info(f"Executing tool: replyToEmail to message_id='{message_id}'")
    # Composio's reply_to_email expects thread_id, not message_id.
    return {"status": "failure", "error": "Replying directly by message_id is not supported. Please find the thread_id and use that."}

@mcp.tool()
async def getLatestEmails(ctx: Context, max_results: int = 10) -> Dict[str, Any]:
    """Retrieve the most recent email messages from your inbox, sorted by date received."""
    logger.info(f"Executing tool: getLatestEmails with max_results={max_results}")
    return await _execute_tool(ctx, "GMAIL_FETCH_EMAILS", query="in:inbox", max_results=max_results)

@mcp.tool()
async def getUnreadEmails(ctx: Context, max_results: int = 10) -> Dict[str, Any]:
    """Retrieve unread email messages from your inbox."""
    logger.info(f"Executing tool: getUnreadEmails with max_results={max_results}")
    return await _execute_tool(ctx, "GMAIL_FETCH_EMAILS", query="is:unread in:inbox", max_results=max_results)

@mcp.tool()
async def createLabel(ctx: Context, name: str) -> Dict[str, Any]:
    """Create a new Gmail label for organizing emails."""
    logger.info(f"Executing tool: createLabel with name='{name}'")
    return await _execute_tool(ctx, "GMAIL_CREATE_LABEL", label_name=name)

@mcp.tool()
async def applyLabels(ctx: Context, message_id: str, label_ids: List[str]) -> Dict[str, Any]:
    """Add one or more labels to a specific email message."""
    logger.info(f"Executing tool: applyLabels to message_id='{message_id}'")
    return await _execute_tool(ctx, "GMAIL_ADD_LABEL_TO_EMAIL", message_id=message_id, add_label_ids=label_ids)

@mcp.tool()
async def createDraft(ctx: Context, to: str, subject: str, body: str) -> Dict[str, Any]:
    """Create a new draft email that can be edited before sending."""
    logger.info(f"Executing tool: createDraft to='{to}'")
    return await _execute_tool(ctx, "GMAIL_CREATE_EMAIL_DRAFT", recipient_email=to, subject=subject, body=body)

@mcp.tool()
async def listDrafts(ctx: Context) -> Dict[str, Any]:
    """List all saved draft emails in the user's account."""
    logger.info("Executing tool: listDrafts")
    return await _execute_tool(ctx, "GMAIL_LIST_DRAFTS")

@mcp.tool()
async def markAsRead(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Mark an email message as read."""
    logger.info(f"Executing tool: markAsRead for message_id='{message_id}'")
    return await _execute_tool(ctx, "GMAIL_ADD_LABEL_TO_EMAIL", message_id=message_id, remove_label_ids=["UNREAD"])

@mcp.tool()
async def moveToTrash(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Move an email message to the trash."""
    logger.info(f"Executing tool: moveToTrash for message_id='{message_id}'")
    return await _execute_tool(ctx, "GMAIL_MOVE_TO_TRASH", message_id=message_id)

@mcp.tool()
async def archiveEmail(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Remove an email message from the inbox without deleting it (archive)."""
    logger.info(f"Executing tool: archiveEmail for message_id='{message_id}'")
    return await _execute_tool(ctx, "GMAIL_ADD_LABEL_TO_EMAIL", message_id=message_id, remove_label_ids=["INBOX"])

@mcp.tool()
async def searchWithAttachments(ctx: Context, max_results: int = 5) -> Dict[str, Any]:
    """Search for email messages that have file attachments."""
    logger.info(f"Executing tool: searchWithAttachments with max_results={max_results}")
    return await _execute_tool(ctx, "GMAIL_FETCH_EMAILS", query="has:attachment", max_results=max_results)

@mcp.tool()
async def searchInFolder(ctx: Context, folder_name: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for email messages within a specific Gmail folder or label."""
    logger.info(f"Executing tool: searchInFolder for folder='{folder_name}'")
    return await _execute_tool(ctx, "GMAIL_FETCH_EMAILS", query=f"in:{folder_name}", max_results=max_results)

@mcp.tool()
async def createFilter(ctx: Context, from_email: Optional[str] = None, to_email: Optional[str] = None, subject: Optional[str] = None, add_label_id: Optional[str] = None, remove_label_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Create a new Gmail filter that automatically applies actions to incoming messages."""
    logger.info(f"Executing tool: createFilter")
    return {"status": "failure", "error": "Creating filters is not currently supported via this interface."}

@mcp.tool()
async def deleteFilter(ctx: Context, filter_id: str) -> Dict[str, Any]:
    """Delete a Gmail filter."""
    logger.info(f"Executing tool: deleteFilter with filter_id='{filter_id}'")
    return {"status": "failure", "error": "Deleting filters is not currently supported."}

@mcp.tool()
async def cancelScheduled(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Cancel a scheduled email. This is done by moving the email to trash."""
    logger.info(f"Executing tool: cancelScheduled for message_id='{message_id}'")
    return await _execute_tool(ctx, "GMAIL_MOVE_TO_TRASH", message_id=message_id)

@mcp.tool()
async def catchup(ctx: Context) -> Dict[str, Any]:
    """Get a quick compact summary of all unread emails from your primary inbox."""
    logger.info("Executing tool: catchup")
    return await _execute_tool(ctx, "GMAIL_FETCH_EMAILS", query="is:unread in:inbox", max_results=20)

@mcp.tool()
async def readEmail(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Retrieve and read the content of a specific email message by its unique ID."""
    logger.info(f"Executing tool: readEmail with message_id='{message_id}'")
    return await _execute_tool(ctx, "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID", message_id=message_id)

@mcp.tool()
async def getEmailsByThread(ctx: Context, thread_id: str) -> Dict[str, Any]:
    """Retrieve all email messages that belong to the same conversation thread."""
    logger.info(f"Executing tool: getEmailsByThread with thread_id='{thread_id}'")
    return await _execute_tool(ctx, "GMAIL_FETCH_MESSAGE_BY_THREAD_ID", thread_id=thread_id)

@mcp.tool()
async def getEmailsBySender(ctx: Context, sender_email: str, max_results: int = 10) -> Dict[str, Any]:
    """Retrieve email messages from a specific sender email address."""
    logger.info(f"Executing tool: getEmailsBySender with sender_email='{sender_email}'")
    return await _execute_tool(ctx, "GMAIL_FETCH_EMAILS", query=f"from:{sender_email}", max_results=max_results)

@mcp.tool()
async def searchEmails(ctx: Context, query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for email messages using Gmail search operators and syntax."""
    logger.info(f"Executing tool: searchEmails with query='{query}'")
    return await _execute_tool(ctx, "GMAIL_FETCH_EMAILS", query=query, max_results=max_results)

@mcp.tool()
async def listLabels(ctx: Context) -> Dict[str, Any]:
    """List all available Gmail labels in the user's account."""
    logger.info("Executing tool: listLabels")
    return await _execute_tool(ctx, "GMAIL_LIST_LABELS")

@mcp.tool()
async def removeLabels(ctx: Context, message_id: str, label_ids: List[str]) -> Dict[str, Any]:
    """Remove one or more labels from a specific email message."""
    logger.info(f"Executing tool: removeLabels from message_id='{message_id}'")
    return await _execute_tool(ctx, "GMAIL_ADD_LABEL_TO_EMAIL", message_id=message_id, remove_label_ids=label_ids)

@mcp.tool()
async def updateDraft(ctx: Context, draft_id: str, to: Optional[str] = None, subject: Optional[str] = None, body: Optional[str] = None) -> Dict[str, Any]:
    """Update an existing draft email with new content."""
    logger.info(f"Executing tool: updateDraft for draft_id='{draft_id}'")
    return {"status": "failure", "error": "Updating drafts is not currently supported."}

@mcp.tool()
async def deleteDraft(ctx: Context, draft_id: str) -> Dict[str, Any]:
    """Delete a saved draft email."""
    logger.info(f"Executing tool: deleteDraft with draft_id='{draft_id}'")
    return await _execute_tool(ctx, "GMAIL_DELETE_DRAFT", draft_id=draft_id)

@mcp.tool()
async def markAsUnread(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Mark an email message as unread."""
    logger.info(f"Executing tool: markAsUnread for message_id='{message_id}'")
    return await _execute_tool(ctx, "GMAIL_ADD_LABEL_TO_EMAIL", message_id=message_id, add_label_ids=["UNREAD"])

@mcp.tool()
async def restoreFromTrash(ctx: Context, message_id: str) -> Dict[str, Any]:
    """Restore an email message from the trash to the inbox."""
    logger.info(f"Executing tool: restoreFromTrash for message_id='{message_id}'")
    return await _execute_tool(ctx, "GMAIL_ADD_LABEL_TO_EMAIL", message_id=message_id, remove_label_ids=["TRASH"])

@mcp.tool()
async def searchByDate(ctx: Context, before: Optional[str] = None, after: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
    """Search for email messages within a specific date range (YYYY/MM/DD format)."""
    logger.info(f"Executing tool: searchByDate with before='{before}', after='{after}'")
    query_parts = []
    if before: query_parts.append(f"before:{before}")
    if after: query_parts.append(f"after:{after}")
    if not query_parts: return {"status": "failure", "error": "Either 'before' or 'after' date must be provided."}
    return await _execute_tool(ctx, "GMAIL_FETCH_EMAILS", query=" ".join(query_parts), max_results=max_results)

@mcp.tool()
async def searchBySize(ctx: Context, size_mb: int, comparison: str = "larger", max_results: int = 5) -> Dict[str, Any]:
    """Search for large email messages above a specified size in MB."""
    logger.info(f"Executing tool: searchBySize with size_mb={size_mb}")
    return await _execute_tool(ctx, "GMAIL_FETCH_EMAILS", query=f"size:{size_mb}m", max_results=max_results)

@mcp.tool()
async def forwardEmail(ctx: Context, message_id: str, to: str) -> Dict[str, Any]:
    """Forward an existing email message to new recipients."""
    logger.info(f"Executing tool: forwardEmail for message_id='{message_id}' to='{to}'")
    return {"status": "failure", "error": "Forwarding emails is not currently supported."}

@mcp.tool()
async def listFilters(ctx: Context) -> Dict[str, Any]:
    """List all Gmail filters in the user's account."""
    logger.info("Executing tool: listFilters")
    return {"status": "failure", "error": "Listing filters is not currently supported."}

@mcp.tool()
async def scheduleEmail(ctx: Context, to: str, subject: str, body: str, send_at_iso: str) -> Dict[str, Any]:
    """Create an email to be sent at a specified future time (ISO 8601 format)."""
    logger.info(f"Executing tool: scheduleEmail to='{to}' at '{send_at_iso}'")
    return {"status": "failure", "error": "Scheduling emails is not currently supported."}

@mcp.tool()
async def listScheduled(ctx: Context) -> Dict[str, Any]:
    """List all scheduled emails. (Simulated)"""
    logger.info("Executing tool: listScheduled")
    return {"status": "failure", "error": "Listing scheduled emails is not currently supported."}

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9001))
    
    print(f"Starting GMail MCP Server on http://{host}:{port}")
    
    mcp.run(transport="sse", host=host, port=port)