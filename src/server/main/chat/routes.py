# src/server/main/chat/routes.py
import datetime
import datetime
import uuid
import json
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse

from .models import ChatMessageInput, ChatHistoryRequest
from .utils import get_chat_history_util, generate_chat_llm_stream, generate_chat_title
from ..auth.utils import PermissionChecker, AuthHelper
from ..dependencies import mongo_manager
from typing import Optional

auth_helper = AuthHelper()

router = APIRouter(
    tags=["Chat"]
)
logger = logging.getLogger(__name__)

@router.post("/get-history", summary="Get Chat History")
async def get_chat_history_endpoint(
    request: ChatHistoryRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))
):
    # Robustly handle chatId which may be a string or an array
    chat_id_from_req = request.chatId
    final_chat_id: Optional[str] = None

    if isinstance(chat_id_from_req, str):
        final_chat_id = chat_id_from_req
    elif isinstance(chat_id_from_req, list):
        if chat_id_from_req: # Check if list is not empty
            final_chat_id = str(chat_id_from_req[0])

    if not final_chat_id:
        # A new chat page might call this without a valid ID.
        # Returning an empty list is appropriate.
        return JSONResponse(content={"messages": []})

    messages = await get_chat_history_util(user_id, mongo_manager, final_chat_id)
    return JSONResponse(content={"messages": messages})

# Removing list, rename, delete chat endpoints as per the new design.

@router.post("/chat", summary="Process Chat Message (Overlay Chat)")
async def chat_endpoint(
    request_body: ChatMessageInput, 
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat", "write:chat"]))
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User") if user_profile else "User"
    # For the new stateless overlay chat, we don't need to handle chatId, new chats, or titles.
    # We just process the incoming message history.
    chat_id_from_req = request_body.chatId
    chat_id: Optional[str] = None
    if isinstance(chat_id_from_req, str) and chat_id_from_req:
        chat_id = chat_id_from_req
    elif isinstance(chat_id_from_req, list) and chat_id_from_req:
        chat_id = str(chat_id_from_req[0])


    async def event_stream_generator():
        # Removed logic for sending 'chat_created' event
        try:
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