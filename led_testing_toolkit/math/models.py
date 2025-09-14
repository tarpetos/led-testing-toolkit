from __future__ import annotations

from pydantic import BaseModel


class Point(BaseModel):
    x: float | int
    y: float | int


class Record(BaseModel):
    coordinates: list[Point] = []


class Dataset(BaseModel):
    records: list[Record] = []
