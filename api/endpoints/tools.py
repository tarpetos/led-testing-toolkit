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
    """
    Split logs based on provided patterns.

    Args:
        files: A list of uploaded log files.
        max_patterns: The maximum number of patterns to split.
        start_pattern: The regex pattern indicating the start.
        end_pattern: The regex pattern indicating the end.

    Returns:
        A streaming response or a dictionary with an error message.

    """
    return await tools_service.split_logs(  # pragma: no cover
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
    """
    Compare a measured pattern with an etalon pattern.

    Args:
        measured_collection: The collection of the measured pattern.
        measured_record: The measured record.
        etalon_device: The etalon device.
        etalon_pattern: The etalon pattern name.

    Returns:
        A dictionary containing comparison results.

    """
    return await tools_service.compare_patterns(  # pragma: no cover
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
    """
    Compare a log pattern with an etalon pattern.

    Args:
        pattern_index: The index of the log pattern.
        etalon_device: The etalon device name.
        etalon_pattern: The etalon pattern name.

    Returns:
        A dictionary containing comparison results.

    """
    return await tools_service.compare_log_pattern(  # pragma: no cover
        pattern_index=pattern_index,
        etalon_device=etalon_device,
        etalon_pattern=etalon_pattern,
    )


@router.post("/generate-etalons")
async def generate_etalons(
    device_name: Annotated[str | None, Form()] = None,
    pattern_name: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    """
    Generate etalon patterns.

    Args:
        device_name: The name of the device (optional).
        pattern_name: The name of the pattern (optional).

    Returns:
        A dictionary containing generation results.

    """
    return await tools_service.generate_etalons(  # pragma: no cover
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
    """
    Generate logs from parameters.

    Args:
        output_file: The name of the output file.
        save_to_db: Whether to save to database.
        mode: The generation mode.
        duration: The duration of the generation.
        interval: The interval string.
        noise: The noise level.
        lag: The lag value.
        reporting_chance: The chance of reporting.
        num_leds: The number of LEDs.
        color: The color to use.
        fade: The fade amount.
        sequence: The sequence of colors.
        palette: The palette to use.

    Returns:
        A generated file response, streaming response, or error dictionary.

    """
    return await tools_service.generate_from_parameters(  # pragma: no cover
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
    """
    Generate logs from a source file or collection.

    Args:
        source_type: The type of source.
        file: The uploaded source file.
        collection: The collection name.
        pattern_name: The pattern name.
        process_all: Whether to process all items.
        save_to_db: Whether to save to database.
        output_dir: The output directory.
        count: The number of generations.
        noise: The noise level.
        lag: The lag value.
        reporting_chance: The chance of reporting.
        interval: The interval string.
        mode: The generation mode.

    Returns:
        A streaming response or error dictionary.

    """
    return await tools_service.generate_from_source(  # pragma: no cover
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
