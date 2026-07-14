from typing import Final

COLLECTION_NAME_SEPARATOR: Final[str] = "-"
ETALONS_COLLECTION_SUFFIX: Final[str] = "ETALONS"


def validate_measured_collection_name(
    name: str,
    *,
    separator: str = COLLECTION_NAME_SEPARATOR,
    etalons_suffix: str = ETALONS_COLLECTION_SUFFIX,
) -> str:
    """
    Validate and return the measured collection name.

    Args:
        name: The measured collection name.
        separator: The separator character.
        etalons_suffix: The suffix reserved for etalon collections.

    Returns:
        The uppercase validated name.

    Raises:
        ValueError: If the separator is missing or more than one is found.
        AssertionError: If the suffix is the etalons suffix.

    """
    name = name.upper()
    etalons_suffix = etalons_suffix.upper()
    if separator not in name or name.count(separator) != 1:
        raise ValueError(
            f"Measured collection name must consist of device name and "
            f"LED pattern name separated by SINGLE `{separator}`!",
        )
    _, measured_suffix = tuple(name.split(separator))
    assert measured_suffix != etalons_suffix, (
        f"Etalons collection suffix `{etalons_suffix}` is not allowed to be used as a measured collection suffix!"
    )

    return name


def validate_etalons_collection_name(
    name: str,
    *,
    suffix: str = ETALONS_COLLECTION_SUFFIX,
    separator: str = COLLECTION_NAME_SEPARATOR,
) -> str:
    """
    Validate and return the etalon collection name.

    Args:
        name: The etalons collection name.
        suffix: The expected etalons suffix.
        separator: The separator character.

    Returns:
        The uppercase validated name.

    Raises:
        ValueError: If the suffix or separator is missing, or more than one separator is found.

    """
    name = name.upper()
    suffix = suffix.upper()
    if suffix not in name or separator not in name or name.count(separator) != 1:
        raise ValueError(
            f"Etalons collection name must consist of device name and "
            f"suffix `{suffix}` separated by SINGLE `{separator}`!",
        )

    return name


def parse_collection_name(name: str, *, separator: str = COLLECTION_NAME_SEPARATOR) -> tuple[str, ...]:
    """
    Parse a collection name into parts using the given separator.

    Args:
        name: The collection name to parse.
        separator: The separator character.

    Returns:
        A tuple of string parts (usually device name and pattern name/suffix).

    Raises:
        ValueError: If the separator is missing or more than one is found.

    """
    name = name.upper()
    if separator not in name or name.count(separator) != 1:
        raise ValueError(
            f"Collection name must consist of device name and "
            f"LED pattern name OR etalons suffix name separated "
            f"by SINGLE `{separator}`!",
        )

    return tuple(name.split(separator))
