from __future__ import annotations

from collections.abc import Sequence


def make_sequence(obj: object) -> Sequence:
    string_type: bool = isinstance(obj, (str, bytes))
    return obj if isinstance(obj, Sequence) and not string_type else (obj,)
