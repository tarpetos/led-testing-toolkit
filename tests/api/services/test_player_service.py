import pytest
import asyncio
from unittest.mock import patch
import time

from api.services.player_service import PlayerService


@pytest.fixture
def player():
    return PlayerService()


def test_initial_state(player):
    assert player.pattern_data is None
    assert not player.is_playing
    assert player.playback_start_time == 0.0
    assert player.total_duration == 0.0


def test_calculate_pattern_times_no_data(player):
    player._calculate_pattern_times()
    assert player.playback_start_abs_time == 0.0
    assert player.total_duration == 0.0


def test_calculate_pattern_times_with_data(player):
    player.pattern_data = {
        "LED1": [[1, [255, 0, 0], 1.0], [1, [0, 255, 0], 3.5]],
        "LED2": "invalid",
        "LED3": [[1, [0, 0, 255]]],
    }
    player._calculate_pattern_times()
    assert player.playback_start_abs_time == 1.0
    assert player.total_duration == 2.5


def test_calculate_pattern_times_invalid_data(player):
    player.pattern_data = {"LED1": [], "LED2": "invalid", "LED3": None}
    player._calculate_pattern_times()
    assert player.playback_start_abs_time == 0.0
    assert player.total_duration == 0.0


@pytest.mark.asyncio
async def test_load_etalon_pattern():
    player = PlayerService()
    with patch("api.services.player_service.MongoDbConnector") as mock_mongo:
        connector_instance = mock_mongo.return_value.__aenter__.return_value
        connector_instance.read.return_value = {"LED1": [[1, [255, 0, 0], 0.0]], "other": 1}

        await player.load_etalon_pattern("col", "pat")

        assert player.pattern_data == {"LED1": [[1, [255, 0, 0], 0.0]]}
        assert player.total_duration == 0.0


@pytest.mark.asyncio
async def test_load_etalon_pattern_empty():
    player = PlayerService()
    with patch("api.services.player_service.MongoDbConnector") as mock_mongo:
        connector_instance = mock_mongo.return_value.__aenter__.return_value
        connector_instance.read.return_value = None

        await player.load_etalon_pattern("col", "pat")

        assert player.pattern_data is None


@pytest.mark.asyncio
async def test_load_measured_pattern():
    player = PlayerService()
    with patch("api.services.player_service.MongoDbConnector") as mock_mongo:
        connector_instance = mock_mongo.return_value.__aenter__.return_value
        connector_instance.read_random.return_value = {"LED1": [[1, [0, 255, 0], 1.0]]}

        await player.load_measured_pattern("col")

        assert player.pattern_data == {"LED1": [[1, [0, 255, 0], 1.0]]}


@pytest.mark.asyncio
async def test_load_measured_pattern_empty():
    player = PlayerService()
    with patch("api.services.player_service.MongoDbConnector") as mock_mongo:
        connector_instance = mock_mongo.return_value.__aenter__.return_value
        connector_instance.read_random.return_value = None

        await player.load_measured_pattern("col")

        assert player.pattern_data is None


def test_update_led_states_for_time(player):
    player.pattern_data = {
        "LED1": [[1, [255, 0, 0], 1.0], [1, [0, 255, 0], 2.0]],
        "LED2": [[1, [0, 0, 255], 1.5]],
        "LED3": [[1, "invalid", 1.0]],
        "LED4": [[1, ["invalid", 0, 0], 1.0]],
    }
    player.playback_start_abs_time = 1.0

    player._update_led_states_for_time(0.0)
    assert player._current_led_states["LED1"].r == 255
    assert player._current_led_states["LED1"].g == 0
    assert player._current_led_states["LED1"].b == 0
    assert player._current_led_states["LED2"].b == 0
    assert "LED4" not in player._current_led_states

    player._update_led_states_for_time(0.5)
    assert player._current_led_states["LED1"].r == 255
    assert player._current_led_states["LED2"].b == 255

    player._update_led_states_for_time(1.0)
    assert player._current_led_states["LED1"].g == 255
    assert player._current_led_states["LED2"].b == 255


def test_update_led_states_for_time_empty(player):
    player._update_led_states_for_time(0.0)
    assert player._current_led_states == {}


@pytest.mark.asyncio
async def test_playback_controls(player):
    player.pattern_data = {"LED1": [[1, [255, 0, 0], 0.0], [1, [0, 255, 0], 1.0]]}
    player._calculate_pattern_times()

    assert player.total_duration == 1.0

    await player.resume()
    assert player.is_playing

    # Coverage for resume when paused_elapsed_time >= total_duration
    player.is_playing = False
    player.paused_elapsed_time = 1.5
    await player.resume()
    assert player.paused_elapsed_time == 0.0
    assert player.is_playing

    await player.pause()
    assert not player.is_playing
    assert player.paused_elapsed_time >= 0

    await player.seek_to_time(0.5)
    assert player.paused_elapsed_time == 0.5

    await player.resume()
    await player.seek_to_time(0.2)
    assert player.paused_elapsed_time == 0.2

    await player.seek_to_time(2.0)
    assert player.paused_elapsed_time == 1.0

    await player.stop()
    assert player.pattern_data is None
    assert not player.is_playing


@pytest.mark.asyncio
async def test_seek_without_data(player):
    await player.seek_to_time(1.0)
    assert player.paused_elapsed_time == 0.0


@pytest.mark.asyncio
async def test_get_state(player):
    state = player.get_state()
    assert not state.status.has_pattern

    player.pattern_data = {"LED1": [[1, [255, 0, 0], 0.0]]}
    player._calculate_pattern_times()

    state = player.get_state()
    assert state.status.has_pattern
    assert state.status.total_duration == 0.0


@pytest.mark.asyncio
async def test_load_raw_pattern_data(player):
    await player.load_raw_pattern_data({"LED1": [[1, [255, 0, 0], 0.0]]})
    assert player.pattern_data is not None
    await player.load_raw_pattern_data(None)
    assert player.pattern_data is None


@pytest.mark.asyncio
async def test_playback_loop_task(player):
    player.pattern_data = {"LED1": [[1, [255, 0, 0], 0.0], [1, [0, 255, 0], 1.0]]}
    player._calculate_pattern_times()
    await player.resume()

    task = asyncio.create_task(player.playback_loop())
    await asyncio.sleep(0.05)
    task.cancel()

    assert player.is_playing

    player.is_playing = True
    player.playback_start_time = time.time() - 2.0
    task = asyncio.create_task(player.playback_loop())
    await asyncio.sleep(0.05)
    task.cancel()
    assert not player.is_playing
