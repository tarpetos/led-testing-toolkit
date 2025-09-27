from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Final

import numpy as np
from numpy import ndarray

if TYPE_CHECKING:
    from led_testing_toolkit.math.models import Point


class Interpolator:
    DEFAULT_LOWER_BOUND: Final[int] = 0
    DEFAULT_UPPER_BOUND: Final[int] = 100

    MIN_INTERPOLATION_POINTS: Final[int] = 2
    SHAPE: Final[int] = 2

    def __init__(self, *, lower_bound: int = DEFAULT_LOWER_BOUND, upper_bound: int = DEFAULT_UPPER_BOUND) -> None:
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    async def interpolate_linear(
        self,
        coordinates: list[Point],
        *,
        num_points: int,
        x_max: float | None = None,
    ) -> tuple[ndarray, ndarray]:
        if num_points < self.MIN_INTERPOLATION_POINTS:
            raise ValueError(f"Number of interpolation points must be at least {self.MIN_INTERPOLATION_POINTS}!")

        return await asyncio.to_thread(self._interpolate_linear_sync, coordinates, num_points, x_max)

    def _interpolate_linear_sync(
        self,
        coordinates: list[Point],
        num_points: int,
        x_max: float | None = None,
    ) -> tuple[ndarray, ndarray]:
        coords = np.array([[point.x, point.y] for point in coordinates], dtype=float)

        if coords.ndim != self.SHAPE or coords.shape[1] != self.SHAPE:
            raise ValueError("Input must be a list or array of [x, y] coordinates with shape (n, 2)!")

        x = coords[:, 0]
        y = coords[:, 1]

        max_x = x_max if x_max is not None else x.max()
        x_new = np.linspace(x.min(), max_x, num_points)
        y_new = np.interp(x_new, x, y)
        y_new = np.clip(y_new, a_min=self.lower_bound, a_max=self.upper_bound)

        x_new_relative = x_new - x_new.min()
        return x_new_relative, y_new
