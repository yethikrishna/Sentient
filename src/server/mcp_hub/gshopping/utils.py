from typing import Dict, Any
import httpx

# The Google Shopping search can be powered by the Custom Search API,
# similar to the general google_search MCP.
GOOGLE_SEARCH_API_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

async def perform_shopping_search(api_key: str, cse_id: str, query: str) -> Dict[str, Any]:
    """
    Performs a product search using the Google Custom Search API.
    """
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": 5,  # Return up to 5 product results
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(GOOGLE_SEARCH_API_ENDPOINT, params=params)
            response.raise_for_status()
            data = response.json()

            formatted_results = {
                "products": [],
            }

            items = data.get("items", [])
            for item in items:
                # Extract product-specific information if available
                pagemap = item.get("pagemap", {})
                product_info = pagemap.get("product", [{}])[0]
                offer_info = pagemap.get("offer", [{}])[0]

                formatted_results["products"].append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet"),
                    "price": offer_info.get("price"),
                    "currency": offer_info.get("pricecurrency"),
                    "brand": product_info.get("brand"),
                })

            return formatted_results

        except httpx.HTTPStatusError as e:
            error_details = e.response.json().get("error", {})
            raise Exception(f"Google API Error: {error_details.get('code')} - {error_details.get('message')}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred: {e}")