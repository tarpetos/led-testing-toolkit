import traceback
from typing import Any

from fastapi import APIRouter, HTTPException

from api.models.requests import SelectEtalonRequest, SelectMeasuredRequest
from api.models.responses import (
    GetDevicesResponse,
    GetEtalonPatternsResponse,
    MessageResponse,
)
from api.services.device_services import device_service
from api.services.player_service import player_service

router = APIRouter()


@router.get("/devices/", response_model=GetDevicesResponse)
async def get_devices() -> dict[str, Any]:
    """
    Retrieve all devices data.

    Returns:
        A dictionary containing device data.

    """
    return await device_service.get_all_devices_data()


@router.get("/devices/{device_name}/etalon/patterns", response_model=GetEtalonPatternsResponse)
async def get_etalon_patterns(device_name: str) -> list[str]:
    """
    Get all etalon patterns for a specific device.

    Args:
        device_name: The name of the device.

    Returns:
        A list of etalon pattern names.

    Raises:
        HTTPException: If the device or its etalon collection is not found.

    """
    devices = await device_service.get_all_devices_data()
    device_data = devices.get(device_name.upper())
    if not device_data or not device_data.get("etalon_collection"):
        raise HTTPException(
            status_code=404,
            detail="Etalon collection for device not found!",
        )

    return await device_service.get_etalon_patterns(device_data["etalon_collection"])


@router.post("/devices/{device_name}/etalon/select")
async def select_etalon(device_name: str, request: SelectEtalonRequest) -> MessageResponse:
    """
    Select and load an etalon pattern for a device.

    Args:
        device_name: The name of the device.
        request: The select etalon request payload.

    Returns:
        A message response indicating successful loading.

    Raises:
        HTTPException: If the device or etalon collection is not found, or if an internal error occurs.

    """
    try:
        devices = await device_service.get_all_devices_data()
        device_data = devices.get(device_name.upper())
        if not device_data or not device_data.get("etalon_collection"):
            raise HTTPException(  # noqa:  TRY301
                status_code=404,
                detail="Device or etalon collection not found!",
            )

        await player_service.load_etalon_pattern(device_data["etalon_collection"], request.pattern_name)
    except Exception as e:
        tb_str = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {tb_str}") from e

    return MessageResponse(
        message=f"Etalon `{request.pattern_name}` loaded successfully",
    )


@router.get("/measured/{collection_name}/records")
async def get_measured_records(collection_name: str) -> list[str]:
    """
    Get all measured records for a specific collection.

    Args:
        collection_name: The name of the collection.

    Returns:
        A list of measured record names.

    """
    return await device_service.get_measured_records(collection_name)


@router.post("/devices/{device_name}/measured/select")
async def select_measured(device_name: str, request: SelectMeasuredRequest) -> MessageResponse:  # noqa: ARG001
    """
    Select and load a measured pattern.

    Args:
        device_name: The name of the device.
        request: The select measured request payload.

    Returns:
        A message response indicating successful loading.

    Raises:
        HTTPException: If an internal error occurs during loading.

    """
    try:
        await player_service.load_measured_pattern(request.collection_name)
    except Exception as e:
        tb_str = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Server error: {tb_str}") from e

    return MessageResponse(
        message=f"Random record from `{request.collection_name}` loaded successfully",
    )
