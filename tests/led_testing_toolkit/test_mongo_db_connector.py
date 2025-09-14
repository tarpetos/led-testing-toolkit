import pytest
import os
from unittest.mock import patch

from led_testing_toolkit.mongo_db_connector import get_async_mongo_client


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("env_vars", "call_args", "expected_result", "raises_exception"),
    [
        pytest.param(
            {
                "MONGO_DB_HOST": "test_host",
                "MONGO_DB_PORT": "27018",
                "MONGO_DB_USERNAME": "test_user",
                "MONGO_DB_PASSWORD": "test_pass",
            },
            {},
            {
                "host": "test_host",
                "port": 27018,
                "username": "test_user",
                "password": "test_pass",
                "directConnection": True,
            },
            None,
            id="uses_environment_variables",
        ),
        pytest.param(
            {"MONGO_DB_HOST": "env_host", "MONGO_DB_USERNAME": "env_user", "MONGO_DB_PASSWORD": "env_pass"},
            {"host": "custom_host", "port": 27019, "username": "custom_user", "password": "custom_pass"},
            {
                "host": "custom_host",
                "port": 27019,
                "username": "custom_user",
                "password": "custom_pass",
                "directConnection": True,
            },
            None,
            id="arguments_override_environment",
        ),
        pytest.param(
            {"MONGO_DB_USERNAME": "test_user", "MONGO_DB_PASSWORD": "test_pass"},
            {},
            {
                "host": "localhost",
                "port": 27017,
                "username": "test_user",
                "password": "test_pass",
                "directConnection": True,
            },
            None,
            id="uses_default_host_and_port",
        ),
        pytest.param({"MONGO_DB_PASSWORD": "p"}, {}, None, ValueError, id="raises_error_on_missing_username"),
        pytest.param({"MONGO_DB_USERNAME": "u"}, {}, None, ValueError, id="raises_error_on_missing_password"),
    ],
)
async def test_get_async_mongo_client(env_vars, call_args, expected_result, raises_exception):
    with (
        patch("led_testing_toolkit.mongo_db_connector.load_dotenv"),
        patch("led_testing_toolkit.mongo_db_connector.AsyncMongoClient") as mock_client,
        patch.dict(os.environ, env_vars, clear=True),
    ):
        if raises_exception:
            with pytest.raises(raises_exception):
                await get_async_mongo_client(**call_args)
            mock_client.assert_not_called()
        else:
            await get_async_mongo_client(**call_args)
            mock_client.assert_called_once_with(**expected_result)
