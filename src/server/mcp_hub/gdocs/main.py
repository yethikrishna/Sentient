import os
import asyncio
import json
from typing import Dict, Any, Optional, List

from dotenv import load_dotenv
from fastmcp import FastMCP, Context
from googleapiclient.errors import HttpError
from fastmcp.utilities.logging import configure_logging, get_logger

from . import auth, prompts, utils

# --- Standardized Logging Setup ---
configure_logging(level="INFO")
logger = get_logger(__name__)

# --- LLM and Environment Configuration ---
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev-local')
if ENVIRONMENT == 'dev-local':
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

mcp = FastMCP(
    name="GDocsServer",
    instructions="Provides tools to create, search, read, modify, and share Google Docs documents.",
)

@mcp.resource("prompt://gdocs-agent-system")
def get_gdocs_system_prompt() -> str:
    """Provides the system prompt that instructs the main orchestrator agent on how to use the gdocs tools."""
    return prompts.MAIN_AGENT_SYSTEM_PROMPT

async def _execute_tool(ctx: Context, func, service_types=['docs', 'drive'], **kwargs):
    try:
        user_id = auth.get_user_id_from_context(ctx)
        creds = await auth.get_google_creds(user_id)

        services = {}
        if 'docs' in service_types:
            services['docs_service'] = auth.authenticate_gdocs(creds)
        if 'drive' in service_types:
            services['drive_service'] = auth.authenticate_gdrive(creds)

        # Run the synchronous function in a separate thread
        result = await asyncio.to_thread(func, **services, **kwargs)
        return {"status": "success", "result": result}
    except HttpError as e:
        return {"status": "failure", "error": f"Google API Error: {e.content.decode()}"}
    except Exception as e:
        logger.error(f"Tool execution failed for '{func.__name__}': {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}

@mcp.tool()
async def createDocument(ctx: Context, title: str) -> Dict[str, Any]:
    """
    Creates a new, empty Google Docs document with a specified title.
    """
    logger.info(f"Executing tool: createDocument with title='{title}'")
    def _create(docs_service, title):
        doc = docs_service.documents().create(body={"title": title}).execute()
        return {"documentId": doc["documentId"], "title": doc["title"]}
    return await _execute_tool(ctx, _create, service_types=['docs'], title=title)

@mcp.tool()
async def listDocuments(ctx: Context, query: Optional[str] = None) -> Dict[str, Any]:
    """
    Searches for Google Docs documents in the user's Drive. Can be filtered by a search `query` in the document's name or content.
    """
    logger.info(f"Executing tool: listDocuments with query='{query}'")
    def _list(drive_service, query):
        q = "mimeType='application/vnd.google-apps.document'"
        if query:
            q += f" and name contains '{query}'"
        response = drive_service.files().list(q=q, pageSize=20, fields="files(id, name, webViewLink)").execute()
        return [utils._simplify_document_list_entry(f) for f in response.get("files", [])]
    return await _execute_tool(ctx, _list, service_types=['drive'], query=query)

@mcp.tool()
async def getDocument(ctx: Context, document_id: str) -> Dict[str, Any]:
    """
    Retrieves the full content of a Google Docs document as plain text, given its `document_id`.
    """
    logger.info(f"Executing tool: getDocument with document_id='{document_id}'")
    def _get(docs_service, document_id):
        doc = docs_service.documents().get(documentId=document_id).execute()
        return {"title": doc.get("title"), "content": utils._parse_document_content(doc)}
    return await _execute_tool(ctx, _get, service_types=['docs'], document_id=document_id)

@mcp.tool()
async def deleteDocument(ctx: Context, document_id: str) -> Dict[str, Any]:
    """
    Permanently deletes a Google Docs document. Requires the `document_id`.
    """
    logger.info(f"Executing tool: deleteDocument with document_id='{document_id}'")
    def _delete(drive_service, document_id):
        drive_service.files().delete(fileId=document_id).execute()
        return {"message": f"Document {document_id} deleted successfully."}
    return await _execute_tool(ctx, _delete, service_types=['drive'], document_id=document_id)

@mcp.tool()
async def shareDocument(ctx: Context, document_id: str, email_address: str, role: str = "reader", share_type: str = "user") -> Dict[str, Any]:
    """
    Shares a Google Docs document with a specific user via their `email_address`. The `role` can be 'reader', 'commenter', or 'writer'.
    """
    logger.info(f"Executing tool: shareDocument for document_id='{document_id}' with email='{email_address}'")
    def _share(drive_service, document_id, email_address, role, share_type):
        permission = {'type': share_type, 'role': role, 'emailAddress': email_address}
        drive_service.permissions().create(fileId=document_id, body=permission, sendNotificationEmail=True).execute()
        return {"message": f"Document {document_id} shared with {email_address} as a {role}."}
    return await _execute_tool(ctx, _share, service_types=['drive'], document_id=document_id, email_address=email_address, role=role, share_type=share_type)

@mcp.tool()
async def appendText(ctx: Context, document_id: str, text: str) -> Dict[str, Any]:
    """
    Adds new text to the very end of a specified Google Docs document.
    """
    logger.info(f"Executing tool: appendText to document_id='{document_id}'")
    def _append(docs_service, document_id, text):
        doc = docs_service.documents().get(documentId=document_id, fields="body(content)").execute()
        end_index = doc['body']['content'][-1]['endIndex'] - 1
        requests = [{'insertText': {'location': {'index': end_index}, 'text': f"\n{text}"}}]
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
        return {"message": "Text appended successfully."}
    return await _execute_tool(ctx, _append, service_types=['docs'], document_id=document_id, text=text)

@mcp.tool()
async def insertText(ctx: Context, document_id: str, text: str, index: int) -> Dict[str, Any]:
    """
    Inserts text at a specific character `index` within a Google Docs document.
    """
    logger.info(f"Executing tool: insertText at index={index} in document_id='{document_id}'")
    def _insert(docs_service, document_id, text, index):
        requests = [{'insertText': {'location': {'index': index}, 'text': text}}]
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
        return {"message": "Text inserted successfully."}
    return await _execute_tool(ctx, _insert, service_types=['docs'], document_id=document_id, text=text, index=index)

@mcp.tool()
async def replaceText(ctx: Context, document_id: str, find_text: str, replace_text: str) -> Dict[str, Any]:
    """
    Finds and replaces all occurrences of a specific string (`find_text`) with a new string (`replace_text`) within a document.
    """
    logger.info(f"Executing tool: replaceText in document_id='{document_id}'")
    def _replace(docs_service, document_id, find_text, replace_text):
        requests = [{'replaceAllText': {'containsText': {'text': find_text, 'matchCase': False}, 'replaceText': replace_text}}]
        response = docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
        return {"message": f"Text replaced. Occurrences: {response['replies'][0]['replaceAllText']['occurrencesChanged']}"}
    return await _execute_tool(ctx, _replace, service_types=['docs'], document_id=document_id, find_text=find_text, replace_text=replace_text)

if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9004))
    
    print(f"Starting GDocs MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)