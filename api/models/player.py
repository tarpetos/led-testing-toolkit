from pydantic import BaseModel


class LedState(BaseModel):
    r: int
    g: int
    b: int


class PlayerStatus(BaseModel):
    has_pattern: bool
    is_playing: bool
    current_time: float
    total_duration: float


class PlayerUpdate(BaseModel):
    type: str = "player_update"
    status: PlayerStatus
    leds: dict[str, LedState]
