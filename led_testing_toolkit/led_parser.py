from __future__ import annotations

import re
import tempfile
from asyncio import TaskGroup
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

import aiofiles
import loguru

from .led_models import LED, Color, LEDPattern, LEDSequence

if TYPE_CHECKING:
    from collections.abc import Sequence

    from loguru._logger import Logger


class LedParser:
    """Class for processing raw indication retrieved from log files."""

    def __init__(
        self,
        log_file_paths: Sequence[Path | str] | None = None,
        led_search_pattern: re.Pattern = re.compile(r"LED(\d)=\[(\d+),(\d+),(\d+)]"),
        led_identifier: str = "LED",
        logger: Logger = loguru.logger,
    ) -> None:
        self._log_file_paths: tuple[Path, ...] = tuple(Path(path) for path in log_file_paths) if log_file_paths else ()
        self._log_search_pattern: Final[re.Pattern] = led_search_pattern
        self._led_identifier: Final[str] = led_identifier
        self._logger: Logger = logger

        self._parsed_patterns: dict[Path, list[LEDPattern]] = {}

    @property
    def patterns(self) -> dict[Path, list[LEDPattern]]:
        return self._parsed_patterns

    async def _create_temp_log_file(self, source_file: Path) -> tempfile.NamedTemporaryFile:
        """
        Create a temporary copy of the log file to read from.

        :param source_file: Path to the original log file
        :return: NamedTemporaryFile object
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
    ) -> list[dict[str, str]] | None:
        """
        Read indication logs from a temporary log file.

        Splits them into 3 parts:
            1. Timestamp
            2. Logging level
            3. Message itself

        :param temp_file: a temporary log file object opened for reading
        :param log_line_length: the expected length of each message list after splitting
        :return: preprocessed patterns
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
                    self._logger.warning(f"Malformed log line skipped: {line}")
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

    async def _retrieve_patterns(self, log_file: Path) -> list[dict[str, str]]:
        """
        Initial parsing of indication patterns to split them and convert them from strings to dictionaries.

        :param log_file: file to read patterns from
        :return: preprocessed patterns
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

    def _check_color_events(self, log_line: str) -> dict[str, LED] | None:
        """
        Extract all LEDs from log_line and return as dict with keys {"LED1": LED(...), "LED2": LED(...), ...}
        If there is a duplicate LED in line, only the first one is used.
        """
        led_matches = self._log_search_pattern.findall(log_line)

        if not led_matches:
            return None

        led_dict = {}

        for led_num, r, g, b in led_matches:
            led_key = f"{self._led_identifier}{led_num}"

            if led_key not in led_dict:
                rgb = (int(r), int(g), int(b))
                led_dict[led_key] = LED(rel_time=0.0, color=Color(*rgb), abs_time=0.0)

        return led_dict

    def _recalculate_led_times(self, sequences: dict, timestamps_per_led: dict) -> list[LEDSequence] | None:
        """
        Recalculate relative and absolute for all LED sequences.

        :param sequences: dictionary containing LED sequences data
        :param timestamps_per_led: dictionary containing timestamps for each LED
        """
        all_timestamps = []
        for timestamps in timestamps_per_led.values():
            all_timestamps.extend(timestamps)

        if not all_timestamps:
            return None

        global_start_time = min(all_timestamps)

        led_sequences = []
        for led_key, sequence in sequences.items():
            led_timestamps = timestamps_per_led[led_key]
            led_start_time = min(led_timestamps)

            for i, led_obj in enumerate(sequence):
                current_timestamp = led_timestamps[i]
                led_obj.rel_time = self.get_date_diff(led_start_time, current_timestamp)
                led_obj.abs_time = self.get_date_diff(global_start_time, current_timestamp)

            led_sequences.append(LEDSequence(int(led_key.removeprefix(self._led_identifier)), sequence))
        return led_sequences

    async def parse_log_file(self, log_file_path: Path, *, ignore_before_date: datetime | None = None) -> None:
        """
        Parse a single log file to extract LED patterns and sequences.

        Processes raw log data to identify LED color events, calculates relative and absolute
        timing for each LED sequence, and stores the parsed patterns.

        :param log_file_path: Path to the log file to be parsed
        :param ignore_before_date: optional datetime filter - entries before this date will be ignored
        """
        log_file_path = Path(log_file_path)
        parsed_patterns = []
        raw_patterns = await self._retrieve_patterns(log_file_path)
        if not raw_patterns:
            return

        self._logger.debug(f"Retrieved {len(raw_patterns)} pattern(s) from log file `{log_file_path}`.")
        for count, raw_pattern in enumerate(raw_patterns, 1):
            sequences = {}
            timestamps_per_led = {}
            for timestamp, log_line in raw_pattern.items():
                date = datetime.fromisoformat(timestamp)
                if ignore_before_date and date < ignore_before_date:
                    continue

                parsed_line = self._check_color_events(log_line)

                if parsed_line is None:
                    continue

                for led_key, led_data in parsed_line.items():
                    if led_key not in sequences:
                        sequences[led_key] = []
                        timestamps_per_led[led_key] = []

                    sequences[led_key].append(led_data)
                    timestamps_per_led[led_key].append(date)

            parsed_sequences = self._recalculate_led_times(sequences, timestamps_per_led)
            if parsed_sequences is None:
                self._logger.warning(f"Parsing of pattern #{count} is skipped!")
                continue
            parsed_patterns.append(LEDPattern("", "", sequences=parsed_sequences))
        self._parsed_patterns[log_file_path] = parsed_patterns

    async def parse_patterns(self, *, ignore_before_date: datetime | None = None) -> None:
        """
        Parse all configured log files concurrently to extract LED patterns.

        :param ignore_before_date: datetime filter - log entries before this date will be ignored across all files
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
        Get the time difference between two specified dates.

        :param start_time: initial date
        :param end_time: final date
        :return: time difference in seconds
        """
        delta = end_time - start_time
        return delta.total_seconds()
