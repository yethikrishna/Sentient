# src/server/main/voice/routes.py
import datetime
import traceback
import asyncio
import numpy as np 
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from starlette.websockets import WebSocketState
import logging 

from .models import VoiceOfferRequest, VoiceAnswerResponse
from ..auth.utils import AuthHelper, PermissionChecker 
from ..app import auth_helper 
from ..app import main_websocket_manager 
from ..app import stt_model_instance 
from ..app import tts_model_instance 
from ..app import is_dev_env 

# OrpheusTTS and related classes are now imported conditionally below to avoid loading them in production.
from .tts import TTSOptionsBase # Base options from .tts.base


router = APIRouter(
    prefix="/voice",
    tags=["Voice Communication"]
)
logger = logging.getLogger(__name__) 


@router.post("/webrtc/offer", summary="Handle WebRTC Offer")
async def handle_webrtc_offer(
    offer_request: VoiceOfferRequest, 
    user_id: str = Depends(auth_helper.get_current_user_id) 
):
    print(f"[{datetime.datetime.now()}] [VOICE_OFFER] Received WebRTC offer from {user_id}, type: {offer_request.type}")
    return VoiceAnswerResponse(sdp="dummy-answer-sdp-from-server", type="answer")

@router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    authenticated_user_id: str | None = None
    try:
        authenticated_user_id = await auth_helper.ws_authenticate(websocket)
        if not authenticated_user_id:
            return 

        await main_websocket_manager.connect_voice(websocket, authenticated_user_id)
        logger.info(f"[{datetime.datetime.now()}] [VOICE_WS] User {authenticated_user_id} connected to voice WebSocket.")

        while True:
            audio_bytes = await websocket.receive_bytes()
            
            if not stt_model_instance:
                logger.error(f"[{datetime.datetime.now()}] [VOICE_WS] STT service not available for user {authenticated_user_id}.")
                await websocket.send_json({"type": "error", "message": "STT service not available."})
                continue
            
            client_sample_rate = 16000 
            transcribed_text = await stt_model_instance.transcribe(audio_bytes, sample_rate=client_sample_rate)
            await websocket.send_json({"type": "stt_result", "text": transcribed_text})
            logger.info(f"[{datetime.datetime.now()}] [VOICE_WS_STT] User {authenticated_user_id}: '{transcribed_text}'")

            if not transcribed_text or transcribed_text.strip() == "":
                 llm_response_text = "I didn't catch that. Could you please repeat?"
            else:
                # For voice, you might use a simpler Qwen Agent interaction or a specific prompt.
                # This is a placeholder for where Qwen Agent could be invoked for voice commands.
                # from ..qwen_agent_utils import get_qwen_assistant
                # voice_agent = get_qwen_assistant(system_message="You are a voice assistant.")
                # qwen_messages = [{"role": "user", "content": transcribed_text}]
                # async for response_part in voice_agent.run(messages=qwen_messages):
                #    if response_part and response_part[-1].get('role') == 'assistant':
                #        llm_response_text = response_part[-1].get('content','')
                #        break # Taking the first assistant textual response
                # else:
                #    llm_response_text = "I processed that with Qwen Agent (voice)."
                llm_response_text = f"I understood: '{transcribed_text}'. This is a voice dummy response." # Current dummy
            
            await websocket.send_json({"type": "llm_response", "text": llm_response_text})
            logger.info(f"[{datetime.datetime.now()}] [VOICE_WS_LLM] User {authenticated_user_id} -> LLM: '{llm_response_text}'")
            
            if not tts_model_instance:
                logger.error(f"[{datetime.datetime.now()}] [VOICE_WS] TTS service not available for user {authenticated_user_id}.")
                await websocket.send_json({"type": "error", "message": "TTS service not available."})
                await websocket.send_json({"type": "tts_stream_end"}) 
                continue

            tts_options: TTSOptionsBase = {} 
            if is_dev_env and isinstance(tts_model_instance, OrpheusTTS): 
               tts_options = OrpheusTTSOptions(voice_id="tara") 

            logger.info(f"[{datetime.datetime.now()}] [VOICE_WS_TTS] Streaming TTS for user {authenticated_user_id}: '{llm_response_text[:30]}...'")
            async for audio_chunk in tts_model_instance.stream_tts(llm_response_text, options=tts_options):
                if isinstance(audio_chunk, bytes):
                    await websocket.send_bytes(audio_chunk)
                elif isinstance(audio_chunk, tuple) and len(audio_chunk) == 2 and isinstance(audio_chunk[1], np.ndarray):
                    _sr, chunk_np_array = audio_chunk
                    audio_int16 = (chunk_np_array * 32767).astype(np.int16)
                    await websocket.send_bytes(audio_int16.tobytes())
                else:
                    logger.warning(f"[{datetime.datetime.now()}] [VOICE_WS_TTS] TTS for user {authenticated_user_id} yielded unexpected chunk type: {type(audio_chunk)}")
            
            await websocket.send_json({"type": "tts_stream_end"})
            logger.info(f"[{datetime.datetime.now()}] [VOICE_WS_TTS] Finished TTS stream for user {authenticated_user_id}.")

    except WebSocketDisconnect:
        logger.info(f"[{datetime.datetime.now()}] [VOICE_WS] Client disconnected (User: {authenticated_user_id or 'unknown'}).")
    except Exception as e:
        err_msg = f"An internal server error occurred: {str(e)}"
        logger.error(f"[{datetime.datetime.now()}] [VOICE_WS_ERROR] Error (User: {authenticated_user_id or 'unknown'}): {e}", exc_info=True)
        # Check client_state before sending, as per FastAPI documentation
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json({"type": "error", "message": err_msg})
            except Exception as send_err: 
                logger.error(f"[{datetime.datetime.now()}] [VOICE_WS_ERROR] Failed to send error to client: {send_err}")
    finally:
        if authenticated_user_id:
            main_websocket_manager.disconnect_voice(websocket)
            logger.info(f"[{datetime.datetime.now()}] [VOICE_WS] User {authenticated_user_id} voice WebSocket cleanup complete.")