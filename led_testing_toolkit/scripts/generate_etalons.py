import argparse
import asyncio

from loguru import logger

from led_testing_toolkit.mongo_db_connector import MongoDbConnector
from led_testing_toolkit.utils.collection_name import (
    ETALONS_COLLECTION_SUFFIX,
    parse_collection_name,
)
from led_testing_toolkit.utils.data_processing import generate_etalon


async def _get_collections(device_name: str | None = None, pattern_name: str | None = None) -> list[str]:
    async with MongoDbConnector() as connector:
        collection_names = await connector.list_collections()

    device_name_filter, pattern_name_filter = set(), set()
    for name in collection_names:
        if device_name and name.startswith(device_name.upper()):
            device_name_filter.add(name)
        if pattern_name and name.endswith(pattern_name.upper()):
            pattern_name_filter.add(name)

    if filtered_collections := list(device_name_filter.intersection(pattern_name_filter)):
        return filtered_collections

    return collection_names


async def _generate_etalons(collection_names: list[str]) -> None:
    if not collection_names:
        logger.warning("Collection names list is empty! Nothing to generate.")
        return

    for measure_collection_name in collection_names:
        try:
            _, suffix = parse_collection_name(measure_collection_name)
            if suffix != ETALONS_COLLECTION_SUFFIX:
                logger.debug(f"Generating etalon based on data from {measure_collection_name} collection...")
                etalon_collection_name = await generate_etalon(measure_collection_name)
                logger.success(f"Etalon stored in {etalon_collection_name} collection successfully!")
        except Exception as e:
            logger.error(f"`{measure_collection_name}` skipped! Reason: {e!s}")


async def main() -> None:
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

    collections = await _get_collections(cli_args.device_name, cli_args.pattern_name)
    await _generate_etalons(collections)


if __name__ == "__main__":
    asyncio.run(main())
