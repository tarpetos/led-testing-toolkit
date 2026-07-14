import argparse
import os
import runpy
from unittest import mock

import pytest

from led_testing_toolkit.scripts.generate_indication_from_source import (
    generate_indication_from_source_main,
    main,
)


@pytest.mark.asyncio
async def test_generate_indication_from_source_main():
    with mock.patch("led_testing_toolkit.scripts.generate_indication_from_source.SimulationRunner") as MockRunner:
        mock_runner_instance = mock.AsyncMock()
        mock_runner_instance.run.return_value = ["out.log"]
        MockRunner.return_value = mock_runner_instance

        args = argparse.Namespace()
        res = await generate_indication_from_source_main(args)

        assert res == ["out.log"]


@pytest.mark.asyncio
async def test_main():
    with (
        mock.patch("argparse.ArgumentParser.parse_args") as mock_args,
        mock.patch(
            "led_testing_toolkit.scripts.generate_indication_from_source.generate_indication_from_source_main",
            new_callable=mock.AsyncMock,
        ) as mock_main,
    ):
        mock_args.return_value = argparse.Namespace(source_type="log")
        await main()
        mock_main.assert_called_once_with(mock_args.return_value)


def test_dunder_main():
    script_path = os.path.join("led_testing_toolkit", "scripts", "generate_indication_from_source.py")
    with open(script_path) as f:
        code = f.read()
    with mock.patch("asyncio.run") as mock_run:
        namespace = {"__name__": "__main__"}
        exec(compile(code, script_path, "exec"), namespace)
        mock_run.assert_called_once()
        coro = mock_run.call_args[0][0]
        coro.close()
