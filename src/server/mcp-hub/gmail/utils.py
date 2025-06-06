# server/mcp-hub/gmail/helpers.py

import base64
from email.mime.text import MIMEText
from typing import Dict, Any, List
import httpx
from sentence_transformers import SentenceTransformer, util
from urllib.parse import quote
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError


def extract_email_body(payload: Dict[str, Any]) -> str:
    """
    Recursively extracts the body of an email from its payload.
    It prioritizes 'text/plain', then 'text/html'.

    Args:
        payload (Dict[str, Any]): The payload of a Gmail message.

    Returns:
        str: The decoded email body.
    """
    if "parts" in payload:
        # It's a multipart message, iterate through parts
        text_plain_content = ""
        text_html_content = ""
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                text_plain_content += base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            elif part["mimeType"] == "text/html":
                text_html_content += base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
        
        # Prefer plain text over HTML
        return text_plain_content if text_plain_content else text_html_content
    elif "body" in payload and "data" in payload["body"]:
        # Single part message
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    
    return ""


async def create_message(to: str, subject: str, message: str) -> str:
    """
    Creates a MIME message for an email and encodes it.

    Args:
        to (str): Recipient email address.
        subject (str): Email subject.
        message (str): Email body text.

    Returns:
        str: Raw, URL-safe base64 encoded MIME message.
    """
    try:
        # The external elaborator service call can be added back here if needed
        # For now, we use the message directly for simplicity.
        
        # Elaborator call example (if you run the service):
        # async with httpx.AsyncClient() as client:
        #     response = await client.post("http://localhost:5000/elaborator", json={...})
        #     elaborated_message = response.json().get("message", message)
        
        msg = MIMEText(message)
        msg["To"] = to
        msg["Subject"] = subject
        return urlsafe_b64encode(msg.as_bytes()).decode()
    except Exception as error:
        raise Exception(f"Error creating message: {error}")


async def find_best_matching_email(service: Resource, query: str) -> Dict[str, Any]:
    """
    Searches inbox and finds the best matching email based on semantic similarity.

    Args:
        service (Resource): Authenticated Gmail API service.
        query (str): The query string to compare against email content.

    Returns:
        Dict[str, Any]: A dictionary containing the status and details of the best match.
    """
    try:
        results = service.users().messages().list(userId="me", q="in:inbox").execute()
        messages = results.get("messages", [])

        if not messages:
            return {"status": "failure", "error": "No recent emails found in inbox."}

        email_data: List[Dict[str, Any]] = []
        for message in messages[:20]: # Search more messages for better matching
            msg = service.users().messages().get(userId="me", id=message["id"], format="full").execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            email_body = extract_email_body(msg.get("payload", {}))

            email_data.append({
                "id": message["id"],
                "threadId": msg.get("threadId"),
                "subject": headers.get("Subject", "No Subject"),
                "from": headers.get("From", "Unknown Sender"),
                "to": headers.get("To"),
                "reply_to": headers.get("Reply-To"),
                "message_id_header": headers.get("Message-ID"),
                "snippet": msg.get("snippet", ""),
                "body": email_body,
            })

        model = SentenceTransformer("all-MiniLM-L6-v2")
        query_embedding = model.encode(query, convert_to_tensor=True)
        email_embeddings = model.encode([e["subject"] + " " + e["body"] for e in email_data], convert_to_tensor=True)

        scores = util.pytorch_cos_sim(query_embedding, email_embeddings)[0]
        best_match_index = scores.argmax().item()
        best_email = email_data[best_match_index]

        return {"status": "success", "email_details": best_email}

    except HttpError as error:
        return {"status": "failure", "error": f"Google API Error: {error}"}
    except Exception as error:
        return {"status": "failure", "error": str(error)}