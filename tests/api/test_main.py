import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from api.main import app


def test_read_root():
    with (
        patch("api.main.player_service.playback_loop", new_callable=AsyncMock),
        patch("api.main.websocket.broadcast_loop", new_callable=AsyncMock),
    ):
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
