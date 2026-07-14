from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from api.models.requests import SelectPatternRequest
from api.models.responses import SelectPatternResponse, UploadLogResponse
from api.services.log_parser_service import log_parser_service
from api.services.player_service import player_service
from led_testing_toolkit.utils.data_processing import convert_normalized_to_raw_format

router = APIRouter(prefix="/parser", tags=["Parser"])


@router.post("/upload-log")
async def upload_log_file(file: Annotated[UploadFile, File()] = ...) -> UploadLogResponse:
    """
    Upload and parse a log file.

    Args:
        file: The uploaded log file.

    Returns:
        An upload log response containing parsed data.

    Raises:
        HTTPException: If parsing the log file fails.

    """
    try:
        content = await file.read()
        return await log_parser_service.parse_log_file(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse log file: {e!s}") from e


@router.post("/select-pattern")
async def select_log_pattern(request: SelectPatternRequest) -> SelectPatternResponse:
    """
    Select a log pattern to load into the player.

    Args:
        request: The request payload containing the pattern index.

    Returns:
        A response indicating successful loading of the pattern.

    Raises:
        HTTPException: If the pattern index is invalid or the pattern is not found.

    """
    try:
        pattern_index = request.index
    except (ValueError, TypeError) as e:  # pragma: no cover
        raise HTTPException(status_code=400, detail="Invalid pattern index provided!") from e  # pragma: no cover

    normalized_pattern = log_parser_service.get_pattern_by_index(pattern_index)
    if not normalized_pattern:
        raise HTTPException(status_code=404, detail=f"Pattern with index {pattern_index} not found!")

    raw_pattern_data = convert_normalized_to_raw_format(normalized_pattern)

    await player_service.load_raw_pattern_data(raw_pattern_data)

    return {"message": f"Pattern #{pattern_index + 1} loaded into player successfully."}
