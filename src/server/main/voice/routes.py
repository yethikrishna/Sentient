from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from starlette.websockets import WebSocketState
import logging

router = APIRouter(
    prefix="/voice",
    tags=["Voice Communication"]
)

logger = logging.getLogger(__name__)

# The old websocket-based voice endpoint is now replaced by the WebRTC endpoint in app.py
# This file is kept to maintain the router structure but contains no active routes.
