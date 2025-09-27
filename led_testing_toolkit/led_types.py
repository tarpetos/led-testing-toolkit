from __future__ import annotations

from datetime import datetime
from pathlib import Path

from led_testing_toolkit.math.models import Record

LedRecordEntry = list[float | list[float | int]]

LedData = list[dict[str, list[LedRecordEntry]]] | dict[str, list[LedRecordEntry]]

NormalizedLedData = dict[str, dict[str, list[Record] | Record]]

EtalonDbFormat = dict[str, list[list[float]]]

ComparisonResults = dict[str, dict[str, dict[str, float | str]]]

ParsedPatterns = dict[Path, list[dict[str, dict[str, list[Record]]]]]

RawPattern = list[dict[str, str]]

LedRgbData = dict[str, dict[str, int]]

LedSequence = dict[str, list[dict]]

Timestamps = dict[str, list[datetime]]
