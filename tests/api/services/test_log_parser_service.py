import pytest
from unittest.mock import MagicMock, AsyncMock

from api.services.log_parser_service import LogParserService

class DummyPoint:
    def __init__(self, z):
        self.z = z

    def __eq__(self, other):
        return isinstance(other, DummyPoint) and self.z == other.z

class DummyRecord:
    def __init__(self, coords):
        self.coordinates = coords

    def __eq__(self, other):
        return isinstance(other, DummyRecord) and self.coordinates == other.coordinates

@pytest.fixture
def parser_service():
    mock_led_parser = MagicMock()
    mock_led_parser.parse_log_file = AsyncMock()
    return LogParserService(mock_led_parser)

@pytest.mark.asyncio
async def test_parse_log_file_empty(parser_service):
    parser_service._parser.patterns = {}
    
    result = await parser_service.parse_log_file(b"content")
    
    assert result == []
    assert parser_service.last_parsed_patterns == []
    parser_service._parser.clear.assert_called_once()

@pytest.mark.asyncio
async def test_parse_log_file_with_data(parser_service):
    pattern_data = {
        "led1": {
            "r": [DummyRecord([DummyPoint(1.0), DummyPoint(3.0)])]
        }
    }
    parser_service._parser.patterns = {"file": [pattern_data]}
    
    result = await parser_service.parse_log_file(b"content")
    
    assert len(result) == 1
    assert result[0]["index"] == 0
    assert result[0]["duration"] == 2.0
    assert parser_service.last_parsed_patterns == [pattern_data]

def test_get_pattern_by_index(parser_service):
    parser_service.last_parsed_patterns = [{"pat": 1}]
    
    assert parser_service.get_pattern_by_index(0) == {"pat": 1}
    assert parser_service.get_pattern_by_index(1) is None
    assert parser_service.get_pattern_by_index(-1) is None

def test_calculate_pattern_duration_no_time():
    pattern = {
        "led1": {
            "r": [DummyRecord([])]
        }
    }
    dur = LogParserService._calculate_pattern_duration(pattern)
    assert dur == 0.0
