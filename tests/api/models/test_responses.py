import pytest
from pydantic import ValidationError
from api.models.responses import (
    MessageResponse,
    StatusResponse,
    ErrorResponse,
    SuccessResponse,
    DeviceData,
    GetDevicesResponse,
    GetEtalonPatternsResponse,
    SelectPatternResponse,
    PatternMetadata,
    UploadLogResponse,
    SeekResponse,
)


def test_message_response():
    resp = MessageResponse(message="Hello")
    assert resp.message == "Hello"


def test_status_response():
    resp = StatusResponse(status="running")
    assert resp.status == "running"


def test_error_response():
    resp = ErrorResponse(message="Error occurred")
    assert resp.status == "error"
    assert resp.message == "Error occurred"


def test_success_response():
    resp = SuccessResponse(message="Operation successful")
    assert resp.status == "success"
    assert resp.message == "Operation successful"


def test_device_data():
    data = DeviceData(etalon_collection="etalon1", measured_collections=["meas1", "meas2"])
    assert data.etalon_collection == "etalon1"
    assert data.measured_collections == ["meas1", "meas2"]

    # Test allowing extra attributes
    data_extra = DeviceData(etalon_collection=None, measured_collections=None, extra_field="value")
    assert data_extra.etalon_collection is None
    assert getattr(data_extra, "extra_field", None) == "value"


def test_get_devices_response():
    dev = DeviceData(etalon_collection=None, measured_collections=None)
    resp = GetDevicesResponse({"dev1": dev})
    assert "dev1" in resp.root


def test_get_etalon_patterns_response():
    resp = GetEtalonPatternsResponse(["pat1", "pat2"])
    assert resp.root == ["pat1", "pat2"]


def test_select_pattern_response():
    resp = SelectPatternResponse(message="Selected")
    assert resp.status == "success"
    assert resp.message == "Selected"


def test_pattern_metadata():
    meta = PatternMetadata(index=1, duration=5.5)
    assert meta.index == 1
    assert meta.duration == 5.5


def test_upload_log_response():
    meta = PatternMetadata(index=1, duration=5.5)
    resp = UploadLogResponse([meta])
    assert resp.root[0].index == 1
    assert resp.root[0].duration == 5.5


def test_seek_response():
    resp = SeekResponse(status="ok", time=10.0)
    assert resp.status == "ok"
    assert resp.time == 10.0
