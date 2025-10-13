from pydantic import BaseModel, Field


class SelectEtalonRequest(BaseModel):
    pattern_name: str = Field(
        ...,
        description="The name of the etalon pattern to load",
    )


class SelectMeasuredRequest(BaseModel):
    collection_name: str = Field(
        ...,
        description="The name of the measured collection to load a random record from",
    )


class SeekRequest(BaseModel):
    time: float = Field(..., ge=0, description="The time to seek to in seconds")


class SelectPatternRequest(BaseModel):
    index: int
