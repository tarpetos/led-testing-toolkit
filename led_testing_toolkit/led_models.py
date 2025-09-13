from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import field_validator
from pydantic.dataclasses import dataclass

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class Color:
    R: int  # 0-255
    G: int  # 0-255
    B: int  # 0-255


@dataclass
class LED:
    timestamp: datetime
    rel_time: float  # 0, 1.5, 2.5, ...
    color: Color  # Color(0, 255, 0), Color(0, 25, 23), Color(13, 55, 2), ...

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v: datetime | str) -> datetime:
        if not isinstance(v, datetime):
            raise TypeError("field `timestamp` must be an instance `datetime`:")
        return v


@dataclass
class LEDSequence:
    number: int  # 1, 2, 3, 4, ...
    leds: Sequence[LED]  # [LED(rel_time=0.0, color=Color(0, 255, 0)), LED(rel_time=0.0, color=Color(0, 255, 0)), ...]


@dataclass
class LEDPattern:
    device_prefix: str
    name: str
    sequences: Sequence[LEDSequence]
