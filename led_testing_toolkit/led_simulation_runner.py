import random
import re
import sys
from argparse import Namespace
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import loguru
import numpy as np
from loguru._logger import Logger

from led_testing_toolkit.led_modeler.generator import LedGenerator
from led_testing_toolkit.led_modeler.models import AppConfig
from led_testing_toolkit.led_modeler.patterns import Pattern
from led_testing_toolkit.led_modeler.simulator import PhotoresistorSimulator
from led_testing_toolkit.led_modeler.utils import configure_logger
from led_testing_toolkit.led_parser import LedParser
from led_testing_toolkit.led_types import NormalizedLedData
from led_testing_toolkit.math.models import Point, Record
from led_testing_toolkit.mongo_db_connector import MongoDbConnector
from led_testing_toolkit.utils.collection_name import ETALONS_COLLECTION_SUFFIX


class ReplayPattern(Pattern):
    def __init__(self, pattern_data: NormalizedLedData) -> None:
        all_led_names = list(pattern_data.keys())
        if not all_led_names:
            raise ValueError("Pattern data does not contain any LED information!")

        numeric_ids = [int(match.group()) for name in all_led_names if (match := re.search(r"\d+", name))]

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


class SimulationRunner:
    def __init__(self, args: Namespace, logger: Logger) -> None:
        self.args = args
        self.logger = logger

    def _convert_db_doc_to_normalized_data(self, doc: dict[str, Any] | Mapping[str, Any]) -> NormalizedLedData:
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
                    self.logger.warning(f"Skipping malformed data point for {led_name}: {point_data} | Error: {e!s}")
        return led_data

    def _adapt_parser_data_for_replay(self, pattern_data: NormalizedLedData) -> NormalizedLedData:
        adapted_data = {}
        first_abs_time = float("inf")

        for channels in pattern_data.values():
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
                    new_coords.extend([Point(x=p.z - first_abs_time, y=p.y, z=p.x) for p in records[0].coordinates])
                adapted_data[led_name][color] = [Record(coordinates=new_coords)]

        return adapted_data

    async def _get_patterns_from_source(self) -> list[NormalizedLedData]:
        if self.args.source_type == "log":
            return await self._get_patterns_from_log()
        if self.args.source_type == "db":
            return await self._get_patterns_from_db()
        return []

    async def _get_patterns_from_log(self) -> list[NormalizedLedData]:
        if not self.args.filepath.exists():
            self.logger.error(f"Log file not found: {self.args.filepath}")
            sys.exit(1)
        parser = LedParser(str(self.args.filepath))
        await parser.parse_patterns()
        patterns = parser.patterns.get(self.args.filepath, [])
        if not patterns:
            self.logger.error(f"No patterns found in file {self.args.filepath}.")
            sys.exit(1)
        return patterns

    async def _get_patterns_from_db(self) -> list[NormalizedLedData]:
        is_etalon_source = self.args.collection.upper().endswith(ETALONS_COLLECTION_SUFFIX)
        db_type = "etalon" if is_etalon_source else "measured"

        if is_etalon_source and not self.args.pattern_name:
            self.logger.error(
                f"Argument '-n/--pattern_name' is required for an etalon collection ('{self.args.collection}').",
            )
            sys.exit(1)

        patterns_to_process = []
        async with MongoDbConnector() as connector:
            if db_type == "etalon":
                self.logger.debug(
                    f"Loading etalon '{self.args.pattern_name}' from collection '{self.args.collection}'...",
                )
                await connector.use_collection(self.args.collection, auto_create=False)
                doc = await connector.read({"_id": self.args.pattern_name.upper()})
                if not doc:
                    self.logger.error(
                        f"Etalon '{self.args.pattern_name.upper()}' not found in collection '{self.args.collection}'.",
                    )
                    sys.exit(1)
                patterns_to_process.append(self._convert_db_doc_to_normalized_data(doc))
            elif db_type == "measured":
                self.logger.debug(f"Loading records from measured collection '{self.args.collection}'...")
                await connector.use_collection(self.args.collection, auto_create=False)
                all_docs = await connector.read({}, find_many=True)
                if not all_docs:
                    self.logger.error(f"Collection '{self.args.collection}' is empty or does not exist.")
                    sys.exit(1)

                if self.args.process_all:
                    self.logger.debug(
                        f"Found {len(all_docs)} records. Processing all of them as per --process-all flag.",
                    )
                    docs_to_process = all_docs
                else:
                    self.logger.debug(f"Found {len(all_docs)} records. Processing ONE random record.")
                    docs_to_process = [random.choice(all_docs)]

                patterns_to_process.extend([self._convert_db_doc_to_normalized_data(doc) for doc in docs_to_process])
        return patterns_to_process

    async def run(self) -> None:
        base_name = ""
        if self.args.source_type == "log":
            base_name = self.args.filepath.stem
        elif self.args.source_type == "db":
            is_etalon = self.args.collection.upper().endswith(ETALONS_COLLECTION_SUFFIX)
            base_name = f"{self.args.collection}_{self.args.pattern_name}" if is_etalon else self.args.collection

        patterns_to_process = await self._get_patterns_from_source()

        if not patterns_to_process:
            self.logger.error("No source patterns found to process. Exiting.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{self.args.source_type}_{base_name}_{timestamp}.log"
        output_path = self.args.output_dir / output_filename

        sim_logger = configure_logger(str(output_path), "LedGenerator")
        if not self.args.save_to_db:
            self.logger.debug(f"Simulations will be written to file: {output_path}")

        total_generations = 0
        for i, pattern_data in enumerate(patterns_to_process):
            pattern_num = i + 1
            self.logger.debug(f"----- Processing Source Pattern #{pattern_num} -----")

            adapted_pattern_data = (
                self._adapt_parser_data_for_replay(pattern_data) if self.args.source_type == "log" else pattern_data
            )

            if not adapted_pattern_data:
                self.logger.warning(f"Source pattern #{pattern_num} is empty after processing. Skipping.")
                continue

            replay_pattern = ReplayPattern(adapted_pattern_data)
            duration = replay_pattern.end_time
            self.logger.debug(f"Replay duration for source pattern #{pattern_num}: {duration:.2f} seconds.")

            all_led_ids = list(adapted_pattern_data.keys())
            if not all_led_ids:
                self.logger.warning(f"No LEDs found in source pattern #{pattern_num}. Skipping.")
                continue

            for j in range(1, self.args.count + 1):
                total_generations += 1
                self.logger.debug(
                    f"--- Generating Simulation {j}/{self.args.count} for Source Pattern #{pattern_num} ---",
                )

                config_dict: dict[str, Any] = {
                    "duration": duration,
                    "output_file": str(output_path),
                    "num_leds": len(all_led_ids),
                    "mode": self.args.mode,
                    **vars(self.args),
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
                generator = LedGenerator(
                    config=config,
                    patterns=[replay_pattern],
                    simulator=simulator,
                    logger=loguru.logger if self.args.save_to_db else sim_logger,
                    save_to_db_collection=self.args.save_to_db,
                )
                await generator.run()

        self.logger.success(f"Completed. Generated {total_generations} total simulations.")
