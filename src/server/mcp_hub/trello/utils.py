# src/server/mcp_hub/trello/utils.py
import httpx
from typing import Dict, Any, Optional

TRELLO_API_BASE_URL = "https://api.trello.com/1"

async def _make_request(creds: Dict, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None):
    auth_params = {"key": creds["api_key"], "token": creds["token"]}
    full_params = {**auth_params, **(params or {})}
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            f"{TRELLO_API_BASE_URL}{endpoint}",
            params=full_params,
            json=json_data
        )
        response.raise_for_status()
        return response.json()

async def list_boards_util(creds: Dict, **kwargs):
    boards = await _make_request(creds, "GET", "/members/me/boards")
    return [{"id": b["id"], "name": b["name"]} for b in boards]

async def get_lists_on_board_util(creds: Dict, board_id: str):
    lists = await _make_request(creds, "GET", f"/boards/{board_id}/lists")
    return [{"id": l["id"], "name": l["name"]} for l in lists]

async def get_cards_in_list_util(creds: Dict, list_id: str):
    cards = await _make_request(creds, "GET", f"/lists/{list_id}/cards")
    return [{"id": c["id"], "name": c["name"], "desc": c["desc"]} for c in cards]

async def create_card_util(creds: Dict, list_id: str, name: str, desc: Optional[str] = None):
    params = {"idList": list_id, "name": name}
    if desc:
        params["desc"] = desc
    return await _make_request(creds, "POST", "/cards", params=params)