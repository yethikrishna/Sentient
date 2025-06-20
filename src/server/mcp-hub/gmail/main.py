import os
from typing import Dict, Any, List
from dotenv import load_dotenv
from urllib.parse import quote
import base64
from email.mime.text import MIMEText
import asyncio

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from fastmcp.prompts.prompt import Message

# Local imports for modularity
from . import auth
from . import prompts
from . import utils as helpers

# Load environment variables from .env file
load_dotenv()

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


# --- Tool Definitions ---
@mcp.tool()
async def send_email(ctx: Context, to: str, subject: str, body: str) -> Dict[str, Any]:
    """Sends an email to a specified recipient."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gmail(creds)
        
        message_raw = await helpers.create_message(to, subject, body)
        message_body = {"raw": message_raw}
        
        service.users().messages().send(userId="me", body=message_body).execute()
        return {"status": "success", "result": "Email sent successfully."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def create_draft(ctx: Context, to: str, subject: str, body: str) -> Dict[str, Any]:
    """Creates a draft email."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gmail(creds)

        message_raw = await helpers.create_message(to, subject, body)
        message_body = {"message": {"raw": message_raw}}
        
        draft = service.users().drafts().create(userId="me", body=message_body).execute()
        return {"status": "success", "result": f"Draft created successfully with ID: {draft['id']}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def search_inbox(ctx: Context, query: str) -> Dict[str, Any]:
    """Searches the Gmail inbox for emails matching a query."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gmail(creds)

        def _execute_sync_search():
            results = service.users().messages().list(userId="me", q=query).execute()
            messages = results.get("messages", [])
            email_data: List[Dict[str, Any]] = []

            for message in messages[:10]:
                msg = service.users().messages().get(userId="me", id=message["id"], format="full").execute()
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                email_data.append({
                    "id": message["id"],
                    "subject": headers.get("Subject", "No Subject"),
                    "from": headers.get("From", "Unknown Sender"),
                    "snippet": msg.get("snippet", ""),
                    "body": helpers.extract_email_body(msg.get("payload", {})),
                })
            return email_data

        email_data = await asyncio.to_thread(_execute_sync_search)
        
        gmail_search_url = f"https://mail.google.com/mail/u/0/#search/{quote(query)}"
        return {
            "status": "success",
            "result": {
                "response": "Emails found successfully",
                "email_data": email_data,
                "gmail_search_url": gmail_search_url,
            },
        }
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def reply_email(ctx: Context, query: str, body: str) -> Dict[str, Any]:
    """Finds an email based on a query and sends a reply."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gmail(creds)

        match = await helpers.find_best_matching_email(service, query)
        if match["status"] != "success":
            return match

        original = match["email_details"]
        to = original.get('reply_to') or original.get('from')
        subject = f"Re: {original['subject']}"
        thread_id = original['threadId']
        
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        msg["In-Reply-To"] = original.get("message_id_header")
        msg["References"] = original.get("message_id_header")
        
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        
        service.users().messages().send(
            userId="me",
            body={"raw": raw_message, "threadId": thread_id}
        ).execute()

        return {"status": "success", "result": "Reply sent successfully."}
    except Exception as e:
        return {"status": "failure", "error": f"Error replying to email: {e}"}

@mcp.tool()
async def forward_email(ctx: Context, query: str, to: str) -> Dict[str, Any]:
    """Finds an email based on a query and forwards it."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gmail(creds)

        match = await helpers.find_best_matching_email(service, query)
        if match["status"] != "success":
            return match

        original = match["email_details"]
        subject = f"Fwd: {original['subject']}"
        body = f"-------- Forwarded message --------\nFrom: {original['from']}\nSubject: {original['subject']}\n\n{original['body']}"
        
        message_raw = await helpers.create_message(to, subject, body)
        message_body = {"raw": message_raw}
        
        service.users().messages().send(userId="me", body=message_body).execute()

        return {"status": "success", "result": f"Email forwarded to {to} successfully."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def delete_email(ctx: Context, query: str) -> Dict[str, Any]:
    """Finds and deletes an email based on a query."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gmail(creds)
        
        match = await helpers.find_best_matching_email(service, query)
        if match["status"] != "success":
            return match
            
        email_id = match["email_details"]["id"]
        service.users().messages().delete(userId="me", id=email_id).execute()
        return {"status": "success", "result": "Email deleted successfully."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def mark_email_as_read(ctx: Context, query: str) -> Dict[str, Any]:
    """Finds an email by query and marks it as read."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gmail(creds)
        
        match = await helpers.find_best_matching_email(service, query)
        if match["status"] != "success":
            return match
            
        email_id = match["email_details"]["id"]
        service.users().messages().modify(userId="me", id=email_id, body={"removeLabelIds": ["UNREAD"]}).execute()
        return {"status": "success", "result": "Email marked as read."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def mark_email_as_unread(ctx: Context, query: str) -> Dict[str, Any]:
    """Finds an email by query and marks it as unread."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gmail(creds)
        
        match = await helpers.find_best_matching_email(service, query)
        if match["status"] != "success":
            return match
            
        email_id = match["email_details"]["id"]
        service.users().messages().modify(userId="me", id=email_id, body={"addLabelIds": ["UNREAD"]}).execute()
        return {"status": "success", "result": "Email marked as unread."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def delete_spam_emails(ctx: Context) -> Dict[str, Any]:
    """Deletes all emails from the spam folder."""
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gmail(creds)
        
        results = service.users().messages().list(userId="me", q="in:spam").execute()
        messages = results.get("messages", [])

        if not messages:
            return {"status": "success", "result": "No spam messages found."}

        # Batch delete is more efficient, but for simplicity, we delete one by one
        for message in messages:
            service.users().messages().delete(userId="me", id=message["id"]).execute()
            
        return {"status": "success", "result": f"Deleted {len(messages)} spam messages."}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9001))
    
    print(f"Starting GMail MCP Server on http://{host}:{port}")
    
    mcp.run(transport="sse", host=host, port=port)