import os
import io
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple

import httpx
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

async def search_unsplash_image(query: str) -> Optional[str]:
    """Search for an image on Unsplash and return its URL."""
    if not UNSPLASH_ACCESS_KEY:
        print("Warning: UNSPLASH_ACCESS_KEY not set. Cannot search for images.")
        return None
    
    url = f"https://api.unsplash.com/search/photos?query={query}&per_page=1"
    headers = {'Authorization': f'Client-ID {UNSPLASH_ACCESS_KEY}'}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data.get("results"):
                return data["results"][0]["urls"]["regular"]
    except Exception as e:
        print(f"Error searching Unsplash: {e}")
    return None

async def upload_image_to_drive(drive_service: Resource, image_url: str, file_name: str) -> Optional[str]:
    """Download an image from a URL and upload it to Google Drive."""
    try:
        async with httpx.AsyncClient() as client:
            image_response = await client.get(image_url, follow_redirects=True)
            image_response.raise_for_status()
            image_bytes = image_response.content
        
        file_metadata = {'name': file_name}
        media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype='image/jpeg')
        
        def _upload():
            return drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        uploaded_file = await asyncio.to_thread(_upload)
        file_id = uploaded_file.get('id')
        
        def _make_public():
            permission = {'type': 'anyone', 'role': 'reader'}
            drive_service.permissions().create(fileId=file_id, body=permission).execute()
        
        await asyncio.to_thread(_make_public)
        return f"https://drive.google.com/uc?id={file_id}"
    except Exception as e:
        print(f"Failed to upload image to Google Drive: {e}")
        return None

def create_google_document_sync(docs_service: Resource, drive_service: Resource, title: str, sections: List[Dict]) -> Dict:
    """Synchronous logic to create a Google Doc."""
    try:
        doc = docs_service.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        
        requests = []
        index = 1

        for section in sections:
            if 'heading' in section:
                heading_text = f"{section['heading']}\n"
                requests.append({"insertText": {"location": {"index": index}, "text": heading_text}})
                requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": index, "endIndex": index + len(heading_text) - 1},
                        "paragraphStyle": {"namedStyleType": section.get('heading_level', 'HEADING_2').upper()},
                        "fields": "namedStyleType"
                    }
                })
                index += len(heading_text)

            if 'paragraphs' in section:
                for para in section['paragraphs']:
                    para_text = f"{para}\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": para_text}})
                    index += len(para_text)

            if 'bullet_points' in section:
                for bullet in section['bullet_points']:
                    bullet_text = f"{bullet}\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": bullet_text}})
                    requests.append({
                        "createParagraphBullets": {
                            "range": {"startIndex": index, "endIndex": index + len(bullet_text) - 1},
                            "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
                        }
                    })
                    index += len(bullet_text)
        
        if requests:
            docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()

        return {"status": "success", "result": {"message": f"Document '{title}' created.", "url": doc_url}}
    except HttpError as e:
        return {"status": "failure", "error": f"Google API Error: {e.content.decode()}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}