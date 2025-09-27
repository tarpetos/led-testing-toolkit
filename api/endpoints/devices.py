import traceback
from typing import Any

from fastapi import APIRouter, HTTPException

from api.models.common_models import MessageResponse
from api.models.devices_models import (
    GetDevicesResponse,
    GetEtalonPatternsResponse,
    SelectEtalonRequest,
    SelectMeasuredRequest,
)
from api.services.device_services import device_service
from api.services.player_service import player_service

router = APIRouter()


@router.get("/devices/", response_model=GetDevicesResponse)
async def get_devices() -> dict[str, Any]:
    return await device_service.get_all_devices_data()


@router.get("/devices/{device_name}/etalon/patterns", response_model=GetEtalonPatternsResponse)
async def get_etalon_patterns(device_name: str) -> list[str]:
    devices = await device_service.get_all_devices_data()
    device_data = devices.get(device_name.upper())
    if not device_data or not device_data.get("etalon_collection"):
        raise HTTPException(
            status_code=404,
            detail="Etalon collection for device not found",
        )

    return await device_service.get_etalon_patterns(device_data["etalon_collection"])


@router.post("/devices/{device_name}/etalon/select")
async def select_etalon(device_name: str, request: SelectEtalonRequest) -> MessageResponse:
    try:
        devices = await device_service.get_all_devices_data()
        device_data = devices.get(device_name.upper())
        if not device_data or not device_data.get("etalon_collection"):
            raise HTTPException(  # noqa:  TRY301
                status_code=404,
                detail="Device or etalon collection not found",
            )

        await player_service.load_etalon_pattern(device_data["etalon_collection"], request.pattern_name)
    except Exception as e:
        tb_str = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {tb_str}") from e

    return MessageResponse(
        message=f"Etalon '{request.pattern_name}' loaded successfully",
    )


@router.post("/devices/{device_name}/measured/select")
async def select_measured(device_name: str, request: SelectMeasuredRequest) -> MessageResponse:  # noqa: ARG001
    try:
        await player_service.load_measured_pattern(request.collection_name)
    except Exception as e:
        tb_str = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {tb_str}") from e

    return MessageResponse(
        message=f"Random record from '{request.collection_name}' loaded successfully",
    )
