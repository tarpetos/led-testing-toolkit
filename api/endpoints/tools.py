from typing import Annotated, Any

from fastapi import APIRouter, File, Form, UploadFile
from starlette.responses import FileResponse, StreamingResponse

from api.services.tools_service import tools_service

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.post("/split-logs", response_model=None)
async def split_logs(
    files: Annotated[list[UploadFile], File()] = ...,
    max_patterns: Annotated[int, Form()] = 1,
    start_pattern: Annotated[str, Form()] = r"LED(\d+)=\w+",
    end_pattern: Annotated[
        str, Form()
    ] = r"Indication absence time exceeded limit: (\d+.\d+) seconds|--- END INDICATION PATTERN \w+ ---",
) -> StreamingResponse | dict[str, str]:
    return await tools_service.split_logs(
        files=files,
        max_patterns=max_patterns,
        start_pattern=start_pattern,
        end_pattern=end_pattern,
    )


@router.post("/compare-patterns")
async def compare_patterns(
    measured_collection: Annotated[str, Form()],
    measured_record: Annotated[str, Form()],
    etalon_device: Annotated[str, Form()],
    etalon_pattern: Annotated[str, Form()],
) -> dict[str, dict] | dict[str, str]:
    return await tools_service.compare_patterns(
        measured_collection=measured_collection,
        measured_record=measured_record,
        etalon_device=etalon_device,
        etalon_pattern=etalon_pattern,
    )


@router.post("/compare-log-pattern")
async def compare_log_pattern(
    pattern_index: Annotated[int, Form()],
    etalon_device: Annotated[str, Form()],
    etalon_pattern: Annotated[str, Form()],
) -> dict[str, dict] | dict[str, str]:
    return await tools_service.compare_log_pattern(
        pattern_index=pattern_index,
        etalon_device=etalon_device,
        etalon_pattern=etalon_pattern,
    )


@router.post("/generate-etalons")
async def generate_etalons(
    device_name: Annotated[str | None, Form()] = None,
    pattern_name: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    return await tools_service.generate_etalons(
        device_name=device_name,
        pattern_name=pattern_name,
    )


@router.post("/generate-from-parameters", response_model=None)
async def generate_from_parameters(  # noqa: PLR0913
    output_file: Annotated[str, Form()] = "led_indication.log",
    save_to_db: Annotated[str | None, Form()] = None,
    mode: Annotated[str, Form()] = "simulate",
    duration: Annotated[float, Form()] = ...,
    interval: Annotated[str, Form()] = "15-40",
    noise: Annotated[float, Form()] = 3.0,
    lag: Annotated[float, Form()] = 0.4,
    reporting_chance: Annotated[float, Form()] = 0.85,
    num_leds: Annotated[int | None, Form()] = None,
    color: Annotated[str | None, Form()] = None,
    fade: Annotated[float, Form()] = 0.5,
    sequence: Annotated[str | None, Form()] = None,
    palette: Annotated[str | None, Form()] = None,
) -> dict[str, str] | FileResponse | StreamingResponse:
    return await tools_service.generate_from_parameters(
        output_file=output_file,
        save_to_db=save_to_db,
        mode=mode,
        duration=duration,
        interval=interval,
        noise=noise,
        lag=lag,
        reporting_chance=reporting_chance,
        num_leds=num_leds,
        color=color,
        fade=fade,
        sequence=sequence,
        palette=palette,
    )


@router.post("/generate-from-source", response_model=None)
async def generate_from_source(  # noqa: PLR0913
    source_type: Annotated[str, Form()] = ...,
    file: Annotated[UploadFile, File()] = None,
    collection: Annotated[str | None, Form()] = None,
    pattern_name: Annotated[str | None, Form()] = None,
    process_all: Annotated[bool, Form()] = False,
    save_to_db: Annotated[str | None, Form()] = None,
    output_dir: Annotated[str, Form()] = "generated_logs",
    count: Annotated[int, Form()] = 1,
    noise: Annotated[float, Form()] = 3.0,
    lag: Annotated[float, Form()] = 0.4,
    reporting_chance: Annotated[float, Form()] = 0.85,
    interval: Annotated[str, Form()] = "15-40",
    mode: Annotated[str, Form()] = "instant",
) -> dict[str, str] | StreamingResponse:
    return await tools_service.generate_from_source(
        source_type=source_type,
        file=file,
        collection=collection,
        pattern_name=pattern_name,
        process_all=process_all,
        save_to_db=save_to_db,
        output_dir=output_dir,
        count=count,
        noise=noise,
        lag=lag,
        reporting_chance=reporting_chance,
        interval=interval,
        mode=mode,
    )
