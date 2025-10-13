from pydantic import BaseModel, RootModel

from api.models.common_models import SuccessResponse


class SelectPatternRequest(BaseModel):
    index: int


class SelectPatternResponse(SuccessResponse):
    pass


class PatternMetadata(BaseModel):
    index: int
    duration: float


class UploadLogResponse(RootModel[list[PatternMetadata]]):
    pass
