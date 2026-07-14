from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import loguru

if TYPE_CHECKING:
    from loguru._logger import Logger


def configure_logger(file_path: str, source_name: str) -> Logger:
    """
    Configures and returns a loguru logger instance.

    Args:
        file_path: The path to the output log file.
        source_name: A unique name to bind to logs from this source, used for filtering.

    Returns:
        A configured loguru logger instance.

    """
    logger = loguru.logger
    logger.remove()

    logger = logger.bind(source=source_name)

    logger.add(
        file_path,
        format="{time:%Y-%m-%dT%H:%M:%S.%f%z} {level} {message}",
        level="TRACE",
        filter=lambda record: record["extra"].get("source") == source_name,
    )

    logger.add(
        sink=sys.stderr,
        format="<green>{time:%Y-%m-%dT%H:%M:%S.%f}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="TRACE",
        filter=lambda record: record["extra"].get("source") == source_name,
    )
    return logger


def lerp(start: int, end: int, t: float) -> int:
    """
    Performs linear interpolation between two integer values.

    Args:
        start: The starting value (at t=0).
        end: The ending value (at t=1).
        t: The interpolation factor, typically between 0.0 and 1.0.

    Returns:
        The interpolated integer value.

    """
    return int(start + (end - start) * t)


def add_colors(color1: list[int], color2: list[int]) -> list[int]:
    """
    Adds two RGB colors together, clamping each channel at 255.

    Args:
        color1: The first RGB color as a list of integers.
        color2: The second RGB color as a list of integers.

    Returns:
        The resulting summed and clamped RGB color.

    """
    return [min(255, c1 + c2) for c1, c2 in zip(color1, color2, strict=False)]
