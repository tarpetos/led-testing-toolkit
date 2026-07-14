import argparse
import os
import runpy
from unittest import mock

import pytest

from led_testing_toolkit.scripts.compare_patterns import main


@pytest.mark.asyncio
async def test_compare_patterns_main():
    with (
        mock.patch("argparse.ArgumentParser.parse_args") as mock_args,
        mock.patch(
            "led_testing_toolkit.scripts.compare_patterns.read_measured", new_callable=mock.AsyncMock
        ) as mock_read,
        mock.patch(
            "led_testing_toolkit.scripts.compare_patterns.make_indication_comparison_results",
            new_callable=mock.AsyncMock,
        ) as mock_make,
    ):
        mock_args.return_value = argparse.Namespace(
            measured_collection="MEASURED_COL",
            etalon_device="DEV",
            etalon_pattern="PAT",
        )
        mock_read.return_value = "measured_data"

        await main()

        mock_read.assert_called_once_with("MEASURED_COL", get_random=True)
        mock_make.assert_called_once_with("measured_data", "DEV", "PAT")


def test_compare_patterns_dunder_main():
    script_path = os.path.join("led_testing_toolkit", "scripts", "compare_patterns.py")
    with open(script_path) as f:
        code = f.read()
    with mock.patch("asyncio.run") as mock_run:
        namespace = {"__name__": "__main__"}
        exec(compile(code, script_path, "exec"), namespace)
        mock_run.assert_called_once()
        coro = mock_run.call_args[0][0]
        coro.close()
