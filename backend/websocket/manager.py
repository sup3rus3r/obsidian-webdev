"""WebSocket connection registry."""
from fastapi import WebSocket


class ConnectionManager:
    """Asyncio-safe registry of active WebSocket connections, keyed by an arbitrary string ID.

    Connections are stored in lists to support multiple simultaneous viewers
    (e.g. two browser tabs watching the same agent session).
    """

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, key: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(key, []).append(ws)

    def disconnect(self, key: str, ws: WebSocket) -> None:
        conns = self._connections.get(key, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(key, None)

    def is_connected(self, key: str) -> bool:
        return bool(self._connections.get(key))

    def connection_count(self, key: str) -> int:
        return len(self._connections.get(key, []))

    async def send_json(self, key: str, data: dict) -> None:
        for ws in list(self._connections.get(key, [])):
            try:
                await ws.send_json(data)
            except Exception:
                pass

    async def send_text(self, key: str, text: str) -> None:
        for ws in list(self._connections.get(key, [])):
            try:
                await ws.send_text(text)
            except Exception:
                pass

    async def send_bytes(self, key: str, data: bytes) -> None:
        for ws in list(self._connections.get(key, [])):
            try:
                await ws.send_bytes(data)
            except Exception:
                pass


agent_manager = ConnectionManager()
terminal_manager = ConnectionManager()
