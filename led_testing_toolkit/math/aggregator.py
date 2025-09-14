from __future__ import annotations

import asyncio
from itertools import cycle
from typing import TYPE_CHECKING

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import rgb2hex
from numpy import ndarray

from led_testing_toolkit.math.models import Dataset, Point, Record

if TYPE_CHECKING:
    from led_testing_toolkit.math.interpolator import Interpolator


class Aggregator:
    def __init__(
        self,
        dataset: Dataset,
        interpolator: Interpolator,
    ) -> None:
        self._records: list[Record] = dataset.records
        self._interpolator: Interpolator = interpolator
        self._interpolated: list[tuple[ndarray, ndarray]] = []
        self._etalon: dict[str, ndarray] = {}

    @property
    def etalon(self) -> Record:
        if self._etalon:
            points = [Point(x=x, y=y) for x, y in zip(self._etalon["x"], self._etalon["y"], strict=False)]
            return Record(coordinates=points)
        return Record()

    async def _interpolate(self) -> None:
        self._interpolated.clear()

        tasks = []
        for record in self._records:
            if not record.coordinates:
                continue

            task = self._interpolator.interpolate_linear(
                record.coordinates,
                num_points=len(record.coordinates),
            )
            tasks.append(task)

        if tasks:
            self._interpolated = await asyncio.gather(*tasks)

    async def _aggregate(self) -> None:
        if not self._interpolated:
            self._etalon = {}
            return

        await asyncio.to_thread(self._aggregate_sync)

    def _aggregate_sync(self) -> None:
        max_time = max(x_new_relative.max() for x_new_relative, _ in self._interpolated)
        num_points = max(len(x_new_relative) for x_new_relative, _ in self._interpolated)
        all_times = np.linspace(0, max_time, num_points)

        y_values = np.full((len(self._interpolated), num_points), np.nan)

        for i, (x_new_relative, y_new) in enumerate(self._interpolated):
            y_values[i] = np.interp(all_times, x_new_relative, y_new, left=np.nan, right=np.nan)

        aggregated_y = np.nanmean(y_values, axis=0)
        self._etalon = {"x": all_times, "y": aggregated_y}

    async def start(self) -> None:
        await self._interpolate()
        await self._aggregate()

    def build_plots(self, **kwargs) -> str | None:
        plt.figure(figsize=(10, 6))
        colors = self.get_plot_colors()

        for x, y in self._interpolated:
            plt.plot(x, y, color=next(colors), alpha=0.6)

        if self._etalon:
            plt.plot(self._etalon["x"], self._etalon["y"], color="black")

        plt.title(kwargs.get("title", "Interpolated measurements with etalon (black on top)"))
        plt.xlabel(kwargs.get("xlabel", "X"))
        plt.ylabel(kwargs.get("ylabel", "Y"))
        plt.ylim(self._interpolator.LOWER_BOUND, self._interpolator.UPPER_BOUND + 5)
        plt.grid(True)
        plt.tight_layout()

        save_path = kwargs.get("save_path")
        plt.savefig(save_path) if save_path else plt.show()
        return save_path

    @staticmethod
    def get_plot_colors() -> cycle:
        cmaps = [mpl.colormaps.get_cmap(name) for name in ["tab10", "Set3", "Paired"]]
        num_colors_per_cmap = 7
        hex_colors = []

        for cmap in cmaps:
            hex_colors.extend([rgb2hex(cmap(i / cmap.N)) for i in range(num_colors_per_cmap)])

        return cycle(hex_colors)
