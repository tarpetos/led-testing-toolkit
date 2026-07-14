from led_testing_toolkit.led_modeler.patterns import (
    FadePattern, ChaserPattern, KeyframesPattern, SimplePattern, Pattern
)
from led_testing_toolkit.led_modeler.models import (
    FadePatternConfig, ChaserPatternConfig, KeyframesPatternConfig, Keyframe
)

def test_pattern_base():
    class DummyPattern(Pattern):
        def update(self, elapsed_s):
            super().update(elapsed_s)
            return {}
            
    p = DummyPattern([1, 2], 0.0, 10.0)
    assert p.get_active_leds() == {"LED1", "LED2"}

def test_fade_pattern():
    config = FadePatternConfig(type="fade", led_ids=[1], duration=2.0, peak_time=1.0, color=[255, 0, 0], start_time=0.0, end_time=2.0)
    p = FadePattern(config)
    
    # outside bounds
    assert p.update(-1.0) == {}
    assert p.update(2.1) == {}
    
    # before peak
    state = p.update(0.5)
    assert state["LED1"]["color"] == [127, 0, 0]
    assert state["LED1"]["rel_time"] == 0.5
    
    # peak
    state = p.update(1.0)
    assert state["LED1"]["color"] == [255, 0, 0]
    
    # after peak
    state = p.update(1.5)
    assert state["LED1"]["color"] == [127, 0, 0]
    
    # test peak time 0
    config0 = FadePatternConfig(type="fade", led_ids=[1], duration=2.0, peak_time=0.0, color=[255, 0, 0], start_time=0.0, end_time=2.0)
    p0 = FadePattern(config0)
    state0 = p0.update(0.0)
    assert state0["LED1"]["color"] == [255, 0, 0]
    
    # test fade out duration 0
    config_fast_end = FadePatternConfig(type="fade", led_ids=[1], duration=1.0, peak_time=1.0, color=[255, 0, 0], start_time=0.0, end_time=2.0)
    p_fast_end = FadePattern(config_fast_end)
    state_fast = p_fast_end.update(1.5)
    assert state_fast["LED1"]["color"] == [0, 0, 0]

def test_chaser_pattern():
    config = ChaserPatternConfig(type="chaser", led_ids=[1, 2], cycle_duration=2.0, pulse_width=0.5, start_time=0.0, end_time=4.0, color=[255, 0, 0])
    p = ChaserPattern(config)
    
    # outside bounds
    assert p.update(-1.0) == {}
    assert p.update(4.1) == {}
    
    # update inside bounds
    state = p.update(0.0)
    # cycle pos 0, led 1 distance is 0, so full color
    assert state["LED1"]["color"] == [255, 0, 0]
    
    state = p.update(1.0)
    # cycle pos 0.5, active index 1, led 2 (index 1) distance 0 -> full color
    assert state["LED2"]["color"] == [255, 0, 0]

def test_keyframes_pattern():
    config = KeyframesPatternConfig(
        type="keyframes", 
        led_ids=[1], 
        start_time=0.0, 
        end_time=5.0, 
        keyframes=[
            Keyframe(time=1.0, color=[255, 0, 0]),
            Keyframe(time=2.0, color=[0, 255, 0])
        ]
    )
    p = KeyframesPattern(config)
    
    assert p.update(-1.0) == {}
    
    # Before first keyframe
    state = p.update(0.5)
    assert state["LED1"]["color"] == [255, 0, 0]
    
    # Interpolating
    state = p.update(1.5)
    assert state["LED1"]["color"] == [127, 127, 0]
    
    # After last keyframe
    state = p.update(3.0)
    assert state["LED1"]["color"] == [0, 255, 0]
    
    # Test identical times duration 0
    config_0 = KeyframesPatternConfig(
        type="keyframes", 
        led_ids=[1], 
        start_time=0.0, 
        end_time=5.0, 
        keyframes=[
            Keyframe(time=1.0, color=[255, 0, 0]),
            Keyframe(time=1.0, color=[0, 255, 0])
        ]
    )
    p_0 = KeyframesPattern(config_0)
    state_0 = p_0.update(1.0)
    # duration 0 means it should be the end color [0, 255, 0]
    assert state_0["LED1"]["color"] == [0, 255, 0]

def test_simple_pattern():
    p = SimplePattern(num_leds=2, color=[255, 0, 0], fade_s=1.0, sequence="all_at_once")
    state = p.update(0.5)
    assert state["LED1"]["color"] == [127, 0, 0]
    assert state["LED2"]["color"] == [127, 0, 0]
    
    p_seq = SimplePattern(num_leds=2, color=[255, 0, 0], fade_s=1.0, sequence="sequential")
    state = p_seq.update(0.5)
    assert state["LED1"]["color"] == [127, 0, 0]
    assert "LED2" not in state
    
    state2 = p_seq.update(1.5)
    assert state2["LED1"]["color"] == [255, 0, 0]
    assert state2["LED2"]["color"] == [127, 0, 0]

    # Test fade_s = 0
    p_fast = SimplePattern(num_leds=1, color=[255, 0, 0], fade_s=0.0, sequence="all_at_once")
    state_fast = p_fast.update(0.5)
    assert state_fast["LED1"]["color"] == [255, 0, 0]
