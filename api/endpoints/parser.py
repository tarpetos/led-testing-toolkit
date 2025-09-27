from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from api.models.common_models import MessageResponse
from api.models.parser_models import (
    SelectPatternRequest,
    UploadLogResponse,
)
from api.services.parser_service import log_parser_service
from api.services.player_service import player_service

router = APIRouter(prefix="/parser", tags=["Parser"])


@router.post("/upload-log")
async def upload_log_file(file: Annotated[UploadFile, File()] = ...) -> UploadLogResponse:
    if not file.filename.endswith(".log"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .log file.")

    content = await file.read()
    patterns_metadata = await log_parser_service.parse_log_file(content)

    if not patterns_metadata:
        raise HTTPException(status_code=404, detail="No valid LED patterns found in the log file.")

    return patterns_metadata


@router.post("/select-pattern")
async def select_pattern_from_log(request: SelectPatternRequest) -> MessageResponse:
    pattern_data = log_parser_service.get_pattern_by_index(request.index)
    if pattern_data is None:
        raise HTTPException(status_code=404, detail="Pattern with the specified index not found.")

    await player_service.load_raw_pattern_data(pattern_data)

    return MessageResponse(message=f"Pattern #{request.index + 1} from log file loaded successfully")
