import pytest
from unittest import mock

from led_testing_toolkit.utils.make_indication_comparison import make_indication_comparison_results


@pytest.mark.asyncio
async def test_make_indication_comparison_results():
    with (
        mock.patch("led_testing_toolkit.utils.make_indication_comparison.read_etalon") as mock_read_etalon,
        mock.patch("led_testing_toolkit.utils.make_indication_comparison.make_comparisons") as mock_make_comparisons,
    ):
        mock_read_etalon.return_value = "etalon_data"
        mock_make_comparisons.return_value = {
            "LED1": {
                "r": {"plot": "plot_r", "accuracy": 90.0},
                "g": {"plot": "plot_g", "accuracy": -1.0},
            },
            "LED2": {
                "b": {"plot": "plot_b", "accuracy": 80.0},
            },
        }

        results = await make_indication_comparison_results("measured_data", "dev", "pat")

        assert results["overall_accuracy"] == 85.0
        assert results["leds"]["LED1"]["r"]["accuracy"] == 90.0
        assert results["leds"]["LED1"]["r"]["plot"] == "plot_r"

        # Test without accuracies
        mock_make_comparisons.return_value = {}
        results = await make_indication_comparison_results("measured_data", "dev", "pat")
        assert results["overall_accuracy"] == 0
