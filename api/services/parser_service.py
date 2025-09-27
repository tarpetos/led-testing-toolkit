import copy
import tempfile
from pathlib import Path

from api.utils.helpers import convert_normalized_to_raw_format
from led_testing_toolkit.led_parser import LedParser


class ParserService:
    def __init__(self):
        self.parser = LedParser()
        self.last_parsed_patterns: list[dict] = []

    async def parse_log_file(self, file_content: bytes) -> list[dict]:
        self.last_parsed_patterns = []

        with tempfile.NamedTemporaryFile(mode="wb", delete=True, suffix=".log") as temp_file:
            temp_file.write(file_content)
            temp_file.flush()

            await self.parser.parse_log_file(Path(temp_file.name))

        parsed_data = next(iter(self.parser.patterns.values()), [])
        self.parser.clear()

        if not parsed_data:
            return []

        self.last_parsed_patterns = copy.deepcopy(parsed_data)

        patterns_metadata = []
        for i, pattern in enumerate(self.last_parsed_patterns):
            duration = self._calculate_pattern_duration(pattern)
            patterns_metadata.append({"index": i, "duration": duration})

        return patterns_metadata

    def get_pattern_by_index(self, index: int) -> dict | None:
        if 0 <= index < len(self.last_parsed_patterns):
            normalized_pattern = self.last_parsed_patterns[index]

            return convert_normalized_to_raw_format(normalized_pattern)

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

        if not has_time:
            return 0.0

        return max_time - min_time


log_parser_service = ParserService()
