import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import WebSocketDisconnect

from api.main import app
from api.endpoints.websocket import manager, broadcast_loop

@pytest.fixture
def client():
    with patch("api.main.player_service.playback_loop", new_callable=AsyncMock), \
         patch("api.main.websocket.broadcast_loop", new_callable=AsyncMock):
        with TestClient(app) as c:
            yield c

def test_websocket_endpoint(client):
    # Ensure manager is empty
    manager.active_connections.clear()
    with client.websocket_connect("/api/v1/ws/led") as websocket:
        assert len(manager.active_connections) == 1
    assert len(manager.active_connections) == 0

@pytest.mark.anyio
async def test_manager_broadcast_state():
    with patch("api.endpoints.websocket.player_service.get_state") as mock_get_state:
        mock_state = MagicMock()
        mock_state.model_dump_json.return_value = "{}"
        mock_get_state.return_value = mock_state
        
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send_text.side_effect = WebSocketDisconnect()
        mock_ws3 = AsyncMock()
        mock_ws3.send_text.side_effect = Exception("error")
        
        manager.active_connections = [mock_ws1, mock_ws2, mock_ws3]
        await manager.broadcast_state()
        
        mock_ws1.send_text.assert_called_once_with("{}")
        assert len(manager.active_connections) == 1
        assert manager.active_connections[0] == mock_ws1

@pytest.mark.anyio
async def test_broadcast_loop():
    with patch("api.endpoints.websocket.manager.broadcast_state", new_callable=AsyncMock) as mock_broadcast, \
         patch("api.endpoints.websocket.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        
        mock_sleep.side_effect = asyncio.CancelledError()
        manager.active_connections = [AsyncMock()]
        try:
            await broadcast_loop()
        except asyncio.CancelledError:
            pass
        mock_broadcast.assert_called_once()

@pytest.mark.anyio
async def test_broadcast_loop_exception():
    with patch("api.endpoints.websocket.manager.broadcast_state", new_callable=AsyncMock) as mock_broadcast, \
         patch("api.endpoints.websocket.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        
        mock_broadcast.side_effect = Exception("error")
        mock_sleep.side_effect = asyncio.CancelledError()
        manager.active_connections = [AsyncMock()]
        try:
            await broadcast_loop()
        except asyncio.CancelledError:
            pass
        mock_broadcast.assert_called_once()
