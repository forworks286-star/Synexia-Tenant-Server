from fastapi import WebSocket
import asyncio


class ConnectionManager:
    def __init__(self):
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, message: dict):
        if not self._clients:
            return
        async with self._lock:
            clients_snapshot = set(self._clients)
        dead = set()
        for ws in clients_snapshot:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        if dead:
            async with self._lock:
                self._clients -= dead


ws_manager = ConnectionManager()
