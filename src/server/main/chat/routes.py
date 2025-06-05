# src/server/main/chat/routes.py
import datetime
import uuid
import json
import asyncio
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from .models import ChatMessageInput
from .utils import get_chat_history_util, generate_chat_llm_stream # generate_chat_llm_stream will use Qwen
from ..auth.utils import PermissionChecker 
from ..app import mongo_manager_instance as mongo_manager 
from ..app import auth_helper 
# is_dev_env is not directly needed here if generate_chat_llm_stream handles it via qwen_agent_utils

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
    await mongo_manager.update_user_profile(user_id, {"userData.active_chat_id": new_active_chat_id})
    
    return JSONResponse(content={"message": "Chat history cleared.", "activeChatId": new_active_chat_id})


@router.post("/chat", summary="Process Chat Message (Text)")
async def chat_endpoint(
    request_body: ChatMessageInput, 
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat", "write:chat"]))
):
    user_profile = await mongo_manager.get_user_profile(user_id)
    username = user_profile.get("userData", {}).get("personalInfo", {}).get("name", user_id) if user_profile else user_id
    
    _, active_chat_id = await get_chat_history_util(user_id, mongo_manager)

    user_msg_db_id = str(uuid.uuid4()) # Pre-generate ID for user message for consistency
    await mongo_manager.add_chat_message(user_id, active_chat_id, {
        "id": user_msg_db_id,
        "message": request_body.input, "isUser": True, "isVisible": True 
    })

    async def response_generator():
        # Yield user message confirmation
        yield json.dumps({
            "type": "userMessage", "id": user_msg_db_id, "message": request_body.input, 
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }) + "\n"
        
        # Placeholder for assistant's response ID
        assistant_temp_id_for_stream = str(uuid.uuid4()) 
        # Removed "Thinking..." message as Qwen Agent stream might start quickly or include tool calls

        full_llm_response_text = ""
        final_message_id_from_llm_stream = assistant_temp_id_for_stream
        
        try:
            async for item in generate_chat_llm_stream(
                user_id=user_id,
                active_chat_id=active_chat_id, # Pass chat ID for history fetching
                user_input=request_body.input,
                username=username, # For potential personalization in prompts if Qwen Agent uses it
                db_manager=mongo_manager,
                assistant_message_id_override=assistant_temp_id_for_stream # Pass the pre-generated ID
                ):
                
                # Accumulate full text from 'token' if it's a stream part,
                # or from 'full_message' if it's the final summary.
                # The 'generate_chat_llm_stream' should yield a 'full_message' field in its final "done: True" event.
                if item.get("type") == "assistantStream" and item.get("token"):
                    full_llm_response_text += item["token"]
                
                if item.get("type") == "assistantStream" and item.get("done") is True:
                    full_llm_response_text = item.get("full_message", full_llm_response_text) # Prioritize full_message
                    final_message_id_from_llm_stream = item.get("messageId", final_message_id_from_llm_stream)


                yield json.dumps(item) + "\n"
            
            # Store the complete assistant message AFTER the stream has finished
            # Use the potentially updated full_llm_response_text and final_message_id_from_llm_stream
            if full_llm_response_text: # Only save if there was a response
                 await mongo_manager.add_chat_message(user_id, active_chat_id, {
                    "id": final_message_id_from_llm_stream, 
                    "message": full_llm_response_text, 
                    "isUser": False, 
                    "isVisible": True,
                    "memoryUsed": False, "agentsUsed": True, "internetUsed": False, "proUsed": False # Example flags
                })
            else:
                logger.warning(f"No LLM response text generated for user {user_id}, chat {active_chat_id}.")

        except Exception as e:
            logger.error(f"Error during chat LLM stream for user {user_id}: {e}", exc_info=True)
            error_response = {
                "type": "error",
                "messageId": assistant_temp_id_for_stream, # Use the same ID for error context
                "message": "Sorry, I encountered an error while processing your request."
            }
            yield json.dumps(error_response) + "\n"
            # Optionally, save an error message to chat history
            await mongo_manager.add_chat_message(user_id, active_chat_id, {
                "id": assistant_temp_id_for_stream,
                "message": "Error: Could not get a response.",
                "isUser": False,
                "isVisible": False, # Or true, depending on desired UX for errors
                "error": str(e) 
            })
            
    return StreamingResponse(response_generator(), media_type="application/x-ndjson")