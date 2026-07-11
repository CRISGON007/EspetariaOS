from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket


class RealtimeManager:
    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, event: str, payload: dict[str, Any]) -> None:
        if not self.connections:
            return
        message = json.dumps({"event": event, "payload": payload}, ensure_ascii=False)
        dead: list[WebSocket] = []
        for connection in list(self.connections):
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


realtime = RealtimeManager()
