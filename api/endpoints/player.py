from fastapi import APIRouter

from api.models.common_models import StatusResponse
from api.models.player_models import SeekRequest, SeekResponse
from api.services.player_service import player_service

router = APIRouter(prefix="/player", tags=["Player"])


@router.post("/resume")
async def resume_playback() -> StatusResponse:
    await player_service.resume()
    return StatusResponse(status="resumed")


@router.post("/pause")
async def pause_playback() -> StatusResponse:
    await player_service.pause()
    return StatusResponse(status="paused")


@router.post("/stop")
async def stop_playback() -> StatusResponse:
    await player_service.stop()
    return StatusResponse(status="stopped")


@router.post("/seek")
async def seek_playback(request: SeekRequest) -> SeekResponse:
    await player_service.seek_to_time(request.time)
    return SeekResponse(status="seeked", time=request.time)
