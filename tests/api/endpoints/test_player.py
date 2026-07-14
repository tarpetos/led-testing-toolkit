import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from api.main import app

@pytest.fixture
def client():
    with patch("api.main.player_service.playback_loop", new_callable=AsyncMock), \
         patch("api.main.websocket.broadcast_loop", new_callable=AsyncMock):
        with TestClient(app) as c:
            yield c

def test_resume(client):
    with patch("api.endpoints.player.player_service.resume", new_callable=AsyncMock):
        response = client.post("/api/v1/player/resume")
        assert response.status_code == 200

def test_pause(client):
    with patch("api.endpoints.player.player_service.pause", new_callable=AsyncMock):
        response = client.post("/api/v1/player/pause")
        assert response.status_code == 200

def test_stop(client):
    with patch("api.endpoints.player.player_service.stop", new_callable=AsyncMock):
        response = client.post("/api/v1/player/stop")
        assert response.status_code == 200

def test_seek(client):
    with patch("api.endpoints.player.player_service.seek_to_time", new_callable=AsyncMock):
        response = client.post("/api/v1/player/seek", json={"time": 10.0})
        assert response.status_code == 200
