# src/server/chat_server/utils.py
import asyncio
import datetime
from typing import AsyncGenerator, Dict, Any, Optional
import uuid # For message IDs

# Dummy chat response generation
async def generate_dummy_chat_stream_logic(user_input: str, username: str) -> AsyncGenerator[Dict[str, Any], None]:
    print(f"[{datetime.datetime.now()}] [ChatServer_Utils] Generating dummy stream for input: '{user_input[:30]}...' by {username}")
    
    assistant_message_id = str(uuid.uuid4())

    dummy_texts = [
        f"Hello {username}! ", "This ", "is ", "a ", "dummy ", "chat ", "server ", 
        "response. ", f"You said: '{user_input[:20]}...'. "
    ]
    full_response_text = "".join(dummy_texts)

    for text_part in dummy_texts:
        yield {
            "type": "assistantStream", 
            "token": text_part, 
            "done": False, 
            "messageId": assistant_message_id
        }
        await asyncio.sleep(0.05) 
    
    yield {
        "type": "assistantStream", 
        "token": "", 
        "done": True, 
        "messageId": assistant_message_id,
        "full_message": full_response_text, # Send the full message at the end
        "memoryUsed": False, "agentsUsed": False, "internetUsed": False, "proUsed": False # Dummy metadata
    }