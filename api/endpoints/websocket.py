import asyncio
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.services.player_service import player_service

router = APIRouter()


class ConnectionManager:
    """Manager for WebSocket connections."""

    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """
        Connect a new WebSocket.

        Args:
            websocket: The WebSocket instance to connect.

        """
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnect a WebSocket.

        Args:
            websocket: The WebSocket instance to disconnect.

        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_state(self) -> None:
        """Broadcast the player state to all active connections."""
        state = player_service.get_state()
        state_json = state.model_dump_json()
        disconnected_connections = []

        for connection in list(self.active_connections):
            try:
                await connection.send_text(state_json)
            except WebSocketDisconnect:
                disconnected_connections.append(connection)
            except Exception:
                disconnected_connections.append(connection)
                traceback.print_exc()

        for connection in disconnected_connections:
            self.disconnect(connection)


manager = ConnectionManager()


async def broadcast_loop() -> None:
    """Continuously broadcast the player state to active connections."""
    while True:
        try:
            if manager.active_connections:
                await manager.broadcast_state()
        except Exception:
            traceback.print_exc()
        await asyncio.sleep(0.01)


@router.websocket("/ws/led")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for LED state.

    Args:
        websocket: The WebSocket connection.

    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
