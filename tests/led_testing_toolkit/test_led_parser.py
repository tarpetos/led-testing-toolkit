import pytest
import re
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

from led_testing_toolkit.led_parser import LedParser


@pytest.fixture
def parser():
    return LedParser()


def test_patterns_property(parser):
    assert parser.patterns == {}


@pytest.mark.anyio
async def test_create_temp_log_file(parser, tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("dummy content")
    temp_file = await parser._create_temp_log_file(log_file)
    assert temp_file is not None
    assert Path(temp_file.name).exists()
    temp_file.close()


@pytest.mark.anyio
async def test_create_temp_log_file_not_found(parser):
    with pytest.raises(FileNotFoundError):
        await parser._create_temp_log_file(Path("nonexistent.log"))


@pytest.mark.anyio
async def test_create_temp_log_file_exception(parser, tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("dummy")
    with patch("aiofiles.open", side_effect=Exception("mocked error")):
        with pytest.raises(Exception):
            await parser._create_temp_log_file(log_file)


@pytest.mark.anyio
async def test_read_temp_log_file(parser):
    content = """2023-01-01T12:00:00 INFO LED1=[255,0,0]
    
malformed
2023-01-01T12:00:01 INFO LED2=[0,255,0]
2023-01-01T12:00:02 INFO OTHER_MESSAGE"""

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".log", delete=False) as f:
        f.write(content)
        f.flush()
        f_name = f.name

    class DummyFile:
        name = f_name

    result = await parser._read_temp_log_file(DummyFile())

    assert len(result) == 1
    assert "2023-01-01T12:00:00" in result[0]
    assert "2023-01-01T12:00:01" in result[0]


@pytest.mark.anyio
async def test_retrieve_patterns(parser, tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("2023-01-01T12:00:00 INFO LED1=[255,0,0]")

    result = await parser._retrieve_patterns(log_file)
    assert len(result) == 1


@pytest.mark.anyio
async def test_retrieve_patterns_not_found(parser):
    result = await parser._retrieve_patterns(Path("nonexistent.log"))
    assert result == []


@pytest.mark.anyio
async def test_retrieve_patterns_exception(parser, tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("dummy")
    with patch("led_testing_toolkit.led_parser.LedParser._create_temp_log_file", side_effect=Exception("mocked error")):
        result = await parser._retrieve_patterns(log_file)
        assert result == []


def test_extract_led_data(parser):
    res = parser._extract_led_data("LED1=[255,0,0] LED2=[0,255,0]")
    assert res == {"LED1": {"r": 255, "g": 0, "b": 0}, "LED2": {"r": 0, "g": 255, "b": 0}}

    res = parser._extract_led_data("NO LEDS HERE")
    assert res is None

    res = parser._extract_led_data("LED1=[255,0,0] LED1=[0,255,0]")
    assert res == {"LED1": {"r": 255, "g": 0, "b": 0}}


def test_convert_to_mathematical_model(parser):
    res = parser._convert_to_mathematical_model({}, {})
    assert res == {}

    res = parser._convert_to_mathematical_model({"LED1": []}, {"LED1": []})
    assert res == {}

    d1 = datetime(2023, 1, 1, 12, 0, 0)
    d2 = datetime(2023, 1, 1, 12, 0, 1)

    led_data = {"LED1": [{"r": 255, "g": 0, "b": 0}, {"r": 0, "g": 255, "b": 0}]}
    timestamps = {"LED1": [d1, d2]}

    res = parser._convert_to_mathematical_model(led_data, timestamps)
    assert "LED1" in res
    assert len(res["LED1"]["r"][0].coordinates) == 2
    assert res["LED1"]["r"][0].coordinates[0].x == 0.0
    assert res["LED1"]["r"][0].coordinates[1].x == 1.0


@pytest.mark.anyio
async def test_parse_log_file(parser, tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("2023-01-01T12:00:00 INFO LED1=[255,0,0]\n2023-01-01T12:00:01 INFO LED1=[0,255,0]")

    await parser.parse_log_file(log_file)
    assert log_file in parser.patterns
    assert len(parser.patterns[log_file]) == 1

    parser.clear()
    await parser.parse_log_file(log_file, ignore_before_date=datetime(2023, 1, 1, 12, 0, 1))
    assert len(parser.patterns[log_file][0]["LED1"]["r"][0].coordinates) == 1

    parser.clear()
    empty_log = tmp_path / "empty.log"
    empty_log.write_text("")
    await parser.parse_log_file(empty_log)
    assert empty_log not in parser.patterns

    log_file2 = tmp_path / "test2.log"
    log_file2.write_text("2023-01-01T12:00:00 INFO NO_LED\n2023-01-01T12:00:01 INFO LED1=[0,255,0]")
    await parser.parse_log_file(log_file2)
    assert log_file2 in parser.patterns

    # Pattern skip test due to empty model
    log_file3 = tmp_path / "test3.log"
    log_file3.write_text("2023-01-01T12:00:00 INFO OTHER\n")
    await parser.parse_log_file(log_file3)
    # The dictionary won't be modified because raw_patterns has no valid LED data
    # Wait, if there are raw patterns but no led data
    log_file4 = tmp_path / "test4.log"
    log_file4.write_text("2023-01-01T12:00:00 INFO LED_BUT_NOT_MATCHED\n")
    await parser.parse_log_file(log_file4)


@pytest.mark.anyio
async def test_parse_patterns(tmp_path):
    log_file1 = tmp_path / "test1.log"
    log_file2 = tmp_path / "test2.log"
    log_file1.write_text("2023-01-01T12:00:00 INFO LED1=[255,0,0]")
    log_file2.write_text("2023-01-01T12:00:00 INFO LED2=[0,255,0]")

    parser = LedParser(log_file1, log_file2)
    await parser.parse_patterns()
    assert log_file1 in parser.patterns
    assert log_file2 in parser.patterns


def test_clear(parser):
    parser._parsed_patterns[Path("dummy")] = []
    parser.clear()
    assert parser.patterns == {}


def test_get_date_diff(parser):
    d1 = datetime(2023, 1, 1, 12, 0, 0)
    d2 = datetime(2023, 1, 1, 12, 0, 5)
    assert parser.get_date_diff(d1, d2) == 5.0
