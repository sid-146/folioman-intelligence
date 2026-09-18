"""Parser for TickerTape ETF pages."""

from __future__ import annotations

from typing import Any

from folioman_intelligence.clients.tickertape.parsers.base import BaseParser


class ETFParser(BaseParser[Any]):
    """Parser for ETF pages and Next.js hydration payload."""

    def parse(self, content: Any) -> Any:
        raise NotImplementedError("ETFParser will be implemented in a future update.")
