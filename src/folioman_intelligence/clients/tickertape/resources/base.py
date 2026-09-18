"""Base resource class for TickerTape client."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from folioman_intelligence.clients.tickertape.client import TickerTapeClient


class _BaseResource:
    """Base resource associated with a TickerTapeClient instance."""

    def __init__(self, client: TickerTapeClient) -> None:
        self._client = client
