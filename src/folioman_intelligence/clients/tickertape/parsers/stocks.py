"""Parser for TickerTape stock pages."""

from __future__ import annotations

from typing import Any

from folioman_intelligence.clients.tickertape.parsers.base import BaseParser


class StockParser(BaseParser[Any]):
    """Parser for stock pages and Next.js hydration payload."""

    def parse(self, content: Any) -> Any:
        raise NotImplementedError("StockParser will be implemented in a future update.")
