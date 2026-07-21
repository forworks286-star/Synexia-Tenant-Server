import asyncio
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._clients: dict[WebSocket, int | None] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int | None = None):
        await websocket.accept()
        async with self._lock:
            self._clients[websocket] = user_id

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._clients.pop(websocket, None)

    async def broadcast(self, message: dict):
        async with self._lock:
            cibles = list(self._clients.keys())
        morts = []
        for ws in cibles:
            try:
                await ws.send_json(message)
            except Exception:
                morts.append(ws)
        if morts:
            async with self._lock:
                for ws in morts:
                    self._clients.pop(ws, None)

    async def send_to_user(self, user_id: int, message: dict):
        async with self._lock:
            cibles = [ws for ws, uid in self._clients.items() if uid == user_id]
        morts = []
        for ws in cibles:
            try:
                await ws.send_json(message)
            except Exception:
                morts.append(ws)
        if morts:
            async with self._lock:
                for ws in morts:
                    self._clients.pop(ws, None)


ws_manager = ConnectionManager()