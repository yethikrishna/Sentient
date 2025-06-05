# src/server/main/ws_manager.py
import datetime
from typing import Dict, Any, Optional
from fastapi import WebSocket, status, WebSocketDisconnect # Ensure WebSocketState if used

class MainWebSocketManager:
    def __init__(self):
        # Separate dictionaries for different types of connections if needed
        self.voice_connections: Dict[str, WebSocket] = {}
        self.notification_connections: Dict[str, WebSocket] = {}
        print(f"[{datetime.datetime.now()}] [MainServer_WS_Manager] Initialized.")

    # --- Voice WebSocket Connection Management ---
    async def connect_voice(self, websocket: WebSocket, user_id: str):
        if user_id in self.voice_connections:
            old_ws = self.voice_connections.pop(user_id, None)
            if old_ws:
                try: await old_ws.close(code=status.WS_1000_NORMAL_CLOSURE, reason="New voice connection by same user.")
                except Exception as e: print(f"[WS_VOICE_MGR_ERROR] Closing old voice WS for {user_id}: {e}")
        self.voice_connections[user_id] = websocket
        print(f"[WS_VOICE_MGR] Voice WebSocket connected for user: {user_id}. Total voice: {len(self.voice_connections)}")

    def disconnect_voice(self, websocket: WebSocket):
        uid = next((uid for uid, ws in self.voice_connections.items() if ws == websocket), None)
        if uid and uid in self.voice_connections:
            del self.voice_connections[uid]
            print(f"[WS_VOICE_MGR] Voice WebSocket disconnected for user: {uid}. Total voice: {len(self.voice_connections)}")

    # --- Notification WebSocket Connection Management ---
    async def connect_notifications(self, websocket: WebSocket, user_id: str):
        if user_id in self.notification_connections:
            old_ws = self.notification_connections.pop(user_id, None)
            if old_ws:
                try: await old_ws.close(code=status.WS_1000_NORMAL_CLOSURE, reason="New notification connection by same user.")
                except Exception as e: print(f"[WS_NOTIF_MGR_ERROR] Closing old notif WS for {user_id}: {e}")
        self.notification_connections[user_id] = websocket
        print(f"[WS_NOTIF_MGR] Notification WebSocket connected for user: {user_id}. Total notif: {len(self.notification_connections)}")

    def disconnect_notifications(self, websocket: WebSocket):
        uid = next((uid for uid, ws in self.notification_connections.items() if ws == websocket), None)
        if uid and uid in self.notification_connections:
            del self.notification_connections[uid]
            print(f"[WS_NOTIF_MGR] Notification WebSocket disconnected for user: {uid}. Total notif: {len(self.notification_connections)}")

    # --- Generic Send/Broadcast (can be specialized if needed) ---
    async def send_personal_json_message(self, message_data: Dict[str, Any], user_id: str, connection_type: str = "notifications"):
        connections_dict = self.notification_connections if connection_type == "notifications" else self.voice_connections
        websocket = connections_dict.get(user_id)
        if websocket:
            try:
                await websocket.send_json(message_data)
            except Exception as e:
                print(f"[WS_MGR_ERROR] Sending JSON to {user_id} ({connection_type}): {e}. Disconnecting.")
                if connection_type == "notifications": self.disconnect_notifications(websocket)
                else: self.disconnect_voice(websocket)
    
    async def broadcast_json_to_all_notifications(self, message_data: Dict[str, Any]):
        disconnected_sockets = []
        for user_id, websocket in self.notification_connections.items():
            try:
                await websocket.send_json(message_data)
            except Exception as e:
                print(f"[WS_MGR_ERROR] Broadcasting notif to {user_id}: {e}. Marking for disconnect.")
                disconnected_sockets.append(websocket)
        for ws_to_remove in disconnected_sockets:
            self.disconnect_notifications(ws_to_remove)