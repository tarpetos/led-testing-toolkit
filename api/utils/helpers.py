from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from led_testing_toolkit.led_types import NormalizedLedData


def convert_normalized_to_raw_format(normalized_data: NormalizedLedData) -> dict[str, list]:
    """
    Converts data from the LedParser's normalized format (separated by RGB channels)
    back into the raw, MongoDB-like format.

    :param normalized_data: The output from LedParser, e.g., {'LED1': {'r': [Record], 'g': [Record], 'b': [Record]}}.
    :return: Data in raw format, e.g., {'LED1': [[rel_time, [r,g,b], abs_time], ...]}.
    """
    raw_data = {}
    if not normalized_data:
        return raw_data

    for led_id, color_channels in normalized_data.items():
        raw_data[led_id] = []

        if not ("r" in color_channels and "g" in color_channels and "b" in color_channels):
            continue

        r_coords = color_channels["r"][0].coordinates
        g_coords = color_channels["g"][0].coordinates
        b_coords = color_channels["b"][0].coordinates

        for r_point, g_point, b_point in zip(r_coords, g_coords, b_coords, strict=False):
            raw_entry = [
                r_point.x,  # rel_time
                [r_point.y, g_point.y, b_point.y],  # [r, g, b]
                r_point.z,  # abs_time
            ]
            raw_data[led_id].append(raw_entry)

    return raw_data


async def cancel_task(task: asyncio.Task, /, teardown: bool = True) -> None:
    task.cancel()

    if not teardown:
        return

    with suppress(asyncio.CancelledError):
        await task
