from __future__ import annotations

from datetime import datetime

from pydantic import field_validator
from pydantic.dataclasses import dataclass

from collections.abc import Sequence


@dataclass
class Color:
    R: int
    G: int
    B: int

    @field_validator("R", "G", "B")
    @classmethod
    def validate_rgb(cls, v):
        if not 0 <= v <= 255:
            raise TypeError("RGB values must be between 0 and 255:")
        return v


@dataclass
class LED:
    rel_time: float
    color: Color
    abs_time: float


@dataclass
class LEDSequence:
    number: int
    leds: Sequence[LED]


@dataclass
class LEDPattern:
    device_prefix: str
    name: str
    sequences: Sequence[LEDSequence]
