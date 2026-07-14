import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from led_testing_toolkit.led_modeler.generator import LedGenerator
from led_testing_toolkit.led_modeler.models import AppConfig, FadePatternConfig
from led_testing_toolkit.led_modeler.patterns import FadePattern
from led_testing_toolkit.led_modeler.simulator import PhotoresistorSimulator


@pytest.fixture
def base_config():
    return AppConfig(
        mode="instant",
        duration=1.0,
        output_file="out.json",
        interval="100",
        noise=0.0,
        lag=0.0,
        reporting_chance=1.0,
        num_leds=1,
        color="255,255,255",
        sequence="all_at_once",
    )


def test_generator_instant(base_config):
    simulator = PhotoresistorSimulator(["LED1"], noise_level=0.0, lag=0.0, reporting_chance=1.0)
    pattern_config = FadePatternConfig(
        type="fade", led_ids=[1], duration=1.0, peak_time=0.5, start_time=0.0, end_time=1.0
    )
    pattern = FadePattern(pattern_config)

    logger = MagicMock()
    gen = LedGenerator(base_config, [pattern], simulator, logger)
    gen.generate_instant()

    # Assert logs happened
    assert logger.debug.call_count > 0


def test_generator_simulate(base_config):
    base_config.mode = "simulate"
    base_config.interval = "10"  # 10ms
    base_config.duration = 0.05  # 50ms
    base_config.interval_ms_range = (10, 10)

    simulator = PhotoresistorSimulator(["LED1"], noise_level=0.0, lag=0.0, reporting_chance=1.0)
    pattern_config = FadePatternConfig(
        type="fade", led_ids=[1], duration=1.0, peak_time=0.5, start_time=0.0, end_time=1.0
    )
    pattern = FadePattern(pattern_config)

    logger = MagicMock()
    gen = LedGenerator(base_config, [pattern], simulator, logger)

    asyncio.run(gen.run())
    assert logger.debug.call_count > 0


def test_generator_keyboard_interrupt(base_config):
    base_config.mode = "simulate"
    simulator = PhotoresistorSimulator(["LED1"], noise_level=0.0, lag=0.0, reporting_chance=1.0)
    logger = MagicMock()
    gen = LedGenerator(base_config, [], simulator, logger)

    with patch.object(gen, "_simulation_loop", side_effect=KeyboardInterrupt):
        asyncio.run(gen.run())

    logger.warning.assert_called_with("Simulation interrupted by user.")


def test_save_to_db(base_config):
    base_config.mode = "instant"
    simulator = PhotoresistorSimulator(["LED1"], noise_level=0.0, lag=0.0, reporting_chance=1.0)
    pattern_config = FadePatternConfig(
        type="fade", led_ids=[1], duration=1.0, peak_time=0.5, start_time=0.0, end_time=1.0
    )
    pattern = FadePattern(pattern_config)

    logger = MagicMock()
    gen = LedGenerator(base_config, [pattern], simulator, logger, save_to_db_collection="device-test_col")

    # mock MongoDBConnector
    with patch("led_testing_toolkit.led_modeler.generator.MongoDbConnector") as mock_connector_cls:
        mock_connector = AsyncMock()
        mock_connector.__aenter__.return_value = mock_connector
        mock_connector.insert.return_value = MagicMock(inserted_id="123")
        mock_connector_cls.return_value = mock_connector

        asyncio.run(gen.run())

        mock_connector.use_collection.assert_called_with("DEVICE-TEST_COL", auto_create=True)
        mock_connector.insert.assert_called_once()
        logger.success.assert_called_with("Successfully inserted document with _id: 123")


def test_save_to_db_empty(base_config):
    base_config.mode = "instant"
    base_config.duration = 0.0  # No iterations
    simulator = PhotoresistorSimulator(["LED1"], noise_level=0.0, lag=0.0, reporting_chance=1.0)
    logger = MagicMock()
    gen = LedGenerator(base_config, [], simulator, logger, save_to_db_collection="device-test_col")

    asyncio.run(gen.run())
    logger.warning.assert_any_call("No data was generated to save to the database.")


def test_save_to_db_failure(base_config):
    base_config.mode = "instant"
    simulator = PhotoresistorSimulator(["LED1"], noise_level=0.0, lag=0.0, reporting_chance=1.0)
    pattern_config = FadePatternConfig(
        type="fade", led_ids=[1], duration=1.0, peak_time=0.5, start_time=0.0, end_time=1.0
    )
    pattern = FadePattern(pattern_config)

    logger = MagicMock()
    gen = LedGenerator(base_config, [pattern], simulator, logger, save_to_db_collection="device-test_col")

    # mock MongoDBConnector
    with patch("led_testing_toolkit.led_modeler.generator.MongoDbConnector") as mock_connector_cls:
        mock_connector = AsyncMock()
        mock_connector.__aenter__.return_value = mock_connector
        mock_connector.insert.return_value = MagicMock(inserted_id=None)
        mock_connector_cls.return_value = mock_connector

        asyncio.run(gen.run())
        logger.error.assert_any_call("Failed to insert document into database.")


def test_save_to_db_exception(base_config):
    base_config.mode = "instant"
    simulator = PhotoresistorSimulator(["LED1"], noise_level=0.0, lag=0.0, reporting_chance=1.0)
    pattern_config = FadePatternConfig(
        type="fade", led_ids=[1], duration=1.0, peak_time=0.5, start_time=0.0, end_time=1.0
    )
    pattern = FadePattern(pattern_config)

    logger = MagicMock()
    gen = LedGenerator(base_config, [pattern], simulator, logger, save_to_db_collection="device-test_col")

    # mock MongoDBConnector
    with patch("led_testing_toolkit.led_modeler.generator.MongoDbConnector") as mock_connector_cls:
        mock_connector = AsyncMock()
        mock_connector.__aenter__.return_value = mock_connector
        mock_connector.insert.side_effect = Exception("DB Error")
        mock_connector_cls.return_value = mock_connector

        asyncio.run(gen.run())
        logger.error.assert_called_with("An error occurred while saving to MongoDB: DB Error")


def test_format_log_message_empty(base_config):
    simulator = PhotoresistorSimulator(["LED1"], noise_level=0.0, lag=0.0, reporting_chance=1.0)
    gen = LedGenerator(base_config, [], simulator, MagicMock())
    assert gen._format_log_message({}) == ""
