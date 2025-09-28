from abc import ABC, abstractmethod

from led_testing_toolkit.led_modeler.models import (
    ChaserPatternConfig,
    Color,
    FadePatternConfig,
    KeyframesPatternConfig,
)
from led_testing_toolkit.led_modeler.utils import lerp


class Pattern(ABC):
    """Abstract base class for all LED patterns."""

    def __init__(self, led_ids: list[int], start_time: float, end_time: float):
        self.led_ids = led_ids
        self.start_time = start_time
        self.end_time = end_time
        self.led_names = {f"LED{i}" for i in self.led_ids}

    def get_active_leds(self) -> set[str]:
        """
        Returns the set of LED names controlled by this pattern.

        Returns:
            A set of strings, e.g., {"LED1", "LED3"}.

        """
        return self.led_names

    @abstractmethod
    def update(self, elapsed_s: float) -> dict[str, list[int]]:
        """
        Calculates the state of all controlled LEDs at a given time.

        Args:
            elapsed_s: The total elapsed time in the simulation.

        Returns:
            A dictionary mapping LED names to their calculated [R, G, B] color.

        """


class FadePattern(Pattern):
    """A pattern that fades a color in and out over a duration."""

    def __init__(self, config: FadePatternConfig):
        super().__init__(config.led_ids, config.start_time, config.end_time)
        self.config = config

    def update(self, elapsed_s: float) -> dict[str, list[int]]:
        states = {}
        if not (self.start_time <= elapsed_s < self.end_time):
            return states

        time_in_pattern = elapsed_s - self.start_time
        peak_time = self.config.peak_time
        duration = self.config.duration

        if time_in_pattern < peak_time:
            progress = (time_in_pattern / peak_time) if peak_time > 0 else 1
        else:
            fade_out_duration = duration - peak_time
            progress = 1 - ((time_in_pattern - peak_time) / fade_out_duration) if fade_out_duration > 0 else 0

        progress = max(0, min(1, progress))
        final_color = [lerp(0, c, progress) for c in self.config.color]

        for led_id in self.led_ids:
            states[f"LED{led_id}"] = final_color
        return states


class ChaserPattern(Pattern):
    """A 'larson scanner' pattern where a pulse of light moves across LEDs."""

    def __init__(self, config: ChaserPatternConfig) -> None:
        super().__init__(config.led_ids, config.start_time, config.end_time)
        self.config = config

    def update(self, elapsed_s: float) -> dict[str, list[int]]:
        states = {}
        if not (self.start_time <= elapsed_s < self.end_time):
            return states

        time_in_pattern = elapsed_s - self.start_time
        cycle_pos = (time_in_pattern % self.config.cycle_duration) / self.config.cycle_duration
        active_led_index_float = cycle_pos * len(self.led_ids)

        for i, led_id in enumerate(self.led_ids):
            distance = min(abs(i - active_led_index_float), len(self.led_ids) - abs(i - active_led_index_float))
            pulse_effect = max(0.0, 1 - (distance / (self.config.pulse_width * len(self.led_ids))))

            if pulse_effect > 0:
                final_color = [lerp(0, c, pulse_effect) for c in self.config.color]
                states[f"LED{led_id}"] = final_color
        return states


class KeyframesPattern(Pattern):
    """A pattern that interpolates between a series of defined color keyframes."""

    def __init__(self, config: KeyframesPatternConfig) -> None:
        super().__init__(config.led_ids, config.start_time, config.end_time)
        self.config = config

    def update(self, elapsed_s: float) -> dict[str, list[int]]:
        states = {}
        if not (self.start_time <= elapsed_s < self.end_time) or not self.config.keyframes:
            return states

        time_in_pattern = elapsed_s - self.start_time
        color = [0, 0, 0]

        if time_in_pattern < self.config.keyframes[0].time:
            color = self.config.keyframes[0].color
        elif time_in_pattern >= self.config.keyframes[-1].time:
            color = self.config.keyframes[-1].color
        else:
            for i in range(len(self.config.keyframes) - 1):
                k_start, k_end = self.config.keyframes[i], self.config.keyframes[i + 1]
                if k_start.time <= time_in_pattern < k_end.time:
                    duration = k_end.time - k_start.time
                    progress = (time_in_pattern - k_start.time) / duration if duration > 0 else 1.0
                    color = [lerp(s, e, progress) for s, e in zip(k_start.color, k_end.color, strict=False)]
                    break

        for led_id in self.led_ids:
            states[f"LED{led_id}"] = color
        return states


class SimplePattern(Pattern):
    """A simple pattern for lighting all LEDs at once or sequentially."""

    def __init__(self, num_leds: int, color: Color, fade_s: float, sequence: str) -> None:
        super().__init__(list(range(1, num_leds + 1)), 0.0, float("inf"))
        self.color = color
        self.fade_s = fade_s
        self.sequence = sequence

    def update(self, elapsed_s: float) -> dict[str, list[int]]:
        states = {}
        for led_id in self.led_ids:
            start_time = 0.0 if self.sequence == "all_at_once" else (led_id - 1) * self.fade_s

            if elapsed_s >= start_time:
                progress = (elapsed_s - start_time) / self.fade_s if self.fade_s > 0 else 1.0
                progress = min(1.0, progress)
                final_color = [lerp(0, c, progress) for c in self.color]
                states[f"LED{led_id}"] = final_color
        return states
