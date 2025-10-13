from pydantic import BaseModel


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
