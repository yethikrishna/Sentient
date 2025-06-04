# src/server/main_server/ws_manager.py
import datetime
from typing import Dict, Any, Optional
import json
from fastapi import WebSocket, WebSocketDisconnect, status # Ensure WebSocketState if used

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        print(f"[{datetime.datetime.now()}] [MainServer_WS_Manager] Initialized.")

    async def connect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            print(f"[{datetime.datetime.now()}] [MainServer_WS_Manager] User {user_id} reconnected. Closing old WS.")
            old_ws = self.active_connections.pop(user_id, None)
            if old_ws:
                try:
                    # Use a standard close code like 1000 (Normal Closure) or 1008 (Policy Violation)
                    await old_ws.close(code=status.WS_1000_NORMAL_CLOSURE, reason="New connection by same user.")
                except Exception as e:
                    print(f"[{datetime.datetime.now()}] [MainServer_WS_Manager_ERROR] Error closing old WS for {user_id}: {e}")
        
        self.active_connections[user_id] = websocket
        print(f"[{datetime.datetime.now()}] [MainServer_WS_Manager] WebSocket connected for user: {user_id}. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        user_id_to_remove = None
        for uid, ws in self.active_connections.items():
            if ws == websocket:
                user_id_to_remove = uid
                break
        
        if user_id_to_remove:
            # Check if key exists before deleting
            if user_id_to_remove in self.active_connections:
                del self.active_connections[user_id_to_remove]
            print(f"[{datetime.datetime.now()}] [MainServer_WS_Manager] WebSocket disconnected for user: {user_id_to_remove}. Total: {len(self.active_connections)}")

    async def send_personal_message(self, message_data: Dict[str, Any], user_id: str):
        websocket = self.active_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_json(message_data)
                # print(f"[{datetime.datetime.now()}] [MainServer_WS_Manager] Sent message to {user_id}: type {message_data.get('type')}")
            except Exception as e:
                print(f"[{datetime.datetime.now()}] [MainServer_WS_Manager_ERROR] Error sending message to {user_id}: {e}. Disconnecting.")
                self.disconnect(websocket)
    
    async def broadcast_json_to_all(self, message_data: Dict[str, Any]):
        """Broadcasts a JSON message to all connected and authenticated clients."""
        disconnected_sockets = []
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message_data)
                # print(f"[{datetime.datetime.now()}] [MainServer_WS_Manager] Broadcasted message to {user_id}: type {message_data.get('type')}")
            except Exception as e:
                print(f"[{datetime.datetime.now()}] [MainServer_WS_Manager_ERROR] Error broadcasting to {user_id}: {e}. Marking for disconnect.")
                disconnected_sockets.append(websocket)
        
        for ws_to_remove in disconnected_sockets:
            self.disconnect(ws_to_remove)