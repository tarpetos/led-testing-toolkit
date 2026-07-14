import pytest
from pydantic import ValidationError
from api.models.player import LedState, PlayerStatus, PlayerUpdate


def test_led_state():
    state = LedState(r=255, g=128, b=0)
    assert state.r == 255
    assert state.g == 128
    assert state.b == 0


def test_player_status():
    status = PlayerStatus(has_pattern=True, is_playing=False, current_time=1.5, total_duration=10.0)
    assert status.has_pattern is True
    assert status.is_playing is False
    assert status.current_time == 1.5
    assert status.total_duration == 10.0


def test_player_update():
    status = PlayerStatus(has_pattern=True, is_playing=False, current_time=1.5, total_duration=10.0)
    led_state = LedState(r=255, g=128, b=0)
    update = PlayerUpdate(status=status, leds={"led_1": led_state})
    
    assert update.type == "player_update"
    assert update.status == status
    assert update.leds["led_1"] == led_state


def test_led_state_invalid():
    with pytest.raises(ValidationError):
        LedState(r="invalid", g=128, b=0)
