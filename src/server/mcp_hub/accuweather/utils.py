# server/mcp_hub/accuweather/utils.py

import os
import json
from pathlib import Path
from typing import Dict, Optional, Any
import httpx

# --- Cache Configuration ---
CACHE_DIR = Path.home() / ".cache" / "mcp_weather"
LOCATION_CACHE_FILE = CACHE_DIR / "location_cache.json"

def get_cached_location(location_name: str) -> Optional[Dict]:
    """Get location data from cache if it exists."""
    if not LOCATION_CACHE_FILE.exists():
        return None
    try:
        with open(LOCATION_CACHE_FILE, "r") as f:
            cache = json.load(f)
            return cache.get(location_name.lower())
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def cache_location(location_name: str, location_data: Dict):
    """Cache location data for future use."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = {}
    if LOCATION_CACHE_FILE.exists():
        try:
            with open(LOCATION_CACHE_FILE, "r") as f:
                cache = json.load(f)
        except json.JSONDecodeError:
            pass  # Overwrite corrupted cache
    
    cache[location_name.lower()] = location_data
    with open(LOCATION_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

# --- API Client ---
ACCUWEATHER_BASE_URL = "http://dataservice.accuweather.com"

async def get_location_details(location_name: str, api_key: str) -> Dict:
    """
    Gets the location key and details, using a cache to avoid redundant API calls.
    """
    cached_data = get_cached_location(location_name)
    if cached_data:
        return cached_data

    async with httpx.AsyncClient() as client:
        params = {"apikey": api_key, "q": location_name}
        response = await client.get(f"{ACCUWEATHER_BASE_URL}/locations/v1/cities/search", params=params)
        response.raise_for_status()
        locations = response.json()
        
        if not locations:
            raise Exception(f"Location '{location_name}' not found.")
        
        first_location = locations[0]
        location_details = {
            "key": first_location["Key"],
            "name": first_location["LocalizedName"],
            "country": first_location["Country"]["LocalizedName"],
            "region": first_location["AdministrativeArea"]["LocalizedName"],
        }
        
        cache_location(location_name, location_details)
        return location_details

async def fetch_current_conditions(location_key: str, api_key: str) -> Dict:
    """Fetches current weather conditions for a given location key."""
    async with httpx.AsyncClient() as client:
        params = {"apikey": api_key, "details": "true"}
        response = await client.get(f"{ACCUWEATHER_BASE_URL}/currentconditions/v1/{location_key}", params=params)
        response.raise_for_status()
        conditions = response.json()
        if not conditions:
            raise Exception("Could not retrieve current conditions.")
        return conditions[0]

async def fetch_daily_forecast(location_key: str, api_key: str) -> Dict:
    """Fetches the 5-day weather forecast for a given location key."""
    async with httpx.AsyncClient() as client:
        params = {"apikey": api_key, "metric": "true"}
        response = await client.get(f"{ACCUWEATHER_BASE_URL}/forecasts/v1/daily/5day/{location_key}", params=params)
        response.raise_for_status()
        return response.json()