import asyncio
from typing import Dict, Any, Optional
from googleapiclient.discovery import Resource

def _simplify_person(person: Dict) -> Dict:
    """Simplifies a Person resource for easier consumption by an LLM."""
    names = person.get("names", [{}])
    emails = person.get("emailAddresses", [{}])
    phones = person.get("phoneNumbers", [{}])
    
    return {
        "resourceName": person.get("resourceName"),
        "etag": person.get("etag"),
        "displayName": names[0].get("displayName", "N/A"),
        "email": emails[0].get("value", "N/A"),
        "phone": phones[0].get("value", "N/A"),
    }

async def find_contact_by_query(service: Resource, query: str) -> Optional[Dict]:
    """Finds a single contact by query."""
    def _search():
        results = service.people().connections().list(
            resourceName='people/me',
            pageSize=1,
            personFields='names,emailAddresses,phoneNumbers',
            query=query
        ).execute()
        return results.get('connections', [])

    connections = await asyncio.to_thread(_search)
    return connections[0] if connections else None