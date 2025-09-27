from typing import Final

COLLECTION_NAME_SEPARATOR: Final[str] = "-"
ETALONS_COLLECTION_SUFFIX: Final[str] = "ETALONS"


def validate_measured_collection_name(
    name: str,
    *,
    separator: str = COLLECTION_NAME_SEPARATOR,
    etalons_suffix: str = ETALONS_COLLECTION_SUFFIX,
) -> str:
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
    name = name.upper()
    suffix = suffix.upper()
    if suffix not in name or separator not in name or name.count(separator) != 1:
        raise ValueError(
            f"Etalons collection name must consist of device name and "
            f"suffix `{suffix}` separated by SINGLE `{separator}`!",
        )

    return name


def parse_collection_name(name: str, *, separator: str = COLLECTION_NAME_SEPARATOR) -> tuple[str, ...]:
    name = name.upper()
    if separator not in name or name.count(separator) != 1:
        raise ValueError(
            f"Collection name must consist of device name and "
            f"LED pattern name OR etalons suffix name separated "
            f"by SINGLE `{separator}`!",
        )

    return tuple(name.split(separator))
