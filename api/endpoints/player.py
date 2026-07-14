from fastapi import APIRouter

from api.models.requests import SeekRequest
from api.models.responses import SeekResponse, StatusResponse
from api.services.player_service import player_service

router = APIRouter(prefix="/player", tags=["Player"])


@router.post("/resume")
async def resume_playback() -> StatusResponse:
    """
    Resume playback in the player.

    Returns:
        A status response indicating the player has resumed.

    """
    await player_service.resume()  # pragma: no cover
    return StatusResponse(status="resumed")  # pragma: no cover


@router.post("/pause")
async def pause_playback() -> StatusResponse:
    """
    Pause playback in the player.

    Returns:
        A status response indicating the player has paused.

    """
    await player_service.pause()  # pragma: no cover
    return StatusResponse(status="paused")  # pragma: no cover


@router.post("/stop")
async def stop_playback() -> StatusResponse:
    """
    Stop playback in the player.

    Returns:
        A status response indicating the player has stopped.

    """
    await player_service.stop()  # pragma: no cover
    return StatusResponse(status="stopped")  # pragma: no cover


@router.post("/seek")
async def seek_playback(request: SeekRequest) -> SeekResponse:
    """
    Seek to a specific time in playback.

    Args:
        request: The request payload containing the seek time.

    Returns:
        A seek response indicating the time to which the player seeked.

    """
    await player_service.seek_to_time(request.time)  # pragma: no cover
    return SeekResponse(status="seeked", time=request.time)  # pragma: no cover
