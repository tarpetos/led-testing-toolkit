import pytest
from unittest import mock
import numpy as np
from led_testing_toolkit.utils.data_processing import (
    make_sequence,
    extract_led_rgb_data,
    convert_etalon_to_db_format,
    compute_average_abs_times,
    read_measured,
    read_etalon,
    generate_etalon,
    make_comparison,
    make_comparisons,
    convert_normalized_to_raw_format,
    save_patterns_to_db,
)
from led_testing_toolkit.math.models import Record, Point

def test_make_sequence():
    assert make_sequence("test") == ("test",)
    assert make_sequence(["a"]) == ["a"]
    assert make_sequence(1) == (1,)

@pytest.mark.asyncio
async def test_extract_led_rgb_data():
    raw_data = {
        "LED1": [
            [0.1, [255, 0, 0], 1.0],
            [0.2, [0, 255, 0], 2.0]
        ],
        "LED2": "invalid",
        "LED3": [
            [0.1, [255, 0], 1.0] # Invalid rgb data
        ],
        "LED4": [
            123 # TypeError
        ]
    }
    
    with mock.patch("led_testing_toolkit.utils.data_processing.logger") as mock_log:
        res = await extract_led_rgb_data([raw_data])
        
        assert "LED1" in res
        assert len(res["LED1"]["r"][0].coordinates) == 2
        assert res["LED1"]["r"][0].coordinates[0].x == 0.1
        assert res["LED1"]["r"][0].coordinates[0].y == 255
        assert res["LED1"]["r"][0].coordinates[0].z == 1.0
        
        # Test invalid data
        assert "LED2" in res
        mock_log.warning.assert_any_call("Skipping invalid LED data for LED2!")
        
        assert "LED3" in res
        mock_log.warning.assert_any_call("Invalid RGB data in LED3: [255, 0]")
        
        assert "LED4" in res
        mock_log.error.assert_called()

def test_convert_etalon_to_db_format():
    r_coords = [Point(x=1, y=255, z=0), Point(x=2, y=255, z=0)]
    g_coords = [Point(x=1, y=0, z=0), Point(x=2, y=0, z=0)]
    b_coords = [Point(x=1, y=0, z=0), Point(x=2, y=0, z=0)]
    
    data = {
        "LED1": {
            "r": mock.Mock(coordinates=r_coords),
            "g": mock.Mock(coordinates=g_coords),
            "b": mock.Mock(coordinates=b_coords),
        }
    }
    
    res = convert_etalon_to_db_format(data, {"LED1": [1.0, 2.0]})
    assert "LED1" in res
    assert len(res["LED1"]) == 2
    assert res["LED1"][0][0] == 1.0
    assert res["LED1"][0][1] == [255, 0, 0]
    assert res["LED1"][0][2] == 1.0

def test_compute_average_abs_times():
    records = [
        mock.Mock(coordinates=[mock.Mock(z=1.0), mock.Mock(z=2.0)]),
        mock.Mock(coordinates=[mock.Mock(z=3.0)])
    ]
    
    res = compute_average_abs_times(records)
    assert np.isnan(res[1]) or res[1] == 2.0
    assert res[0] == 2.0

@pytest.mark.asyncio
async def test_read_measured():
    with mock.patch("led_testing_toolkit.utils.data_processing.MongoDbConnector") as mock_conn, \
         mock.patch("led_testing_toolkit.utils.data_processing.extract_led_rgb_data") as mock_extract:
         
        mock_conn_instance = mock.AsyncMock()
        mock_conn.return_value.__aenter__.return_value = mock_conn_instance
        
        mock_conn_instance.read.return_value = [{"data": "val"}]
        mock_extract.return_value = "extracted"
        
        res = await read_measured("DEV-PAT", get_random=True)
        assert res == "extracted"
        
        res2 = await read_measured("DEV-PAT", record_id="507f1f77bcf86cd799439011")
        assert res2 == "extracted"
        
        res3 = await read_measured("DEV-PAT")
        assert res3 == "extracted"

@pytest.mark.asyncio
async def test_read_etalon():
    with mock.patch("led_testing_toolkit.utils.data_processing.MongoDbConnector") as mock_conn, \
         mock.patch("led_testing_toolkit.utils.data_processing.extract_led_rgb_data") as mock_extract:
        
        mock_conn_instance = mock.AsyncMock()
        mock_conn.return_value.__aenter__.return_value = mock_conn_instance
        
        mock_conn_instance.read.return_value = [{"data": "val"}]
        mock_extract.return_value = "extracted"
        
        res = await read_etalon("PAT", "DEV-ETALONS")
        assert res == "extracted"
        
        mock_conn_instance.read.return_value = None
        with pytest.raises(ValueError, match="No etalon data found for pattern name `PAT`!"):
            await read_etalon("PAT", "DEV-ETALONS")

@pytest.mark.asyncio
async def test_generate_etalon():
    with mock.patch("led_testing_toolkit.utils.data_processing.read_measured") as mock_read, \
         mock.patch("led_testing_toolkit.utils.data_processing.MongoDbConnector") as mock_conn, \
         mock.patch("led_testing_toolkit.utils.data_processing.Aggregator") as MockAgg, \
         mock.patch("led_testing_toolkit.utils.data_processing.compute_average_abs_times") as mock_compute, \
         mock.patch("led_testing_toolkit.utils.data_processing.convert_etalon_to_db_format") as mock_convert:
        
        mock_conn_instance = mock.AsyncMock()
        mock_conn.return_value.__aenter__.return_value = mock_conn_instance
        
        mock_read.return_value = {
            "LED1": {
                "r": [],
            }
        }
        
        mock_agg = mock.AsyncMock()
        mock_agg.get_plots_base64 = mock.Mock(return_value="plot")
        mock_agg.etalon = "etalon"
        MockAgg.return_value = mock_agg
        
        mock_compute.return_value = [1.0]
        mock_convert.return_value = {"formatted": "data"}
        
        res_col, res_plots = await generate_etalon("DEV-PAT")
        
        assert res_col == "DEV-ETALONS"
        assert res_plots == {"LED1": {"r": "plot"}}
        mock_conn_instance.upsert.assert_called_once()

@pytest.mark.asyncio
async def test_make_comparison():
    with mock.patch("led_testing_toolkit.utils.data_processing.Comparator") as MockComp:
        mock_comp = mock.AsyncMock()
        mock_comp.start.return_value = 99.0
        mock_comp.build_plots = mock.Mock(return_value="plot")
        MockComp.return_value = mock_comp
        
        acc, plot = await make_comparison("e", "m", led="LED1", color="r")
        assert acc == 99.0
        assert plot == "plot"

@pytest.mark.asyncio
async def test_make_comparisons():
    with mock.patch("led_testing_toolkit.utils.data_processing.make_comparison") as mock_make:
        mock_make.return_value = (99.0, "plot")
        
        etalon_data = {"LED1": {"r": ["e_r"]}}
        measured_data = {"LED1": {"r": ["m_r"]}}
        
        res = await make_comparisons(etalon_data, measured_data)
        assert res == {"LED1": {"r": {"accuracy": 99.0, "plot": "plot"}}}

def test_convert_normalized_to_raw_format():
    assert convert_normalized_to_raw_format({}) == {}
    
    norm = {
        "LED1": {
            "r": [mock.Mock(coordinates=[Point(x=1, y=255, z=0)])],
            "g": [mock.Mock(coordinates=[Point(x=1, y=0, z=0)])],
            "b": [mock.Mock(coordinates=[Point(x=1, y=0, z=0)])],
        },
        "LED2": {
            "r": [mock.Mock(coordinates=[Point(x=1, y=255, z=0)])]
        }
    }
    
    res = convert_normalized_to_raw_format(norm)
    assert "LED1" in res
    assert res["LED1"][0] == [1, [255, 0, 0], 0]
    assert len(res["LED2"]) == 0

@pytest.mark.asyncio
async def test_save_patterns_to_db():
    with mock.patch("led_testing_toolkit.utils.data_processing.logger") as mock_log, \
         mock.patch("led_testing_toolkit.utils.data_processing.convert_normalized_to_raw_format") as mock_convert, \
         mock.patch("led_testing_toolkit.utils.data_processing.MongoDbConnector") as mock_conn:
        
        mock_conn_instance = mock.AsyncMock()
        mock_conn.return_value.__aenter__.return_value = mock_conn_instance
        mock_conn_instance.insert.return_value = mock.Mock(inserted_ids=[1])
        
        await save_patterns_to_db([], "col")
        mock_log.warning.assert_called()
        
        mock_convert.return_value = {"raw": "data"}
        
        await save_patterns_to_db([{"p": "1"}], "col")
        mock_conn_instance.insert.assert_called()
        mock_log.success.assert_called()
        
        mock_conn_instance.insert.side_effect = Exception("test")
        await save_patterns_to_db([{"p": "1"}], "col")
        mock_log.exception.assert_called()
