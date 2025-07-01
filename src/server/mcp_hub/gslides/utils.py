import os
import io
import asyncio
from typing import Dict, Any, List, Optional
import httpx
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
import matplotlib.pyplot as plt

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

async def search_unsplash_image(query: str) -> Optional[str]:
    """Asynchronously searches for an image on Unsplash."""
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

async def add_image_from_url_to_slide(slides_service: Resource, drive_service: Resource, presentation_id: str, slide_id: str, image_url: str):
    """Downloads an image and adds it to a slide."""
    try:
        async with httpx.AsyncClient() as client:
            image_response = await client.get(image_url, follow_redirects=True)
            image_response.raise_for_status()
        
        file_name = f'slide_image_{slide_id}.jpg'
        image_bytes = image_response.content
        return await add_image_from_bytes_to_slide(slides_service, drive_service, presentation_id, slide_id, image_bytes, file_name, 'image/jpeg')
    except Exception as e:
        print(f"Failed to add image from URL: {e}")

def generate_chart_bytes(chart_type: str, categories: List[str], data: List[float]) -> bytes:
    """Generates a chart image and returns its bytes."""
    plt.figure(figsize=(6, 4))
    if chart_type == "bar": plt.bar(categories, data)
    elif chart_type == "pie": plt.pie(data, labels=categories, autopct='%1.1f%%')
    elif chart_type == "line": plt.plot(categories, data)
    else: raise ValueError(f"Unsupported chart type: {chart_type}")
    plt.title("Chart")
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return buf.getvalue()

async def add_image_from_bytes_to_slide(slides_service: Resource, drive_service: Resource, presentation_id: str, slide_id: str, image_bytes: bytes, file_name: str, mimetype: str):
    """Uploads image bytes to Drive and then adds to slide."""
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=mimetype)
    uploaded_file = await asyncio.to_thread(lambda: drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute())
    file_id = uploaded_file.get('id')
    
    await asyncio.to_thread(lambda: drive_service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute())
    image_url_on_drive = f"https://drive.google.com/uc?id={file_id}"

    create_image_request = {
        "createImage": {
            "url": image_url_on_drive,
            "elementProperties": {
                "pageObjectId": slide_id,
                "size": {"width": {"magnitude": 450, "unit": "PT"}, "height": {"magnitude": 300, "unit": "PT"}},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": 50, "translateY": 150, "unit": "PT"}
            }
        }
    }
    await asyncio.to_thread(lambda: slides_service.presentations().batchUpdate(presentationId=presentation_id, body={"requests": [create_image_request]}).execute())

async def create_presentation_from_outline(slides_service: Resource, drive_service: Resource, outline: Dict[str, Any]) -> Dict[str, Any]:
    """The main logic to create the presentation, adapted for async execution."""
    try:
        title = outline.get("topic", "Untitled Presentation")
        user_name = outline.get("username", "Sentient User")
        
        presentation_body = {'title': title}
        presentation = await asyncio.to_thread(lambda: slides_service.presentations().create(body=presentation_body).execute())
        presentation_id = presentation.get('presentationId')
        presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"

        # Update Title Slide
        title_slide_id = presentation['slides'][0]['objectId']
        title_placeholder_id = presentation['slides'][0]['pageElements'][0]['objectId']
        subtitle_placeholder_id = presentation['slides'][0]['pageElements'][1]['objectId']
        
        requests = [
            {"insertText": {"objectId": title_placeholder_id, "text": title}},
            {"insertText": {"objectId": subtitle_placeholder_id, "text": f"Created by {user_name}"}}
        ]
        await asyncio.to_thread(lambda: slides_service.presentations().batchUpdate(presentationId=presentation_id, body={'requests': requests}).execute())

        # Create Content Slides
        for slide_data in outline.get('slides', []):
            create_slide_request = {"createSlide": {"slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"}}}
            response = await asyncio.to_thread(lambda: slides_service.presentations().batchUpdate(presentationId=presentation_id, body={"requests": [create_slide_request]}).execute())
            new_slide_id = response['replies'][0]['createSlide']['objectId']
            
            # Refetch to get placeholders
            new_slide_page = await asyncio.to_thread(lambda: slides_service.presentations().pages().get(presentationId=presentation_id, pageObjectId=new_slide_id).execute())
            title_id = new_slide_page['pageElements'][0]['objectId']
            body_id = new_slide_page['pageElements'][1]['objectId']
            
            slide_content_text = "\n".join(slide_data.get('content', []))
            slide_requests = [
                {"insertText": {"objectId": title_id, "text": slide_data.get('title', ' ')}},
                {"insertText": {"objectId": body_id, "text": slide_content_text}}
            ]
            await asyncio.to_thread(lambda: slides_service.presentations().batchUpdate(presentationId=presentation_id, body={'requests': slide_requests}).execute())

            # Handle image
            if 'image_description' in slide_data:
                image_url = await search_unsplash_image(slide_data['image_description'])
                if image_url:
                    await add_image_from_url_to_slide(slides_service, drive_service, presentation_id, new_slide_id, image_url)
            
            # Handle chart
            if 'chart' in slide_data:
                chart = slide_data['chart']
                chart_bytes = await asyncio.to_thread(generate_chart_bytes, chart['type'], chart['categories'], chart['data'])
                await add_image_from_bytes_to_slide(slides_service, drive_service, presentation_id, new_slide_id, chart_bytes, f"chart_{new_slide_id}.png", 'image/png')
        
        return {"status": "success", "result": {"message": f"Presentation '{title}' created.", "url": presentation_url}}
    except HttpError as e:
        return {"status": "failure", "error": f"Google API Error: {e.content.decode()}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}