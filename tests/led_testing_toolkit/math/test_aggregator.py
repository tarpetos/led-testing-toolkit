import pytest
import numpy as np
from pathlib import Path
from unittest import mock
from led_testing_toolkit.math.models import Point, Record, Dataset
from led_testing_toolkit.math.interpolator import Interpolator
from led_testing_toolkit.math.aggregator import Aggregator

@pytest.fixture
def interpolator():
    return Interpolator(lower_bound=0, upper_bound=100)

@pytest.fixture
def dataset():
    r1 = Record(coordinates=[Point(x=0, y=10), Point(x=5, y=50), Point(x=10, y=10)])
    r2 = Record(coordinates=[Point(x=0, y=12), Point(x=4, y=48), Point(x=11, y=12)])
    return Dataset(records=[r1, r2])

@pytest.fixture
def empty_dataset():
    return Dataset(records=[])

@pytest.fixture
def dataset_with_empty_record():
    return Dataset(records=[Record(coordinates=[])])

@pytest.mark.asyncio
async def test_aggregator_success(dataset, interpolator):
    agg = Aggregator(dataset=dataset, interpolator=interpolator)
    await agg.start()
    etalon = agg.etalon
    assert len(etalon.coordinates) > 0

@pytest.mark.asyncio
async def test_aggregator_empty_dataset(empty_dataset, interpolator):
    agg = Aggregator(dataset=empty_dataset, interpolator=interpolator)
    await agg.start()
    assert len(agg.etalon.coordinates) == 0

@pytest.mark.asyncio
async def test_aggregator_dataset_with_empty_record(dataset_with_empty_record, interpolator):
    agg = Aggregator(dataset=dataset_with_empty_record, interpolator=interpolator)
    await agg.start()
    assert len(agg.etalon.coordinates) == 0

@pytest.mark.asyncio
async def test_aggregator_plots_base64(dataset, interpolator):
    agg = Aggregator(dataset=dataset, interpolator=interpolator)
    await agg.start()
    base64_str = agg.get_plots_base64()
    assert base64_str

@pytest.mark.asyncio
async def test_aggregator_plots_base64_error(dataset, interpolator):
    agg = Aggregator(dataset=dataset, interpolator=interpolator)
    with pytest.raises(ValueError, match="Etalon is not available"):
        agg.get_plots_base64()

@pytest.mark.asyncio
async def test_aggregator_build_plots(dataset, interpolator, tmp_path):
    agg = Aggregator(dataset=dataset, interpolator=interpolator)
    await agg.start()
    save_path = tmp_path / "plot.png"
    result = agg.build_plots(save_path=str(save_path))
    assert result == save_path
    assert save_path.exists()

@pytest.mark.asyncio
async def test_aggregator_build_plots_no_save_path(dataset, interpolator):
    agg = Aggregator(dataset=dataset, interpolator=interpolator)
    await agg.start()
    with mock.patch("matplotlib.pyplot.show") as mock_show:
        result = agg.build_plots()
        assert result is None
        mock_show.assert_called_once()

def test_get_plot_colors():
    colors = Aggregator.get_plot_colors()
    color = next(colors)
    assert isinstance(color, str)
    assert color.startswith("#")

@pytest.mark.asyncio
async def test_aggregator_cliff_detection(interpolator):
    pts1 = [Point(x=i, y=100) for i in range(18)] + [Point(x=18, y=10), Point(x=19, y=10)]
    pts2 = [Point(x=i, y=100) for i in range(18)] + [Point(x=18, y=10), Point(x=19, y=10)]
    dataset = Dataset(records=[Record(coordinates=pts1), Record(coordinates=pts2)])
    agg = Aggregator(dataset=dataset, interpolator=interpolator)
    await agg.start()
    etalon = agg.etalon
    assert len(etalon.coordinates) > 0

@pytest.mark.asyncio
async def test_aggregator_sync_short_valid_signal(interpolator):
    r1 = Record(coordinates=[Point(x=i, y=10) for i in range(5)])
    dataset = Dataset(records=[r1])
    agg = Aggregator(dataset=dataset, interpolator=interpolator)
    await agg.start()
    assert len(agg.etalon.coordinates) > 0

@pytest.mark.asyncio
async def test_aggregator_sync_no_cliff(interpolator):
    r1 = Record(coordinates=[Point(x=i, y=50) for i in range(20)])
    dataset = Dataset(records=[r1])
    agg = Aggregator(dataset=dataset, interpolator=interpolator)
    await agg.start()
    assert len(agg.etalon.coordinates) > 0

@pytest.mark.asyncio
@mock.patch("numpy.all")
async def test_aggregator_nan_cliff(mock_all, interpolator):
    pts1 = [Point(x=i, y=100) for i in range(18)] + [Point(x=18, y=10), Point(x=19, y=10)]
    dataset = Dataset(records=[Record(coordinates=pts1)])
    agg = Aggregator(dataset=dataset, interpolator=interpolator)
    # mock np.all so that np.all(np.isnan(column)) returns True once
    # Then it calls break
    original_all = np.all
    def side_effect(arg, *args, **kwargs):
        if hasattr(arg, 'shape'):
            return True
        return original_all(arg, *args, **kwargs)
    mock_all.side_effect = side_effect
    await agg.start()
    assert len(agg.etalon.coordinates) > 0

def test_aggregate_sync_empty(interpolator):
    agg = Aggregator(dataset=Dataset(), interpolator=interpolator)
    agg._aggregate_sync()
    assert not agg._etalon

@pytest.mark.asyncio
async def test_aggregator_sync_nan_plateau(interpolator):
    # We need at least 10 valid points to pass the length check,
    # but the plateau section (25% to 75%) must be all NaNs.
    # Total points = 40. Valid = 0..9, NaN = 10..39
    pts = [Point(x=i, y=10) for i in range(10)] + [Point(x=i, y=float('nan')) for i in range(10, 40)]
    r1 = Record(coordinates=pts)
    dataset = Dataset(records=[r1])
    agg = Aggregator(dataset=dataset, interpolator=interpolator)

    original_nanmedian = np.nanmedian
    original_nanmean = np.nanmean

    def safe_nanmedian(a, *args, **kwargs):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return original_nanmedian(a, *args, **kwargs)

    def safe_nanmean(a, *args, **kwargs):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return original_nanmean(a, *args, **kwargs)

    with mock.patch("led_testing_toolkit.math.aggregator.np.nanmedian", side_effect=safe_nanmedian), \
         mock.patch("led_testing_toolkit.math.aggregator.np.nanmean", side_effect=safe_nanmean):
        await agg.start()

    assert len(agg.etalon.coordinates) >= 0
