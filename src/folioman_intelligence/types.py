"""Reusable Pydantic v2 Annotated types with custom serializers."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from uuid import UUID

from pydantic import PlainSerializer

# Decimal -> float on serialization, None-safe
ConfiguredDecimal = Annotated[
    Decimal,
    PlainSerializer(lambda x: float(x), return_type=float, when_used="unless-none"),
]

# Date -> ISO 8601 string ("YYYY-MM-DD") on serialization, None-safe
ConfiguredDate = Annotated[
    date,
    PlainSerializer(lambda x: x.isoformat(), return_type=str, when_used="unless-none"),
]

# Datetime -> ISO 8601 string on serialization, None-safe
ConfiguredDatetime = Annotated[
    datetime,
    PlainSerializer(lambda x: x.isoformat(), return_type=str, when_used="unless-none"),
]

# Time -> ISO string ("HH:MM:SS") on serialization, None-safe
ConfiguredTime = Annotated[
    time,
    PlainSerializer(lambda x: x.isoformat(), return_type=str, when_used="unless-none"),
]

# Timedelta -> total seconds as float on serialization, None-safe
ConfiguredTimedelta = Annotated[
    timedelta,
    PlainSerializer(
        lambda x: x.total_seconds(), return_type=float, when_used="unless-none"
    ),
]

# UUID -> canonical string on serialization, None-safe
ConfiguredUUID = Annotated[
    UUID,
    PlainSerializer(lambda x: str(x), return_type=str, when_used="unless-none"),
]

# Path -> POSIX string on serialization, None-safe
ConfiguredPath = Annotated[
    Path,
    PlainSerializer(lambda x: x.as_posix(), return_type=str, when_used="unless-none"),
]

__all__ = [
    "ConfiguredDecimal",
    "ConfiguredDate",
    "ConfiguredDatetime",
    "ConfiguredTime",
    "ConfiguredTimedelta",
    "ConfiguredUUID",
    "ConfiguredPath",
]
