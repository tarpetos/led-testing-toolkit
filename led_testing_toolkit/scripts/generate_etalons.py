import argparse
import asyncio

from loguru import logger

from led_testing_toolkit.mongo_db_connector import MongoDbConnector
from led_testing_toolkit.utils.collection_name import (
    ETALONS_COLLECTION_SUFFIX,
    parse_collection_name,
)
from led_testing_toolkit.utils.data_processing import generate_etalon


async def _get_collections(
    device_name: str | None = None,
    pattern_name: str | None = None,
    *,
    force_specific_collection: bool = False,
) -> list[str]:
    """
    Retrieve a list of collection names from MongoDB based on device and pattern filters.

    Args:
        device_name: Optional device name prefix to filter by.
        pattern_name: Optional pattern name suffix to filter by.
        force_specific_collection: If True, requires exact match for `DEVICE-PATTERN`.

    Returns:
        A list of matching collection names.

    Raises:
        ValueError: If force_specific_collection is True and the requested collection is not found.

    """
    async with MongoDbConnector() as connector:
        collection_names = await connector.list_collections()

    if force_specific_collection:
        device_name = device_name or ""
        pattern_name = pattern_name or ""
        if (collection_name := f"{device_name.upper()}-{pattern_name.upper()}") not in collection_names:
            raise ValueError(f"Collection `{collection_name}` not found!")

    device_name_filter, pattern_name_filter = set(), set()
    for name in collection_names:
        if device_name and name.startswith(device_name.upper()):
            device_name_filter.add(name)
        if pattern_name and name.endswith(pattern_name.upper()):
            pattern_name_filter.add(name)

    if filtered_collections := list(device_name_filter.intersection(pattern_name_filter)):
        return filtered_collections

    return collection_names


async def _generate_etalons(collection_names: list[str]) -> tuple[list[str], dict[str, dict[str, str]]]:
    """
    Generate etalons for the specified collections and store them in the database.

    Args:
        collection_names: A list of measured collection names.

    Returns:
        A tuple containing a list of generated etalon collection names and a dictionary of plots.

    """
    if not collection_names:
        logger.warning("Collection names list is empty! Nothing to generate.")
        return [], {}

    generated_etalons = []
    plots = {}
    for measure_collection_name in collection_names:
        try:
            _, suffix = parse_collection_name(measure_collection_name)
            if suffix != ETALONS_COLLECTION_SUFFIX:
                logger.debug(f"Generating etalon based on data from {measure_collection_name} collection...")
                etalon_collection_name, etalon_plots = await generate_etalon(measure_collection_name)
                logger.success(f"Etalon stored in {etalon_collection_name} collection successfully!")
                generated_etalons.append(etalon_collection_name)
                plots.update(etalon_plots)
        except Exception as e:
            logger.error(f"`{measure_collection_name}` skipped! Reason: {e!s}")
    return generated_etalons, plots


async def generate_etalons_main(
    device_name: str,
    pattern_name: str,
    force_specific_collection: bool,
) -> tuple[list[str], dict[str, dict[str, str]]]:
    """
    Main logic to get collections and generate etalons for them.

    Args:
        device_name: The device name filter.
        pattern_name: The pattern name filter.
        force_specific_collection: Whether to force exact match of `DEVICE-PATTERN`.

    Returns:
        A tuple with generated etalons list and the plot dictionary.

    """
    collections = await _get_collections(device_name, pattern_name, force_specific_collection=force_specific_collection)
    return await _generate_etalons(collections)


async def main() -> None:
    """Main entry point for generating etalons from command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-dn",
        "--device-name",
        help="Device name prefix that will be used to generate etalon(s)",
    )
    parser.add_argument(
        "-pn",
        "--pattern-name",
        help="Indication pattern that will be used to generate specific etalon",
    )
    cli_args = parser.parse_args()

    await generate_etalons_main(cli_args.device_name, cli_args.pattern_name, False)


if __name__ == "__main__":
    asyncio.run(main())
