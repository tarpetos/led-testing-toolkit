from __future__ import annotations

import asyncio
import base64
import io
import warnings
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from numpy import ndarray
from scipy.fft import fft, fftfreq

from led_testing_toolkit.math.models import Point, Record

if TYPE_CHECKING:
    from led_testing_toolkit.math.interpolator import Interpolator


class WeakSignalWarning(UserWarning):
    """Warning raised when the measured signal is too weak."""


class Comparator:
    """
    Compares measured signals against etalon signals.

    Attributes:
        _etalon (Record): The etalon record.
        _measured (Record): The measured record.
        _interpolator (Interpolator): The interpolator instance.
        _aligned_data (dict[str, Record]): Aligned etalon and measured records.
        _accuracy (float): The calculated accuracy.
        _is_weak (bool): Whether the measured signal is considered weak.
        _is_checked (bool): Whether the signal strength has been checked.

    """

    def __init__(self, etalon: Record, measured: Record, interpolator: Interpolator) -> None:
        """
        Initializes the Comparator.

        Args:
            etalon (Record): The reference (etalon) record.
            measured (Record): The measured record.
            interpolator (Interpolator): The interpolator to use for alignment.

        """
        self._etalon = etalon
        self._measured = measured
        self._interpolator = interpolator
        self._aligned_data: dict[str, Record] = {}
        self._accuracy = 0.0
        self._is_weak = False
        self._is_checked = False

    def _check_signal_strength(self) -> None:
        """Checks if the measured signal is weak."""
        if not self._measured.coordinates:
            self._is_weak = True
            self._is_checked = True
            return

        y_values = np.array([point.y for point in self._measured.coordinates])
        max_y = np.max(y_values)

        dynamic_range = self._interpolator.upper_bound - self._interpolator.lower_bound
        threshold = self._interpolator.lower_bound + 0.05 * dynamic_range

        if max_y < threshold:
            self._is_weak = True

        self._is_checked = True

    async def _align_measured_with_etalons(self) -> None:
        """Asynchronously aligns the measured data with the etalon data."""
        etalon_times = np.array([point.x for point in self._etalon.coordinates], dtype=float)
        etalon_y = np.array([point.y for point in self._etalon.coordinates], dtype=float)

        x_new_relative, y_measured = await self._interpolator.interpolate(
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
        """
        Synchronously aligns the data.

        Args:
            etalon_times (ndarray): Etalon time coordinates.
            etalon_y (ndarray): Etalon y coordinates.
            x_new_relative (ndarray): Relative new x coordinates.
            y_measured (ndarray): Measured y coordinates.

        """
        y_measured_aligned = np.interp(etalon_times, x_new_relative, y_measured, left=np.nan, right=np.nan)
        etalon_points = [Point(x=x, y=y) for x, y in zip(etalon_times, etalon_y, strict=False)]
        measured_points = [Point(x=x, y=y) for x, y in zip(etalon_times, y_measured_aligned, strict=False)]
        self._aligned_data = {
            "etalon": Record(coordinates=etalon_points),
            "measured": Record(coordinates=measured_points),
        }

    async def _compare(self) -> float:
        """
        Asynchronously compares the aligned data.

        Returns:
            float: The accuracy percentage.

        """
        etalon_y = np.array([point.y for point in self._aligned_data["etalon"].coordinates], dtype=float)
        measured_y = np.array([point.y for point in self._aligned_data["measured"].coordinates], dtype=float)

        self._accuracy = await asyncio.to_thread(
            self._compare_sync,
            etalon_y,
            measured_y,
        )
        return self._accuracy

    def _compare_sync(self, etalon_y: ndarray, measured_y: ndarray) -> float:
        """
        Synchronously compares the aligned data.

        Args:
            etalon_y (ndarray): Aligned etalon y values.
            measured_y (ndarray): Aligned measured y values.

        Returns:
            float: The combined accuracy percentage.

        """
        mae_accuracy = self._calculate_mae_accuracy(etalon_y=etalon_y, measured_y=measured_y)
        correlation_accuracy = self._calculate_correlation_accuracy(etalon_y=etalon_y, measured_y=measured_y)
        fft_accuracy = self._calculate_fft_accuracy(etalon_y=etalon_y, measured_y=measured_y)
        metrics = (mae_accuracy, correlation_accuracy, fft_accuracy)
        total_accuracy = sum(metrics) / len(metrics)
        return max(0.0, total_accuracy)

    def _calculate_mae_accuracy(self, etalon_y: ndarray, measured_y: ndarray) -> float:
        """
        Calculates accuracy based on Mean Absolute Error.

        Args:
            etalon_y (ndarray): Aligned etalon y values.
            measured_y (ndarray): Aligned measured y values.

        Returns:
            float: Accuracy percentage based on MAE.

        """
        valid_indices = ~np.isnan(measured_y)
        if not np.any(valid_indices):
            return 0.0

        differences = np.abs(etalon_y[valid_indices] - measured_y[valid_indices])
        mae = np.mean(differences)
        accuracy = 100 * (1 - mae / self._interpolator.upper_bound)
        return max(0.0, accuracy)

    def _calculate_correlation_accuracy(self, etalon_y: ndarray, measured_y: ndarray) -> float:
        """
        Calculates accuracy based on correlation.

        Args:
            etalon_y (ndarray): Aligned etalon y values.
            measured_y (ndarray): Aligned measured y values.

        Returns:
            float: Accuracy percentage based on correlation.

        """
        valid_indices = ~np.isnan(measured_y)
        if np.sum(valid_indices) < 2:
            return 0.0

        y1 = etalon_y[valid_indices]
        y2 = measured_y[valid_indices]

        correlation_matrix = np.corrcoef(y1, y2)
        correlation = correlation_matrix[0, 1]
        return max(0.0, correlation) * 100

    def _calculate_fft_accuracy(self, etalon_y: ndarray, measured_y: ndarray) -> float:
        """
        Calculates accuracy based on FFT magnitude differences.

        Args:
            etalon_y (ndarray): Aligned etalon y values.
            measured_y (ndarray): Aligned measured y values.

        Returns:
            float: Accuracy percentage based on FFT magnitude.

        """
        valid_indices = ~np.isnan(measured_y)
        if not np.any(valid_indices):
            return 0.0

        y1 = etalon_y[valid_indices]
        y2 = measured_y[valid_indices]

        _, mag1 = self._calculate_fft(y1)
        _, mag2 = self._calculate_fft(y2)

        mag1_normalized = mag1 / mag1.max() if mag1.max() > 0 else mag1

        mag2_normalized = mag2 / mag2.max() if mag2.max() > 0 else mag2

        mse = np.mean((mag1_normalized - mag2_normalized) ** 2)
        accuracy = 100 * (1 - mse)
        return max(0.0, accuracy)

    @staticmethod
    def _calculate_fft(y: ndarray) -> tuple[ndarray, ndarray]:
        """
        Calculates FFT and returns frequencies and magnitudes.

        Args:
            y (ndarray): The signal data.

        Returns:
            tuple[ndarray, ndarray]: Frequencies and magnitudes.

        """
        n = len(y)
        if n == 0:
            return np.array([]), np.array([])
        yf = fft(y)
        xf = fftfreq(n, 1)[: n // 2]
        magnitude = 2.0 / n * np.abs(yf[0 : n // 2])
        return xf, magnitude

    async def start(self) -> float:
        """
        Starts the comparison process.

        Returns:
            float: The accuracy percentage, or -1.0 if the signal is too weak.

        """
        if not self._is_checked:
            await asyncio.to_thread(self._check_signal_strength)

        if self._is_weak:
            warnings.warn("Measured signal is too weak! Comparison ignored.", WeakSignalWarning, stacklevel=2)
            return -1.0

        await self._align_measured_with_etalons()
        return await self._compare()

    def build_plots(self, **kwargs) -> str:
        """
        Builds plots comparing the signals.

        Args:
            **kwargs: Plotting options (figsize, title, etalon_label, etc.).

        Returns:
            str: Base64 encoded string of the plot image.

        Raises:
            ValueError: If aligned data is not available.

        """
        if not self._is_checked:
            self._check_signal_strength()

        if self._is_weak:
            warnings.warn("Measured signal is too weak! Plotting ignored.", WeakSignalWarning, stacklevel=2)
            return ""

        if not self._aligned_data:
            raise ValueError("Aligned data is not available! Run start() method first!")

        etalon_x = np.array([point.x for point in self._aligned_data["etalon"].coordinates])
        etalon_y = np.array([point.y for point in self._aligned_data["etalon"].coordinates])
        measured_y = np.array([point.y for point in self._aligned_data["measured"].coordinates])

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=kwargs.get("figsize", (12, 10)))
        fig.suptitle(kwargs.get("title", f"Etalon vs measured (similarity: {self._accuracy:.2f}%)"), fontsize=16)

        ax1.plot(
            etalon_x,
            etalon_y,
            label=kwargs.get("etalon_label", "Etalon"),
            color=kwargs.get("etalon_color", "blue"),
        )
        ax1.plot(
            etalon_x,
            measured_y,
            label=kwargs.get("measured_label", "Measured"),
            color=kwargs.get("measured_color", "orange"),
            linestyle="--",
        )
        ax1.set_title("Time domain comparison")
        ax1.set_xlabel(kwargs.get("xlabel", "X"))
        ax1.set_ylabel(kwargs.get("ylabel", "Y"))
        ax1.legend(loc="upper right")
        ax1.set_ylim(self._interpolator.lower_bound - 5, self._interpolator.upper_bound + 5)
        ax1.grid(True)

        valid_indices = ~np.isnan(measured_y)
        etalon_freq, etalon_mag = self._calculate_fft(etalon_y[valid_indices])
        measured_freq, measured_mag = self._calculate_fft(measured_y[valid_indices])

        ax2.plot(etalon_freq, etalon_mag, label="Etalon spectrum", color=kwargs.get("etalon_color", "blue"))
        ax2.plot(
            measured_freq,
            measured_mag,
            label="Measured spectrum",
            color=kwargs.get("measured_color", "orange"),
            linestyle="--",
        )
        ax2.set_title("Frequency spectrum comparison")
        ax2.set_xlabel("Frequency")
        ax2.set_ylabel("Magnitude")
        ax2.legend(loc="upper right")
        ax2.grid(True)

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        return base64.b64encode(buf.getvalue()).decode("utf-8")
