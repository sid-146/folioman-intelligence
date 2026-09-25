"""Folioman Intelligence Service."""

from folioman_client import (
    FoliomanAPIError,
    FoliomanAuthError,
    FoliomanClient,
    FoliomanError,
    FoliomanNotFoundError,
)
from tickertape import (
    TickerTapeClient,
    TickerTapeError,
    TickerTapeHTTPError,
    TickerTapeNotFoundError,
    TickerTapeParseError,
)
from folioman_intelligence.config import FoliomanSettings, settings
from folioman_intelligence.types import (
    ConfiguredDate,
    ConfiguredDatetime,
    ConfiguredDecimal,
    ConfiguredPath,
    ConfiguredTime,
    ConfiguredTimedelta,
    ConfiguredUUID,
)

__all__ = [
    "FoliomanClient",
    "FoliomanError",
    "FoliomanAuthError",
    "FoliomanNotFoundError",
    "FoliomanAPIError",
    "TickerTapeClient",
    "TickerTapeError",
    "TickerTapeHTTPError",
    "TickerTapeNotFoundError",
    "TickerTapeParseError",
    "FoliomanSettings",
    "settings",
    "ConfiguredDecimal",
    "ConfiguredDate",
    "ConfiguredDatetime",
    "ConfiguredTime",
    "ConfiguredTimedelta",
    "ConfiguredUUID",
    "ConfiguredPath",
]
