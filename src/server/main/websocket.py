# src/server/main/websocket.py
import datetime
import logging 
from typing import Dict, Any, Optional
from fastapi import WebSocket, status, WebSocketDisconnect, WebSocketState 

logger = logging.getLogger(__name__) 

class MainWebSocketManager:
    def __init__(self):
        self.voice_connections: Dict[str, WebSocket] = {}
        self.notification_connections: Dict[str, WebSocket] = {}
        logger.info(f"[{datetime.datetime.now()}] [MainServer_WebSocketManager] Initialized.")

    async def connect_voice(self, websocket: WebSocket, user_id: str):
        # Close existing connection for the same user, if any
        if user_id in self.voice_connections:
            old_ws = self.voice_connections.pop(user_id, None)
            if old_ws and old_ws.client_state == WebSocketState.CONNECTED:
                try: 
                    await old_ws.close(code=status.WS_1000_NORMAL_CLOSURE, reason="New voice connection by same user.")
                    logger.info(f"[{datetime.datetime.now()}] [WS_VOICE_MGR] Closed old voice WebSocket for user: {user_id}")
                except Exception as e: 
                    logger.error(f"[{datetime.datetime.now()}] [WS_VOICE_MGR_ERROR] Closing old voice WS for {user_id}: {e}")
        
        self.voice_connections[user_id] = websocket
        logger.info(f"[{datetime.datetime.now()}] [WS_VOICE_MGR] Voice WebSocket connected for user: {user_id}. Total voice connections: {len(self.voice_connections)}")

    def disconnect_voice(self, websocket: WebSocket):
        # Find user_id for the given websocket object
        uid_to_remove = None
        for uid, ws in self.voice_connections.items():
            if ws == websocket:
                uid_to_remove = uid
                break
        
        if uid_to_remove and uid_to_remove in self.voice_connections:
            del self.voice_connections[uid_to_remove]
            logger.info(f"[{datetime.datetime.now()}] [WS_VOICE_MGR] Voice WebSocket disconnected for user: {uid_to_remove}. Total voice connections: {len(self.voice_connections)}")
        # else: (no specific log if websocket not found, could be already removed)

    async def connect_notifications(self, websocket: WebSocket, user_id: str):
        if user_id in self.notification_connections:
            old_ws = self.notification_connections.pop(user_id, None)
            if old_ws and old_ws.client_state == WebSocketState.CONNECTED:
                try: 
                    await old_ws.close(code=status.WS_1000_NORMAL_CLOSURE, reason="New notification connection by same user.")
                    logger.info(f"[{datetime.datetime.now()}] [WS_NOTIF_MGR] Closed old notification WebSocket for user: {user_id}")
                except Exception as e: 
                    logger.error(f"[{datetime.datetime.now()}] [WS_NOTIF_MGR_ERROR] Closing old notif WS for {user_id}: {e}")

        self.notification_connections[user_id] = websocket
        logger.info(f"[{datetime.datetime.now()}] [WS_NOTIF_MGR] Notification WebSocket connected for user: {user_id}. Total notification connections: {len(self.notification_connections)}")

    def disconnect_notifications(self, websocket: WebSocket):
        uid_to_remove = None
        for uid, ws in self.notification_connections.items():
            if ws == websocket:
                uid_to_remove = uid
                break
        
        if uid_to_remove and uid_to_remove in self.notification_connections:
            del self.notification_connections[uid_to_remove]
            logger.info(f"[{datetime.datetime.now()}] [WS_NOTIF_MGR] Notification WebSocket disconnected for user: {uid_to_remove}. Total notification connections: {len(self.notification_connections)}")

    async def send_personal_json_message(self, message_data: Dict[str, Any], user_id: str, connection_type: str = "notifications"):
        connections_dict = self.notification_connections if connection_type == "notifications" else self.voice_connections
        websocket = connections_dict.get(user_id)
        
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json(message_data)
            except WebSocketDisconnect: # Should be caught by client_state check, but good for robustness
                logger.info(f"[{datetime.datetime.now()}] [WS_MGR_INFO] WebSocket for user {user_id} ({connection_type}) disconnected during send (caught).")
                if connection_type == "notifications": self.disconnect_notifications(websocket)
                else: self.disconnect_voice(websocket)
            except RuntimeError as e: # Can happen if trying to send on a closed/closing socket
                logger.error(f"[{datetime.datetime.now()}] [WS_MGR_ERROR] Runtime error sending JSON to {user_id} ({connection_type}): {e}. Disconnecting.", exc_info=False)
                if connection_type == "notifications": self.disconnect_notifications(websocket)
                else: self.disconnect_voice(websocket)
            except Exception as e:
                logger.error(f"[{datetime.datetime.now()}] [WS_MGR_ERROR] Generic error sending JSON to {user_id} ({connection_type}): {e}. Disconnecting.", exc_info=True)
                if connection_type == "notifications": self.disconnect_notifications(websocket)
                else: self.disconnect_voice(websocket)
        elif websocket: # Websocket object exists but not connected
            logger.warning(f"[{datetime.datetime.now()}] [WS_MGR_WARN] Attempted to send to user {user_id} ({connection_type}) but WebSocket state is {websocket.client_state}. Cleaning up.")
            if connection_type == "notifications": self.disconnect_notifications(websocket)
            else: self.disconnect_voice(websocket)


    async def broadcast_json_to_all_notifications(self, message_data: Dict[str, Any]):
        sockets_to_remove: List[WebSocket] = []
        
        # Iterate over a copy for safe removal if disconnect occurs during iteration
        for user_id, websocket in list(self.notification_connections.items()): 
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json(message_data)
                except WebSocketDisconnect:
                    logger.info(f"[{datetime.datetime.now()}] [WS_MGR_INFO] WebSocket for user {user_id} (notifications) disconnected during broadcast (caught).")
                    sockets_to_remove.append(websocket)
                except RuntimeError as e:
                    logger.error(f"[{datetime.datetime.now()}] [WS_MGR_ERROR] Runtime error broadcasting notif to {user_id}: {e}. Marking for disconnect.", exc_info=False)
                    sockets_to_remove.append(websocket)
                except Exception as e:
                    logger.error(f"[{datetime.datetime.now()}] [WS_MGR_ERROR] Generic error broadcasting notif to {user_id}: {e}. Marking for disconnect.", exc_info=True)
                    sockets_to_remove.append(websocket)
            else: # Socket exists but not connected
                logger.warning(f"[{datetime.datetime.now()}] [WS_MGR_WARN] Notification socket for user {user_id} found in non-connected state ({websocket.client_state}) during broadcast. Marking for removal.")
                sockets_to_remove.append(websocket)

        for ws_to_remove in sockets_to_remove:
            self.disconnect_notifications(ws_to_remove)