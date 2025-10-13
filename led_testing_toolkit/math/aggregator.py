from __future__ import annotations

import asyncio
import base64
import io
from itertools import cycle
from pathlib import Path
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
    def __init__(self, dataset: Dataset, interpolator: Interpolator) -> None:
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

            task = self._interpolator.interpolate(
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

    def _aggregate_sync(self) -> None:  # noqa: C901
        if not self._interpolated:
            return

        longest_x = max(self._interpolated, key=lambda item: len(item[0]))[0]
        num_points = len(longest_x)
        y_matrix = np.full((len(self._interpolated), num_points), np.nan)

        for i, (x, y) in enumerate(self._interpolated):
            y_matrix[i, :] = np.interp(longest_x, x, y, left=np.nan, right=np.nan)

        cliff_start_indices = []
        cliffs = []

        for i in range(y_matrix.shape[0]):
            signal = y_matrix[i, :]
            valid_signal = signal[~np.isnan(signal)]
            if len(valid_signal) < 10:
                continue

            plateau_start, plateau_end = int(0.25 * num_points), int(0.75 * num_points)
            plateau_level = np.nanmedian(signal[plateau_start:plateau_end])

            if np.isnan(plateau_level):
                continue

            threshold = 0.9 * plateau_level
            cliff_idx = -1
            for j in range(num_points - 2, plateau_end, -1):
                if not np.isnan(signal[j]) and signal[j] > threshold:
                    cliff_idx = j + 1
                    break

            if cliff_idx != -1 and cliff_idx < num_points:
                cliff_start_indices.append(cliff_idx)
                cliffs.append(signal[cliff_idx:])

        if not cliffs:
            aggregated_y = np.nanmean(y_matrix, axis=0)
            self._etalon = {"x": longest_x, "y": aggregated_y}
            return

        max_cliff_len = max(len(c) for c in cliffs)
        padded_cliffs = np.full((len(cliffs), max_cliff_len), np.nan)
        for i, c in enumerate(cliffs):
            padded_cliffs[i, : len(c)] = c

        averaged_cliff_list = []
        for col_idx in range(padded_cliffs.shape[1]):
            column = padded_cliffs[:, col_idx]
            if np.all(np.isnan(column)):
                break
            averaged_cliff_list.append(np.nanmean(column))
        averaged_cliff = np.array(averaged_cliff_list)

        avg_cliff_start_index = int(np.mean(cliff_start_indices))
        plateau_part = np.nanmean(y_matrix[:, :avg_cliff_start_index], axis=0)

        final_y_combined = np.concatenate((plateau_part, averaged_cliff))

        final_y = final_y_combined[:num_points]
        final_x = longest_x[: len(final_y)]

        self._etalon = {"x": final_x, "y": final_y}

    async def start(self) -> None:
        await self._interpolate()
        await self._aggregate()

    def get_plots_base64(self, **kwargs) -> str:
        if not self.etalon.coordinates:
            raise ValueError("Etalon is not available! Run start() method first.")

        fig, ax = plt.subplots(1, 1, figsize=kwargs.get("figsize", (12, 6)))
        fig.suptitle(kwargs.get("title", "Aggregated data"), fontsize=16)

        colors = self.get_plot_colors()
        for x, y in self._interpolated:
            ax.plot(x, y, color=next(colors), alpha=0.5, linewidth=1)

        x_etalon = [p.x for p in self.etalon.coordinates]
        y_etalon = [p.y for p in self.etalon.coordinates]

        ax.plot(x_etalon, y_etalon, color="black", linewidth=2, label="Etalon")
        ax.set_title("Time domain")
        ax.set_xlabel(kwargs.get("xlabel", "Time (s)"))
        ax.set_ylabel(kwargs.get("ylabel", "Color (0-255)"))
        ax.legend(loc="upper right")
        ax.grid(True)

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def build_plots(self, **kwargs) -> Path:
        plt.figure(figsize=(10, 6))
        colors = self.get_plot_colors()

        for x, y in self._interpolated:
            plt.plot(x, y, color=next(colors), alpha=0.6)

        if (
            self._etalon
            and "x" in self._etalon
            and "y" in self._etalon
            and len(self._etalon["x"]) > 0
            and len(self._etalon["y"]) > 0
        ):
            plt.plot(self._etalon["x"], self._etalon["y"], color="black")

        plt.title(kwargs.get("title", "Interpolated measurements with etalon (black on top)"))
        plt.xlabel(kwargs.get("xlabel", "X"))
        plt.ylabel(kwargs.get("ylabel", "Y"))
        plt.ylim(self._interpolator.lower_bound - 5, self._interpolator.upper_bound + 5)
        plt.grid(True)
        plt.tight_layout()

        save_path = Path(kwargs.get("save_path"))
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path) if save_path else plt.show()
        plt.close()
        return save_path

    @staticmethod
    def get_plot_colors() -> cycle:
        cmaps = [mpl.colormaps.get_cmap(name) for name in ["tab10", "Set3", "Paired"]]
        num_colors_per_cmap = 7
        hex_colors = []

        for cmap in cmaps:
            hex_colors.extend([rgb2hex(cmap(i / cmap.N)) for i in range(num_colors_per_cmap)])

        return cycle(hex_colors)
