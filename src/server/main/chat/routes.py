import datetime
import uuid
import json
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse

from .models import ChatMessageInput
from .utils import generate_chat_llm_stream
from ..auth.utils import PermissionChecker
from ..dependencies import mongo_manager

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
    user_profile = await mongo_manager.get_user_profile(user_id)
    username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User") if user_profile else "User"
    
    # The new stateless chat sends the entire message history.
    # We no longer save or retrieve history from the database here.
    
    async def event_stream_generator():
        try:
            # Pass the full message history directly to the LLM stream generator
            async for event in generate_chat_llm_stream(
                user_id,
                request_body.messages,
                username,
                mongo_manager,
                enable_internet=request_body.enable_internet,
                enable_weather=request_body.enable_weather,
                enable_news=request_body.enable_news,
                enable_maps=request_body.enable_maps,
                enable_shopping=request_body.enable_shopping
            ):
                if not event: continue
                yield json.dumps(event) + "\n"
        except asyncio.CancelledError:
             logger.info(f"Client disconnected, stream cancelled for user {user_id}.")
        except Exception as e:
            logger.error(f"Error in chat stream for user {user_id}: {e}", exc_info=True)
            error_response = {
                "type": "error",
                "message": "Sorry, I encountered an error while processing your request."
            }
            yield json.dumps(error_response) + "\n"

    return StreamingResponse(event_stream_generator(), media_type="application/x-ndjson")