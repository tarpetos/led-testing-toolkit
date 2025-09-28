from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from led_testing_toolkit.led_modeler.utils import add_colors

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from loguru._logger import Logger

    from led_testing_toolkit.led_modeler.models import AppConfig
    from led_testing_toolkit.led_modeler.patterns import Pattern
    from led_testing_toolkit.led_modeler.simulator import PhotoresistorSimulator


class LedGenerator:
    """Generates and simulates LED patterns."""

    def __init__(
        self,
        config: AppConfig,
        patterns: list[Pattern],
        simulator: PhotoresistorSimulator,
        logger: Logger,
    ) -> None:
        self.config = config
        self.patterns = patterns
        self.simulator = simulator
        self.logger = logger
        self.simulation_start_time = datetime.now().astimezone()

    def _update_states(self, elapsed_s: float) -> dict[str, list[int]]:
        """
        Updates the master LED states by evaluating all active patterns.

        Args:
            elapsed_s: The current elapsed time in the simulation.

        Returns:
            A dictionary of the final, combined state of all LEDs.

        """
        all_led_names = set()
        for p in self.patterns:
            all_led_names.update(p.get_active_leds())

        final_states = {led_name: [0, 0, 0] for led_name in all_led_names}

        for pattern in self.patterns:
            pattern_states = pattern.update(elapsed_s)
            for led_name, color in pattern_states.items():
                final_states[led_name] = add_colors(final_states.get(led_name, [0, 0, 0]), color)

        return final_states

    def _get_current_sleep_interval(self) -> float:
        """
        Calculates a random sleep interval based on the configured range.

        Returns:
            The sleep interval in seconds.

        """
        min_ms, max_ms = self.config.interval_ms_range
        ms = random.randint(min_ms, max_ms)  # noqa: S311
        return ms / 1000.0

    @staticmethod
    def _format_log_message(states_to_log: dict[str, list[int]]) -> str:
        """
        Formats a dictionary of LED states into a standardized log string.

        Args:
            states_to_log: The states to format.

        Returns:
            A comma-separated string of LED states.

        """
        if not states_to_log:
            return ""
        parts = [f"{led_id}=[{','.join(map(str, rgb))}]" for led_id, rgb in sorted(states_to_log.items())]
        return ", ".join(parts)

    def _run_common_loop(self, get_elapsed_time: Callable, should_continue: Callable) -> Generator[None, Any]:
        """
        The main simulation loop logic, shared by 'instant' and 'simulate' modes.

        Args:
            get_elapsed_time: A function that returns the current simulation time.
            should_continue: A function that returns True if the loop should continue.

        """
        self.logger.info(f"--- START INDICATION PATTERN {self.config.mode.upper()} ---")
        while should_continue():
            elapsed_s = get_elapsed_time()
            ideal_states = self._update_states(elapsed_s)
            reportable_states = self.simulator.get_reading(ideal_states)

            if reportable_states:
                log_message = self._format_log_message(reportable_states)
                if self.config.mode == "instant":
                    simulated_timestamp = self.simulation_start_time + timedelta(seconds=elapsed_s)
                    self.logger.patch(lambda record, ts=simulated_timestamp: record.update(time=ts)).debug(log_message)
                else:
                    self.logger.debug(log_message)

            yield

        self.logger.info(f"--- END INDICATION PATTERN {self.config.mode.upper()} ---")

    def generate_instant(self) -> None:
        """Runs the simulation to completion as fast as possible."""
        current_time_s = 0.0

        def get_elapsed_time() -> float:
            nonlocal current_time_s
            t = current_time_s
            current_time_s += self._get_current_sleep_interval()
            return t

        runner = self._run_common_loop(get_elapsed_time, lambda: current_time_s < self.config.duration)
        for _ in runner:
            pass

    async def _simulation_loop(self) -> None:
        """Runs the simulation in real-time using asyncio."""
        start_time = time.monotonic()
        runner = self._run_common_loop(
            lambda: time.monotonic() - start_time,
            lambda: (time.monotonic() - start_time) < self.config.duration,
        )
        for _ in runner:
            await asyncio.sleep(self._get_current_sleep_interval())

    def run(self) -> None:
        """Starts the simulation based on the configured mode."""
        if self.config.mode == "instant":
            self.generate_instant()
        elif self.config.mode == "simulate":
            try:
                asyncio.run(self._simulation_loop())
            except KeyboardInterrupt:
                self.logger.warning("Simulation interrupted by user.")
