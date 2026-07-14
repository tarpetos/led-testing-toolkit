from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Final

import numpy as np
from numpy import ndarray

if TYPE_CHECKING:
    from led_testing_toolkit.math.models import Point


class Interpolator:
    """
    Class to interpolate signals to a standard format.

    Attributes:
        lower_bound (int): The lower bound for interpolated values.
        upper_bound (int): The upper bound for interpolated values.

    """

    DEFAULT_LOWER_BOUND: Final[int] = 0
    DEFAULT_UPPER_BOUND: Final[int] = 100

    MIN_INTERPOLATION_POINTS: Final[int] = 2
    SHAPE: Final[int] = 2

    def __init__(self, *, lower_bound: int = DEFAULT_LOWER_BOUND, upper_bound: int = DEFAULT_UPPER_BOUND) -> None:
        """
        Initializes the Interpolator.

        Args:
            lower_bound (int): The lowest allowed value for interpolation clipping. Defaults to 0.
            upper_bound (int): The highest allowed value for interpolation clipping. Defaults to 100.

        """
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    async def interpolate(
        self,
        coordinates: list[Point],
        *,
        num_points: int,
        x_max: float | None = None,
    ) -> tuple[ndarray, ndarray]:
        """
        Asynchronously interpolates a list of points.

        Args:
            coordinates (list[Point]): List of points to interpolate.
            num_points (int): The number of points to interpolate to.
            x_max (float | None): The maximum x value for interpolation. Defaults to None.

        Returns:
            tuple[ndarray, ndarray]: A tuple of relative x values and interpolated y values.

        Raises:
            ValueError: If `num_points` is less than `MIN_INTERPOLATION_POINTS`.

        """
        if num_points < self.MIN_INTERPOLATION_POINTS:
            raise ValueError(f"Number of interpolation points must be at least {self.MIN_INTERPOLATION_POINTS}!")

        return await asyncio.to_thread(self._interpolate_sync, coordinates, num_points, x_max)

    def _interpolate_sync(
        self,
        coordinates: list[Point],
        num_points: int,
        x_max: float | None = None,
    ) -> tuple[ndarray, ndarray]:
        """
        Synchronously interpolates a list of points.

        Args:
            coordinates (list[Point]): List of points to interpolate.
            num_points (int): The number of points to interpolate to.
            x_max (float | None): The maximum x value for interpolation. Defaults to None.

        Returns:
            tuple[ndarray, ndarray]: A tuple of relative x values and interpolated y values.

        Raises:
            ValueError: If coordinates array is not of expected shape (n, 2).

        """
        if not coordinates:
            return np.array([]), np.array([])

        coords = np.array([[point.x, point.y] for point in coordinates], dtype=float)

        if coords.ndim != self.SHAPE or coords.shape[1] != self.SHAPE:
            raise ValueError("Input must be a list or array of [x, y] coordinates with shape (n, 2)!")

        x, y = coords[:, 0], coords[:, 1].copy()

        if len(y) > 3:
            y_orig = y.copy()
            signal_range = np.nanmax(y_orig) - np.nanmin(y_orig)

            if signal_range > 1e-6:
                dynamic_threshold = signal_range * 0.35
                for i in range(1, len(y) - 1):
                    prev_val, curr_val, next_val = y_orig[i - 1], y_orig[i], y_orig[i + 1]
                    local_median = np.median([prev_val, next_val])

                    if abs(curr_val - local_median) > dynamic_threshold:
                        y[i] = local_median

        interp_x_max = x_max if x_max is not None else x[-1]
        x_new = np.linspace(x[0], interp_x_max, num_points)
        y_new = np.interp(x_new, x, y)

        y_new = np.clip(y_new, a_min=self.lower_bound, a_max=self.upper_bound)
        x_new_relative = x_new - x_new[0] if len(x_new) > 0 else np.array([])

        return x_new_relative, y_new
