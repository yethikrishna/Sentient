from typing import Dict, Any, Optional
import httpx

DISCORD_API_BASE = "https://discord.com/api/v10"

class DiscordApiClient:
    def __init__(self, bot_token: str):
        self._headers = {"Authorization": f"Bot {bot_token}"}

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, json: Optional[Dict] = None) -> Any:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, f"{DISCORD_API_BASE}{endpoint}", headers=self._headers, params=params, json=json)
                response.raise_for_status()
                # Some Discord API calls return 204 No Content on success
                if response.status_code == 204:
                    return {"status": "success"}
                return response.json()
            except httpx.HTTPStatusError as e:
                raise Exception(f"Discord API Error: {e.response.status_code} - {e.response.text}")

    async def list_guilds(self) -> Any:
        return await self._request("GET", "/users/@me/guilds")

    async def list_channels(self, guild_id: str) -> Any:
        return await self._request("GET", f"/guilds/{guild_id}/channels")

    async def send_channel_message(self, channel_id: str, content: str) -> Any:
        json_payload = {"content": content}
        return await self._request("POST", f"/channels/{channel_id}/messages", json=json_payload)

    async def get_user_info(self) -> Any:
        # Note: this uses the user's access token, not the bot token.
        # This class will primarily use the bot token. Getting user info is more complex.
        # Let's stick to bot actions.
        pass