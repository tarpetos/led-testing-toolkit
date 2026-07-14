"""
Response models for the API.

This module contains data models representing the response payloads
sent by various API endpoints.
"""

from pydantic import BaseModel, RootModel


class MessageResponse(BaseModel):
    """Response model containing a simple message."""

    message: str


class StatusResponse(BaseModel):
    """Response model containing a status."""

    status: str


class ErrorResponse(BaseModel):
    """Response model for an error."""

    status: str = "error"
    message: str


class SuccessResponse(BaseModel):
    """Response model for a successful operation."""

    status: str = "success"
    message: str


class DeviceData(BaseModel):
    """Represents data associated with a device."""

    etalon_collection: str | None
    measured_collections: list[str] | None

    model_config = {"extra": "allow"}


class GetDevicesResponse(RootModel[dict[str, DeviceData]]):
    """Response model for retrieving multiple devices."""


class GetEtalonPatternsResponse(RootModel[list[str]]):
    """Response model for retrieving a list of etalon patterns."""


class SelectPatternResponse(SuccessResponse):
    """Response model for selecting a pattern."""


class PatternMetadata(BaseModel):
    """Metadata associated with a specific pattern."""

    index: int
    duration: float


class UploadLogResponse(RootModel[list[PatternMetadata]]):
    """Response model for uploading a log, returning extracted patterns metadata."""


class SeekResponse(StatusResponse):
    """Response model for a seek operation."""

    time: float
