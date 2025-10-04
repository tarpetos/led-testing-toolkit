import argparse
import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from pydantic import BaseModel, Field

from led_testing_toolkit.led_modeler.generator import LedGenerator
from led_testing_toolkit.led_modeler.models import AppConfig
from led_testing_toolkit.led_modeler.patterns import Pattern
from led_testing_toolkit.led_modeler.simulator import PhotoresistorSimulator
from led_testing_toolkit.led_modeler.utils import configure_logger
from led_testing_toolkit.led_parser import LedParser
from led_testing_toolkit.mongo_db_connector import MongoDbConnector


class Point(BaseModel):
    x: float = Field(..., description="Timeline point for interpolation (Absolute Time)")
    y: float = Field(..., description="Color value (0-255)")
    z: float = Field(..., description="Original relative LED time (for reference)")


class Record(BaseModel):
    coordinates: list[Point] = []


NormalizedLedData = dict[str, dict[str, list[Record]]]


def convert_db_doc_to_normalized_data(doc: dict[str, Any]) -> NormalizedLedData:
    led_data = {}
    led_identifier = "LED"
    first_abs_time = float("inf")

    for key, value in doc.items():
        if isinstance(key, str) and key.startswith(led_identifier) and isinstance(value, list) and value:
            try:
                min_time_in_led = min(p[2] for p in value if isinstance(p, list) and len(p) == 3)
                first_abs_time = min(first_abs_time, min_time_in_led)
            except (ValueError, TypeError, IndexError):
                continue

    if first_abs_time == float("inf"):
        first_abs_time = 0

    for key, value in doc.items():
        if not isinstance(key, str) or not key.startswith(led_identifier):
            continue
        led_name = key
        led_data[led_name] = {"r": [Record()], "g": [Record()], "b": [Record()]}
        if not isinstance(value, list):
            continue

        for point_data in value:
            try:
                rel_time, rgb, abs_time = point_data
                r_val, g_val, b_val = rgb
                timeline_time = abs_time - first_abs_time
                led_data[led_name]["r"][0].coordinates.append(Point(x=timeline_time, y=r_val, z=rel_time))
                led_data[led_name]["g"][0].coordinates.append(Point(x=timeline_time, y=g_val, z=rel_time))
                led_data[led_name]["b"][0].coordinates.append(Point(x=timeline_time, y=b_val, z=rel_time))
            except (ValueError, TypeError, IndexError) as e:
                logger.warning(f"Skipping malformed data point for {led_name}: {point_data} | Error: {e}")
    return led_data


def adapt_parser_data_for_replay(pattern_data: NormalizedLedData) -> NormalizedLedData:
    adapted_data = {}
    first_abs_time = float("inf")

    for led_name, channels in pattern_data.items():  # noqa: B007
        if "r" in channels and channels["r"] and channels["r"][0].coordinates:
            try:
                min_time_in_led = min(p.z for p in channels["r"][0].coordinates)
                first_abs_time = min(first_abs_time, min_time_in_led)
            except (ValueError, TypeError):
                continue

    if first_abs_time == float("inf"):
        first_abs_time = 0

    for led_name, channels in pattern_data.items():
        adapted_data[led_name] = {}
        for color, records in channels.items():
            new_coords = []
            if records and records[0].coordinates:
                new_coords.append([Point(x=p.z - first_abs_time, y=p.y, z=p.x) for p in records[0].coordinates])
            adapted_data[led_name][color] = [Record(coordinates=new_coords)]

    return adapted_data


class ReplayPattern(Pattern):
    def __init__(self, pattern_data: NormalizedLedData):
        all_led_names = list(pattern_data.keys())
        if not all_led_names:
            raise ValueError("Pattern data does not contain any LED information.")

        numeric_ids = []
        for name in all_led_names:
            match = re.search(r"\d+", name)
            if match:
                numeric_ids.append(int(match.group()))

        max_time = 0.0
        for channels in pattern_data.values():
            for records in channels.values():
                if records and records[0].coordinates:
                    local_max = max((p.x for p in records[0].coordinates), default=0.0)
                    max_time = max(max_time, local_max)

        super().__init__(numeric_ids, 0.0, max_time)
        self._prepare_interpolation_data(pattern_data)

    def _prepare_interpolation_data(self, pattern_data: NormalizedLedData) -> None:
        self._prepped_data = {}
        for led_name, channels in pattern_data.items():
            self._prepped_data[led_name] = {}
            for channel, records in channels.items():
                if records and records[0].coordinates:
                    points = sorted(records[0].coordinates, key=lambda p: p.x)
                    x_vals = [p.x for p in points]
                    y_vals = [p.y for p in points]
                    if not x_vals or x_vals[0] != 0:
                        x_vals.insert(0, 0.0)
                        y_vals.insert(0, 0.0)
                    self._prepped_data[led_name][channel] = (x_vals, y_vals)

    def update(self, elapsed_s: float) -> dict[str, list[int]]:
        states = {}
        if not (self.start_time <= elapsed_s < self.end_time and self.end_time > 0):
            return states

        for led_name in self.led_names:
            if led_name not in self._prepped_data:
                states[led_name] = [0, 0, 0]
                continue

            r, g, b = 0.0, 0.0, 0.0
            if "r" in self._prepped_data[led_name] and self._prepped_data[led_name]["r"]:
                x, y = self._prepped_data[led_name]["r"]
                r = np.interp(elapsed_s, x, y)
            if "g" in self._prepped_data[led_name] and self._prepped_data[led_name]["g"]:
                x, y = self._prepped_data[led_name]["g"]
                g = np.interp(elapsed_s, x, y)
            if "b" in self._prepped_data[led_name] and self._prepped_data[led_name]["b"]:
                x, y = self._prepped_data[led_name]["b"]
                b = np.interp(elapsed_s, x, y)

            final_color = [max(0, min(255, int(c))) for c in [r, g, b]]
            states[led_name] = final_color
        return states


async def get_patterns_from_log(file_path: Path) -> list[NormalizedLedData]:
    if not file_path.exists():
        logger.error(f"Log file not found: {file_path}")
        sys.exit(1)
    parser = LedParser(str(file_path))
    await parser.parse_patterns()
    patterns = parser.patterns.get(file_path, [])
    if not patterns:
        logger.error(f"No patterns found in file {file_path}.")
        sys.exit(1)
    return patterns


async def get_patterns_from_db(collection_name: str, db_type: str, pattern_name: str | None) -> list[NormalizedLedData]:
    patterns_to_process = []
    async with MongoDbConnector() as connector:
        if db_type == "etalon":
            if not pattern_name:
                logger.error("For 'etalon' source, --pattern_name is required.")
                sys.exit(1)
            logger.info(f"Loading etalon '{pattern_name}' from collection '{collection_name}'...")
            await connector.use_collection(collection_name, auto_create=False)
            doc = await connector.read({"_id": pattern_name.upper()})
            if not doc:
                logger.error(f"Etalon '{pattern_name.upper()}' not found in collection '{collection_name}'.")
                sys.exit(1)
            patterns_to_process.append(convert_db_doc_to_normalized_data(doc))
        elif db_type == "measured":
            logger.info(f"Loading records from measured collection '{collection_name}'...")
            await connector.use_collection(collection_name, auto_create=False)
            all_docs = await connector.read({}, find_many=True)
            if not all_docs:
                logger.error(f"Collection '{collection_name}' is empty or does not exist.")
                sys.exit(1)
            logger.info(f"Found {len(all_docs)} records. Processing all of them.")
            patterns_to_process.extend([convert_db_doc_to_normalized_data(doc) for doc in all_docs])
    return patterns_to_process


async def main() -> None:  # noqa: PLR0915
    parser = argparse.ArgumentParser(
        description="Generator for LED indication simulations from existing data.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="source_type", required=True)

    log_parser = subparsers.add_parser("log", help="Use a log file as the source.")
    log_parser.add_argument("filepath", type=Path, help="Path to the log file.")

    db_parser = subparsers.add_parser("db", help="Use a database as the source.")
    db_parser.add_argument(
        "collection",
        help="Name of the collection (e.g., 'FD-CALL' for measured, 'FD-ETALONS' for etalons).",
    )
    db_parser.add_argument(
        "-t",
        "--db_type",
        choices=["measured", "etalon"],
        required=True,
        help="Type of the collection.",
    )
    db_parser.add_argument("-n", "--pattern_name", help="Pattern name (_id) to use (for 'etalon' type only).")

    for p in [log_parser, db_parser]:
        p.add_argument(
            "-o",
            "--output_dir",
            default="generated_logs",
            type=Path,
            help="Directory to save generated logs.",
        )
        p.add_argument(
            "-c",
            "--count",
            type=int,
            default=1,
            help="Number of fictitious records to generate per source pattern.",
        )
        p.add_argument("--noise", type=float, default=3.0, help="Sensor noise level.")
        p.add_argument("--lag", type=float, default=0.4, help="Sensor reaction lag (0.0-1.0).")
        p.add_argument(
            "--reporting-chance",
            type=float,
            default=0.85,
            help="Probability of reporting a change (0.0-1.0).",
        )
        p.add_argument("--interval", default="15-40", help="Random logging interval in ms.")
        p.add_argument("--mode", choices=["simulate", "instant"], default="instant", help="Execution mode.")

    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    patterns_to_process = []
    base_name = ""
    if args.source_type == "log":
        base_name = args.filepath.stem
        patterns_to_process = await get_patterns_from_log(args.filepath)
        logger.info(f"Found {len(patterns_to_process)} patterns to process in log file.")
    elif args.source_type == "db":
        base_name = args.collection if args.db_type == "measured" else f"{args.collection}_{args.pattern_name}"
        patterns_to_process = await get_patterns_from_db(args.collection, args.db_type, args.pattern_name)

    if not patterns_to_process:
        logger.error("No source patterns found to process. Exiting.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{args.source_type}_{base_name}_{timestamp}.log"
    output_path = args.output_dir / output_filename

    logger.info(f"All simulations will be written to a single file: {output_path}")
    sim_logger = configure_logger(str(output_path), "LedGenerator")

    total_generations = 0
    for i, pattern_data in enumerate(patterns_to_process):
        pattern_num = i + 1
        logger.info(f"----- Processing Source Pattern #{pattern_num} -----")

        adapted_pattern_data = adapt_parser_data_for_replay(pattern_data) if args.source_type == "log" else pattern_data

        if not adapted_pattern_data:
            logger.warning(f"Source pattern #{pattern_num} is empty after processing. Skipping.")
            continue

        replay_pattern = ReplayPattern(adapted_pattern_data)
        duration = replay_pattern.end_time
        logger.info(f"Replay duration for source pattern #{pattern_num}: {duration:.2f} seconds.")

        all_led_ids = list(adapted_pattern_data.keys())
        if not all_led_ids:
            logger.warning(f"No LEDs found in source pattern #{pattern_num}. Skipping.")
            continue

        for j in range(1, args.count + 1):
            total_generations += 1
            sim_logger.info(f"--- Generating Simulation {j}/{args.count} for Source Pattern #{pattern_num} ---")

            config_dict: dict[str, Any] = {
                "duration": duration,
                "output_file": str(output_path),
                "num_leds": len(all_led_ids),
                "mode": args.mode,
                **vars(args),
                "color": "0,0,0",
                "sequence": "all_at_once",
            }
            config = AppConfig(**config_dict)

            simulator = PhotoresistorSimulator(
                led_ids=all_led_ids,
                noise_level=config.noise,
                lag=config.lag,
                reporting_chance=config.reporting_chance,
            )
            generator = LedGenerator(config, [replay_pattern], simulator, sim_logger)
            generator.run()

    logger.success(f"Completed. Appended {total_generations} total simulations to '{output_path}'.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
