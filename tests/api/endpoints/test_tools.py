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

def test_split_logs(client):
    with patch("api.endpoints.tools.tools_service.split_logs", new_callable=AsyncMock) as mock_split:
        mock_split.return_value = {"status": "ok"}
        response = client.post("/api/v1/tools/split-logs", files={"files": ("test.log", b"test")}, data={"max_patterns": 1, "start_pattern": "s", "end_pattern": "e"})
        assert response.status_code == 200

def test_compare_patterns(client):
    with patch("api.endpoints.tools.tools_service.compare_patterns", new_callable=AsyncMock) as mock_compare:
        mock_compare.return_value = {"status": "ok"}
        response = client.post("/api/v1/tools/compare-patterns", data={"measured_collection": "c", "measured_record": "r", "etalon_device": "d", "etalon_pattern": "p"})
        assert response.status_code == 200

def test_compare_log_pattern(client):
    with patch("api.endpoints.tools.tools_service.compare_log_pattern", new_callable=AsyncMock) as mock_compare:
        mock_compare.return_value = {"status": "ok"}
        response = client.post("/api/v1/tools/compare-log-pattern", data={"pattern_index": 1, "etalon_device": "d", "etalon_pattern": "p"})
        assert response.status_code == 200

def test_generate_etalons(client):
    with patch("api.endpoints.tools.tools_service.generate_etalons", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {"status": "ok"}
        response = client.post("/api/v1/tools/generate-etalons", data={"device_name": "d", "pattern_name": "p"})
        assert response.status_code == 200

def test_generate_from_parameters(client):
    with patch("api.endpoints.tools.tools_service.generate_from_parameters", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {"status": "ok"}
        response = client.post("/api/v1/tools/generate-from-parameters", data={"duration": 10.0})
        assert response.status_code == 200

def test_generate_from_source(client):
    with patch("api.endpoints.tools.tools_service.generate_from_source", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {"status": "ok"}
        response = client.post("/api/v1/tools/generate-from-source", data={"source_type": "t"})
        assert response.status_code == 200
