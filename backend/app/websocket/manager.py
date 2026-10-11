import json
import logging
from typing import Dict, Set, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Maps session_id to set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)
        logger.info(f"WebSocket client connected to session {session_id}. Total: {len(self.active_connections[session_id])}")

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket client disconnected from session {session_id}")

    async def broadcast(self, session_id: str, event_type: str, data: Any):
        if session_id not in self.active_connections:
            return

        message = json.dumps({"event": event_type, "data": data})
        dead_sockets = set()

        for connection in list(self.active_connections[session_id]):
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Error sending message to websocket: {e}")
                dead_sockets.add(connection)

        for dead in dead_sockets:
            self.disconnect(session_id, dead)


ws_manager = ConnectionManager()
