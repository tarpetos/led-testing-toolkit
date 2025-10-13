from led_testing_toolkit.led_types import NormalizedLedData
from led_testing_toolkit.utils.collection_name import ETALONS_COLLECTION_SUFFIX
from led_testing_toolkit.utils.data_processing import make_comparisons, read_etalon


async def make_indication_comparison_results(
    measured_data: NormalizedLedData,
    etalon_device: str,
    etalon_pattern: str,
) -> dict:
    etalon_device, etalon_pattern = etalon_device.upper(), etalon_pattern.upper()

    normalized_etalon_data = await read_etalon(etalon_pattern, f"{etalon_device}-{ETALONS_COLLECTION_SUFFIX}")
    results = await make_comparisons(normalized_etalon_data, measured_data)

    structured_results = {
        "leds": {},
        "overall_accuracy": 0,
    }
    accuracies = []

    for led, rgb_data in results.items():
        structured_results["leds"][led] = {}
        for color, data in rgb_data.items():
            structured_results["leds"][led][color] = {
                "plot": data["plot"],
                "accuracy": data["accuracy"],
            }
            if data["accuracy"] != -1.0:
                accuracies.append(data["accuracy"])

    if accuracies:
        structured_results["overall_accuracy"] = sum(accuracies) / len(accuracies)

    return structured_results
