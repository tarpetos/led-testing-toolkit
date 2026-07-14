import os
import importlib
from unittest.mock import patch


def test_config_default():
    with patch.dict(os.environ, {}, clear=True):
        # We need to reload the module to re-evaluate the constants
        import api.core.config as config
        importlib.reload(config)
        assert config.API_HOST == "127.0.0.1"
        assert config.API_PORT == 8080


def test_config_override():
    with patch.dict(os.environ, {"API_HOST": "0.0.0.0", "API_PORT": "9090"}, clear=True):
        import api.core.config as config
        importlib.reload(config)
        assert config.API_HOST == "0.0.0.0"
        assert config.API_PORT == 9090
