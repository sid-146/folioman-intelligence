"""Sitemap resource for TickerTape client."""

from __future__ import annotations

import logging
from typing import Optional

from folioman_intelligence.clients.tickertape.errors import TickerTapeParseError
from folioman_intelligence.clients.tickertape.models import SitemapReference, SitemapURL
from folioman_intelligence.clients.tickertape.parsers.sitemap import SitemapParser
from folioman_intelligence.clients.tickertape.resources.base import _BaseResource

logger = logging.getLogger(__name__)


class SitemapResource(_BaseResource):
    """Resource managing XML sitemaps with local persistent caching."""

    async def get(
        self,
        category: str = "mf",
        *,
        force_refresh: bool = False,
    ) -> list[SitemapURL]:
        """Get parsed sitemap URLs for a category.

        By default, loads from persistent disk cache (.cache/tickertape)
        unless force_refresh is True or cache does not exist.

        Args:
            category: Category key ('mf', 'stocks', 'etf', etc.) or custom sitemap key.
            force_refresh: If True, bypasses local cache, fetches live XML, and updates cache.

        Returns:
            List of parsed SitemapURL items.
        """
        category_key = category.lower().strip()

        # Check disk cache unless forced refresh
        if not force_refresh:
            cached_items = self._client.cache_manager.load(category_key)
            if cached_items is not None:
                logger.debug(
                    "Loaded %d sitemap items for '%s' from cache",
                    len(cached_items),
                    category_key,
                )
                return cached_items

        # Fetch live XML and refresh cache
        return await self.refresh(category_key)

    async def refresh(self, category: str = "mf") -> list[SitemapURL]:
        """Fetch live XML sitemap, parse it, update the local cache, and return items.

        Args:
            category: Category key ('mf', 'stocks', 'etf', etc.) or full URL.

        Returns:
            List of refreshed SitemapURL items.
        """
        category_key = category.lower().strip()

        if category_key.startswith(("http://", "https://")):
            url = category
            # Derive cache category key from URL or keep generic
            cache_category = category.rstrip("/").split("/")[-2] or "custom"
        else:
            url = self._client.sitemap_urls.get(category_key)
            if not url:
                raise ValueError(
                    f"Unknown sitemap category '{category}'. Available categories: {list(self._client.sitemap_urls.keys())}"
                )
            cache_category = category_key

        logger.info("Fetching live sitemap XML from %s", url)
        response_text = await self._client.request("GET", url)

        parser = SitemapParser(response_text)
        parsed_result = parser.parse()

        if not isinstance(parsed_result, list):
            raise TickerTapeParseError(
                f"Unexpected parsed sitemap result type: {type(parsed_result)}"
            )

        if parsed_result and isinstance(parsed_result[0], SitemapReference):
            raise TickerTapeParseError(
                f"Sitemap at {url} is a sitemap index containing child sitemaps. Use get_references() instead."
            )

        items: list[SitemapURL] = parsed_result  # type: ignore

        # Persist to disk cache
        self._client.cache_manager.save(cache_category, items)
        return items

    async def get_references(self, url_or_category: str) -> list[SitemapReference]:
        """Fetch and parse a sitemap index XML into a list of SitemapReference items."""
        if url_or_category.startswith(("http://", "https://")):
            url = url_or_category
        else:
            url = self._client.sitemap_urls.get(url_or_category.lower().strip(), "")
            if not url:
                raise ValueError(f"Unknown sitemap category: {url_or_category}")

        response_text = await self._client.request("GET", url)
        parser = SitemapParser(response_text)
        parsed = parser.parse()

        return [item for item in parsed if isinstance(item, SitemapReference)]

    def is_cached(self, category: str = "mf") -> bool:
        """Check if local cache exists for a given category."""
        return self._client.cache_manager.exists(category.lower().strip())

    def clear_cache(self, category: Optional[str] = None) -> None:
        """Clear the cached sitemap file for category or all sitemaps."""
        self._client.cache_manager.clear(category)
