from typing import Dict, Any, Optional
import httpx

EVERNOTE_API_BASE = "https://sandbox.evernote.com/api/v1"

class EvernoteApiClient:
    def __init__(self, token: str):
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, json: Optional[Dict] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, f"{EVERNOTE_API_BASE}{endpoint}", headers=self._headers, params=params, json=json)
                response.raise_for_status()
                if response.status_code == 204: # No Content
                    return {"status": "success"}
                return response.json()
            except httpx.HTTPStatusError as e:
                error_text = e.response.text
                try:
                    error_json = e.response.json()
                    error_message = error_json.get("error", str(e))
                except:
                    error_message = error_text
                raise Exception(f"Evernote API Error: {e.response.status_code} - {error_message}")

    async def list_notebooks(self) -> Dict:
        return await self._request("GET", "/notebooks")

    async def create_note(self, notebook_id: str, title: str, content: str) -> Dict:
        note_body = {
            "notebookGuid": notebook_id,
            "title": title,
            "content": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
                f'<en-note>{content}</en-note>'
            )
        }
        return await self._request("POST", "/notes", json=note_body)
