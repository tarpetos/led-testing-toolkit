"""
Request models for the API.

This module contains data models representing incoming request payloads
for various API endpoints.
"""

from pydantic import BaseModel, Field


class SelectEtalonRequest(BaseModel):
    """Request model to select an etalon pattern."""

    pattern_name: str = Field(
        ...,
        description="The name of the etalon pattern to load",
    )


class SelectMeasuredRequest(BaseModel):
    """Request model to select a measured collection."""

    collection_name: str = Field(
        ...,
        description="The name of the measured collection to load a random record from",
    )


class SeekRequest(BaseModel):
    """Request model to seek the player to a specific time."""

    time: float = Field(..., ge=0, description="The time to seek to in seconds")


class SelectPatternRequest(BaseModel):
    """Request model to select a specific pattern index."""

    index: int
