from led_testing_toolkit.led_modeler.utils import configure_logger, lerp, add_colors
import pytest
from pathlib import Path


def test_configure_logger(tmp_path: Path):
    log_file = tmp_path / "test.log"
    logger = configure_logger(str(log_file), "test_source")
    assert logger is not None
    # could also test if it writes something if needed


def test_lerp():
    assert lerp(0, 100, 0.5) == 50
    assert lerp(10, 20, 0) == 10
    assert lerp(10, 20, 1) == 20


def test_add_colors():
    assert add_colors([100, 150, 200], [50, 50, 50]) == [150, 200, 250]
    assert add_colors([200, 200, 200], [100, 100, 100]) == [255, 255, 255]
    assert add_colors([0, 0, 0], [0, 0, 0]) == [0, 0, 0]
