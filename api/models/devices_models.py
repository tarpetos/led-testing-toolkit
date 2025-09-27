from pydantic import BaseModel, RootModel


class SelectEtalonRequest(BaseModel):
    pattern_name: str


class SelectMeasuredRequest(BaseModel):
    collection_name: str


class DeviceData(BaseModel):
    etalon_collection: str

    class Config:  # noqa: D106
        extra = "allow"


class GetDevicesResponse(RootModel[dict[str, DeviceData]]):
    pass


class GetEtalonPatternsResponse(RootModel[list[str]]):
    pass
