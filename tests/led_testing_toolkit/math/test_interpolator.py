import pytest
import numpy as np
from unittest import mock
from led_testing_toolkit.math.models import Point
from led_testing_toolkit.math.interpolator import Interpolator

@pytest.fixture
def interpolator():
    return Interpolator(lower_bound=0, upper_bound=100)

def test_interpolator_init(interpolator):
    assert interpolator.lower_bound == 0
    assert interpolator.upper_bound == 100

@pytest.mark.asyncio
async def test_interpolate_success(interpolator):
    points = [Point(x=0, y=10), Point(x=5, y=50), Point(x=10, y=90)]
    x_new, y_new = await interpolator.interpolate(points, num_points=5)
    
    assert len(x_new) == 5
    assert len(y_new) == 5
    assert np.allclose(x_new, [0, 2.5, 5.0, 7.5, 10.0])
    assert np.allclose(y_new, [10, 30, 50, 70, 90])

@pytest.mark.asyncio
async def test_interpolate_min_points_error(interpolator):
    points = [Point(x=0, y=10), Point(x=10, y=90)]
    with pytest.raises(ValueError, match="Number of interpolation points must be at least"):
        await interpolator.interpolate(points, num_points=1)

@pytest.mark.asyncio
async def test_interpolate_empty_coordinates(interpolator):
    x_new, y_new = await interpolator.interpolate([], num_points=5)
    assert len(x_new) == 0
    assert len(y_new) == 0

@pytest.mark.asyncio
async def test_interpolate_clipping(interpolator):
    points = [Point(x=0, y=-10), Point(x=10, y=150)]
    x_new, y_new = await interpolator.interpolate(points, num_points=3)
    assert np.allclose(y_new, [0, 70, 100])

@pytest.mark.asyncio
async def test_interpolate_outlier_removal(interpolator):
    points = [Point(x=0, y=10), Point(x=1, y=15), Point(x=2, y=90), Point(x=3, y=20), Point(x=4, y=25)]
    x_new, y_new = await interpolator.interpolate(points, num_points=5)
    assert np.max(y_new) <= 57.5

@pytest.mark.asyncio
async def test_interpolate_no_outlier_removal(interpolator):
    points = [Point(x=0, y=10), Point(x=1, y=10), Point(x=2, y=10), Point(x=3, y=10)]
    x_new, y_new = await interpolator.interpolate(points, num_points=4)
    assert np.allclose(y_new, [10, 10, 10, 10])

@pytest.mark.asyncio
@mock.patch('numpy.array')
async def test_interpolate_invalid_shape(mock_array, interpolator):
    mock_array.return_value = np.zeros((2, 3))
    points = [Point(x=0, y=10), Point(x=1, y=10)]
    with pytest.raises(ValueError, match="Input must be a list or array"):
        await interpolator.interpolate(points, num_points=5)

    mock_array.return_value = np.zeros((2, 2, 2))
    with pytest.raises(ValueError, match="Input must be a list or array"):
        await interpolator.interpolate(points, num_points=5)
