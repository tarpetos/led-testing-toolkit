from pydantic import BaseModel, RootModel


class SelectPatternRequest(BaseModel):
    index: int


class PatternMetadata(BaseModel):
    index: int
    duration: float


class UploadLogResponse(RootModel[list[PatternMetadata]]):
    pass
