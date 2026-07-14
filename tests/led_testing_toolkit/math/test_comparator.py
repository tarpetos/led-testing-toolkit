import pytest
import numpy as np
import warnings
from led_testing_toolkit.math.models import Point, Record
from led_testing_toolkit.math.interpolator import Interpolator
from led_testing_toolkit.math.comparator import Comparator, WeakSignalWarning

@pytest.fixture
def interpolator():
    return Interpolator(lower_bound=0, upper_bound=100)

@pytest.fixture
def etalon():
    return Record(coordinates=[Point(x=0, y=10), Point(x=5, y=50), Point(x=10, y=90)])

@pytest.fixture
def measured():
    return Record(coordinates=[Point(x=0, y=10), Point(x=6, y=50), Point(x=10, y=90)])

@pytest.mark.asyncio
async def test_comparator_success(etalon, measured, interpolator):
    comp = Comparator(etalon=etalon, measured=measured, interpolator=interpolator)
    accuracy = await comp.start()
    assert accuracy > 0

@pytest.mark.asyncio
async def test_comparator_weak_signal(etalon, interpolator):
    measured = Record(coordinates=[Point(x=0, y=1), Point(x=5, y=2), Point(x=10, y=1)])
    comp = Comparator(etalon=etalon, measured=measured, interpolator=interpolator)
    with pytest.warns(WeakSignalWarning):
        accuracy = await comp.start()
    assert accuracy == -1.0

@pytest.mark.asyncio
async def test_comparator_empty_measured(etalon, interpolator):
    measured = Record(coordinates=[])
    comp = Comparator(etalon=etalon, measured=measured, interpolator=interpolator)
    with pytest.warns(WeakSignalWarning):
        accuracy = await comp.start()
    assert accuracy == -1.0

@pytest.mark.asyncio
async def test_comparator_plots(etalon, measured, interpolator):
    comp = Comparator(etalon=etalon, measured=measured, interpolator=interpolator)
    await comp.start()
    base64_str = comp.build_plots()
    assert base64_str

@pytest.mark.asyncio
async def test_comparator_plots_unstarted(etalon, measured, interpolator):
    comp = Comparator(etalon=etalon, measured=measured, interpolator=interpolator)
    # Mock _is_checked to True and _is_weak to False to hit the "not self._aligned_data" check
    comp._is_checked = True
    comp._is_weak = False
    with pytest.raises(ValueError, match="Aligned data is not available"):
        comp.build_plots()

@pytest.mark.asyncio
async def test_comparator_plots_weak_signal(etalon, interpolator):
    measured = Record(coordinates=[Point(x=0, y=1), Point(x=5, y=2), Point(x=10, y=1)])
    comp = Comparator(etalon=etalon, measured=measured, interpolator=interpolator)
    with pytest.warns(WeakSignalWarning):
        res = comp.build_plots()
    assert res == ""

def test_calculate_mae_accuracy_empty():
    comp = Comparator(etalon=Record(), measured=Record(), interpolator=Interpolator())
    acc = comp._calculate_mae_accuracy(np.array([]), np.array([]))
    assert acc == 0.0

def test_calculate_correlation_accuracy_empty():
    comp = Comparator(etalon=Record(), measured=Record(), interpolator=Interpolator())
    acc = comp._calculate_correlation_accuracy(np.array([1]), np.array([1]))
    assert acc == 0.0

def test_calculate_fft_accuracy_empty():
    comp = Comparator(etalon=Record(), measured=Record(), interpolator=Interpolator())
    acc = comp._calculate_fft_accuracy(np.array([]), np.array([]))
    assert acc == 0.0

def test_calculate_fft_accuracy_zero_mag():
    comp = Comparator(etalon=Record(), measured=Record(), interpolator=Interpolator())
    acc = comp._calculate_fft_accuracy(np.array([0, 0, 0, 0]), np.array([0, 0, 0, 0]))
    assert acc == 100.0

def test_calculate_fft_empty():
    comp = Comparator(etalon=Record(), measured=Record(), interpolator=Interpolator())
    xf, mag = comp._calculate_fft(np.array([]))
    assert len(xf) == 0
    assert len(mag) == 0
