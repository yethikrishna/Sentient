# server/mcp_hub/gmail/helpers.py

import os
import base64
from email.mime.text import MIMEText
from typing import Dict, Any, List

from google import genai
from google.genai import types
import numpy as np
from dotenv import load_dotenv
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

# Load API key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize the Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


def extract_email_body(payload: Dict[str, Any]) -> str:
    """
    Recursively extracts the body of an email from its payload.
    Prefers 'text/plain' over 'text/html'.
    """
    if "parts" in payload:
        text_plain, text_html = "", ""
        for part in payload["parts"]:
            data = part.get("body", {}).get("data")
            if not data:
                continue
            decoded = base64.urlsafe_b64decode(data).decode("utf-8")
            if part["mimeType"] == "text/plain":
                text_plain += decoded
            elif part["mimeType"] == "text/html":
                text_html += decoded
        return text_plain or text_html

    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    return ""


async def create_message(to: str, subject: str, message: str) -> str:
    """
    Creates and base64-encodes a MIME email.
    """
    msg = MIMEText(message)
    msg["To"] = to
    msg["Subject"] = subject
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")


async def find_best_matching_email(service: Resource, query: str) -> Dict[str, Any]:
    """
    Searches the user's inbox and returns the email whose subject+body
    is most semantically similar to the provided query, using Gemini embeddings.
    """
    try:
        # 1) List recent messages
        resp = service.users().messages().list(userId="me", q="in:inbox").execute()
        msgs = resp.get("messages", [])
        if not msgs:
            return {"status": "failure", "error": "No emails found in inbox."}

        # 2) Fetch full details for up to 20 messages
        email_data: List[Dict[str, Any]] = []
        for m in msgs[:20]:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="full"
            ).execute()
            headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
            body = extract_email_body(msg["payload"])
            email_data.append({
                "id": m["id"],
                "threadId": msg.get("threadId"),
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "to": headers.get("To"),
                "body": body,
            })

        # 3) Prepare the texts to embed: query + each email's subject+body
        docs = [f'{e["subject"]} {e["body"]}' for e in email_data]

        # 4) Call Gemini embed_content in a single batch for all texts
        #    This returns a list of ContentEmbedding objects in resp.embeddings
        #    We extract the .values list from each one.
        all_texts = [query] + docs
        resp = client.models.embed_content(
            model="gemini-embedding-exp-03-07",
            contents=all_texts,
            config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
        )
        embeddings = [ce.values for ce in resp.embeddings]

        # 5) Separate query embedding and doc embeddings
        q_emb = np.array(embeddings[0])
        doc_embs = np.array(embeddings[1:])

        # 6) Compute cosine similarities
        norms = np.linalg.norm(doc_embs, axis=1) * np.linalg.norm(q_emb)
        scores = (doc_embs @ q_emb) / norms
        best_idx = int(np.argmax(scores))

        # 7) Return the best matching email
        return {
            "status": "success",
            "email_details": email_data[best_idx]
        }

    except HttpError as e:
        return {"status": "failure", "error": f"Google API Error: {e}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}