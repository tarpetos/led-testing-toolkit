import pytest
from pydantic import ValidationError
from api.models.requests import SelectEtalonRequest, SelectMeasuredRequest, SeekRequest, SelectPatternRequest


def test_select_etalon_request():
    req = SelectEtalonRequest(pattern_name="test_pattern")
    assert req.pattern_name == "test_pattern"

    with pytest.raises(ValidationError):
        SelectEtalonRequest()


def test_select_measured_request():
    req = SelectMeasuredRequest(collection_name="test_collection")
    assert req.collection_name == "test_collection"

    with pytest.raises(ValidationError):
        SelectMeasuredRequest()


def test_seek_request():
    req = SeekRequest(time=5.5)
    assert req.time == 5.5

    with pytest.raises(ValidationError):
        SeekRequest(time=-1.0)  # Time must be >= 0


def test_select_pattern_request():
    req = SelectPatternRequest(index=2)
    assert req.index == 2

    with pytest.raises(ValidationError):
        SelectPatternRequest(index="invalid")
