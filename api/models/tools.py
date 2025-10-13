from pydantic import BaseModel


class ComparePatternsRequest(BaseModel):
    measured_collection: str
    measured_record: str
    etalon_device: str
    etalon_pattern: str


class CompareLogPatternRequest(BaseModel):
    pattern_index: int
    etalon_device: str
    etalon_pattern: str


class GenerateEtalonsRequest(BaseModel):
    device_name: str | None = None
    pattern_name: str | None = None
