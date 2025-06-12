import datetime
import traceback
import asyncio
import uuid
import numpy as np
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from starlette.websockets import WebSocketState
import logging

from .models import VoiceOfferRequest, VoiceAnswerResponse
from ..dependencies import mongo_manager, auth_helper, websocket_manager as main_websocket_manager
from ..chat.utils import process_voice_command
from .tts import TTSOptionsBase

router = APIRouter(
    prefix="/voice",
    tags=["Voice Communication"]
)
logger = logging.getLogger(__name__)

@router.post("/webrtc/offer", summary="Handle WebRTC Offer (Legacy)")
async def handle_webrtc_offer(
    offer_request: VoiceOfferRequest,
    user_id: str = Depends(auth_helper.get_current_user_id)
):
    logger.warning(f"Legacy WebRTC offer endpoint called by {user_id}. This flow is deprecated.")
    return VoiceAnswerResponse(sdp="dummy-answer-sdp-from-server", type="answer")

@router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    from ..app import stt_model_instance, tts_model_instance

    authenticated_user_id: str | None = None
    active_chat_id: str | None = None

    try:
        authenticated_user_id = await auth_helper.ws_authenticate(websocket)
        if not authenticated_user_id: return

        user_profile = await mongo_manager.get_user_profile(authenticated_user_id)
        username = "User"
        if user_profile and user_profile.get("userData"):
            active_chat_id = user_profile["userData"].get("active_chat_id")
            username = user_profile["userData"].get("personalInfo", {}).get("name", "User")
        
        if not active_chat_id:
            active_chat_id = str(uuid.uuid4())
            await mongo_manager.create_new_chat_session(authenticated_user_id, active_chat_id)
            await mongo_manager.update_user_profile(authenticated_user_id, {"userData.active_chat_id": active_chat_id})

        await main_websocket_manager.connect_voice(websocket, authenticated_user_id)
        logger.info(f"User {authenticated_user_id} connected to voice WebSocket.")
        await websocket.send_json({"type": "status", "message": "listening"})

        while True:
            audio_bytes = await websocket.receive_bytes()
            if not stt_model_instance:
                await websocket.send_json({"type": "error", "message": "STT service not available."})
                continue
            
            transcribed_text = await stt_model_instance.transcribe(audio_bytes, sample_rate=16000)
            await websocket.send_json({"type": "stt_result", "text": transcribed_text})
            logger.info(f"STT Result for {authenticated_user_id}: '{transcribed_text}'")

            if not transcribed_text or not transcribed_text.strip(): continue

            await websocket.send_json({"type": "status", "message": "thinking"})
            llm_response_text, assistant_message_id = await process_voice_command(
                user_id=authenticated_user_id, active_chat_id=active_chat_id,
                transcribed_text=transcribed_text, username=username, db_manager=mongo_manager
            )

            await websocket.send_json({"type": "llm_result", "text": llm_response_text, "messageId": assistant_message_id})
            logger.info(f"LLM Result for {authenticated_user_id}: '{llm_response_text}'")
            
            if not tts_model_instance:
                await websocket.send_json({"type": "error", "message": "TTS service not available."})
                await websocket.send_json({"type": "tts_stream_end"})
                continue

            await websocket.send_json({"type": "status", "message": "speaking"})
            tts_options: TTSOptionsBase = {}
            logger.info(f"Streaming TTS for {authenticated_user_id}: '{llm_response_text[:30]}...'")

            async for audio_chunk in tts_model_instance.stream_tts(llm_response_text, options=tts_options):
                if isinstance(audio_chunk, tuple) and len(audio_chunk) == 2 and isinstance(audio_chunk[1], np.ndarray):
                    _, chunk_np_array = audio_chunk
                    audio_float32 = chunk_np_array.astype(np.float32)
                    await websocket.send_bytes(audio_float32.tobytes())
                elif isinstance(audio_chunk, bytes):
                    await websocket.send_bytes(audio_chunk)
            
            await websocket.send_json({"type": "tts_stream_end"})
            logger.info(f"Finished TTS stream for user {authenticated_user_id}.")
            await websocket.send_json({"type": "status", "message": "listening"})

    except WebSocketDisconnect:
        logger.info(f"Client disconnected (User: {authenticated_user_id or 'unknown'}).")
    except Exception as e:
        err_msg = f"An internal server error occurred: {str(e)}"
        logger.error(f"Voice WS Error for User {authenticated_user_id or 'unknown'}: {e}", exc_info=True)
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json({"type": "error", "message": err_msg})
            except Exception as send_err: 
                logger.error(f"Failed to send error to client: {send_err}")
    finally:
        if authenticated_user_id:
            await main_websocket_manager.disconnect_voice(websocket)
            logger.info(f"User {authenticated_user_id} voice WebSocket cleanup complete.")