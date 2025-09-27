from pydantic import BaseModel, Field


class SelectEtalonRequest(BaseModel):
    pattern_name: str = Field(
        ...,
        description="The name of the etalon pattern to load",
    )


class SelectMeasuredRequest(BaseModel):
    collection_name: str = Field(
        ...,
        description="The name of the measured collection to load a random record from",
    )


class SeekRequest(BaseModel):
    time: float = Field(..., ge=0, description="The time to seek to in seconds")


class PlayerStatus(BaseModel):
    has_pattern: bool
    is_playing: bool
    current_time: float
    total_duration: float


class LedState(BaseModel):
    r: int
    g: int
    b: int


class PlayerUpdate(BaseModel):
    type: str = "player_update"
    status: PlayerStatus
    leds: dict[str, LedState]
