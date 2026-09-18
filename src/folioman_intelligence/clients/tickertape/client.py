"""TickerTape API and Scraper Client.

An asynchronous, typed Python client for TickerTape.
Provides access to XML sitemaps (with persistent local caching) and mutual fund data
with an extensible architecture for future asset types (stocks, ETFs, screens).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import httpx

from folioman_intelligence.clients.tickertape.constants import (
    BASE_URL,
    DEFAULT_CACHE_DIR,
    DEFAULT_HEADERS,
    SITEMAP_URLS,
)
from folioman_intelligence.clients.tickertape.errors import (
    TickerTapeHTTPError,
    TickerTapeNotFoundError,
)
from folioman_intelligence.clients.tickertape.resources.mf import MutualFundsResource
from folioman_intelligence.clients.tickertape.resources.sitemap import SitemapResource
from folioman_intelligence.clients.tickertape.storage import SitemapCacheManager

logger = logging.getLogger(__name__)


class TickerTapeClient:
    """Asynchronous client for interacting with TickerTape.

    ```
    Example:
        async with TickerTapeClient() as client:
            # Reads from persistent cache (.cache/tickertape) or fetches live XML if not cached:
            mf_sitemap = await client.sitemap.get("mf")

            # Force live refresh and update disk cache:
            refreshed = await client.sitemap.refresh("mf")

            # Fetch fund details and ISIN:
            fund = await client.mf.get("quant-infrastructure-fund-M_QUNG")
            print(fund.isin, fund.nav)
    ```
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        http_client: Optional[httpx.AsyncClient] = None,
        headers: Optional[dict[str, str]] = None,
        sitemap_urls: Optional[dict[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_dir = Path(cache_dir)
        self.sitemap_urls = dict(sitemap_urls or SITEMAP_URLS)

        req_headers = dict(DEFAULT_HEADERS)
        if headers:
            req_headers.update(headers)
        self._default_headers = req_headers

        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            headers=self._default_headers,
            timeout=self.timeout,
            follow_redirects=True,
        )

        # Storage & persistent cache manager
        self.cache_manager = SitemapCacheManager(cache_dir=self.cache_dir)

        # Resource sub-clients
        self.sitemap = SitemapResource(self)
        self.mf = MutualFundsResource(self)
        # self.mutual_funds = self.mf #? Not sure why AI added this.

    async def __aenter__(self) -> TickerTapeClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP transport."""
        if self._owns_http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def _build_url(self, url_or_path: str) -> str:
        """Build full URL if given relative path."""
        url = url_or_path.strip()
        if url.startswith(("http://", "https://")):
            return url
        if not url.startswith("/"):
            url = f"/{url}"
        return f"{self.base_url}{url}"

    async def request(
        self,
        method: str,
        url_or_path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any,
    ) -> str:
        """Execute an HTTP request and return text response.

        Args:
            method: HTTP method ('GET', 'POST', etc.)
            url_or_path: Full URL or path relative to base_url.
            params: Optional query parameters.
            headers: Optional extra headers.

        Returns:
            Response body string.

        Raises:
            TickerTapeNotFoundError: On HTTP 404.
            TickerTapeHTTPError: On other HTTP 4xx/5xx status codes.
        """
        full_url = self._build_url(url_or_path)

        req_headers = dict(self._default_headers)
        if headers:
            req_headers.update(headers)

        try:
            response = await self._http_client.request(
                method=method,
                url=full_url,
                params=params,
                headers=req_headers,
                **kwargs,
            )
        except httpx.RequestError as exc:
            raise TickerTapeHTTPError(
                f"Request to {full_url} failed: {exc}",
                status_code=0,
            ) from exc

        if response.status_code == 404:
            raise TickerTapeNotFoundError(
                f"Resource not found at {full_url}",
                status_code=404,
                response_data=response.text[:200],
            )

        if response.is_error:
            raise TickerTapeHTTPError(
                f"HTTP {response.status_code} error from {full_url}",
                status_code=response.status_code,
                response_data=response.text[:500],
            )

        return response.text
