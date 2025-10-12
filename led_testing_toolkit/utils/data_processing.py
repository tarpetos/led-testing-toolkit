from __future__ import annotations

import os
import random
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl
import numpy as np
from loguru import logger

from led_testing_toolkit.math.aggregator import Aggregator
from led_testing_toolkit.math.comparator import Comparator
from led_testing_toolkit.math.interpolator import Interpolator
from led_testing_toolkit.math.models import Dataset, Point, Record
from led_testing_toolkit.mongo_db_connector import MongoDbConnector
from led_testing_toolkit.utils.collection_name import (
    ETALONS_COLLECTION_SUFFIX,
    parse_collection_name,
    validate_etalons_collection_name,
    validate_measured_collection_name,
)

if TYPE_CHECKING:
    from led_testing_toolkit.led_types import (
        ComparisonResults,
        EtalonDbFormat,
        LedData,
        NormalizedLedData,
    )

mpl.use("Agg")


def make_sequence(obj: object) -> Sequence:
    string_type: bool = isinstance(obj, (str, bytes))
    return obj if isinstance(obj, Sequence) and not string_type else (obj,)


async def extract_led_rgb_data(
    records: LedData,
) -> NormalizedLedData:
    records = make_sequence(records)
    led_data = {}

    for record in records:
        for led_name, led_records in record.items():
            if led_name not in led_data:
                led_data[led_name] = {"r": [], "g": [], "b": []}

            if not isinstance(led_records, list):
                logger.warning(f"Skipping invalid LED data for {led_name}!")
                continue

            red_points, green_points, blue_points = [], [], []

            for led_record in led_records:
                try:
                    x_value = led_record[0]  # relative LED time
                    rgb_values = led_record[1]  # [r, g, b]
                    abs_time = led_record[2]  # absolute LED time
                    if isinstance(rgb_values, list) and len(rgb_values) >= 3:
                        red_points.append(Point(x=x_value, y=rgb_values[0], z=abs_time))
                        green_points.append(Point(x=x_value, y=rgb_values[1], z=abs_time))
                        blue_points.append(Point(x=x_value, y=rgb_values[2], z=abs_time))
                    else:
                        logger.warning(f"Invalid RGB data in {led_name}: {rgb_values}")
                except (IndexError, TypeError) as e:
                    logger.error(f"Error processing record for {led_name}: {e!s}")

            led_data[led_name]["r"].append(Record(coordinates=red_points))
            led_data[led_name]["g"].append(Record(coordinates=green_points))
            led_data[led_name]["b"].append(Record(coordinates=blue_points))

    return led_data


def convert_etalon_to_db_format(
    etalons_data: NormalizedLedData,
    abs_avg_times: dict[str, list[float]],
) -> EtalonDbFormat:
    etalon_dict = {}
    for led, rgb_data in etalons_data.items():
        if etalon_dict.get(led) is None:
            etalon_dict[led] = []

        for r_p, g_p, b_p, abs_time in zip(
            rgb_data["r"].coordinates,
            rgb_data["g"].coordinates,
            rgb_data["b"].coordinates,
            abs_avg_times[led],
            strict=False,
        ):
            etalon_dict[led].append(
                [
                    sum([r_p.x, g_p.x, b_p.x]) / 3,
                    [r_p.y, g_p.y, b_p.y],
                    abs_time,
                ],
            )
    return etalon_dict


def compute_average_abs_times(records: list[Record]) -> list[float]:
    abs_time_records = [[point.z for point in record.coordinates] for record in records]
    max_length = max(len(abs_times) for abs_times in abs_time_records)
    padded_records = [abs_times + [np.nan] * (max_length - len(abs_times)) for abs_times in abs_time_records]
    records_array = np.array(padded_records)
    return np.nanmean(records_array, axis=0).tolist()


async def read_measured(
    name: str,
    *,
    db_name: str | None = os.getenv("MONGO_DB_NAME"),
    get_random: bool = False,
) -> NormalizedLedData:
    measure_collection_name = validate_measured_collection_name(name)

    async with MongoDbConnector(db_name) as connector:
        await connector.use_collection(measure_collection_name, auto_create=False)
        raw_dataset = await connector.read({}, projection={"_id": 0}, find_many=True)

    if get_random:
        raw_dataset = random.choice(raw_dataset)

    return await extract_led_rgb_data(raw_dataset)


async def read_etalon(
    pattern_name: str,
    etalon_collection_name: str,
    *,
    db_name: str | None = os.getenv("MONGO_DB_NAME"),
) -> NormalizedLedData:
    etalon_collection_name = validate_etalons_collection_name(etalon_collection_name)
    async with MongoDbConnector(db_name) as connector:
        await connector.use_collection(etalon_collection_name)
        etalon_data = await connector.read({"_id": pattern_name.upper()}, projection={"_id": 0})

    if etalon_data is None:
        raise ValueError(f"No etalon data found for pattern name `{pattern_name}`!")

    return await extract_led_rgb_data(etalon_data)


async def generate_etalon(
    measure_collection_name: str,
    *,
    db_name: str | None = os.getenv("MONGO_DB_NAME"),
    plot_dir_path: Path | str = Path(),
) -> str:
    plot_dir_path = Path(plot_dir_path)
    if not plot_dir_path.is_dir():
        raise ValueError(f"`{plot_dir_path}` is not a valid directory path!")

    device_name, etalon_record_key = parse_collection_name(measure_collection_name)
    etalon_collection_name = validate_etalons_collection_name(f"{device_name}-{ETALONS_COLLECTION_SUFFIX}")

    normalized_dataset = await read_measured(measure_collection_name, db_name=db_name)
    async with MongoDbConnector(db_name) as connector:
        await connector.use_collection(etalon_collection_name, auto_create=True)

        etalons_data, abs_avg_times = {}, {}
        base_plot_path = Path(plot_dir_path, etalon_record_key.lower(), "aggregated", str(uuid.uuid4()))
        interpolator = Interpolator(lower_bound=0, upper_bound=255)
        for led, rgb_dataset in normalized_dataset.items():
            etalons_data[led] = {}
            abs_avg_times[led] = compute_average_abs_times(rgb_dataset["r"])
            tasks = [
                (color, Aggregator(dataset=Dataset(records=data), interpolator=interpolator))
                for color, data in rgb_dataset.items()
            ]
            for color, aggregator in tasks:
                await aggregator.start()
                aggregator.build_plots(
                    title=f"{led.upper()} ({color.upper()} channel) - aggregated data",
                    save_path=base_plot_path / led.lower() / color.lower(),
                )
                etalons_data[led][color] = aggregator.etalon

        etalon_dict = convert_etalon_to_db_format(etalons_data, abs_avg_times)
        await connector.upsert(query={"_id": etalon_record_key}, update_data=etalon_dict)
    return etalon_collection_name


async def make_comparison(
    etalon: Record,
    measured: Record,
    *,
    led: str,
    color: str,
    plot_path: Path | str,
) -> float:
    comparator = Comparator(etalon, measured, Interpolator(lower_bound=0, upper_bound=255))
    accuracy = await comparator.start()
    comparator.build_plots(
        title=f"{led.upper()} ({color.upper()} channel) - comparison (similarity: {accuracy:.2f}%)",
        save_path=plot_path,
        xlabel="Time (s)",
        ylabel="Color (0-255)",
    )
    return accuracy


async def make_comparisons(
    normalized_etalon_data: NormalizedLedData,
    normalized_measured_data: NormalizedLedData,
    plot_dir_path: Path | str = Path(),
) -> ComparisonResults:
    comparison_results = {}
    base_plot_path = Path(plot_dir_path, "comparison", str(uuid.uuid4()))
    for led, rgb_data in normalized_etalon_data.items():
        comparison_results[led] = {}
        for color, etalon in rgb_data.items():
            plot_path = base_plot_path / led.lower() / color.lower()
            accuracy = await make_comparison(
                etalon[0],
                normalized_measured_data[led][color][0],
                led=led,
                color=color,
                plot_path=plot_path,
            )
            comparison_results[led][color] = {"plot_path": plot_path, "accuracy": accuracy}

    return comparison_results


def convert_normalized_to_raw_format(normalized_data: NormalizedLedData) -> dict[str, list]:
    """
    Converts data from the LedParser's normalized format (separated by RGB channels)
    back into the raw, MongoDB-like format.

    Args:
        normalized_data: The output from LedParser, e.g., {'LED1': {'r': [Record], 'g': [Record], 'b': [Record]}}.

    Returns:
        Data in raw format, e.g., {'LED1': [[rel_time, [r,g,b], abs_time], ...]}.

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
                r_point.x,
                [r_point.y, g_point.y, b_point.y],
                r_point.z,
            ]
            raw_data[led_id].append(raw_entry)

    return raw_data


async def save_patterns_to_db(
    parsed_patterns: list[dict],
    collection_name: str,
    *,
    db_name: str | None = None,
) -> None:
    """
    Converts parsed LED patterns to a raw format and saves them to a MongoDB collection.

    Args:
        parsed_patterns: A list of parsed patterns from the Parser.
        collection_name: The name of the MongoDB collection to save the data to.
        db_name: The name of the database. If None, uses the default from environment variables.

    """
    if not parsed_patterns:
        logger.warning("No parsed patterns to save to the database.")
        return

    logger.info(f"Preparing to save {len(parsed_patterns)} patterns to collection '{collection_name}'.")

    raw_patterns = [convert_normalized_to_raw_format(p) for p in parsed_patterns]

    try:
        async with MongoDbConnector(db_name) as connector:
            await connector.use_collection(collection_name, auto_create=True)
            result = await connector.insert(raw_patterns, insert_many=True)
            if result:
                logger.success(
                    f"Successfully inserted {len(result.inserted_ids)} documents into '{collection_name}'.",
                )
    except Exception:
        logger.exception(f"Failed to save patterns to collection '{collection_name}'.")
