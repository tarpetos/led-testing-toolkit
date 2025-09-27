from pydantic import BaseModel

from api.models.common_models import StatusResponse


class SeekRequest(BaseModel):
    time: float


class SeekResponse(StatusResponse):
    time: float
