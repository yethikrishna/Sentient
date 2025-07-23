import datetime
import uuid
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from main.chat.models import ChatMessageInput, RenameChatRequest
from main.chat.utils import generate_chat_llm_stream
from main.auth.utils import PermissionChecker
from main.dependencies import mongo_manager
from workers.tasks import generate_chat_title

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)
logger = logging.getLogger(__name__)

class ChatIdResponse(BaseModel):
    chatId: str

@router.post("/message", summary="Process Chat Message (Overlay Chat)")
async def chat_endpoint(
    request_body: ChatMessageInput, 
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat", "write:chat"]))
):
    chat_id = request_body.chatId
    is_new_chat = not chat_id

    # 1. Get the last user message from the payload
    user_message = next((msg for msg in reversed(request_body.messages) if msg.get("role") == "user"), None)
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found in the request.")

    # 2. If it's a new chat, create it. Otherwise, add the message to the existing chat.
    if is_new_chat:
        # Add timestamp to the first message before creating chat
        user_message['timestamp'] = datetime.datetime.now(datetime.timezone.utc)
        chat_id = await mongo_manager.create_chat(user_id, user_message)
        # Trigger a background task to generate a better title from the first message
        generate_chat_title.delay(chat_id, user_id)
    else:
        # If chat exists, just add the new user message
        await mongo_manager.add_message_to_chat(user_id, chat_id, user_message)

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

    async def event_stream_generator():
        assistant_response_buffer = ""
        try:
            # If it's a new chat, send the new chat_id to the client first
            if is_new_chat:
                yield json.dumps({"type": "chat_session", "chatId": chat_id, "tempTitle": user_message.get("content", "New Chat")[:50]}) + "\n"

            async for event in generate_chat_llm_stream(
                user_id,
                request_body.messages,
                user_context,
                preferences,
                db_manager=mongo_manager
            ):
                if not event:
                    continue
                if event.get("type") == "assistantStream":
                    assistant_response_buffer += event.get("token", "")

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
        finally:
            # Save the complete assistant response at the end of the stream
            if assistant_response_buffer.strip() and chat_id:
                assistant_message = {
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": assistant_response_buffer,
                    "timestamp": datetime.datetime.now(datetime.timezone.utc)
                }
                await mongo_manager.add_message_to_chat(user_id, chat_id, assistant_message)
                logger.info(f"Saved assistant response to chat {chat_id} for user {user_id}")

    return StreamingResponse(
        event_stream_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Transfer-Encoding": "chunked",  # Hint chunked encoding
        }
    )
@router.get("/history", summary="Get all chat sessions for a user")
async def get_chat_history(user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))):
    chats = await mongo_manager.get_user_chats(user_id)
    # Convert datetime objects to ISO 8601 strings for JSON serialization
    for chat in chats:
        if "updated_at" in chat and isinstance(chat["updated_at"], datetime.datetime):
            chat["updated_at"] = chat["updated_at"].isoformat()
    return JSONResponse(content={"chats": chats})

@router.get("/history/{chat_id}", summary="Get messages for a specific chat session")
async def get_chat_messages(chat_id: str, user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))):
    chat = await mongo_manager.get_chat(user_id, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    # Convert ObjectId and datetime to string for JSON serialization
    if "_id" in chat:
        chat["_id"] = str(chat["_id"])
    for msg in chat.get("messages", []):
        if "timestamp" in msg and isinstance(msg["timestamp"], datetime.datetime):
            msg["timestamp"] = msg["timestamp"].isoformat()
    if "created_at" in chat and isinstance(chat["created_at"], datetime.datetime):
        chat["created_at"] = chat["created_at"].isoformat()
    if "updated_at" in chat and isinstance(chat["updated_at"], datetime.datetime):
        chat["updated_at"] = chat["updated_at"].isoformat()

    return JSONResponse(content=chat)

@router.delete("/{chat_id}", summary="Delete a chat session")
async def delete_chat(chat_id: str, user_id: str = Depends(PermissionChecker(required_permissions=["write:chat"]))):
    success = await mongo_manager.delete_chat(user_id, chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return JSONResponse(content={"message": "Chat deleted successfully."})

@router.put("/{chat_id}/title", summary="Rename a chat session")
async def rename_chat(chat_id: str, request: RenameChatRequest, user_id: str = Depends(PermissionChecker(required_permissions=["write:chat"]))):
    success = await mongo_manager.update_chat(user_id, chat_id, {"title": request.title})
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return JSONResponse(content={"message": "Chat renamed successfully."})
