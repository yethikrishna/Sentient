import datetime
import uuid
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse

from main.chat.models import ChatMessageInput
from main.chat.utils import generate_chat_llm_stream
from main.auth.utils import PermissionChecker
from main.dependencies import mongo_manager

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)
logger = logging.getLogger(__name__)

@router.post("/message", summary="Process Chat Message (Overlay Chat)")
async def chat_endpoint(
    request_body: ChatMessageInput, 
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat", "write:chat"]))
):
    # Fetch comprehensive user context
    user_profile = await mongo_manager.get_user_profile(user_id)
    user_data = user_profile.get("userData", {}) if user_profile else {}
    personal_info = user_data.get("personalInfo", {})
    preferences = user_data.get("preferences", {})

    user_context = {
        "name": personal_info.get("name", "User"),
        "timezone": personal_info.get("timezone", "UTC"),
        "location": personal_info.get("location"),
        "communication_style": preferences.get("communicationStyle", "friendly and professional")
    }

    # The new stateless chat sends the entire message history.
    # We no longer save or retrieve history from the database here.
    
    async def event_stream_generator():
        try:
            async for event in generate_chat_llm_stream(
                user_id,
                request_body.messages,
                user_context,
                mongo_manager
            ):
                if not event:
                    continue
                print(f"[INFO] Streaming event to user {user_id}: {json.dumps(event)}")
                # yield as bytes and flush
                yield json.dumps(event) + "\n"
        except asyncio.CancelledError:
            print(f"[INFO] Client disconnected, stream cancelled for user {user_id}.")
        except Exception as e:
            print(f"[ERROR] Error in chat stream for user {user_id}: {e}")
            error_response = {
                "type": "error",
                "message": "Sorry, I encountered an error while processing your request."
            }
            yield (json.dumps(error_response) + "\n").encode("utf-8")

    return StreamingResponse(
        event_stream_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Transfer-Encoding": "chunked",  # Hint chunked encoding
        }
    )