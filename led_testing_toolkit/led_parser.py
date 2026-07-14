from __future__ import annotations

import re
import tempfile
from asyncio import TaskGroup
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
import loguru

from led_testing_toolkit.math.models import Point, Record

if TYPE_CHECKING:
    from led_types import (
        LedRgbData,
        LedSequence,
        ParsedPatterns,
        RawPattern,
        Timestamps,
    )
    from loguru._logger import Logger


class LedParser:
    """Class for processing raw LED indication data and converting it to mathematical models."""

    def __init__(
        self,
        *log_file_paths,
        led_search_pattern: re.Pattern[str] = re.compile(r"LED(\d+)=\[(\d+),(\d+),(\d+)]"),
        led_identifier: str = "LED",
        logger: Logger = loguru.logger,
    ) -> None:
        """
        Initializes the LedParser instance.

        Args:
            *log_file_paths: Variable length argument list of log file paths.
            led_search_pattern: Regular expression pattern to identify LED data.
            led_identifier: String identifier used to recognize LED related messages.
            logger: Logger instance to be used for logging.

        """
        self._log_file_paths: tuple[Path, ...] = tuple(Path(path) for path in log_file_paths)
        self._log_search_pattern: re.Pattern[str] = led_search_pattern
        self._led_identifier: str = led_identifier
        self._logger: Logger = logger

        self._parsed_patterns: ParsedPatterns = {}

    @property
    def patterns(self) -> ParsedPatterns:
        """
        Gets the parsed patterns.

        Returns:
            A dictionary containing parsed patterns.

        """
        return self._parsed_patterns

    async def _create_temp_log_file(self, source_file: Path) -> tempfile.NamedTemporaryFile:
        """
        Creates a temporary copy of the log file to read from.

        Args:
            source_file: Path to the original log file.

        Returns:
            NamedTemporaryFile object.

        """
        if not source_file.exists():
            raise FileNotFoundError(f"Source log file `{source_file}` not found!")

        temp_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=True)  # noqa: SIM115

        try:
            async with aiofiles.open(source_file) as src, aiofiles.open(temp_file.name, mode="w+") as dst:
                content = await src.read()
                await dst.write(content)
                await dst.flush()
            temp_file.seek(0)
        except Exception as e:
            temp_file.close()
            self._logger.error(f"Error creating temporary log file: {e!r}")
            raise
        else:
            return temp_file

    async def _read_temp_log_file(
        self,
        temp_file: tempfile.NamedTemporaryFile,
        *,
        log_line_length: int = 3,
    ) -> RawPattern | None:
        """
        Reads indication logs from a temporary log file.

        Splits them into 3 parts:
            1. Timestamp
            2. Logging level
            3. Message itself
        Args:
            temp_file: A temporary log file object opened for reading.
            log_line_length: The expected length of each message list after splitting.

        Returns:
            Preprocessed patterns.

        """
        led_patterns = []
        current_pattern = {}

        async with aiofiles.open(temp_file.name) as f:
            async for log_line in f:
                line = log_line.strip()
                if not line:
                    continue

                parts = line.split(" ", 2)
                if len(parts) != log_line_length:
                    self._logger.warning(f"Malformed log line skipped: `{line}`")
                    continue

                timestamp_str = parts[0]
                message = parts[2]

                if self._led_identifier in message:
                    current_pattern.update({timestamp_str: message})
                elif current_pattern:
                    led_patterns.append(current_pattern)
                    current_pattern = {}

        if current_pattern:
            led_patterns.append(current_pattern)

        return led_patterns

    async def _retrieve_patterns(self, log_file: Path) -> RawPattern:
        """
        Initial parsing of indication patterns to split them and convert them from strings to dictionaries.

        Args:
            log_file: File to read patterns from.

        Returns:
            Preprocessed patterns.

        """
        try:
            temp_file = await self._create_temp_log_file(log_file)
            try:
                return await self._read_temp_log_file(temp_file)
            finally:
                temp_file.close()
        except FileNotFoundError:
            self._logger.warning(f"Log file `{log_file}` not found!")
            return []
        except Exception as e:
            self._logger.error(f"Error parsing log file: {e!r}")
            return []

    def _extract_led_data(self, log_line: str) -> LedRgbData | None:
        """
        Extracts all LEDs from log_line and return as dict with RGB values.

        Args:
            log_line: Raw log line.

        Returns:
            {"LED1": {"r": 255, "g": 0, "b": 128}, "LED2": {...}, ...}
            If there is a duplicate LED in line, only the first one is used.

        """
        led_matches = self._log_search_pattern.findall(log_line)

        if not led_matches:
            return None

        led_dict = {}

        for led_num, r, g, b in led_matches:
            led_key = f"{self._led_identifier}{led_num}"

            if led_key not in led_dict:
                led_dict[led_key] = {
                    "r": int(r),
                    "g": int(g),
                    "b": int(b),
                }

        return led_dict

    def _convert_to_mathematical_model(
        self,
        led_data: LedSequence,
        timestamps: Timestamps,
    ) -> dict[str, dict[str, list[Record]]]:
        """
        Converts LED data to mathematical model format.

        Args:
            led_data: Dictionary containing LED sequences with RGB values.
            timestamps: Dictionary containing timestamps for each LED.

        Returns:
            Mathematical model with Records containing Points for each color channel.

        """
        if not led_data or not timestamps:
            return {}

        all_timestamps = []
        for led_timestamps in timestamps.values():
            all_timestamps.extend(led_timestamps)

        if not all_timestamps:
            return {}

        global_start_time = min(all_timestamps)

        result = {}

        for led_key, data_points in led_data.items():
            led_timestamps = timestamps[led_key]
            led_start_time = min(led_timestamps)

            result[led_key] = {
                "r": [Record(coordinates=[])],
                "g": [Record(coordinates=[])],
                "b": [Record(coordinates=[])],
            }

            for i, data_point in enumerate(data_points):
                current_timestamp = led_timestamps[i]

                rel_time = self.get_date_diff(led_start_time, current_timestamp)
                abs_time = self.get_date_diff(global_start_time, current_timestamp)

                for color_channel in ["r", "g", "b"]:
                    color_value = data_point[color_channel]
                    point = Point(x=rel_time, y=color_value, z=abs_time)
                    result[led_key][color_channel][0].coordinates.append(point)

        return result

    async def parse_log_file(self, log_file_path: Path, *, ignore_before_date: datetime | None = None) -> None:
        """
        Parses a single log file to extract LED patterns and convert to mathematical models.

        Processes raw log data to identify LED color events, calculates relative and absolute
        timing for each LED sequence, and stores the parsed patterns as mathematical models.

        Args:
            log_file_path: Path to the log file to be parsed.
            ignore_before_date: Optional datetime filter - entries before this date will be ignored

        Returns:
            None

        """
        log_file_path = Path(log_file_path)
        parsed_patterns = []
        raw_patterns = await self._retrieve_patterns(log_file_path)
        if not raw_patterns:
            return

        self._logger.debug(f"Retrieved {len(raw_patterns)} pattern(s) from log file `{log_file_path}`.")

        for count, raw_pattern in enumerate(raw_patterns, 1):
            led_data = {}
            timestamps = {}

            for timestamp_str, log_line in raw_pattern.items():
                date = datetime.fromisoformat(timestamp_str)
                if ignore_before_date and date < ignore_before_date:
                    continue

                parsed_line = self._extract_led_data(log_line)

                if parsed_line is None:
                    continue

                for led_key, rgb_values in parsed_line.items():
                    if led_key not in led_data:
                        led_data[led_key] = []
                        timestamps[led_key] = []

                    led_data[led_key].append(rgb_values)
                    timestamps[led_key].append(date)

            mathematical_pattern = self._convert_to_mathematical_model(led_data, timestamps)

            if not mathematical_pattern:
                self._logger.warning(f"Parsing of pattern #{count} is skipped!")
                continue

            parsed_patterns.append(mathematical_pattern)

        if log_file_path not in self._parsed_patterns:
            self._parsed_patterns[log_file_path] = []
        self._parsed_patterns[log_file_path] = parsed_patterns

    async def parse_patterns(self, *, ignore_before_date: datetime | None = None) -> None:
        """
        Parses all configured log files concurrently to extract LED patterns.

        Args:
            ignore_before_date: Datetime filter - log entries before this date will be ignored across all files

        Returns:
            None

        """
        async with TaskGroup() as tg:
            for log_file_path in self._log_file_paths:
                tg.create_task(self.parse_log_file(log_file_path, ignore_before_date=ignore_before_date))

    def clear(self) -> None:
        """Clear all parsed patterns."""
        if self._parsed_patterns:
            self._parsed_patterns.clear()
            self._logger.debug("All parsed patterns cleared.")

    @staticmethod
    def get_date_diff(start_time: datetime, end_time: datetime) -> float:
        """
        Gets the time difference between two specified dates.

        Args:
            start_time: Initial date.
            end_time: Final date.

        Returns:
            Time difference in seconds.

        """
        delta = end_time - start_time
        return delta.total_seconds()
