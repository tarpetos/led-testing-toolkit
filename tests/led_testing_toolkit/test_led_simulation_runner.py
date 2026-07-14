import pytest
import sys
from argparse import Namespace
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import loguru
import numpy as np

from led_testing_toolkit.led_simulation_runner import ReplayPattern, SimulationRunner
from led_testing_toolkit.math.models import Point, Record
from led_testing_toolkit.led_types import NormalizedLedData
from led_testing_toolkit.utils.collection_name import ETALONS_COLLECTION_SUFFIX

def create_sample_pattern_data():
    return {
        "LED1": {
            "r": [Record(coordinates=[Point(x=1.0, y=0.0, z=1.0), Point(x=2.0, y=255.0, z=2.0)])],
            "g": [Record(coordinates=[Point(x=1.0, y=10.0, z=1.0)])],
            "b": [Record(coordinates=[Point(x=1.0, y=20.0, z=1.0)])]
        }
    }

def test_replay_pattern_init():
    pattern_data = create_sample_pattern_data()
    pattern = ReplayPattern(pattern_data)
    assert pattern.start_time == 0.0
    assert pattern.end_time == 2.0

def test_replay_pattern_init_empty():
    with pytest.raises(ValueError):
        ReplayPattern({})

def test_replay_pattern_update():
    pattern_data = create_sample_pattern_data()
    pattern = ReplayPattern(pattern_data)
    
    # Before start
    res = pattern.update(-1.0)
    assert res == {}
    
    # During
    res = pattern.update(1.5)
    assert "LED1" in res
    assert res["LED1"]["color"][0] > 0 # r
    assert res["LED1"]["color"][1] == 10   # g
    assert res["LED1"]["color"][2] == 20   # b
    assert isinstance(res["LED1"]["rel_time"], float)
    
    # Invalid LED
    if isinstance(pattern.led_names, set):
        pattern.led_names.add("LED_INVALID")
    else:
        pattern.led_names.append("LED_INVALID")
    res = pattern.update(0.5)
    assert "LED_INVALID" in res
    assert res["LED_INVALID"]["color"] == [0, 0, 0]
    
def test_simulation_runner_init():
    args = Namespace(source_type="log", filepath=Path("test.log"))
    runner = SimulationRunner(args, loguru.logger)
    assert runner.args == args

def test_convert_db_doc_to_normalized_data():
    runner = SimulationRunner(Namespace(), loguru.logger)
    doc = {
        "LED1": [
            [0.0, [255, 0, 0], 1.0],
            [1.0, [0, 255, 0], 2.0],
            "malformed_point",
            [0.0, 0.0, 1.0] # missing one dim
        ],
        "LED2": "invalid",
        "LED3": [
            "invalid_point"
        ],
        "LED4": [
            [None, [0,0,0], None]
        ],
        "LED5": [
            [1.0, [255, 0, 0], 1.0],
            ["string_rel", [0, 255, 0], "string_abs"] # triggers TypeError in min()
        ],
        "LED_INF": [
            [float("inf"), [0, 0, 0], 4.0] # triggers min_rel_time_for_led == float("inf")
        ],
        "LED6": [
            [0.0, [255, 0], 1.0] # triggers ValueError in unpacking
        ],
        "LED_NO_VALID_ABS": [
            [1.0, [0,0,0], None]
        ]
    }
    
    res = runner._convert_db_doc_to_normalized_data(doc)
    assert "LED1" in res
    assert len(res["LED1"]["r"][0].coordinates) == 2
    assert "LED3" in res
    assert len(res["LED3"]["r"][0].coordinates) == 0

    # another run for first_abs_time == float("inf")
    doc2 = {"LED1": [[1.0, [255,0,0], None]]}
    res2 = runner._convert_db_doc_to_normalized_data(doc2)
    assert "LED1" in res2

def test_adapt_parser_data_for_replay():
    runner = SimulationRunner(Namespace(), loguru.logger)
    pattern_data = create_sample_pattern_data()
    # Change first abs time to test adaptation
    pattern_data["LED1"]["r"][0].coordinates[0].z = None
    pattern_data["LED1"]["r"][0].coordinates[1].z = None
    
    res = runner._adapt_parser_data_for_replay(pattern_data)
    assert "LED1" in res
    assert res["LED1"]["r"][0].coordinates[0].z == -1.0 # 0.0 - 1.0 since g and b have z=1.0

def test_adapt_parser_data_exceptions():
    runner = SimulationRunner(Namespace(), loguru.logger)
    pattern_data = create_sample_pattern_data()
    
    # Bypass Pydantic to trigger TypeError in min() for z
    pattern_data["LED1"]["r"][0].coordinates[0].__dict__["z"] = "str_z"
    # Bypass Pydantic to trigger TypeError in min() for x
    pattern_data["LED1"]["r"][0].coordinates[0].__dict__["x"] = "str_x"
    
    # For g and b, make them empty to trigger inf checks
    pattern_data["LED1"]["g"][0].coordinates[0].z = None
    pattern_data["LED1"]["g"][0].coordinates[0].x = None
    pattern_data["LED1"]["b"][0].coordinates[0].z = None
    pattern_data["LED1"]["b"][0].coordinates[0].x = None
    
    with pytest.raises(TypeError):
        runner._adapt_parser_data_for_replay(pattern_data)

def test_adapt_parser_data_inf():
    runner = SimulationRunner(Namespace(), loguru.logger)
    pattern_data = create_sample_pattern_data()
    for c in ["r", "g", "b"]:
        for p in pattern_data["LED1"][c][0].coordinates:
            p.x = None
            p.z = None
            
    res = runner._adapt_parser_data_for_replay(pattern_data)
    assert "LED1" in res

@pytest.mark.anyio
async def test_get_patterns_from_source_log(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("2023-01-01T12:00:00 INFO LED1=[255,0,0]")
    
    args = Namespace(source_type="log", filepath=log_file)
    runner = SimulationRunner(args, loguru.logger)
    
    res = await runner._get_patterns_from_source()
    assert len(res) == 1

@pytest.mark.anyio
async def test_get_patterns_from_source_log_missing(tmp_path):
    args = Namespace(source_type="log", filepath=tmp_path / "missing.log")
    runner = SimulationRunner(args, loguru.logger)
    with pytest.raises(SystemExit):
        await runner._get_patterns_from_log()

@pytest.mark.anyio
async def test_get_patterns_from_source_log_empty(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("dummy")
    args = Namespace(source_type="log", filepath=log_file)
    runner = SimulationRunner(args, loguru.logger)
    with pytest.raises(SystemExit):
        await runner._get_patterns_from_log()

@pytest.mark.anyio
async def test_get_patterns_from_source_invalid():
    args = Namespace(source_type="invalid")
    runner = SimulationRunner(args, loguru.logger)
    res = await runner._get_patterns_from_source()
    assert res == []

@pytest.mark.anyio
async def test_get_patterns_from_db_etalon_missing_name():
    args = Namespace(source_type="db", collection=f"my{ETALONS_COLLECTION_SUFFIX}", pattern_name=None)
    runner = SimulationRunner(args, loguru.logger)
    with pytest.raises(SystemExit):
        await runner._get_patterns_from_db()

@pytest.mark.anyio
async def test_get_patterns_from_db_etalon(monkeypatch):
    args = Namespace(source_type="db", collection=f"my{ETALONS_COLLECTION_SUFFIX}", pattern_name="test")
    runner = SimulationRunner(args, loguru.logger)
    
    mock_connector_ctx = AsyncMock()
    mock_connector_ctx.read.return_value = {"_id": "TEST", "LED1": [[0.0, [255, 0, 0], 1.0]]}
    mock_connector_ctx.__aenter__.return_value = mock_connector_ctx

    with patch("led_testing_toolkit.led_simulation_runner.MongoDbConnector", return_value=mock_connector_ctx):
        res = await runner._get_patterns_from_db()
        assert len(res) == 1

@pytest.mark.anyio
async def test_get_patterns_from_db_etalon_not_found(monkeypatch):
    args = Namespace(source_type="db", collection=f"my{ETALONS_COLLECTION_SUFFIX}", pattern_name="test")
    runner = SimulationRunner(args, loguru.logger)
    
    mock_connector_ctx = AsyncMock()
    mock_connector_ctx.read.return_value = None
    mock_connector_ctx.__aenter__.return_value = mock_connector_ctx

    with patch("led_testing_toolkit.led_simulation_runner.MongoDbConnector", return_value=mock_connector_ctx):
        with pytest.raises(SystemExit):
            await runner._get_patterns_from_db()

@pytest.mark.anyio
async def test_get_patterns_from_db_measured(monkeypatch):
    args = Namespace(source_type="db", collection="measured_data", process_all=True)
    runner = SimulationRunner(args, loguru.logger)
    
    mock_connector_ctx = AsyncMock()
    mock_connector_ctx.read.return_value = [{"_id": "M1", "LED1": [[0.0, [255, 0, 0], 1.0]]}]
    mock_connector_ctx.__aenter__.return_value = mock_connector_ctx

    with patch("led_testing_toolkit.led_simulation_runner.MongoDbConnector", return_value=mock_connector_ctx):
        res = await runner._get_patterns_from_db()
        assert len(res) == 1

@pytest.mark.anyio
async def test_get_patterns_from_db_measured_empty(monkeypatch):
    args = Namespace(source_type="db", collection="measured_data", process_all=True)
    runner = SimulationRunner(args, loguru.logger)
    
    mock_connector_ctx = AsyncMock()
    mock_connector_ctx.read.return_value = []
    mock_connector_ctx.__aenter__.return_value = mock_connector_ctx

    with patch("led_testing_toolkit.led_simulation_runner.MongoDbConnector", return_value=mock_connector_ctx):
        with pytest.raises(SystemExit):
            await runner._get_patterns_from_db()

@pytest.mark.anyio
async def test_run_empty():
    args = Namespace(source_type="invalid")
    runner = SimulationRunner(args, loguru.logger)
    res = await runner.run()
    assert res == []

@pytest.mark.anyio
async def test_run_success(tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("2023-01-01T12:00:00 INFO LED1=[255,0,0]\n2023-01-01T12:00:01 INFO LED1=[0,255,0]")
    
    args = Namespace(
        source_type="log", 
        filepath=log_file,
        count=1,
        output_dir=str(tmp_path),
        save_to_db=False,
        mode="simulate",
        noise=0.0,
        lag=0.0,
        reporting_chance=1.0,
        interval="10"
    )
    runner = SimulationRunner(args, loguru.logger)
    
    with patch("led_testing_toolkit.led_simulation_runner.LedGenerator.run", new_callable=AsyncMock) as mock_run:
        res = await runner.run()
        assert len(res) == 1
        assert "log_test_" in res[0]
        mock_run.assert_called_once()

@pytest.mark.anyio
async def test_run_success_db(tmp_path):
    args = Namespace(
        source_type="db",
        collection=f"my{ETALONS_COLLECTION_SUFFIX}",
        pattern_name="test_pattern",
        count=1,
        output_dir=str(tmp_path),
        save_to_db=True,
        mode="simulate",
        noise=0.0,
        lag=0.0,
        reporting_chance=1.0,
        interval="10"
    )
    runner = SimulationRunner(args, loguru.logger)
    
    fake_data = {"LED1": {"r": [Record(coordinates=[Point(x=1.0, y=0.0, z=1.0)])]}}
    with patch.object(runner, "_get_patterns_from_db", return_value=[fake_data]):
        with patch("led_testing_toolkit.led_simulation_runner.ReplayPattern") as MockReplay:
            MockReplay.return_value.end_time = 0.0
            with patch("led_testing_toolkit.led_simulation_runner.LedGenerator.run", new_callable=AsyncMock) as mock_run:
                with patch("led_testing_toolkit.led_simulation_runner.LedParser.parse_patterns", new_callable=AsyncMock):
                    res = await runner.run()
                    assert len(res) == 1
                    assert "db_myETALONS_test_pattern" in res[0]
                    mock_run.assert_called_once()

@pytest.mark.anyio
async def test_run_empty_pattern_data(tmp_path):
    args = Namespace(
        source_type="invalid", 
        count=1,
        output_dir=str(tmp_path),
        save_to_db=False,
        mode="simulate",
        noise=0.0,
        lag=0.0,
        reporting_chance=1.0,
        interval="10"
    )
    runner = SimulationRunner(args, loguru.logger)
    with patch.object(runner, "_get_patterns_from_source", return_value=[{}]):
        res = await runner.run()
        assert res == []

@pytest.mark.anyio
async def test_run_no_led_ids(tmp_path):
    args = Namespace(
        source_type="invalid", 
        count=1,
        output_dir=str(tmp_path),
        save_to_db=False,
        mode="simulate",
        noise=0.0,
        lag=0.0,
        reporting_chance=1.0,
        interval="10"
    )
    runner = SimulationRunner(args, loguru.logger)
    
    class FakePattern:
        def __init__(self):
            pass
        keys = lambda self: []
        def values(self):
            class Channels:
                def values(self): return []
            return [Channels()]
        def items(self): return []
        __bool__ = lambda self: True
        def __contains__(self, k): return False
        
    fake_data = FakePattern() # no valid led
    with patch.object(runner, "_get_patterns_from_source", return_value=[fake_data]):
        with patch("led_testing_toolkit.led_simulation_runner.ReplayPattern") as MockReplay:
            MockReplay.return_value.end_time = 0.0
            res = await runner.run()
            assert res == []

@pytest.mark.anyio
async def test_get_patterns_from_db_measured_not_all(monkeypatch):
    args = Namespace(source_type="db", collection="measured_data", process_all=False)
    runner = SimulationRunner(args, loguru.logger)
    
    mock_connector_ctx = AsyncMock()
    mock_connector_ctx.read.return_value = [{"_id": "M1", "LED1": [[0.0, [255, 0, 0], 1.0]]}, {"_id": "M2", "LED1": [[0.0, [255, 0, 0], 1.0]]}]
    mock_connector_ctx.__aenter__.return_value = mock_connector_ctx

    with patch("led_testing_toolkit.led_simulation_runner.MongoDbConnector", return_value=mock_connector_ctx):
        res = await runner._get_patterns_from_db()
        assert len(res) == 1
