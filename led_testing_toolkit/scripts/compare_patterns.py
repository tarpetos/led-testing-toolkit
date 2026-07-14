import argparse
import asyncio

from led_testing_toolkit.utils.data_processing import read_measured
from led_testing_toolkit.utils.make_indication_comparison import (
    make_indication_comparison_results,
)


async def main() -> None:
    """
    Main entry point for comparing a randomly selected measured pattern with an etalon.

    This function parses command-line arguments to obtain the measured collection name,
    etalon device, and etalon pattern. It then reads the measured data and compares it
    against the etalon, displaying the comparison results.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-mc",
        "--measured-collection",
        help="The name of the collection from which the measured "
        "pattern will be randomly selected for comparison with the etalon.",
        required=True,
    )
    parser.add_argument(
        "-ed",
        "--etalon-device",
        help="The name of the device used in the etalon collection name.",
        required=True,
    )
    parser.add_argument(
        "-ep",
        "--etalon-pattern",
        help="The name of the indication pattern stored in the etalon collection.",
        required=True,
    )
    cli_args = parser.parse_args()

    normalized_measured_data = await read_measured(cli_args.measured_collection, get_random=True)
    await make_indication_comparison_results(
        normalized_measured_data,
        cli_args.etalon_device,
        cli_args.etalon_pattern,
    )


if __name__ == "__main__":
    asyncio.run(main())
