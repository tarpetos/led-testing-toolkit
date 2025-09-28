from pathlib import Path

from loguru import logger

from led_testing_toolkit.led_types import NormalizedLedData
from led_testing_toolkit.utils.collection_name import ETALONS_COLLECTION_SUFFIX
from led_testing_toolkit.utils.data_processing import make_comparisons, read_etalon


async def make_indication_comparison(
    measured_data: NormalizedLedData,
    etalon_device: str,
    etalon_pattern: str,
    *,
    plots_path: str | Path | None = None,
) -> float:
    etalon_device, etalon_pattern = etalon_device.upper(), etalon_pattern.upper()

    plots_path = Path(plots_path) if plots_path else Path(etalon_pattern.lower())

    normalized_etalon_data = await read_etalon(etalon_pattern, f"{etalon_device}-{ETALONS_COLLECTION_SUFFIX}")
    results = await make_comparisons(normalized_etalon_data, measured_data, plots_path)
    accuracies = [value[color]["accuracy"] for led, value in results.items() for color in value]
    accuracies = [accuracy for accuracy in accuracies if accuracy != -1.0]
    overall_accuracy = sum(accuracies) / len(accuracies)
    logger.info(f"Overall RGB accuracy: {overall_accuracy:.2f}%")
    return overall_accuracy
