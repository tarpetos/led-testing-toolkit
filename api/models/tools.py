"""
Tool models for the API.

This module contains data models representing request payloads for various
tool endpoints, such as comparing patterns or generating etalons.
"""

from pydantic import BaseModel


class ComparePatternsRequest(BaseModel):
    """Request model for comparing a measured pattern against an etalon."""

    measured_collection: str
    measured_record: str
    etalon_device: str
    etalon_pattern: str


class CompareLogPatternRequest(BaseModel):
    """Request model for comparing a pattern parsed from a log against an etalon."""

    pattern_index: int
    etalon_device: str
    etalon_pattern: str


class GenerateEtalonsRequest(BaseModel):
    """Request model for generating etalon patterns."""

    device_name: str | None = None
    pattern_name: str | None = None
