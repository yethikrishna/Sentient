import httpx
from typing import Dict, Any, Optional

from google.oauth2.credentials import Credentials

PLACES_API_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
DIRECTIONS_API_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"

async def search_places_util(creds: Credentials, query: str) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": creds.client_id, # Can use client_id from OAuth creds as API key in some cases
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.id",
        "Authorization": f"Bearer {creds.token}",
    }
    data = {"textQuery": query, "maxResultCount": 5}

    async with httpx.AsyncClient() as client:
        response = await client.post(PLACES_API_ENDPOINT, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

async def get_directions_util(creds: Credentials, origin: str, destination: str, mode: str) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": creds.client_id,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.legs.steps.navigationInstruction",
        "Authorization": f"Bearer {creds.token}",
    }
    data = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": mode.upper(),
        "computeAlternativeRoutes": False,
        "units": "METRIC"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(DIRECTIONS_API_ENDPOINT, headers=headers, json=data)
        response.raise_for_status()
        return response.json()