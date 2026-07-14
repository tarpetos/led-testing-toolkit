import pytest
from led_testing_toolkit.led_types import (
    LedRecordEntry,
    LedData,
    NormalizedLedData,
    EtalonDbFormat,
    ComparisonResults,
    ParsedPatterns,
    RawPattern,
    LedRgbData,
    LedSequence,
    Timestamps,
)


def test_imports():
    assert LedRecordEntry is not None
