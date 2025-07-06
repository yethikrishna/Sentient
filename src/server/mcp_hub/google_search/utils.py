# server/mcp_hub/google_search/utils.py

from typing import Dict, Any, List
import httpx

GOOGLE_SEARCH_API_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

async def perform_google_search(api_key: str, cse_id: str, query: str) -> Dict[str, Any]:
    """
    Performs a web search using the Google Custom Search API.

    Args:
        api_key (str): The Google API key.
        cse_id (str): The Programmable Search Engine ID (CX).
        query (str): The user's search query.

    Returns:
        Dict[str, Any]: A dictionary containing structured search results.
    """
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": 7,  # Number of search results to return
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(GOOGLE_SEARCH_API_ENDPOINT, params=params)
            response.raise_for_status()
            data = response.json()

            # --- Format Rich Results ---
            formatted_results = {
                "search_results": [],
                "search_information": data.get("searchInformation", {})
            }

            # Format the list of web page results
            items = data.get("items", [])
            for item in items:
                formatted_results["search_results"].append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                })

            return formatted_results

        except httpx.HTTPStatusError as e:
            error_details = e.response.json().get("error", {})
            raise Exception(f"Google API Error: {error_details.get('code')} - {error_details.get('message')}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred: {e}")