import argparse
import os
import runpy
from unittest import mock

import pytest

from led_testing_toolkit.scripts.generate_etalons import (
    _get_collections,
    _generate_etalons,
    generate_etalons_main,
    main,
)

@pytest.mark.asyncio
async def test_get_collections():
    with mock.patch("led_testing_toolkit.scripts.generate_etalons.MongoDbConnector") as mock_conn:
        mock_conn_instance = mock.AsyncMock()
        mock_conn.return_value.__aenter__.return_value = mock_conn_instance
        mock_conn_instance.list_collections.return_value = ["DEV-PAT", "DEV-OTHER", "OTHER-PAT"]
        
        res = await _get_collections("DEV", "PAT")
        assert res == ["DEV-PAT"]
        
        res = await _get_collections()
        assert set(res) == {"DEV-PAT", "DEV-OTHER", "OTHER-PAT"}
        
        res = await _get_collections("DEV", "PAT", force_specific_collection=True)
        assert res == ["DEV-PAT"]
        
        with pytest.raises(ValueError, match="Collection `NOT-FOUND` not found!"):
            await _get_collections("NOT", "FOUND", force_specific_collection=True)

@pytest.mark.asyncio
async def test_generate_etalons_func():
    with mock.patch("led_testing_toolkit.scripts.generate_etalons.logger") as mock_log, \
         mock.patch("led_testing_toolkit.scripts.generate_etalons.generate_etalon") as mock_gen, \
         mock.patch("led_testing_toolkit.scripts.generate_etalons.parse_collection_name") as mock_parse:
        
        res, plots = await _generate_etalons([])
        assert res == []
        assert plots == {}
        
        mock_parse.side_effect = [("DEV", "PAT"), ("DEV", "ETALONS"), Exception("test error")]
        mock_gen.return_value = ("DEV-ETALONS", {"plot1": "data"})
        
        res, plots = await _generate_etalons(["col1", "col2", "col3"])
        
        assert res == ["DEV-ETALONS"]
        assert plots == {"plot1": "data"}
        mock_log.warning.assert_called()

@pytest.mark.asyncio
async def test_generate_etalons_main():
    with mock.patch("led_testing_toolkit.scripts.generate_etalons._get_collections") as mock_get, \
         mock.patch("led_testing_toolkit.scripts.generate_etalons._generate_etalons") as mock_gen:
        
        mock_get.return_value = ["a"]
        mock_gen.return_value = (["b"], {})
        
        res = await generate_etalons_main("dev", "pat", True)
        mock_get.assert_called_once_with("dev", "pat", force_specific_collection=True)
        mock_gen.assert_called_once_with(["a"])
        assert res == (["b"], {})

@pytest.mark.asyncio
async def test_main():
    with mock.patch("argparse.ArgumentParser.parse_args") as mock_args, \
         mock.patch("led_testing_toolkit.scripts.generate_etalons.generate_etalons_main", new_callable=mock.AsyncMock) as mock_gen:
        
        mock_args.return_value = argparse.Namespace(device_name="DEV", pattern_name="PAT")
        await main()
        mock_gen.assert_called_once_with("DEV", "PAT", False)

def test_dunder_main():
    script_path = os.path.join("led_testing_toolkit", "scripts", "generate_etalons.py")
    with open(script_path) as f:
        code = f.read()
    with mock.patch("asyncio.run") as mock_run:
        namespace = {"__name__": "__main__"}
        exec(compile(code, script_path, "exec"), namespace)
        mock_run.assert_called_once()
        coro = mock_run.call_args[0][0]
        coro.close()
