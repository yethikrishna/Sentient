import os
import asyncio
import json
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from fastmcp.prompts.prompt import Message

from . import auth, prompts, utils

# Load environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="GPeopleServer",
    instructions="This server provides tools to interact with the Google People API for managing contacts.",
)

# --- Tool Helper ---
async def _execute_tool(ctx: Context, func, *args, **kwargs) -> Dict[str, Any]:
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)
        service = auth.authenticate_gpeople(creds)
        
        # Use asyncio.to_thread to run synchronous Google API calls
        result = await asyncio.to_thread(func, service, *args, **kwargs)
        
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Tool Implementations (Sync wrappers) ---
def _search_contacts_sync(service, query: str):
    # Use the searchContacts endpoint to search for contacts
    results = service.people().searchContacts(
        query=query,
        pageSize=10,
        readMask='names,emailAddresses,phoneNumbers'
    ).execute()

    # Extract contacts from the results
    connections = results.get('results', [])
    return [utils._simplify_person(p.get('person', {})) for p in connections]

def _create_contact_sync(service, given_name: str, family_name: Optional[str], email_address: Optional[str], phone_number: Optional[str]):
    contact_body = {
        "names": [{"givenName": given_name, "familyName": family_name}],
    }
    if email_address:
        contact_body["emailAddresses"] = [{"value": email_address}]
    if phone_number:
        contact_body["phoneNumbers"] = [{"value": phone_number}]
        
    created_contact = service.people().createContact(body=contact_body).execute()
    return utils._simplify_person(created_contact)

def _delete_contact_sync(service, resource_name: str):
    service.people().deleteContact(resourceName=resource_name).execute()
    return f"Contact {resource_name} deleted successfully."

def _update_contact_field_sync(service, resource_name: str, field_to_update: str, new_value: str):
    # This is a simplified update. It gets the contact, updates a field, and then sends the update.
    # It requires the etag for the update to succeed.
    original_person = service.people().get(
        resourceName=resource_name,
        personFields='names,emailAddresses,phoneNumbers,metadata'
    ).execute()
    
    etag = original_person.get("etag")
    if not etag:
        raise ToolError("Could not retrieve etag for contact, cannot update.")

    updated_person = original_person.copy()
    update_mask_parts = []

    if field_to_update == "email":
        updated_person["emailAddresses"] = [{"value": new_value}]
        update_mask_parts.append("emailAddresses")
    elif field_to_update == "phone":
        updated_person["phoneNumbers"] = [{"value": new_value}]
        update_mask_parts.append("phoneNumbers")
    elif field_to_update == "name":
        # Assumes new_value is "Given Family"
        parts = new_value.split(" ", 1)
        given = parts[0]
        family = parts[1] if len(parts) > 1 else ""
        updated_person["names"] = [{"givenName": given, "familyName": family}]
        update_mask_parts.append("names")
    else:
        raise ToolError(f"Unsupported field for update: {field_to_update}. Can be 'email', 'phone', or 'name'.")
    
    updated_person['etag'] = etag
    
    response = service.people().updateContact(
        resourceName=resource_name,
        body=updated_person,
        updatePersonFields=",".join(update_mask_parts)
    ).execute()
    
    return utils._simplify_person(response)


# --- Tool Definitions ---
@mcp.tool
async def search_contacts(ctx: Context, query: str) -> Dict:
    """Searches for contacts by name, email, or phone number."""
    return await _execute_tool(ctx, _search_contacts_sync, query=query)

@mcp.tool
async def create_contact(ctx: Context, given_name: str, family_name: Optional[str] = None, email_address: Optional[str] = None, phone_number: Optional[str] = None) -> Dict:
    """Creates a new contact with a name and optional email/phone."""
    return await _execute_tool(ctx, _create_contact_sync, given_name=given_name, family_name=family_name, email_address=email_address, phone_number=phone_number)

@mcp.tool
async def delete_contact(ctx: Context, resource_name: str) -> Dict:
    """Deletes a contact using their resourceName. Use search_contacts first to get the resourceName."""
    return await _execute_tool(ctx, _delete_contact_sync, resource_name=resource_name)

@mcp.tool
async def update_contact_field(ctx: Context, resource_name: str, field_to_update: str, new_value: str) -> Dict:
    """
    Updates a specific field for a contact.
    'field_to_update' can be 'email', 'phone', or 'name'.
    Use search_contacts first to get the resourceName.
    For 'name', provide the full name like 'John Doe' as the new_value.
    """
    return await _execute_tool(ctx, _update_contact_field_sync, resource_name=resource_name, field_to_update=field_to_update, new_value=new_value)


# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9019))
    
    print(f"Starting Google People MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)