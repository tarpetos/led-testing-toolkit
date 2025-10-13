import asyncio
import time
from contextlib import suppress

from api.models.player import LedState, PlayerStatus, PlayerUpdate
from led_testing_toolkit.mongo_db_connector import MongoDbConnector


class PlayerService:
    def __init__(self):
        self.pattern_data: dict[str, list] | None = None
        self.is_playing: bool = False
        self.playback_start_time: float = 0.0
        self.paused_elapsed_time: float = 0.0
        self._current_led_states: dict[str, LedState] = {}
        self.lock = asyncio.Lock()
        self.playback_start_abs_time: float = 0.0
        self.total_duration: float = 0.0

    def _reset_player_state_unsafe(self) -> None:
        self.is_playing = False
        self.pattern_data = None
        self.playback_start_time = 0.0
        self.paused_elapsed_time = 0.0
        self._current_led_states = {}
        self.playback_start_abs_time = 0.0
        self.total_duration = 0.0

    def _calculate_pattern_times(self) -> None:
        if not self.pattern_data:
            self.playback_start_abs_time = 0.0
            self.total_duration = 0.0
            return

        min_time = float("inf")
        max_time = float("-inf")
        is_valid_data = False

        for led_data in self.pattern_data.values():
            if isinstance(led_data, list) and led_data:
                is_valid_data = True
                for step in led_data:
                    if isinstance(step, list) and len(step) > 2 and isinstance(step[2], (int, float)):
                        min_time = min(min_time, step[2])
                        max_time = max(max_time, step[2])

        if is_valid_data:
            self.playback_start_abs_time = min_time if min_time != float("inf") else 0.0
            self.total_duration = (max_time - min_time) if max_time > min_time else 0.0
        else:
            self.playback_start_abs_time = 0.0
            self.total_duration = 0.0

    async def load_etalon_pattern(self, collection_name: str, pattern_name: str) -> None:
        async with self.lock:
            self._reset_player_state_unsafe()
            async with MongoDbConnector() as connector:
                await connector.use_collection(collection_name, auto_create=False)
                data = await connector.read({"_id": pattern_name})
            if data and isinstance(data, dict):
                self.pattern_data = {k: v for k, v in data.items() if k.startswith("LED")}
                self._calculate_pattern_times()

    async def load_measured_pattern(self, collection_name: str) -> None:
        async with self.lock:
            self._reset_player_state_unsafe()
            async with MongoDbConnector() as connector:
                await connector.use_collection(collection_name, auto_create=False)
                data = await connector.read_random()
            if data and isinstance(data, dict):
                self.pattern_data = {k: v for k, v in data.items() if k.startswith("LED")}
                self._calculate_pattern_times()

    def _update_led_states_for_time(self, current_time: float) -> None:
        if not self.pattern_data:
            self._current_led_states = {}
            return

        states = {}
        for led_id, led_data in self.pattern_data.items():
            final_rgb = [0, 0, 0]
            if isinstance(led_data, list):
                for step in led_data:
                    if isinstance(step, list) and len(step) > 2 and isinstance(step[2], (int, float)):
                        normalized_step_time = step[2] - self.playback_start_abs_time
                        if normalized_step_time <= current_time:
                            if isinstance(step[1], list) and len(step[1]) >= 3:
                                final_rgb = step[1]
                        else:
                            break
            try:
                states[led_id] = LedState(
                    r=int(final_rgb[0]),
                    g=int(final_rgb[1]),
                    b=int(final_rgb[2]),
                )
            except (ValueError, TypeError):
                continue
        self._current_led_states = states

    async def playback_loop(self) -> None:
        while True:
            with suppress(Exception):
                async with self.lock:
                    if self.pattern_data:
                        current_time = (
                            (time.time() - self.playback_start_time) if self.is_playing else self.paused_elapsed_time
                        )

                        if self.is_playing and current_time >= self.total_duration:
                            self.is_playing = False
                            self.paused_elapsed_time = self.total_duration
                        if self.is_playing:
                            self._update_led_states_for_time(current_time)
            await asyncio.sleep(0.01)

    async def resume(self) -> None:
        async with self.lock:
            if not self.is_playing and self.pattern_data:
                if self.paused_elapsed_time >= self.total_duration:
                    self.paused_elapsed_time = 0.0
                self.is_playing = True
                self.playback_start_time = time.time() - self.paused_elapsed_time

    async def pause(self) -> None:
        async with self.lock:
            if self.is_playing:
                self.is_playing = False
                self.paused_elapsed_time = time.time() - self.playback_start_time

    async def stop(self) -> None:
        async with self.lock:
            self._reset_player_state_unsafe()

    async def seek_to_time(self, seek_time: float) -> None:
        async with self.lock:
            if not self.pattern_data:
                return

            safe_seek_time = max(0.0, min(seek_time, self.total_duration))
            self.paused_elapsed_time = safe_seek_time
            if self.is_playing:
                self.playback_start_time = time.time() - self.paused_elapsed_time

            self._update_led_states_for_time(safe_seek_time)

    def get_state(self) -> PlayerUpdate:
        status = PlayerStatus(
            has_pattern=self.pattern_data is not None,
            is_playing=self.is_playing,
            current_time=0.0,
            total_duration=0.0,
        )

        if self.pattern_data:
            status.total_duration = self.total_duration
            current_time = (time.time() - self.playback_start_time) if self.is_playing else self.paused_elapsed_time
            status.current_time = max(0.0, min(current_time, self.total_duration))

            if not self.is_playing:
                self._update_led_states_for_time(status.current_time)

        return PlayerUpdate(status=status, leds=self._current_led_states)

    async def load_raw_pattern_data(self, pattern_data: dict) -> None:
        async with self.lock:
            self._reset_player_state_unsafe()
            if pattern_data and isinstance(pattern_data, dict):
                self.pattern_data = pattern_data
                self._calculate_pattern_times()


player_service = PlayerService()
