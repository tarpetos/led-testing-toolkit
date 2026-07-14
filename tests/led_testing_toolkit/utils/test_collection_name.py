import pytest
from led_testing_toolkit.utils.collection_name import (
    validate_measured_collection_name,
    validate_etalons_collection_name,
    parse_collection_name,
)


def test_validate_measured_collection_name():
    assert validate_measured_collection_name("DEV-PAT") == "DEV-PAT"

    with pytest.raises(ValueError, match="Measured collection name must consist of device name and"):
        validate_measured_collection_name("DEVPAT")

    with pytest.raises(ValueError, match="Measured collection name must consist of device name and"):
        validate_measured_collection_name("DEV-PAT-EXTRA")

    with pytest.raises(AssertionError, match="Etalons collection suffix"):
        validate_measured_collection_name("DEV-ETALONS")


def test_validate_etalons_collection_name():
    assert validate_etalons_collection_name("DEV-ETALONS") == "DEV-ETALONS"

    with pytest.raises(ValueError, match="Etalons collection name must consist of device name and"):
        validate_etalons_collection_name("DEVETALONS")

    with pytest.raises(ValueError, match="Etalons collection name must consist of device name and"):
        validate_etalons_collection_name("DEV-PAT")

    with pytest.raises(ValueError, match="Etalons collection name must consist of device name and"):
        validate_etalons_collection_name("DEV-ETALONS-EXTRA")


def test_parse_collection_name():
    assert parse_collection_name("DEV-PAT") == ("DEV", "PAT")

    with pytest.raises(ValueError, match="Collection name must consist of device name and"):
        parse_collection_name("DEVPAT")

    with pytest.raises(ValueError, match="Collection name must consist of device name and"):
        parse_collection_name("DEV-PAT-EXTRA")
