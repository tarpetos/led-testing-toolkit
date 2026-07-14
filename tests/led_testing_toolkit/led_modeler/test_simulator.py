import numpy as np
from led_testing_toolkit.led_modeler.simulator import PhotoresistorSimulator


def test_simulator_get_reading():
    sim = PhotoresistorSimulator(["LED1"], noise_level=0.0, lag=0.0, reporting_chance=1.0)
    reading = sim.get_reading({"LED1": [255, 0, 0]})
    assert "LED1" in reading
    assert reading["LED1"] == [255, 0, 0]

    # Test lag
    sim = PhotoresistorSimulator(["LED2"], noise_level=0.0, lag=0.5, reporting_chance=1.0)
    reading = sim.get_reading({"LED2": [100, 100, 100]})
    # initially state is 0, so 0.5 lag means 50
    assert "LED2" in reading
    assert reading["LED2"] == [50, 50, 50]

    # Test reporting chance 0
    sim = PhotoresistorSimulator(["LED3"], noise_level=0.0, lag=0.0, reporting_chance=0.0)
    reading = sim.get_reading({"LED3": [100, 100, 100]})
    assert "LED3" not in reading
