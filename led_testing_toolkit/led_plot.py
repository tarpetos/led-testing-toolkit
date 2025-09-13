from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


class LEDPlot:
    """Class for creating and managing LED data plots using matplotlib."""

    def __init__(self, width: int = 10, height: int = 5, dpi: int = 200) -> None:
        self.plt = plt
        self.fig, self.ax = self.plt.subplots(figsize=(width, height), dpi=dpi)

    def create(  # noqa: PLR0913
        self,
        x: list[float],
        y: list[float],
        title: str = "",
        label: str = "",
        x_label: str = "",
        y_label: str = "",
        *,
        show_points: bool = True,
        line_style: str = "--",
        points_only: bool = False,
        color: str = "blue",
        bg_color: str = "white",
    ) -> None:
        """
        Create a plot with specified data and styling options.

        :param x: x-axis data points
        :param y: y-axis data points
        :param title: plot title
        :param label: legend label
        :param x_label: x-axis label
        :param y_label: y-axis label
        :param show_points: whether to show data points
        :param line_style: style of connecting lines
        :param points_only: if True, show only points without lines
        :param color: color of points and lines
        :param bg_color: plot background color
        """
        self.ax.plot(
            x,
            y,
            ("o" if points_only else f"o{line_style}") if show_points else "",
            color=color,
            label=label,
        )
        self.ax.set_title(title)
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        self.ax.set_facecolor(bg_color)
        self.fig.tight_layout()
        self.ax.grid(True)

    def produce(self, **kwargs) -> Path | None:
        """
        Process the plot by showing and/or saving it.

        :param kwargs: dictionary containing 'show_plot' and 'save_path' options
        """
        kwargs.get("show_plot", True) and self.show()

        img_path: Path | None = None
        if path := kwargs.get("save_path"):
            img_path = self.save(path)

        self.plt.close(self.fig)
        return img_path

    def show(self) -> None:
        """Display the plot using matplotlib's show method."""
        self.plt.show()

    def _recursive_name_search(self, path: Path, name: str, suffix: str, start_at: int = 1) -> Path:
        """
        Recursively search for available file name by incrementing number suffix.

        :param path: initial file path
        :param name: base file name
        :param suffix: file extension
        :param start_at: starting number for suffix
        :return: available file path
        """
        if path.exists():
            file_path = Path(path.parent, f"{name}{start_at}").with_suffix(suffix)
            path = self._recursive_name_search(file_path, name, suffix, start_at + 1)
        return path

    def save(self, path: Path) -> Path:
        """
        Save the plot to a file with automatic name conflict resolution.

        :param path: target file path for saving the plot
        """
        suffix = path.suffix
        abs_path = path.absolute()
        if suffix == "":
            suffix = ".png"
            abs_path = Path(f"{str(abs_path).rstrip('.')}").with_suffix(suffix)

        abs_path = self._recursive_name_search(abs_path, abs_path.stem, suffix)

        Path.mkdir(abs_path.parent, parents=True, exist_ok=True)
        self.fig.savefig(abs_path)
        return abs_path
