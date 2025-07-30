import datetime
import uuid
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
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
    # 1. Check if there are any user messages
    if not any(msg.get("role") == "user" for msg in request_body.messages):
        raise HTTPException(status_code=400, detail="No user message found in the request.")

    # 2. Save all new user messages since the last assistant message
    for msg in reversed(request_body.messages):
        if msg.get("role") == "assistant":
            break
        if msg.get("role") == "user":
            await mongo_manager.add_message(user_id=user_id, role="user", content=msg.get("content", ""), message_id=msg.get("id"))

    # Fetch comprehensive user context
    user_profile = await mongo_manager.get_user_profile(user_id)
    user_data = user_profile.get("userData", {}) if user_profile else {}
    personal_info = user_data.get("personalInfo", {})

    user_context = {
        "name": personal_info.get("name", "User"),
        "timezone": personal_info.get("timezone", "UTC"),
        "location": personal_info.get("location"),
    }

    async def event_stream_generator():
        assistant_response_buffer = ""
        assistant_message_id = None
        try:
            async for event in generate_chat_llm_stream(
                user_id,
                request_body.messages,
                user_context,
                db_manager=mongo_manager
            ):
                if not event:
                    continue
                if event.get("type") == "assistantStream":
                    assistant_response_buffer += event.get("token", "")
                    if not assistant_message_id and event.get("messageId"):
                        assistant_message_id = event["messageId"]

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
            if assistant_response_buffer.strip() and assistant_message_id:
                await mongo_manager.add_message(
                    user_id=user_id,
                    role="assistant",
                    content=assistant_response_buffer.strip(),
                    message_id=assistant_message_id
                )
                logger.info(f"Saved assistant response for user {user_id} with ID {assistant_message_id}")

    return StreamingResponse(
        event_stream_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Transfer-Encoding": "chunked",  # Hint chunked encoding
        }
    )
@router.get("/history", summary="Get message history for a user")
async def get_chat_history(
    request: Request,
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat"]))
):
    limit = int(request.query_params.get("limit", 30))
    before_timestamp = request.query_params.get("before_timestamp")

    messages = await mongo_manager.get_message_history(user_id, limit, before_timestamp)

    # The frontend expects messages in chronological order, but we fetch them in reverse chronological.
    # So we must reverse them before sending.
    return JSONResponse(content={"messages": messages[::-1]})