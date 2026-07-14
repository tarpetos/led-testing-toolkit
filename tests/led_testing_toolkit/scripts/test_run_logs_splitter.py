import argparse
import os
import runpy
from pathlib import Path
from unittest import mock

import pytest

from led_testing_toolkit.scripts.run_logs_splitter import split_logs_main, main

@pytest.mark.asyncio
async def test_split_logs_main():
    with mock.patch("led_testing_toolkit.scripts.run_logs_splitter.LogsSplitter") as MockSplitter:
        mock_splitter_instance = mock.AsyncMock()
        mock_splitter_instance.process_batch.return_value = [Path("out.log")]
        MockSplitter.return_value = mock_splitter_instance
        
        res = await split_logs_main(
            input_files=[Path("in.log")],
            max_patterns=1,
            output_dir=Path("out"),
            start_pattern="start",
            end_pattern="end"
        )
        
        assert res == [Path("out.log")]
        
        # Test ValueError
        MockSplitter.side_effect = ValueError("test error")
        with pytest.raises(ValueError, match="test error"):
            await split_logs_main(
                input_files=[Path("in.log")],
                max_patterns=1,
                output_dir=Path("out"),
                start_pattern="start",
                end_pattern="end"
            )
            
        # Test other exception
        MockSplitter.side_effect = Exception("test error")
        with pytest.raises(Exception, match="test error"):
            await split_logs_main(
                input_files=[Path("in.log")],
                max_patterns=1,
                output_dir=Path("out"),
                start_pattern="start",
                end_pattern="end"
            )

@pytest.mark.asyncio
async def test_main():
    with mock.patch("argparse.ArgumentParser.parse_args") as mock_args, \
         mock.patch("led_testing_toolkit.scripts.run_logs_splitter.split_logs_main", new_callable=mock.AsyncMock) as mock_main:
        mock_args.return_value = argparse.Namespace(
            input_files=[Path("in.log")],
            max_patterns=1,
            output_dir=Path("out"),
            start_pattern="start",
            end_pattern="end"
        )
        await main()
        mock_main.assert_called_once()

def test_dunder_main():
    script_path = os.path.join("led_testing_toolkit", "scripts", "run_logs_splitter.py")
    with open(script_path) as f:
        code = f.read()
    with mock.patch("asyncio.run") as mock_run:
        namespace = {"__name__": "__main__"}
        exec(compile(code, script_path, "exec"), namespace)
        mock_run.assert_called_once()
