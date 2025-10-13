from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from api.models.log_parser_models import SelectPatternResponse, UploadLogResponse
from api.services.log_parser_service import log_parser_service
from api.services.player_service import player_service
from led_testing_toolkit.utils.data_processing import convert_normalized_to_raw_format

router = APIRouter(prefix="/parser", tags=["Parser"])


@router.post("/upload-log")
async def upload_log_file(file: Annotated[UploadFile, File()] = ...) -> UploadLogResponse:
    try:
        content = await file.read()
        return await log_parser_service.parse_log_file(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse log file: {e!s}") from e


@router.post("/select-pattern")
async def select_log_pattern(request: Request) -> SelectPatternResponse:
    try:
        body = await request.json()
        pattern_index = int(body.get("index"))
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail="Invalid pattern index provided.") from e

    normalized_pattern = log_parser_service.get_pattern_by_index(pattern_index)
    if not normalized_pattern:
        raise HTTPException(status_code=404, detail=f"Pattern with index {pattern_index} not found.")

    raw_pattern_data = convert_normalized_to_raw_format(normalized_pattern)

    await player_service.load_raw_pattern_data(raw_pattern_data)

    return {"message": f"Pattern #{pattern_index + 1} loaded into player successfully."}
