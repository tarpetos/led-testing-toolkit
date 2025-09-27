import asyncio
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.services.player_service import player_service

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.remove(websocket)

    async def broadcast_state(self) -> None:
        state = player_service.get_state()
        state_json = state.model_dump_json()
        for connection in list(self.active_connections):
            await connection.send_text(state_json)


manager = ConnectionManager()


async def broadcast_loop() -> None:
    while True:
        try:
            if manager.active_connections:
                await manager.broadcast_state()
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(0.05)


@router.websocket("/ws/led")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
