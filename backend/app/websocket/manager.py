"""WebSocket connection manager and live-event broadcasting.

A single global ``manager`` instance fans out JSON events to every connected
client (sales screens, drawing console, TV displays, pickup stations). It also
tracks a lightweight device registry for the admin "device status" panel via
heartbeat messages.
"""
import asyncio
import json
from datetime import datetime

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active: set[WebSocket] = set()
        # websocket -> {"name","role","last_seen"}
        self.devices: dict[WebSocket, dict] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active.discard(websocket)
        self.devices.pop(websocket, None)

    async def register_device(
        self, websocket: WebSocket, name: str, role: str
    ) -> None:
        self.devices[websocket] = {
            "name": name or "Unknown device",
            "role": role or "viewer",
            "last_seen": datetime.utcnow().isoformat(),
        }

    def heartbeat(self, websocket: WebSocket) -> None:
        if websocket in self.devices:
            self.devices[websocket]["last_seen"] = datetime.utcnow().isoformat()

    def device_list(self) -> list[dict]:
        return list(self.devices.values())

    async def broadcast(self, event: str, payload: dict | None = None) -> None:
        message = json.dumps(
            {
                "event": event,
                "data": payload or {},
                "ts": datetime.utcnow().isoformat(),
            }
        )
        dead = []
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def broadcast_sync(self, event: str, payload: dict | None = None) -> None:
        """Schedule a broadcast from synchronous (request-handler) code."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            asyncio.create_task(self.broadcast(event, payload))
        else:  # pragma: no cover - fallback outside an event loop
            asyncio.run(self.broadcast(event, payload))


manager = ConnectionManager()
