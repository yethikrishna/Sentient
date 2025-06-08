# src/server/main/chat/utils.py
import datetime
import uuid
import json
import asyncio
import logging
from typing import List, Dict, Any, Tuple, AsyncGenerator, Optional

from ..db import MongoManager
from ..llm import get_qwen_assistant # Import the Qwen Agent initializer
# from qwen_agent.llm.schema import Message as QwenMessage # If precise typing is needed

logger = logging.getLogger(__name__)

async def get_chat_history_util(user_id: str, db_manager: MongoManager, chat_id_param: Optional[str] = None) -> Tuple[List[Dict[str, Any]], str]:
    effective_chat_id = chat_id_param
    if not effective_chat_id:
        user_profile = await db_manager.get_user_profile(user_id)
        active_chat_id_from_profile = user_profile.get("userData", {}).get("active_chat_id") if user_profile else None
        
        if active_chat_id_from_profile:
            effective_chat_id = active_chat_id_from_profile
        else:
            all_chat_ids = await db_manager.get_all_chat_ids_for_user(user_id)
            if all_chat_ids:
                effective_chat_id = all_chat_ids[0] 
                if user_profile: 
                    await db_manager.update_user_profile(user_id, {"userData.active_chat_id": effective_chat_id})
            else: 
                new_chat_id = str(uuid.uuid4())
                update_payload = {"userData.active_chat_id": new_chat_id}
                await db_manager.update_user_profile(user_id, update_payload)
                effective_chat_id = new_chat_id
    
    messages_from_db = await db_manager.get_chat_history(user_id, effective_chat_id)
    
    serialized_messages = []
    for m in messages_from_db:
        if isinstance(m, dict) and 'timestamp' in m and isinstance(m['timestamp'], datetime.datetime):
            m['timestamp'] = m['timestamp'].isoformat()
        serialized_messages.append(m)
        
    return [m for m in serialized_messages if m.get("isVisible", True)], effective_chat_id


async def generate_chat_llm_stream(
    user_id: str,
    active_chat_id: str,
    user_input: str, 
    username: str, # Keep for potential future use in prompts
    db_manager: MongoManager,
    assistant_message_id_override: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Handles LLM streaming logic using Qwen Agent.
    """
    assistant_message_id = assistant_message_id_override or str(uuid.uuid4())
    
    try:
        # 1. Initialize Qwen Assistant
        # System prompt could be customized, e.g., using username
        # For now, using default system prompt from qwen_agent_utils
        system_prompt = f"You are a helpful AI assistant. The user's name is {username}."
        qwen_assistant = get_qwen_assistant(system_message=system_prompt)

        # 2. Fetch and format chat history
        # `get_chat_history` already returns visible messages for the active_chat_id
        history_from_db, _ = await get_chat_history_util(user_id, db_manager, active_chat_id)
        
        qwen_formatted_history = []
        for msg_from_db in history_from_db:
            role = "user" if msg_from_db.get("isUser") else "assistant"
            content = str(msg_from_db.get("message", "")) # Ensure content is string
            # Qwen Agent expects {'role': ..., 'content': ...}
            # It can also handle more complex content like ContentItem list
            qwen_formatted_history.append({"role": role, "content": content})
        
        # Add current user input
        qwen_formatted_history.append({"role": "user", "content": str(user_input)})

        # 3. Stream response from Qwen Assistant
        full_response_text_accumulator = []
        streamed_content_length_for_current_msg = 0
        
        # The 'run' method is an async generator yielding lists of new messages (steps)
        async for new_step_messages in qwen_assistant.run(messages=qwen_formatted_history):
            if not new_step_messages:
                continue

            for qwen_msg in new_step_messages: # qwen_msg is a dict
                role = qwen_msg.get('role')
                content = qwen_msg.get('content', '') # Default to empty string if None
                function_call = qwen_msg.get('function_call')

                if role == 'assistant':
                    if function_call:
                        # This is a tool call request
                        streamed_content_length_for_current_msg = 0 # Reset for next potential content
                        yield {
                            "type": "intermediary", 
                            "message": f"Thinking... (tool: {function_call.get('name', 'unknown')})",
                            "details": f"Arguments: {function_call.get('arguments', '{}')}",
                            "id": assistant_message_id 
                        }
                        # Accumulate this step for the final full_message if desired
                        full_response_text_accumulator.append(f"[ToolCall: {function_call.get('name')}({function_call.get('arguments')})]")
                    
                    elif content is not None: # Check for not None, empty string is fine
                        # This is textual content from the assistant.
                        # Qwen Agent streams by updating the content of this message object.
                        if len(content) > streamed_content_length_for_current_msg:
                            new_token_chunk = content[streamed_content_length_for_current_msg:]
                            yield {
                                "type": "assistantStream", 
                                "token": new_token_chunk, 
                                "done": False, 
                                "messageId": assistant_message_id
                            }
                            full_response_text_accumulator.append(new_token_chunk)
                            streamed_content_length_for_current_msg = len(content)
                        # If content length hasn't changed, it might be a re-yield of the same message state,
                        # or an empty update, common in streaming. We only yield if there's new text.
                
                elif role == 'function':
                    # This is a tool execution result
                    streamed_content_length_for_current_msg = 0 # Reset for next potential content
                    yield {
                        "type": "intermediary",
                        "message": f"Tool '{qwen_msg.get('name', 'unknown')}' executed.",
                        "details": f"Result: {str(content)[:100]}...", # Show partial result
                        "id": assistant_message_id
                    }
                    full_response_text_accumulator.append(f"[ToolResponse({qwen_msg.get('name')}): {content}]")
                
                # We don't typically stream 'user' role messages from here as they are inputs.

        # 4. Signal end of stream
        final_text_output = "".join(part for part in full_response_text_accumulator if isinstance(part, str) and not part.startswith("[ToolCall:") and not part.startswith("[ToolResponse("))
        
        # Filter out tool call/response strings from final_text_output if they were added to accumulator
        # A more robust way is to only append to full_response_text_accumulator when it's actual LLM text token.
        # The current logic appends tokens directly, so `final_text_output` made from those parts should be correct.

        yield {
            "type": "assistantStream", "token": "", "done": True, "messageId": assistant_message_id,
            "full_message": final_text_output,
            "memoryUsed": False, "agentsUsed": True, "internetUsed": False, "proUsed": False # Adjust as needed
        }

    except Exception as e:
        logger.error(f"Error in Qwen Agent LLM stream for user {user_id}: {e}", exc_info=True)
        yield {
            "type": "error", # Consistent with chat_endpoint error handling
            "messageId": assistant_message_id,
            "message": "Sorry, an unexpected error occurred with the AI assistant."
        }
        # The chat_endpoint will save an error message to DB