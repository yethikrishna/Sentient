# server/mcp_hub/gdrive/utils.py

import base64
import io
from typing import Dict, Any
from googleapiclient.discovery import Resource
from googleapiclient.http import MediaIoBaseDownload

# Define MIME types for Google Workspace formats
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"
GOOGLE_DRAWING_MIME = "application/vnd.google-apps.drawing"

def download_and_convert_file_sync(service: Resource, file_id: str) -> Dict[str, Any]:
    """
    Downloads a file from Google Drive, converting it based on its MIME type.
    This is a synchronous function intended to be run in a separate thread.
    """
    # First, get file metadata to determine its type
    file_metadata = service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
    mime_type = file_metadata.get("mimeType")

    # Handle Google Workspace file types by exporting them
    if mime_type == GOOGLE_DOC_MIME:
        request = service.files().export_media(fileId=file_id, mimeType="text/plain")
        content = request.execute().decode("utf-8")
        return {"format": "text/markdown", "content": content} # Markdown is a superset of plain text

    if mime_type == GOOGLE_SHEET_MIME:
        request = service.files().export_media(fileId=file_id, mimeType="text/csv")
        content = request.execute().decode("utf-8")
        return {"format": "text/csv", "content": content}

    if mime_type == GOOGLE_SLIDES_MIME:
        request = service.files().export_media(fileId=file_id, mimeType="text/plain")
        content = request.execute().decode("utf-8")
        return {"format": "text/plain", "content": content}

    if mime_type == GOOGLE_DRAWING_MIME:
        request = service.files().export_media(fileId=file_id, mimeType="image/png")
        content_bytes = request.execute()
        content_b64 = base64.b64encode(content_bytes).decode("ascii")
        return {"format": "image/png (base64)", "content": content_b64}
        
    # Handle normal files (text, json, images, pdfs, etc.) by downloading them
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    
    content_bytes = fh.getvalue()
    
    # For common text-based formats, decode to string
    if mime_type in ["text/plain", "text/markdown", "application/json", "text/html", "text/xml"]:
        try:
            return {"format": "text/plain", "content": content_bytes.decode("utf-8")}
        except UnicodeDecodeError:
            # Fallback to base64 if it's not valid UTF-8
            pass

    # For all other files (binaries, pdf, images), return as base64
    content_b64 = base64.b64encode(content_bytes).decode("ascii")
    return {"format": f"{mime_type} (base64)", "content": content_b64}