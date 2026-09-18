"""Parser for TickerTape screens pages."""

from __future__ import annotations

from typing import Any

from folioman_intelligence.clients.tickertape.parsers.base import BaseParser


class ScreenParser(BaseParser[Any]):
    """Parser for screen results and data."""

    def parse(self, content: Any) -> Any:
        raise NotImplementedError(
            "ScreenParser will be implemented in a future update."
        )
