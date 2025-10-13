from collections import defaultdict

from led_testing_toolkit.mongo_db_connector import MongoDbConnector
from led_testing_toolkit.utils.collection_name import (
    ETALONS_COLLECTION_SUFFIX,
    parse_collection_name,
)


class DeviceService:
    @staticmethod
    async def get_all_devices_data() -> dict:
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
        try:
            async with MongoDbConnector() as connector:
                await connector.use_collection(collection_name, auto_create=False)
                records = await connector.read_field("_id")
                return sorted([str(r) for r in records])
        except Exception:
            return []

    @staticmethod
    async def get_etalon_patterns(etalon_collection: str) -> list[str]:
        async with MongoDbConnector() as connector:
            await connector.use_collection(etalon_collection, auto_create=False)
            patterns = await connector.read_field("_id")
            return sorted([p for p in patterns if isinstance(p, str)])


device_service = DeviceService()
