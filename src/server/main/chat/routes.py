# src/server/main/chat/routes.py
import datetime
import datetime
import uuid
import json
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse

from .models import ChatMessageInput, ChatHistoryRequest, RenameChatRequest, DeleteChatRequest
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

@router.get("/list-chats", summary="Get a list of all user chats")
async def list_chats_endpoint(user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))):
	chats_from_db = await mongo_manager.get_all_chats_for_user(user_id)
	serialized_chats = []
	for chat in chats_from_db:
		if isinstance(chat.get("last_updated"), datetime.datetime):
			chat["last_updated"] = chat["last_updated"].isoformat()
		serialized_chats.append(chat)
	return JSONResponse(content={"chats": serialized_chats})

@router.post("/rename-chat", summary="Rename a chat session")
async def rename_chat_endpoint(
    request: RenameChatRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:chat"]))
):
    success = await mongo_manager.rename_chat(user_id, request.chatId, request.newTitle)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found or you don't have permission to rename it.")
    return JSONResponse(content={"message": "Chat renamed successfully."})

@router.post("/delete-chat", summary="Delete a chat session")
async def delete_chat_endpoint(
    request: DeleteChatRequest,
    user_id: str = Depends(PermissionChecker(required_permissions=["write:chat"]))
):
    success = await mongo_manager.delete_chat_history(user_id, request.chatId)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found or you don't have permission to delete it.")
    return JSONResponse(content={"message": "Chat deleted successfully."})

@router.post("/chat", summary="Process Chat Message (Text)")
async def chat_endpoint(
    request_body: ChatMessageInput, 
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat", "write:chat"]))
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", "User") if user_profile else "User"
    
    chat_id_from_req = request_body.chatId
    chat_id: Optional[str] = None
    if isinstance(chat_id_from_req, str) and chat_id_from_req:
        chat_id = chat_id_from_req
    elif isinstance(chat_id_from_req, list) and chat_id_from_req:
        chat_id = str(chat_id_from_req[0])
        
    is_new_chat = not chat_id

    # If it's a new chat, generate a dynamic title first
    if is_new_chat:
        chat_id = str(uuid.uuid4())
        try:
            title = await generate_chat_title(request_body.input)
        except Exception as e:
            logger.error(f"Error generating chat title for user {user_id}: {e}")
            title = ' '.join(request_body.input.split()[:3]) # Fallback title

        await mongo_manager.create_new_chat_session(user_id, chat_id, title)
        logger.info(f"Created new chat with ID {chat_id} and dynamic title '{title}' for user {user_id}")
    else:
        # For existing chats, we don't need the title here.
        title = None

    async def event_stream_generator():
        if is_new_chat and title:
            # Send the dynamically generated chat info to the client
            yield json.dumps({"type": "chat_created", "chatId": chat_id, "title": title}) + "\n"
        try:
            async for event in generate_chat_llm_stream(
                user_id,
                chat_id, # type: ignore
                request_body.input,
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