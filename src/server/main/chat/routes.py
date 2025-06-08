# src/server/main/chat/routes.py
import datetime
import uuid
import json
import asyncio
import logging # Corrected import of logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from .models import ChatMessageInput
from .utils import get_chat_history_util, generate_chat_llm_stream # generate_chat_llm_stream will use Qwen
from ..auth.utils import PermissionChecker, AuthHelper  # Import PermissionChecker and AuthHelper from auth.utils
from ..dependencies import mongo_manager

auth_helper = AuthHelper()

router = APIRouter(
    tags=["Chat"]
)
logger = logging.getLogger(__name__)

@router.post("/get-history", summary="Get Chat History")
async def get_chat_history_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))):
    messages, active_chat_id = await get_chat_history_util(user_id, mongo_manager)
    return JSONResponse(content={"messages": messages, "activeChatId": active_chat_id})

@router.post("/clear-chat-history", summary="Clear Active Chat History")
async def clear_chat_history_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["write:chat"]))):
    user_profile = await mongo_manager.get_user_profile(user_id)
    active_chat_id = user_profile.get("userData", {}).get("active_chat_id") if user_profile else None
    
    if active_chat_id:
        await mongo_manager.delete_chat_history(user_id, active_chat_id)
    
    new_active_chat_id = str(uuid.uuid4())

    # Explicitly create the new chat session document to ensure it exists
    await mongo_manager.create_new_chat_session(user_id, new_active_chat_id)
    
    await mongo_manager.update_user_profile(user_id, {"userData.active_chat_id": new_active_chat_id})
    
    return JSONResponse(content={"message": "Chat history cleared.", "activeChatId": new_active_chat_id})


@router.post("/chat", summary="Process Chat Message (Text)")
async def chat_endpoint(
    request_body: ChatMessageInput, 
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat", "write:chat"]))
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User") if user_profile else "User"
    
    _, active_chat_id = await get_chat_history_util(user_id, mongo_manager)

    async def event_stream_generator():
        try:
            async for event in generate_chat_llm_stream(user_id, active_chat_id, request_body.input, username, mongo_manager):
                if not event: continue # Skip empty events
                yield json.dumps(event) + "\n"
        except asyncio.CancelledError:
             logger.info(f"Client disconnected, stream cancelled for user {user_id}.")
        except Exception as e:
            logger.error(f"Error in chat stream for user {user_id}: {e}", exc_info=True)
            error_response = {
                "type": "error",
                "message": "Sorry, I encountered an error while processing your request."
            }
            yield json.dumps(error_response) + "\n" # This yield might fail if client is already gone

    return StreamingResponse(event_stream_generator(), media_type="application/x-ndjson")