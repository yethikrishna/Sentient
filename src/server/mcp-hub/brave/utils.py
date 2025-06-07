# server/mcp-hub/brave/utils.py

from typing import Dict, Any, List
import httpx

BRAVE_API_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

async def perform_brave_search(api_key: str, query: str) -> Dict[str, Any]:
    """
    Performs a web search using the Brave Search API and formats the results.

    Args:
        api_key (str): The Brave Search API subscription token.
        query (str): The user's search query.

    Returns:
        Dict[str, Any]: A dictionary containing structured search results.
    """
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": query,
        "count": 7,  # Get a good number of results
        "safesearch": "moderate",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                BRAVE_API_ENDPOINT, headers=headers, params=params
            )
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
            data = response.json()

            # --- Format Rich Results ---
            formatted_results = {
                "search_results": [],
                "faq": []
            }

            # 1. Format standard web results
            web_pages = data.get("web", {}).get("results", [])
            for page in web_pages:
                formatted_results["search_results"].append({
                    "title": page.get("title"),
                    "url": page.get("url"),
                    "description": page.get("description"),
                })
            
            # 2. Format FAQ results, if they exist
            faq_items = data.get("faq", {}).get("results", [])
            for item in faq_items:
                formatted_results["faq"].append({
                    "question": item.get("question"),
                    "answer": item.get("answer"),
                    "title": item.get("title"),
                    "url": item.get("url"),
                })

            return formatted_results

        except httpx.HTTPStatusError as e:
            # Provide a more user-friendly error message
            error_details = e.response.json()
            raise Exception(f"Brave API Error: {e.response.status_code} - {error_details.get('type')}: {error_details.get('title')}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred: {e}")