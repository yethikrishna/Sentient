# server/mcp_hub/slack/utils.py

from typing import Dict, Any, Optional
import httpx

SLACK_API_BASE = "https://slack.com/api/"

class SlackApiClient:
    def __init__(self, token: str, team_id: str):
        self._headers = {"Authorization": f"Bearer {token}"}
        self._team_id = team_id

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, json: Optional[Dict] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                if method == "GET":
                    response = await client.get(f"{SLACK_API_BASE}{endpoint}", headers=self._headers, params=params)
                else: # POST
                    response = await client.post(f"{SLACK_API_BASE}{endpoint}", headers=self._headers, json=json)
                
                response.raise_for_status()
                data = response.json()

                if not data.get("ok"):
                    raise Exception(f"Slack API Error: {data.get('error', 'Unknown error')}")
                
                return data
            except httpx.HTTPStatusError as e:
                raise Exception(f"HTTP Error: {e.response.status_code} - {e.response.text}")

    async def list_channels(self, limit: int = 100, cursor: Optional[str] = None) -> Dict:
        params = {
            "types": "public_channel",
            "exclude_archived": "true",
            "limit": min(limit, 200),
            "team_id": self._team_id
        }
        if cursor: params["cursor"] = cursor
        return await self._request("GET", "conversations.list", params=params)

    async def post_message(self, channel_id: str, text: str) -> Dict:
        json = {"channel": channel_id, "text": text}
        return await self._request("POST", "chat.postMessage", json=json)

    async def reply_to_thread(self, channel_id: str, thread_ts: str, text: str) -> Dict:
        json = {"channel": channel_id, "thread_ts": thread_ts, "text": text}
        return await self._request("POST", "chat.postMessage", json=json)
    
    async def add_reaction(self, channel_id: str, timestamp: str, reaction: str) -> Dict:
        json = {"channel": channel_id, "timestamp": timestamp, "name": reaction}
        return await self._request("POST", "reactions.add", json=json)
        
    async def get_channel_history(self, channel_id: str, limit: int = 10) -> Dict:
        params = {"channel": channel_id, "limit": limit}
        return await self._request("GET", "conversations.history", params=params)

    async def get_thread_replies(self, channel_id: str, thread_ts: str) -> Dict:
        params = {"channel": channel_id, "ts": thread_ts}
        return await self._request("GET", "conversations.replies", params=params)

    async def get_users(self, limit: int = 100, cursor: Optional[str] = None) -> Dict:
        params = {"limit": min(limit, 200), "team_id": self._team_id}
        if cursor: params["cursor"] = cursor
        return await self._request("GET", "users.list", params=params)

    async def get_user_profile(self, user_id: str) -> Dict:
        params = {"user": user_id}
        return await self._request("GET", "users.profile.get", params=params)