import httpx
import logging
from typing import Optional, Dict
import asyncio

from main.config import WAHA_URL, WAHA_API_KEY

logger = logging.getLogger(__name__)

async def _waha_request(method: str, endpoint: str, params: Optional[Dict] = None, json: Optional[Dict] = None) -> httpx.Response:
    """Helper function to make authenticated requests to the WAHA API."""
    if not WAHA_URL or not WAHA_API_KEY:
        raise ConnectionError("WAHA_URL and WAHA_API_KEY must be configured.")
    
    headers = {"X-Api-Key": WAHA_API_KEY, "Content-Type": "application/json"}
    url = f"{WAHA_URL.rstrip('/')}{endpoint}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.request(method, url, params=params, json=json, headers=headers)
            res.raise_for_status()
            return res
        except httpx.HTTPStatusError as e:
            logger.error(f"WAHA API Error: {e.response.status_code} on {method} {url} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Could not connect to WAHA API at {url}: {e}")
            raise

async def check_phone_number_exists(phone_number: str) -> Optional[Dict]:
    """Checks if a phone number is registered on WhatsApp using WAHA."""
    try:
        response = await _waha_request("GET", "/api/contacts/check-exists", params={"phone": phone_number, "session": "default"})
        return response.json()
    except Exception:
        return None

async def send_whatsapp_message(chat_id: str, text: str) -> Optional[Dict]:
    """Sends a text message to a WhatsApp chat ID using WAHA."""
    payload = {
        "session": "default",
        "chatId": chat_id,
        "text": text
    }
    try:
        # To make it feel more human, we can simulate typing
        await _waha_request("POST", "/api/startTyping", json={"chatId": chat_id, "session": "default"})
        # A small delay
        await asyncio.sleep(1)
        response = await _waha_request("POST", "/api/sendText", json=payload)
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message to {chat_id}: {e}")
        return None