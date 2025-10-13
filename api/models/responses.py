from pydantic import BaseModel, RootModel


class MessageResponse(BaseModel):
    message: str


class StatusResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str


class SuccessResponse(BaseModel):
    status: str = "success"
    message: str


class DeviceData(BaseModel):
    etalon_collection: str | None
    measured_collections: list[str] | None

    class Config:  # noqa: D106
        extra = "allow"


class GetDevicesResponse(RootModel[dict[str, DeviceData]]):
    pass


class GetEtalonPatternsResponse(RootModel[list[str]]):
    pass


class SelectPatternResponse(SuccessResponse):
    pass


class PatternMetadata(BaseModel):
    index: int
    duration: float


class UploadLogResponse(RootModel[list[PatternMetadata]]):
    pass


class SeekResponse(StatusResponse):
    time: float
