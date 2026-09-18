"""Base parser interface for TickerTape response parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class BaseParser(ABC, Generic[T]):
    """Abstract base class for all TickerTape content and response parsers."""

    @abstractmethod
    def parse(self, content: Any) -> T:
        """Parse raw content (string, bytes, or parsed structure) into domain models.

        Args:
            content: Raw response body or structured data.

        Returns:
            Parsed domain model or collection of models.

        Raises:
            TickerTapeParseError: If parsing fails.
        """
        raise NotImplementedError
