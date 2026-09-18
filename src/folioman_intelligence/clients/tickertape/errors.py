"""Exception hierarchy for the TickerTape client.

Keep exceptions focused, practical, and small.
"""

from __future__ import annotations

from typing import Any


class TickerTapeError(Exception):
    """Base exception for all TickerTape client errors."""


class TickerTapeHTTPError(TickerTapeError):
    """Raised when an HTTP request to TickerTape fails."""

    def __init__(
        self,
        message: str,
        status_code: int,
        response_data: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

    def __str__(self) -> str:
        base = super().__str__()
        if self.response_data:
            return f"[{self.status_code}] {base} - {self.response_data}"
        return f"[{self.status_code}] {base}"


class TickerTapeNotFoundError(TickerTapeHTTPError):
    """Raised when the requested TickerTape resource is not found (HTTP 404)."""


class TickerTapeParseError(TickerTapeError):
    """Raised when parsing response data (XML sitemap, HTML, __NEXT_DATA__) fails."""
