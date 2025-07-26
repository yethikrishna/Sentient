import httpx
import logging
from typing import Optional, Dict
import asyncio
import os

from dotenv import load_dotenv

# Load .env file for 'dev-local' environment.
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path, override=True)

WAHA_URL = os.getenv("WAHA_URL")
WAHA_API_KEY = os.getenv("WAHA_API_KEY")

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

async def send_whatsapp_message(chat_id: str, text: str) -> Optional[Dict]:
    """Sends a text message to a WhatsApp chat ID using WAHA."""
    payload = {
        "session": "default",
        "chatId": chat_id,
        "text": text
    }
    try:
        await _waha_request("POST", "/api/startTyping", json={"chatId": chat_id, "session": "default"})
        await asyncio.sleep(1)
        response = await _waha_request("POST", "/api/sendText", json=payload)
        return response.json()
