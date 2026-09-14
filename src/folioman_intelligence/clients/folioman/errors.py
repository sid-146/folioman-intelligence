"""Exception hierarchy for the Folioman client.

Keep exceptions focused, practical, and small.
"""

from __future__ import annotations

from typing import Any


class FoliomanError(Exception):
    """Base exception for all Folioman client errors."""


class FoliomanAuthError(FoliomanError):
    """Raised when authentication fails (invalid credentials, expired/rejected token refresh)."""


class FoliomanNotFoundError(FoliomanError):
    """Raised when the requested resource is not found (HTTP 404)."""


class FoliomanAPIError(FoliomanError):
    """Raised when the Folioman API returns an error response (HTTP 4xx/5xx)."""

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
