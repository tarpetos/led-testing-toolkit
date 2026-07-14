from __future__ import annotations

from pydantic import BaseModel


class Point(BaseModel):
    """
    A point in 3D space with x, y, and optional z coordinates.

    Attributes:
        x (float | int): The x-coordinate.
        y (float | int): The y-coordinate.
        z (float | int): The z-coordinate (default is 0.0).

    """

    x: float | int
    y: float | int
    z: float | int = 0.0


class Record(BaseModel):
    """
    A sequence of points representing a continuous measurement or signal.

    Attributes:
        coordinates (list[Point]): A list of points that make up the record.

    """

    coordinates: list[Point] = []


class Dataset(BaseModel):
    """
    A collection of records.

    Attributes:
        records (list[Record]): A list of recorded signals or measurements.

    """

    records: list[Record] = []
