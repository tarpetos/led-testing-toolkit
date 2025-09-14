from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from numpy import ndarray

from .models import Point, Record

if TYPE_CHECKING:
    from pathlib import Path

    from .interpolator import Interpolator


class Comparator:
    def __init__(self, etalon: Record, measured: Record, interpolator: Interpolator) -> None:
        self._etalon = etalon
        self._measured = measured
        self._interpolator = interpolator
        self._aligned_data: dict[str, Record] = {}
        self._accuracy = 0.0

    async def _align_measured_with_etalons(self) -> None:
        etalon_times = np.array([point.x for point in self._etalon.coordinates], dtype=float)
        etalon_y = np.array([point.y for point in self._etalon.coordinates], dtype=float)

        x_new_relative, y_measured = await self._interpolator.interpolate_linear(
            self._measured.coordinates,
            num_points=len(self._measured.coordinates),
            x_max=np.max(etalon_times),
        )

        await asyncio.to_thread(
            self._align_data_sync,
            etalon_times,
            etalon_y,
            x_new_relative,
            y_measured,
        )

    def _align_data_sync(
        self,
        etalon_times: ndarray,
        etalon_y: ndarray,
        x_new_relative: ndarray,
        y_measured: ndarray,
    ) -> None:
        y_measured_aligned = np.interp(etalon_times, x_new_relative, y_measured, left=np.nan, right=np.nan)
        etalon_points = [Point(x=x, y=y) for x, y in zip(etalon_times, etalon_y, strict=False)]
        measured_points = [Point(x=x, y=y) for x, y in zip(etalon_times, y_measured_aligned, strict=False)]
        self._aligned_data = {
            "etalon": Record(coordinates=etalon_points),
            "measured": Record(coordinates=measured_points),
        }

    async def _compare(self) -> float:
        etalon_y = np.array([point.y for point in self._aligned_data["etalon"].coordinates], dtype=float)
        measured_y = np.array([point.y for point in self._aligned_data["measured"].coordinates], dtype=float)

        self._accuracy = await asyncio.to_thread(
            self._compare_sync,
            etalon_y,
            measured_y,
        )
        return self._accuracy

    def _compare_sync(self, etalon_y: ndarray, measured_y: ndarray) -> float:
        mae_accuracy = self._calculate_mae_accuracy(etalon_y=etalon_y, measured_y=measured_y)
        point_count_accuracy = self._calculate_point_count_accuracy()
        return (mae_accuracy * 0.9) + (point_count_accuracy * 0.1)

    def _calculate_mae_accuracy(self, etalon_y: ndarray, measured_y: ndarray) -> float:
        differences = np.abs(etalon_y - measured_y)
        valid_diffs = differences[~np.isnan(differences)]
        if len(valid_diffs) == 0:
            return 0.0
        mae = np.mean(valid_diffs)
        accuracy = 100 * (1 - mae / self._interpolator.upper_bound)
        return max(0.0, accuracy)

    def _calculate_point_count_accuracy(self) -> float:
        etalon_count = len(self._etalon.coordinates)
        measured_count = len(self._measured.coordinates)
        if etalon_count == 0 or measured_count == 0:
            return 0.0
        relative_error = abs(measured_count - etalon_count) / max(etalon_count, measured_count)
        return max(0.0, 100 * (1 - relative_error))

    async def start(self) -> float:
        await self._align_measured_with_etalons()
        return await self._compare()

    def build_plots(self, **kwargs) -> Path | None:
        if not self._aligned_data:
            raise ValueError("Aligned data is not available! Run start() method first.")

        etalon_x = np.array([point.x for point in self._aligned_data["etalon"].coordinates])
        etalon_y = np.array([point.y for point in self._aligned_data["etalon"].coordinates])
        measured_x = np.array([point.x for point in self._aligned_data["measured"].coordinates])
        measured_y = np.array([point.y for point in self._aligned_data["measured"].coordinates])

        plt.figure(figsize=kwargs.get("figsize", (10, 6)))

        plt.plot(
            etalon_x,
            etalon_y,
            label=kwargs.get("etalon_label", "Etalon"),
            color=kwargs.get("etalon_color", "blue"),
            linewidth=2,
        )
        plt.plot(
            measured_x,
            measured_y,
            label=kwargs.get("measured_label", "Measured"),
            color=kwargs.get("measured_color", "orange"),
            linestyle="--",
            linewidth=2,
        )

        plt.title(kwargs.get("title", f"Etalon vs measured (similarity: {self._accuracy:.2f}%)"))
        plt.xlabel(kwargs.get("xlabel", "X"))
        plt.ylabel(kwargs.get("ylabel", "Y"))
        plt.legend()
        plt.ylim(self._interpolator.lower_bound - 5, self._interpolator.upper_bound + 5)
        plt.grid(True)

        save_path = kwargs.get("save_path")
        plt.savefig(save_path) if save_path else plt.show()
        return save_path
