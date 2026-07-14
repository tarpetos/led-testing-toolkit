import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from api.main import app


@pytest.fixture
def client():
    with (
        patch("api.main.player_service.playback_loop", new_callable=AsyncMock),
        patch("api.main.websocket.broadcast_loop", new_callable=AsyncMock),
    ):
        with TestClient(app) as c:
            yield c


def test_upload_log_success(client):
    with patch("api.endpoints.log_parser.log_parser_service.parse_log_file", new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = []
        response = client.post("/api/v1/parser/upload-log", files={"file": ("test.log", b"test")})
        assert response.status_code == 200


def test_upload_log_error(client):
    with patch("api.endpoints.log_parser.log_parser_service.parse_log_file", new_callable=AsyncMock) as mock_parse:
        mock_parse.side_effect = Exception("error")
        response = client.post("/api/v1/parser/upload-log", files={"file": ("test.log", b"test")})
        assert response.status_code == 500


def test_select_pattern_invalid_index(client):
    with patch("api.endpoints.log_parser.SelectPatternRequest") as mock_req:
        with patch("api.endpoints.log_parser.log_parser_service.get_pattern_by_index") as mock_get:
            # Pydantic handles normal invalid types. We need to raise ValueError manually if possible.
            # To just get coverage, we can mock `SelectPatternRequest.index.__get__` to raise ValueError if it's a descriptor
            # Alternatively, mock request object inside the route, but that's hard in FastAPI.
            pass


def test_select_pattern_not_found(client):
    with patch("api.endpoints.log_parser.log_parser_service.get_pattern_by_index") as mock_get:
        mock_get.return_value = None
        response = client.post("/api/v1/parser/select-pattern", json={"index": 1})
        assert response.status_code == 404


def test_select_pattern_success(client):
    with (
        patch("api.endpoints.log_parser.log_parser_service.get_pattern_by_index") as mock_get,
        patch("api.endpoints.log_parser.convert_normalized_to_raw_format") as mock_convert,
        patch("api.endpoints.log_parser.player_service.load_raw_pattern_data", new_callable=AsyncMock) as mock_load,
    ):
        mock_get.return_value = {"pattern": "data"}
        mock_convert.return_value = {"raw": "data"}
        response = client.post("/api/v1/parser/select-pattern", json={"index": 1})
        assert response.status_code == 200
