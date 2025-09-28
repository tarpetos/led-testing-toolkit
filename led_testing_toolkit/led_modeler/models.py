from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    ValidationError,
    conlist,
    field_validator,
)

Color = conlist(int, min_length=3, max_length=3)


class BasePatternConfig(BaseModel):
    """Base model for a single pattern block in a palette."""

    led_ids: list[int] = Field(default=[], description="List of LED IDs this pattern applies to.")
    start_time: float = Field(default=0.0, description="Time in seconds when the pattern becomes active.")
    end_time: float = Field(default=float("inf"), description="Time in seconds when the pattern stops being active.")


class FadePatternConfig(BasePatternConfig):
    """Configuration for a fade-in/fade-out pattern."""

    type: Literal["fade"]
    color: Color = Field(default=[255, 255, 255])
    duration: float = Field(..., description="Total duration of the fade effect.")
    peak_time: float = Field(..., description="Time within the duration at which the brightness is at its peak.")


class ChaserPatternConfig(BasePatternConfig):
    """Configuration for a 'chaser' or 'larson scanner' pattern."""

    type: Literal["chaser"]
    color: Color = Field(default=[255, 255, 255])
    cycle_duration: float = Field(default=2.0, description="Time in seconds for one full sweep across all LEDs.")
    pulse_width: float = Field(default=0.5, description="Width of the light pulse as a fraction of the number of LEDs.")


class Keyframe(BaseModel):
    """A single point in time with a specific color."""

    time: float = Field(..., description="Time in seconds for this keyframe within the pattern's local timeline.")
    color: Color


class KeyframesPatternConfig(BasePatternConfig):
    """Configuration for a pattern driven by explicit keyframes."""

    type: Literal["keyframes"] = "keyframes"
    keyframes: list[Keyframe] = Field(..., description="A list of time-stamped color keyframes.")

    @field_validator("keyframes")
    @classmethod
    def sort_keyframes_by_time(cls, v: list[Keyframe]) -> list[Keyframe]:
        """Ensures keyframes are sorted by time for correct interpolation."""
        return sorted(v, key=lambda k: k.time)


AnyPattern = FadePatternConfig | ChaserPatternConfig | KeyframesPatternConfig


class AppConfig(BaseModel):
    """Main application configuration model, derived from CLI arguments."""

    mode: Literal["simulate", "instant"]
    duration: float
    output_file: str
    interval: str
    noise: float
    lag: float
    reporting_chance: float
    num_leds: int | None = None
    color: str | None = None
    fade: float | None = None
    sequence: Literal["all_at_once", "sequential"] | None = None
    palette: str | None = None

    interval_ms_range: tuple[int, int] = (0, 0)
    parsed_color: Color = [0, 0, 0]
    parsed_palette: list[AnyPattern] = []

    @field_validator("interval")
    @classmethod
    def parse_interval(cls, v: str) -> str:
        """Validates the interval format but keeps the original string."""
        try:
            parts = list(map(int, v.split("-")))
            if not (1 <= len(parts) <= 2):
                raise ValueError  # noqa: TRY301
            if any(p < 0 for p in parts):
                raise ValueError  # noqa: TRY301
        except (ValueError, AttributeError) as e:
            sys.exit(f"{e!s}")
        return v

    def model_post_init(self, __context: Any, /) -> None:  # noqa: ANN401
        """Parses string-based arguments into structured data after initial validation."""
        parts = list(map(int, self.interval.split("-")))
        self.interval_ms_range = (parts[0], parts[0]) if len(parts) == 1 else (min(parts), max(parts))

        if self.color:
            try:
                self.parsed_color = list(map(int, self.color.split(",")))
            except (ValueError, AttributeError) as e:
                sys.exit(f"{e!s}")

        if self.palette:
            try:
                palette_path = Path(self.palette)
                if palette_path.exists():
                    with palette_path.open() as f:
                        palette_data = json.load(f)
                else:
                    palette_data = json.loads(self.palette)

                adapter = TypeAdapter(list[AnyPattern])
                self.parsed_palette = adapter.validate_python(palette_data)

            except (json.JSONDecodeError, FileNotFoundError, TypeError, ValidationError) as e:
                sys.exit(f"{e!s}")

        if not self.palette and not all([self.num_leds, self.color, self.sequence]):
            sys.exit(1)
