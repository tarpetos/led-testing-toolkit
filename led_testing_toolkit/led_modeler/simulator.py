import random

import numpy as np


class PhotoresistorSimulator:
    """
    Simulates a photoresistor's 'imperfect' reading of LED states.

    This class introduces noise, response lag, and probabilistic reporting
    to ideal LED color values to mimic a real-world analog sensor.
    """

    def __init__(self, led_ids: list[str], noise_level: float, lag: float, reporting_chance: float):
        self.led_ids = led_ids
        self.noise_level = noise_level
        self.lag = lag
        self.reporting_chance = reporting_chance

        self.sensed_states: dict[str, np.ndarray] = {
            led_id: np.array([0, 0, 0], dtype=float) for led_id in self.led_ids
        }
        self.last_reported_states: dict[str, np.ndarray] = {
            led_id: np.array([0, 0, 0], dtype=int) for led_id in self.led_ids
        }
        self.rng: np.random.Generator = np.random.default_rng()

    def get_reading(self, ideal_states: dict[str, list[int]]) -> dict[str, list[int]]:
        """
        Processes ideal LED states to produce a simulated, imperfect reading.

        Args:
            ideal_states: A dictionary mapping LED IDs to their ideal [R, G, B] color values.

        Returns:
            A dictionary of LED states that have passed the threshold for reporting,
            including noise and lag.

        """
        reportable_leds = {}
        for led_id in self.led_ids:
            ideal_value = np.array(ideal_states.get(led_id, [0, 0, 0]))

            sensed_value = (ideal_value * (1 - self.lag)) + (self.sensed_states[led_id] * self.lag)
            self.sensed_states[led_id] = sensed_value

            noise = self.rng.normal(0, self.noise_level, 3)
            noisy_value = sensed_value + noise

            final_value = np.clip(noisy_value, 0, 255).astype(int)

            change_magnitude = np.linalg.norm(final_value - self.last_reported_states[led_id])
            should_report = random.random() < self.reporting_chance  # noqa: S311

            if change_magnitude > self.noise_level and should_report:
                reportable_leds[led_id] = final_value.tolist()
                self.last_reported_states[led_id] = final_value

        return reportable_leds
