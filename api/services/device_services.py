from collections import defaultdict

from led_testing_toolkit.mongo_db_connector import MongoDbConnector
from led_testing_toolkit.utils.collection_name import (
    ETALONS_COLLECTION_SUFFIX,
    parse_collection_name,
)


class DeviceService:
    """Service class for managing LED device data and patterns."""

    @staticmethod
    async def get_all_devices_data() -> dict:
        """
        Retrieves data for all available LED devices.

        Returns:
            dict: A dictionary mapping device names to their etalon and measured collection names.

        """
        devices_data = defaultdict(lambda: {"etalon_collection": None, "measured_collections": []})

        async with MongoDbConnector() as connector:
            collection_names = await connector.list_collections()

            for name in collection_names:
                try:
                    device_name, suffix = parse_collection_name(name)
                    if suffix == ETALONS_COLLECTION_SUFFIX:
                        devices_data[device_name]["etalon_collection"] = name
                    else:
                        devices_data[device_name]["measured_collections"].append(name)
                except ValueError:
                    continue
        return dict(devices_data)

    @staticmethod
    async def get_measured_records(collection_name: str) -> list[str]:
        """
        Get measured records for a specific collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            list[str]: A list of record IDs as strings.

        """
        try:
            async with MongoDbConnector() as connector:
                await connector.use_collection(collection_name, auto_create=False)
                records = await connector.read_field("_id")
                return sorted([str(r) for r in records])
        except Exception:
            return []

    @staticmethod
    async def get_etalon_patterns(etalon_collection: str) -> list[str]:
        """
        Get etalon patterns for a specific etalon collection.

        Args:
            etalon_collection (str): The name of the etalon collection.

        Returns:
            list[str]: A list of pattern IDs as strings.

        """
        async with MongoDbConnector() as connector:
            await connector.use_collection(etalon_collection, auto_create=False)
            patterns = await connector.read_field("_id")
            return sorted([p for p in patterns if isinstance(p, str)])


device_service = DeviceService()
