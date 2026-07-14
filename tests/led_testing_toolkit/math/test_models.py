import pytest
from led_testing_toolkit.math.models import Point, Record, Dataset

def test_point():
    p = Point(x=1, y=2)
    assert p.x == 1
    assert p.y == 2
    assert p.z == 0.0

def test_record():
    r = Record(coordinates=[Point(x=1, y=2)])
    assert len(r.coordinates) == 1
    assert r.coordinates[0].x == 1

def test_dataset():
    r = Record(coordinates=[Point(x=1, y=2)])
    d = Dataset(records=[r])
    assert len(d.records) == 1
    assert d.records[0].coordinates[0].x == 1
