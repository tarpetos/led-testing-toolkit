"""
Models for the player state.

This module contains data models representing the current state of the player,
including LED statuses and general playback information.
"""

from pydantic import BaseModel


class LedState(BaseModel):
    """Represents the RGB state of a single LED."""

    r: int
    g: int
    b: int


class PlayerStatus(BaseModel):
    """Represents the current status of the player."""

    has_pattern: bool
    is_playing: bool
    current_time: float
    total_duration: float


class PlayerUpdate(BaseModel):
    """Represents an update event broadcasted from the player."""

    type: str = "player_update"
    status: PlayerStatus
    leds: dict[str, LedState]
