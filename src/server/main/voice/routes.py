# src/server/main/voice/routes.py
import datetime
import traceback
import asyncio
import numpy as np # For converting audio bytes if needed by older STT/TTS, or by WebSocket client
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status

from .models import VoiceOfferRequest, VoiceAnswerResponse
from ..auth.utils import AuthHelper, PermissionChecker # Use auth.utils
from ..app import auth_helper # Global instance
from ..app import main_websocket_manager # Global instance
from ..app import stt_model_instance # Global STT instance
from ..app import tts_model_instance # Global TTS instance
from ..app import is_dev_env # Global dev flag

# Import TTS Options if they are specific and used for type hinting
from .tts_services import OrpheusTTSOptions # Example
from .tts_services.base_tts import TTSOptionsBase


router = APIRouter(
    prefix="/voice",
    tags=["Voice Communication"]
)

@router.post("/webrtc/offer", summary="Handle WebRTC Offer")
async def handle_webrtc_offer(
    offer_request: VoiceOfferRequest, 
    user_id: str = Depends(auth_helper.get_current_user_id) 
):
    # This is a simplified dummy response for WebRTC.
    # A real implementation would involve a WebRTC library (like aiortc)
    # to process the offer, establish a peer connection, and generate an answer.
    print(f"[{datetime.datetime.now()}] [VOICE_OFFER] Received WebRTC offer from {user_id}, type: {offer_request.type}")
    # For testing, you can echo back parts of the offer or a fixed answer SDP.
    # This dummy response is unlikely to establish a real WebRTC call.
    return VoiceAnswerResponse(sdp="dummy-answer-sdp-from-server", type="answer")

@router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    authenticated_user_id: str | None = None
    try:
        # Authenticate WebSocket connection
        authenticated_user_id = await auth_helper.ws_authenticate(websocket)
        if not authenticated_user_id:
            # ws_authenticate handles sending auth_failure and closing if needed
            return 

        await main_websocket_manager.connect_voice(websocket, authenticated_user_id)
        print(f"[{datetime.datetime.now()}] [VOICE_WS] User {authenticated_user_id} connected to voice WebSocket.")

        while True:
            audio_bytes = await websocket.receive_bytes()
            
            if not stt_model_instance:
                logger.error(f"[{datetime.datetime.now()}] [VOICE_WS] STT service not available for user {authenticated_user_id}.")
                await websocket.send_json({"type": "error", "message": "STT service not available."})
                continue
            
            # --- STT ---
            # Assuming client sends 16kHz audio. This should be configurable or checked.
            client_sample_rate = 16000 
            transcribed_text = await stt_model_instance.transcribe(audio_bytes, sample_rate=client_sample_rate)
            await websocket.send_json({"type": "stt_result", "text": transcribed_text})
            print(f"[{datetime.datetime.now()}] [VOICE_WS_STT] User {authenticated_user_id}: '{transcribed_text}'")

            # --- Dummy LLM Response (placeholder) ---
            # In a real app, this would involve more complex logic, potentially calling the chat LLM stream.
            if not transcribed_text or transcribed_text.strip() == "":
                 llm_response_text = "I didn't catch that. Could you please repeat?"
            else:
                llm_response_text = f"I understood: '{transcribed_text}'. How can I help you further?"
            await websocket.send_json({"type": "llm_response", "text": llm_response_text})
            print(f"[{datetime.datetime.now()}] [VOICE_WS_LLM] User {authenticated_user_id} -> LLM: '{llm_response_text}'")
            
            # --- TTS ---
            if not tts_model_instance:
                logger.error(f"[{datetime.datetime.now()}] [VOICE_WS] TTS service not available for user {authenticated_user_id}.")
                await websocket.send_json({"type": "error", "message": "TTS service not available."})
                await websocket.send_json({"type": "tts_stream_end"}) # Signal end anyway
                continue

            tts_options: TTSOptionsBase = {} 
            # Example: if using Orpheus and want to specify voice:
            # if is_dev_env and isinstance(tts_model_instance, OrpheusTTS): # OrpheusTTS is the class
            #    tts_options = OrpheusTTSOptions(voice_id="tara") # Orpheus specific options

            print(f"[{datetime.datetime.now()}] [VOICE_WS_TTS] Streaming TTS for user {authenticated_user_id}: '{llm_response_text[:30]}...'")
            async for audio_chunk in tts_model_instance.stream_tts(llm_response_text, options=tts_options):
                if isinstance(audio_chunk, bytes):
                    await websocket.send_bytes(audio_chunk)
                elif isinstance(audio_chunk, tuple) and len(audio_chunk) == 2 and isinstance(audio_chunk[1], np.ndarray):
                    # Handle (sample_rate, np_array) from OrpheusTTS
                    _sr, chunk_np_array = audio_chunk
                    # Convert float32 numpy array to 16-bit PCM bytes
                    audio_int16 = (chunk_np_array * 32767).astype(np.int16)
                    await websocket.send_bytes(audio_int16.tobytes())
                else:
                    logger.warning(f"[{datetime.datetime.now()}] [VOICE_WS_TTS] TTS for user {authenticated_user_id} yielded unexpected chunk type: {type(audio_chunk)}")
            
            await websocket.send_json({"type": "tts_stream_end"})
            print(f"[{datetime.datetime.now()}] [VOICE_WS_TTS] Finished TTS stream for user {authenticated_user_id}.")

    except WebSocketDisconnect:
        print(f"[{datetime.datetime.now()}] [VOICE_WS] Client disconnected (User: {authenticated_user_id or 'unknown'}).")
    except Exception as e:
        err_msg = f"An internal server error occurred: {str(e)}"
        print(f"[{datetime.datetime.now()}] [VOICE_WS_ERROR] Error (User: {authenticated_user_id or 'unknown'}): {e}")
        traceback.print_exc()
        if websocket.client_state != WebSocketState.DISCONNECTED: # type: ignore
            try:
                await websocket.send_json({"type": "error", "message": err_msg})
            except Exception: # Ignore if send fails (e.g., socket already closed)
                pass
    finally:
        if authenticated_user_id:
            main_websocket_manager.disconnect_voice(websocket)
            print(f"[{datetime.datetime.now()}] [VOICE_WS] User {authenticated_user_id} voice WebSocket cleanup complete.")