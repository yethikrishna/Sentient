from typing import Dict, Any, Optional
import httpx

NEWS_API_BASE_URL = "https://newsapi.org/v2"

async def _make_api_request(endpoint: str, api_key: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Helper function to make requests to the NewsAPI."""
    if params is None:
        params = {}
    headers = {"X-Api-Key": api_key}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{NEWS_API_BASE_URL}/{endpoint}", params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "ok":
                raise Exception(f"NewsAPI Error: {data.get('message', 'Unknown error')}")
            return data
        except httpx.HTTPStatusError as e:
            error_details = e.response.json()
            raise Exception(f"NewsAPI HTTP Error: {e.response.status_code} - {error_details.get('message')}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred: {e}")

def _simplify_articles(articles: list) -> list:
    """Simplifies the article list for the LLM."""
    simplified = []
    for article in articles:
        simplified.append({
            "source": article.get("source", {}).get("name"),
            "author": article.get("author"),
            "title": article.get("title"),
            "description": article.get("description"),
            "url": article.get("url"),
            "published_at": article.get("publishedAt"),
        })
    return simplified

async def fetch_top_headlines(api_key: str, query: Optional[str] = None, category: Optional[str] = None, country: str = 'us') -> Dict[str, Any]:
    """Fetches top headlines from NewsAPI."""
    params = {"country": country, "pageSize": 10}
    if query:
        params["q"] = query
    if category:
        params["category"] = category
    
    data = await _make_api_request("top-headlines", api_key, params)
    return {"articles": _simplify_articles(data.get("articles", []))}

async def search_everything(api_key: str, query: str, language: str = 'en', sort_by: str = 'relevancy') -> Dict[str, Any]:
    """Searches for news articles across all sources."""
    params = {
        "q": query,
        "language": language,
        "sortBy": sort_by,
        "pageSize": 10,
    }
    data = await _make_api_request("everything", api_key, params)
    return {"articles": _simplify_articles(data.get("articles", []))}