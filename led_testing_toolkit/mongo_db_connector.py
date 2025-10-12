from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Self

import loguru
import pymongo.errors
from dotenv import load_dotenv
from pymongo import AsyncMongoClient

if TYPE_CHECKING:
    from collections.abc import Mapping

    from loguru._logger import Logger
    from pymongo.asynchronous.collection import AsyncCollection
    from pymongo.asynchronous.database import AsyncDatabase
    from pymongo.results import (
        DeleteResult,
        InsertManyResult,
        InsertOneResult,
        UpdateResult,
    )


async def get_async_mongo_client(
    host: str | None = None,
    port: int | None = None,
    username: str | None = None,
    password: str | None = None,
) -> AsyncMongoClient:
    """
    Initializes and return an async MongoDB client.
    Utilizes a ``.env`` file to configure default environment variables for MongoDB connection settings.

    The file should include the following required fields:
        >>> MONGO_DB_HOST=...
        ... MONGO_DB_PORT=...
        ... MONGO_DB_USERNAME=...
        ... MONGO_DB_PASSWORD=...

    Args:
        host: MongoDB host address.
        port: MongoDB port number.
        username: MongoDB username.
        password: MongoDB password.

    Returns:
        Initialized AsyncMongoClient instance.

    """
    load_dotenv()

    host = host or os.getenv("MONGO_DB_HOST", "localhost")
    port = port or int(os.getenv("MONGO_DB_PORT", "27017"))
    username = username or os.getenv("MONGO_DB_USERNAME")
    password = password or os.getenv("MONGO_DB_PASSWORD")

    if username is None or password is None:
        raise ValueError("One or more values required to create a client are not initialized!")

    return AsyncMongoClient(**vars(), directConnection=True)


class MongoDbConnector:
    def __init__(
        self,
        db_name: str | None = None,
        mongo_client: AsyncMongoClient | None = None,
        logger: Logger = loguru.logger,
    ) -> None:
        self.client = mongo_client
        self.db_name = db_name
        self.db: AsyncDatabase | None = None
        self.collection: AsyncCollection | None = None
        self.logger: Logger = logger

    async def __aenter__(self) -> Self:
        await self.initialize()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def initialize(self) -> None:
        """Initializes the connector with the database connection."""
        if self.client is None:
            self.client = await get_async_mongo_client()
        self.db_name = self.db_name or os.getenv("MONGO_DB_NAME")
        self.db = self.client[self.db_name]

    async def list_collections(self) -> list[str]:
        """Lists all collections in the database."""
        if self.db is None:
            await self.initialize()
        return await self.db.list_collection_names()

    async def use_collection(self, collection_name: str, *, auto_create: bool = True) -> None:
        """
        Sets the active collection.

        Args:
            collection_name: Name of the collection to use.
            auto_create: Whether to create the collection if it doesn't exist.

        Returns:
            None

        """
        if self.db is None:
            await self.initialize()

        collection_names = await self.db.list_collection_names()
        if collection_name not in collection_names:
            if auto_create:
                await self.create(collection_name)
            else:
                raise ValueError(f"Collection {collection_name} does not exist!")

        self.collection = self.db[collection_name]

    async def create(self, collection_name: str) -> AsyncCollection[Mapping[str, Any] | Any]:
        """
        Creates a new collection.

        Args:
            collection_name: Collection name.

        Returns:
             Created collection instance.

        """
        if self.db is None:
            await self.initialize()

        await self.db.create_collection(collection_name)
        return self.db[collection_name]

    async def read(
        self,
        query: dict[str, Any],
        projection: dict[str, int | str] | None = None,
        find_many: bool = False,
    ) -> list[Mapping[str, Any]] | Mapping[str, Any] | None:
        """
        Reads data from the collection.

        Args:
            query: Query filter dictionary.
            projection: Fields to include or exclude.
            find_many: Whether to find multiple documents, defaults to False.

        Returns:
            Async iterator for multiple results or single document or None.

        """
        if self.collection is None:
            raise ValueError("No collection selected! Call `use_collection` first.")

        if find_many:
            return [item async for item in self.collection.find(query, projection)]

        result = await self.collection.find_one(query, projection)
        if not query and result is None:
            self.logger.warning(f"Collection {self.collection.name} has no data!")
        return result

    async def read_random(self) -> Mapping[str, Any] | None:
        """
        Reads a random document from the collection.

        Returns:
            A single random document or None.

        """
        if self.collection is None:
            raise ValueError("No collection selected! Call `use_collection` first.")

        pipeline = [{"$sample": {"size": 1}}]
        async for doc in await self.collection.aggregate(pipeline):
            return doc
        return None

    async def read_field(self, field: str) -> list:
        """
        Gets distinct values for a specific field.

        Args:
            field: field name to query
        Returns:
            List of distinct values.

        """
        if self.collection is None:
            raise ValueError("No collection selected! Call `use_collection` first.")

        return await self.collection.distinct(field)

    async def update(self, query: dict[str, Any], new_data: dict[str, Any]) -> UpdateResult | None:
        """
        Updates a single document in the collection.

        Args:
            query: Query filter dictionary.
            new_data: Data to update.

        Returns:
            Update operation result or None.

        """
        if self.collection is None:
            raise ValueError("No collection selected! Call `use_collection` first.")

        return await self.collection.update_one(query, {"$set": new_data})

    async def delete(self, query: dict[str, Any], del_many: bool = False) -> DeleteResult | None:
        """
        Deletes documents from the collection.

        Args:
            query: Query filter dictionary.
            del_many: Whether to delete multiple documents, defaults to False.

        Returns:
            Delete operation result or None.

        """
        if self.collection is None:
            raise ValueError("No collection selected! Call `use_collection` first.")

        if del_many:
            return await self.collection.delete_many(query)
        return await self.collection.delete_one(query)

    async def insert(
        self,
        query: dict[str, Any] | list[dict[str, Any]],
        insert_many: bool = False,
    ) -> InsertOneResult | InsertManyResult | None:
        """
        Inserts documents into the collection.

        Args:
            query: Document or list of documents to insert.
            insert_many: Whether to insert multiple documents, defaults to False.

        Returns:
            Insert operation result or None.

        """
        if self.collection is None:
            raise ValueError("No collection selected! Call `use_collection` first.")

        try:
            if insert_many and isinstance(query, list):
                return await self.collection.insert_many(query)
            return await self.collection.insert_one(query)
        except pymongo.errors.DuplicateKeyError:
            self.logger.exception("Duplicate key found!")

    async def careful_insert(self, query: dict[str, Any], data: dict[str, Any] | None = None) -> InsertOneResult | None:
        """
        Inserts a document only if it doesn't exist.

        Args:
            query: Query filter dictionary.
            data: Data to insert if different from query, defaults to None.

        Returns:
            Insert operation result or None.

        """
        status = await self.read(query)
        if status is None:
            return await self.insert(query) if data is None else await self.insert(data)
        self.logger.warning("Row with such data already exists!")
        return None

    async def upsert(
        self,
        query: dict[str, Any] | list[dict[str, Any]],
        update_data: dict[str, Any] | None = None,
        many: bool = False,
    ) -> UpdateResult | list[UpdateResult] | None:
        """
        Inserts or updates one or multiple documents in the collection.

        Args:
            query: Query filter dictionary or list of query filter dictionaries.
            update_data: Data to set on update, defaults to query if None.
            many: Whether to process multiple documents, defaults to False.

        Returns:
            Update operation result or None.

        """
        if self.collection is None:
            raise ValueError("No collection selected! Call `use_collection` first.")

        if many and isinstance(query, list):
            filter_query = {"$or": query}
            data = update_data if update_data is not None else query[0]
            return await self.collection.update_many(filter_query, {"$set": data}, upsert=True)
        single_query = query if not isinstance(query, list) else query[0]
        data = update_data if update_data is not None else single_query
        return await self.collection.update_one(single_query, {"$set": data}, upsert=True)

    async def drop(self, collection_name: str) -> dict[str, Any] | None:
        """
        Drop a collection.

        Args:
            collection_name: Name of the collection to drop.

        Returns:
            Drop operation result or None.

        """
        if self.db is None:
            await self.initialize()

        return await self.db.drop_collection(collection_name)

    async def close(self) -> None:
        """Closes the database connection."""
        if self.client:
            await self.client.close()
