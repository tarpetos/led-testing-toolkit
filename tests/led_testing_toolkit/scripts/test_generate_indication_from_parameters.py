import argparse
import os
import runpy
from unittest import mock

import pytest

from led_testing_toolkit.scripts.generate_indication_from_parameters import (
    create_patterns_from_config,
    get_all_led_ids,
    generate_indication_from_parameters_main,
    main,
)

def test_create_patterns_from_config():
    with mock.patch("led_testing_toolkit.scripts.generate_indication_from_parameters.FadePattern") as MockFade, \
         mock.patch("led_testing_toolkit.scripts.generate_indication_from_parameters.ChaserPattern") as MockChaser, \
         mock.patch("led_testing_toolkit.scripts.generate_indication_from_parameters.KeyframesPattern") as MockKeyframes, \
         mock.patch("led_testing_toolkit.scripts.generate_indication_from_parameters.SimplePattern") as MockSimple:
        
        MockFade.return_value = "fade_obj"
        MockChaser.return_value = "chaser_obj"
        MockKeyframes.return_value = "key_obj"
        MockSimple.return_value = "simple_obj"
        
        mock_config_palette = mock.Mock()
        mock_config_palette.parsed_palette = [
            mock.Mock(type="fade"),
            mock.Mock(type="chaser"),
            mock.Mock(type="keyframes"),
            mock.Mock(type="unknown"),
        ]
        
        res = create_patterns_from_config(mock_config_palette)
        assert res == ["fade_obj", "chaser_obj", "key_obj"]
        
        mock_config_simple = mock.Mock()
        mock_config_simple.parsed_palette = None
        mock_config_simple.num_leds = 2
        mock_config_simple.parsed_color = "color"
        mock_config_simple.fade = 1.0
        mock_config_simple.sequence = "seq"
        
        res2 = create_patterns_from_config(mock_config_simple)
        assert res2 == ["simple_obj"]

def test_get_all_led_ids():
    mock_p1 = mock.Mock()
    mock_p1.led_ids = {1, 3}
    mock_p2 = mock.Mock()
    mock_p2.led_ids = {2}
    
    assert get_all_led_ids([mock_p1, mock_p2]) == ["LED1", "LED2", "LED3"]
    assert get_all_led_ids([]) == []

@pytest.mark.asyncio
async def test_generate_indication_from_parameters_main():
    with mock.patch("led_testing_toolkit.scripts.generate_indication_from_parameters.AppConfig") as MockConfig, \
         mock.patch("led_testing_toolkit.scripts.generate_indication_from_parameters.configure_logger") as mock_log, \
         mock.patch("led_testing_toolkit.scripts.generate_indication_from_parameters.create_patterns_from_config") as mock_create, \
         mock.patch("led_testing_toolkit.scripts.generate_indication_from_parameters.get_all_led_ids") as mock_get_ids, \
         mock.patch("led_testing_toolkit.scripts.generate_indication_from_parameters.PhotoresistorSimulator") as MockSim, \
         mock.patch("led_testing_toolkit.scripts.generate_indication_from_parameters.LedGenerator") as MockGen:
        
        mock_config = mock.Mock()
        mock_config.output_file = "out.log"
        mock_config.num_leds = 0
        mock_config.noise = 1.0
        mock_config.lag = 1.0
        mock_config.reporting_chance = 1.0
        MockConfig.return_value = mock_config
        
        mock_create.return_value = ["patterns"]
        mock_get_ids.return_value = ["LED1"]
        
        mock_gen_instance = mock.AsyncMock()
        MockGen.return_value = mock_gen_instance
        
        args = argparse.Namespace(save_to_db="db")
        res = await generate_indication_from_parameters_main(args)
        
        assert res == "out.log"
        mock_gen_instance.run.assert_called_once()
        
        # Test with num_leds
        mock_config.num_leds = 2
        await generate_indication_from_parameters_main(args)
        MockSim.assert_called_with(led_ids=["LED1", "LED2"], noise_level=1.0, lag=1.0, reporting_chance=1.0)

@pytest.mark.asyncio
async def test_main():
    with mock.patch("argparse.ArgumentParser.parse_args") as mock_args, \
         mock.patch("led_testing_toolkit.scripts.generate_indication_from_parameters.generate_indication_from_parameters_main", new_callable=mock.AsyncMock) as mock_main:
        mock_args.return_value = argparse.Namespace()
        await main()
        mock_main.assert_called_once_with(mock_args.return_value)

def test_dunder_main():
    script_path = os.path.join("led_testing_toolkit", "scripts", "generate_indication_from_parameters.py")
    with open(script_path) as f:
        code = f.read()
    with mock.patch("asyncio.run") as mock_run:
        namespace = {"__name__": "__main__"}
        exec(compile(code, script_path, "exec"), namespace)
        mock_run.assert_called_once()
