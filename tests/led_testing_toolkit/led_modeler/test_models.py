import pytest
from led_testing_toolkit.led_modeler.models import AppConfig, KeyframesPatternConfig, Keyframe
from pydantic import ValidationError
import json

def test_app_config_validation(tmp_path):
    config = AppConfig(
        mode="instant",
        duration=10.0,
        output_file="out.json",
        interval="100-200",
        noise=0.1,
        lag=0.1,
        reporting_chance=0.5,
        num_leds=2,
        color="255,0,0",
        sequence="all_at_once"
    )
    assert config.interval_ms_range == (100, 200)
    assert config.parsed_color == [255, 0, 0]
    
    with pytest.raises(SystemExit):
        AppConfig(
            mode="instant", duration=10.0, output_file="out.json", interval="invalid", noise=0.1, lag=0.1, reporting_chance=0.5
        )
        
    with pytest.raises(SystemExit):
        AppConfig(
            mode="instant", duration=10.0, output_file="out.json", interval="100-200-300", noise=0.1, lag=0.1, reporting_chance=0.5
        )

    with pytest.raises(SystemExit):
        AppConfig(
            mode="instant", duration=10.0, output_file="out.json", interval="-10", noise=0.1, lag=0.1, reporting_chance=0.5
        )
        
    with pytest.raises(SystemExit):
        AppConfig(
            mode="instant", duration=10.0, output_file="out.json", interval="100", noise=0.1, lag=0.1, reporting_chance=0.5, color="invalid"
        )
        
    # test single interval
    c2 = AppConfig(
        mode="instant", duration=10.0, output_file="out.json", interval="100", noise=0.1, lag=0.1, reporting_chance=0.5, num_leds=1, color="255,0,0", sequence="all_at_once"
    )
    assert c2.interval_ms_range == (100, 100)

    # test palette file
    pfile = tmp_path / "palette.json"
    pfile.write_text(json.dumps([
        {"type": "fade", "duration": 1.0, "peak_time": 0.5}
    ]))
    
    c3 = AppConfig(
        mode="instant", duration=10.0, output_file="out.json", interval="100", noise=0.1, lag=0.1, reporting_chance=0.5, palette=str(pfile)
    )
    assert len(c3.parsed_palette) == 1
    
    # test palette string
    c4 = AppConfig(
        mode="instant", duration=10.0, output_file="out.json", interval="100", noise=0.1, lag=0.1, reporting_chance=0.5, palette='[{"type": "fade", "duration": 1.0, "peak_time": 0.5}]'
    )
    assert len(c4.parsed_palette) == 1

    # test palette string bad json
    with pytest.raises(SystemExit):
        AppConfig(
            mode="instant", duration=10.0, output_file="out.json", interval="100", noise=0.1, lag=0.1, reporting_chance=0.5, palette='invalid_json'
        )

    # test missing both palette and basic args
    with pytest.raises(SystemExit):
        AppConfig(
            mode="instant", duration=10.0, output_file="out.json", interval="100", noise=0.1, lag=0.1, reporting_chance=0.5
        )

def test_keyframe_sort():
    config = KeyframesPatternConfig(
        type="keyframes",
        keyframes=[
            Keyframe(time=2.0, color=[0,0,0]),
            Keyframe(time=1.0, color=[255,255,255]),
        ]
    )
    assert config.keyframes[0].time == 1.0
