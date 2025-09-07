import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_time_sleep():
    with patch("time.sleep", autospec=True) as mock_sleep:
        yield mock_sleep


@pytest.fixture(autouse=True)
def mock_logger():
    with patch("loguru.logger", autospec=True) as mock_log:
        yield mock_log
