from __future__ import annotations

import asyncio
import random
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from led_testing_toolkit.led_modeler.utils import add_colors
from led_testing_toolkit.mongo_db_connector import MongoDbConnector
from led_testing_toolkit.utils.collection_name import validate_measured_collection_name

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
        save_to_db_collection: str | None = None,
    ) -> None:
        """
        Initialize the LedGenerator.

        Args:
            config: Application configuration.
            patterns: List of patterns.
            simulator: The simulator to use.
            logger: The logger instance.
            save_to_db_collection: Optional DB collection.

        """
        self.config = config
        self.patterns = patterns
        self.simulator = simulator
        self.logger = logger
        self.simulation_start_time = datetime.now().astimezone()
        self.save_to_db_collection = save_to_db_collection
        self.db_output_data: dict[str, list] = defaultdict(list)

    def _update_states(self, elapsed_s: float) -> dict[str, dict[str, float | list[int]]]:
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

        final_states = {led_name: {"color": [0, 0, 0], "rel_time": 0.0} for led_name in all_led_names}

        for pattern in self.patterns:
            pattern_states = pattern.update(elapsed_s)
            for led_name, state_data in pattern_states.items():
                final_states[led_name]["color"] = add_colors(
                    final_states.get(led_name, {}).get("color", [0, 0, 0]),
                    state_data["color"],
                )
                final_states[led_name]["rel_time"] = max(
                    final_states.get(led_name, {}).get("rel_time", 0.0),
                    state_data["rel_time"],
                )

        return final_states

    def _get_current_sleep_interval(self) -> float:
        """
        Calculates a random sleep interval based on the configured range.

        Returns:
            The sleep interval in seconds.

        """
        min_ms, max_ms = self.config.interval_ms_range
        ms = random.randint(min_ms, max_ms)
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
        self.db_output_data.clear()
        if not self.save_to_db_collection:
            self.logger.debug(f"--- START INDICATION PATTERN {self.config.mode.upper()} ---")

        while should_continue():
            elapsed_s = get_elapsed_time()
            ideal_states_with_meta = self._update_states(elapsed_s)

            ideal_colors = {led_id: state["color"] for led_id, state in ideal_states_with_meta.items()}
            reportable_states = self.simulator.get_reading(ideal_colors)

            if reportable_states:
                if self.save_to_db_collection:
                    for led_id, rgb in reportable_states.items():
                        rel_time = ideal_states_with_meta[led_id]["rel_time"]
                        self.db_output_data[led_id].append([rel_time, rgb, elapsed_s])
                else:
                    log_message = self._format_log_message(reportable_states)
                    if self.config.mode == "instant":
                        simulated_timestamp = self.simulation_start_time + timedelta(seconds=elapsed_s)
                        self.logger.patch(lambda record, ts=simulated_timestamp: record.update(time=ts)).debug(
                            log_message,
                        )
                    else:
                        self.logger.debug(log_message)
            yield

        if not self.save_to_db_collection:
            self.logger.debug(f"--- END INDICATION PATTERN {self.config.mode.upper()} ---")

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

    async def _save_to_db(self) -> None:
        """Saves the aggregated simulation data to MongoDB."""
        if not self.db_output_data:
            self.logger.warning("No data was generated to save to the database.")
            return

        collection_name = validate_measured_collection_name(self.save_to_db_collection)
        self.logger.debug(f"Saving generated data to MongoDB collection: `{collection_name}`...")
        try:
            async with MongoDbConnector() as connector:
                await connector.use_collection(collection_name, auto_create=True)
                result = await connector.insert(dict(self.db_output_data))
                if result and result.inserted_id:
                    self.logger.success(f"Successfully inserted document with _id: {result.inserted_id}")
                else:
                    self.logger.error("Failed to insert document into database.")
        except Exception as e:
            self.logger.error(f"An error occurred while saving to MongoDB: {e!s}")

    async def run(self) -> None:
        """Starts the simulation based on the configured mode and saves the output."""
        if self.config.mode == "instant":
            self.generate_instant()
        elif self.config.mode == "simulate":
            try:
                await self._simulation_loop()
            except KeyboardInterrupt:
                self.logger.warning("Simulation interrupted by user.")

        if self.save_to_db_collection:
            await self._save_to_db()
