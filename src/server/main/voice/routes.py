import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
import logging

from .stream_handler import stream as voice_stream, user_context_cache
from ..auth.utils import PermissionChecker # Keep this
from fastrtc.schemas import Offer # Correct import for the Offer model from fastRTC

router = APIRouter(
    prefix="/voice",
    tags=["Voice Communication"]
)

logger = logging.getLogger(__name__)

# This endpoint is authenticated using FastAPI's dependency injection.
# It acts as a wrapper around the fastRTC handler to inject user context.
@router.post("/webrtc/offer", include_in_schema=False)
async def webrtc_offer_endpoint(
    body: Offer, # Use the Offer model from fastRTC.schemas
    user_id: str = Depends(PermissionChecker(required_permissions=["read:chat", "write:chat"]))
):
    webrtc_id = body.webrtc_id
    chat_id = body.metadata.get("chatId") if body.metadata else None
    user_context_cache[webrtc_id] = {"user_id": user_id, "chat_id": chat_id}
    return await voice_stream.handle_offer(body, voice_stream.set_additional_outputs(webrtc_id))

# This endpoint streams status updates and other metadata from the voice handler
# to the client using Server-Sent Events (SSE).
@router.get("/updates")
async def voice_updates(request: Request):
    webrtc_id = request.query_params.get("webrtc_id")
    if not webrtc_id:
        return {"error": "webrtc_id is required"}, 400
    
    async def event_generator():
        async for output in voice_stream.output_stream(webrtc_id):
            # The first (and only) arg in AdditionalOutputs will be our JSON message
            if output.args:
                yield f"data: {json.dumps(output.args[0])}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")