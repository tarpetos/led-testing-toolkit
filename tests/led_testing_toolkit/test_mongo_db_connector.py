import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from pymongo.errors import DuplicateKeyError
from led_testing_toolkit.mongo_db_connector import get_async_mongo_client, MongoDbConnector

@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.close = AsyncMock()
    
    db = AsyncMock()
    client.__getitem__.return_value = db
    
    collection = AsyncMock()
    db.__getitem__.return_value = collection
    
    return client

@pytest.mark.anyio
async def test_get_async_mongo_client():
    with patch.dict(os.environ, {"MONGO_DB_USERNAME": "user", "MONGO_DB_PASSWORD": "password"}):
        client = await get_async_mongo_client()
        assert client is not None
        await client.close()

@pytest.mark.anyio
async def test_get_async_mongo_client_missing_creds():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            await get_async_mongo_client()

@pytest.mark.anyio
async def test_context_manager(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        with patch.dict(os.environ, {"MONGO_DB_NAME": "test_db"}):
            async with MongoDbConnector() as connector:
                assert connector.client is not None
                assert connector.db is not None
            mock_client.close.assert_called_once()

@pytest.mark.anyio
async def test_initialize(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        await connector.initialize()
        assert connector.db is not None

@pytest.mark.anyio
async def test_list_collections(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        mock_client["test_db"].list_collection_names = AsyncMock(return_value=["coll1", "coll2"])
        collections = await connector.list_collections()
        assert collections == ["coll1", "coll2"]

@pytest.mark.anyio
async def test_use_collection(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        db = mock_client["test_db"]
        db.list_collection_names = AsyncMock(return_value=["coll1"])
        db.create_collection = AsyncMock()
        
        await connector.use_collection("coll1")
        assert connector.collection is not None
        
        await connector.use_collection("coll2", auto_create=True)
        db.create_collection.assert_called_once_with("coll2")
        
        with pytest.raises(ValueError):
            await connector.use_collection("coll3", auto_create=False)

@pytest.mark.anyio
async def test_create(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        db = mock_client["test_db"]
        db.create_collection = AsyncMock()
        
        coll = await connector.create("new_coll")
        db.create_collection.assert_called_once_with("new_coll")
        assert coll is not None

@pytest.mark.anyio
async def test_read_without_collection(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        with pytest.raises(ValueError):
            await connector.read({})

@pytest.mark.anyio
async def test_read(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        connector.collection = mock_client["test_db"]["coll"]
        
        # single
        connector.collection.find_one = AsyncMock(return_value={"id": 1})
        res = await connector.read({})
        assert res == {"id": 1}
        
        # no data warning
        connector.collection.find_one = AsyncMock(return_value=None)
        res = await connector.read({})
        assert res is None
        
        # many
        async def async_gen():
            yield {"id": 1}
            yield {"id": 2}
        connector.collection.find = MagicMock(return_value=async_gen())
        res = await connector.read({}, find_many=True)
        assert len(res) == 2

@pytest.mark.anyio
async def test_read_random(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        connector.collection = mock_client["test_db"]["coll"]
        
        async def async_gen():
            yield {"id": 1}
        connector.collection.aggregate = AsyncMock(return_value=async_gen())
        res = await connector.read_random()
        assert res == {"id": 1}

        connector.collection = None
        with pytest.raises(ValueError):
            await connector.read_random()

@pytest.mark.anyio
async def test_read_random_empty(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        connector.collection = mock_client["test_db"]["coll"]
        
        async def async_gen():
            if False:
                yield None
        connector.collection.aggregate = AsyncMock(return_value=async_gen())
        res = await connector.read_random()
        assert res is None

@pytest.mark.anyio
async def test_read_field(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        connector.collection = mock_client["test_db"]["coll"]
        
        connector.collection.distinct = AsyncMock(return_value=["val1", "val2"])
        res = await connector.read_field("field")
        assert res == ["val1", "val2"]

        connector.collection = None
        with pytest.raises(ValueError):
            await connector.read_field("field")

@pytest.mark.anyio
async def test_update(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        connector.collection = mock_client["test_db"]["coll"]
        
        connector.collection.update_one = AsyncMock(return_value="success")
        res = await connector.update({}, {"field": "val"})
        assert res == "success"

        connector.collection = None
        with pytest.raises(ValueError):
            await connector.update({}, {})

@pytest.mark.anyio
async def test_delete(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        connector.collection = mock_client["test_db"]["coll"]
        
        connector.collection.delete_one = AsyncMock(return_value="deleted")
        res = await connector.delete({})
        assert res == "deleted"
        
        connector.collection.delete_many = AsyncMock(return_value="deleted_many")
        res = await connector.delete({}, del_many=True)
        assert res == "deleted_many"

        connector.collection = None
        with pytest.raises(ValueError):
            await connector.delete({})

@pytest.mark.anyio
async def test_insert(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        connector.collection = mock_client["test_db"]["coll"]
        
        connector.collection.insert_one = AsyncMock(return_value="inserted")
        res = await connector.insert({"id": 1})
        assert res == "inserted"
        
        connector.collection.insert_many = AsyncMock(return_value="inserted_many")
        res = await connector.insert([{"id": 1}], insert_many=True)
        assert res == "inserted_many"
        
        connector.collection.insert_one.side_effect = DuplicateKeyError("dup")
        res = await connector.insert({"id": 1})
        assert res is None

        connector.collection = None
        with pytest.raises(ValueError):
            await connector.insert({})

@pytest.mark.anyio
async def test_careful_insert(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        connector.collection = mock_client["test_db"]["coll"]
        
        connector.read = AsyncMock(return_value=None)
        connector.insert = AsyncMock(return_value="inserted")
        res = await connector.careful_insert({"id": 1})
        assert res == "inserted"
        
        connector.read.return_value = {"id": 1}
        res = await connector.careful_insert({"id": 1})
        assert res is None

@pytest.mark.anyio
async def test_upsert(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        connector.collection = mock_client["test_db"]["coll"]
        
        connector.collection.update_one = AsyncMock(return_value="upserted")
        res = await connector.upsert({"id": 1})
        assert res == "upserted"
        
        connector.collection.update_many = AsyncMock(return_value="upserted_many")
        res = await connector.upsert([{"id": 1}], many=True)
        assert res == "upserted_many"

        connector.collection = None
        with pytest.raises(ValueError):
            await connector.upsert({})

@pytest.mark.anyio
async def test_drop(mock_client):
    with patch("led_testing_toolkit.mongo_db_connector.get_async_mongo_client", return_value=mock_client):
        connector = MongoDbConnector(db_name="test_db")
        db = mock_client["test_db"]
        db.drop_collection = AsyncMock(return_value="dropped")
        
        res = await connector.drop("coll")
        assert res == "dropped"

