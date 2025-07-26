# src/server/mcp_hub/todoist/utils.py
from typing import Dict, Any, Optional
import httpx

TODOIST_API_BASE_URL = "https://api.todoist.com/rest/v2"

class TodoistApiClient:
    def __init__(self, token: str):
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, json: Optional[Dict] = None) -> Any:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, f"{TODOIST_API_BASE_URL}/{endpoint}", headers=self._headers, params=params, json=json)
                response.raise_for_status()
                # Some successful responses like delete might not have a body
                if response.status_code == 204:
                    return {"status": "success"}
                return response.json()
            except httpx.HTTPStatusError as e:
                raise Exception(f"Todoist API Error: {e.response.status_code} - {e.response.text}")

    async def get_projects(self):
        return await self._request("GET", "projects")

    async def get_tasks(self, project_id: Optional[str] = None, filter_str: Optional[str] = None):
        params = {}
        if project_id:
            params["project_id"] = project_id
        if filter_str:
            params["filter"] = filter_str
        return await self._request("GET", "tasks", params=params)

    async def create_task(self, content: str, project_id: Optional[str] = None, due_string: Optional[str] = None):
        json_data = {"content": content}
        if project_id:
            json_data["project_id"] = project_id
        if due_string:
            json_data["due_string"] = due_string
        return await self._request("POST", "tasks", json=json_data)

    async def close_task(self, task_id: str):
        return await self._request("POST", f"tasks/{task_id}/close")