import pytest
from pydantic import ValidationError
from api.models.tools import ComparePatternsRequest, CompareLogPatternRequest, GenerateEtalonsRequest


def test_compare_patterns_request():
    req = ComparePatternsRequest(
        measured_collection="col1", measured_record="rec1", etalon_device="dev1", etalon_pattern="pat1"
    )
    assert req.measured_collection == "col1"
    assert req.measured_record == "rec1"
    assert req.etalon_device == "dev1"
    assert req.etalon_pattern == "pat1"

    with pytest.raises(ValidationError):
        ComparePatternsRequest(measured_collection="col1")


def test_compare_log_pattern_request():
    req = CompareLogPatternRequest(pattern_index=5, etalon_device="dev1", etalon_pattern="pat1")
    assert req.pattern_index == 5
    assert req.etalon_device == "dev1"
    assert req.etalon_pattern == "pat1"

    with pytest.raises(ValidationError):
        CompareLogPatternRequest(pattern_index="invalid")


def test_generate_etalons_request():
    req = GenerateEtalonsRequest()
    assert req.device_name is None
    assert req.pattern_name is None

    req2 = GenerateEtalonsRequest(device_name="dev1", pattern_name="pat1")
    assert req2.device_name == "dev1"
    assert req2.pattern_name == "pat1"
