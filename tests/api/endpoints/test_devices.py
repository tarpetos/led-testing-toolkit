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

def test_get_devices(client):
    with patch("api.endpoints.devices.device_service.get_all_devices_data", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"DEVICE1": {"etalon_collection": "col1", "measured_collections": []}}
        response = client.get("/api/v1/devices/")
        assert response.status_code == 200
        assert response.json() == {"DEVICE1": {"etalon_collection": "col1", "measured_collections": []}}

def test_get_etalon_patterns_success(client):
    with patch("api.endpoints.devices.device_service.get_all_devices_data", new_callable=AsyncMock) as mock_get, \
         patch("api.endpoints.devices.device_service.get_etalon_patterns", new_callable=AsyncMock) as mock_patterns:
        mock_get.return_value = {"DEVICE1": {"etalon_collection": "col1"}}
        mock_patterns.return_value = ["pattern1"]
        response = client.get("/api/v1/devices/device1/etalon/patterns")
        assert response.status_code == 200
        assert response.json() == ["pattern1"]

def test_get_etalon_patterns_not_found(client):
    with patch("api.endpoints.devices.device_service.get_all_devices_data", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"DEVICE1": {}}
        response = client.get("/api/v1/devices/device1/etalon/patterns")
        assert response.status_code == 404

def test_select_etalon_success(client):
    with patch("api.endpoints.devices.device_service.get_all_devices_data", new_callable=AsyncMock) as mock_get, \
         patch("api.endpoints.devices.player_service.load_etalon_pattern", new_callable=AsyncMock) as mock_load:
        mock_get.return_value = {"DEVICE1": {"etalon_collection": "col1"}}
        response = client.post("/api/v1/devices/device1/etalon/select", json={"pattern_name": "p1"})
        assert response.status_code == 200

def test_select_etalon_not_found(client):
    with patch("api.endpoints.devices.device_service.get_all_devices_data", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"DEVICE1": {}}
        response = client.post("/api/v1/devices/device1/etalon/select", json={"pattern_name": "p1"})
        assert response.status_code == 500

def test_select_etalon_error(client):
    with patch("api.endpoints.devices.device_service.get_all_devices_data", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("error")
        response = client.post("/api/v1/devices/device1/etalon/select", json={"pattern_name": "p1"})
        assert response.status_code == 500

def test_get_measured_records(client):
    with patch("api.endpoints.devices.device_service.get_measured_records", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = ["rec1"]
        response = client.get("/api/v1/measured/col1/records")
        assert response.status_code == 200

def test_select_measured_success(client):
    with patch("api.endpoints.devices.player_service.load_measured_pattern", new_callable=AsyncMock) as mock_load:
        response = client.post("/api/v1/devices/device1/measured/select", json={"collection_name": "c1"})
        assert response.status_code == 200

def test_select_measured_error(client):
    with patch("api.endpoints.devices.player_service.load_measured_pattern", new_callable=AsyncMock) as mock_load:
        mock_load.side_effect = Exception("error")
        response = client.post("/api/v1/devices/device1/measured/select", json={"collection_name": "c1"})
        assert response.status_code == 500
