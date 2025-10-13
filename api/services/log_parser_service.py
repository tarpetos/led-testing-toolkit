from __future__ import annotations

import copy
import tempfile
from pathlib import Path

from led_testing_toolkit.led_parser import LedParser


class LogParserService:
    def __init__(self, led_parser: LedParser) -> None:
        self._parser = led_parser
        self.last_parsed_patterns: list[dict] = []

    async def parse_log_file(self, file_content: bytes) -> list[dict]:
        self.last_parsed_patterns = []

        with tempfile.NamedTemporaryFile(mode="wb", delete=True, suffix=".log") as temp_file:
            temp_file.write(file_content)
            temp_file.flush()
            await self._parser.parse_log_file(Path(temp_file.name))

        parsed_data = next(iter(self._parser.patterns.values()), [])
        self._parser.clear()

        if not parsed_data:
            return []

        self.last_parsed_patterns = copy.deepcopy(parsed_data)

        return [
            {"index": i, "duration": self._calculate_pattern_duration(pattern)}
            for i, pattern in enumerate(self.last_parsed_patterns)
        ]

    def get_pattern_by_index(self, index: int) -> dict | None:
        if 0 <= index < len(self.last_parsed_patterns):
            return self.last_parsed_patterns[index]
        return None

    @staticmethod
    def _calculate_pattern_duration(pattern: dict) -> float:
        min_time = float("inf")
        max_time = float("-inf")
        has_time = False

        for led_data in pattern.values():
            for color_records in led_data.values():
                for record in color_records:
                    if record.coordinates:
                        for point in record.coordinates:
                            has_time = True
                            min_time = min(min_time, point.z)
                            max_time = max(max_time, point.z)

        return max_time - min_time if has_time else 0.0


log_parser_service = LogParserService(led_parser=LedParser())
