import pytest
from unittest.mock import patch

from api.services.device_services import DeviceService
from led_testing_toolkit.utils.collection_name import ETALONS_COLLECTION_SUFFIX

@pytest.fixture
def mock_mongo():
    with patch("api.services.device_services.MongoDbConnector") as mock:
        yield mock

@pytest.mark.asyncio
async def test_get_all_devices_data(mock_mongo):
    connector_instance = mock_mongo.return_value.__aenter__.return_value
    connector_instance.list_collections.return_value = [
        f"device1_{ETALONS_COLLECTION_SUFFIX}",
        "device1_measured_1",
        "invalid_collection_name"
    ]
    
    with patch("api.services.device_services.parse_collection_name") as mock_parse:
        def side_effect(name):
            if name == f"device1_{ETALONS_COLLECTION_SUFFIX}":
                return "device1", ETALONS_COLLECTION_SUFFIX
            elif name == "device1_measured_1":
                return "device1", "measured_1"
            else:
                raise ValueError("Invalid")
        mock_parse.side_effect = side_effect
        
        result = await DeviceService.get_all_devices_data()
        
        assert "device1" in result
        assert result["device1"]["etalon_collection"] == f"device1_{ETALONS_COLLECTION_SUFFIX}"
        assert result["device1"]["measured_collections"] == ["device1_measured_1"]

@pytest.mark.asyncio
async def test_get_measured_records_success(mock_mongo):
    connector_instance = mock_mongo.return_value.__aenter__.return_value
    connector_instance.read_field.return_value = ["rec1", "rec2"]
    
    result = await DeviceService.get_measured_records("col_name")
    
    connector_instance.use_collection.assert_called_with("col_name", auto_create=False)
    assert result == ["rec1", "rec2"]

@pytest.mark.asyncio
async def test_get_measured_records_exception(mock_mongo):
    mock_mongo.return_value.__aenter__.side_effect = Exception("error")
    
    result = await DeviceService.get_measured_records("col_name")
    
    assert result == []

@pytest.mark.asyncio
async def test_get_etalon_patterns(mock_mongo):
    connector_instance = mock_mongo.return_value.__aenter__.return_value
    connector_instance.read_field.return_value = ["pat1", "pat2", 123]
    
    result = await DeviceService.get_etalon_patterns("col_name")
    
    connector_instance.use_collection.assert_called_with("col_name", auto_create=False)
    assert result == ["pat1", "pat2"]
