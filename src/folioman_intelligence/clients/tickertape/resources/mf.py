"""Mutual funds resource for TickerTape client."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, List, Dict

from folioman_intelligence.clients.tickertape.lookup.indexer import ISINIndexer
from folioman_intelligence.clients.tickertape.lookup.models import ISINMapping
from folioman_intelligence.clients.tickertape.lookup.resolver import ISINResolver
from folioman_intelligence.clients.tickertape.lookup.table import ISINLookupTable
from folioman_intelligence.clients.tickertape.models import MutualFundDetail
from folioman_intelligence.clients.tickertape.parsers.mf import MFParser
from folioman_intelligence.clients.tickertape.resources.base import _BaseResource

logger = logging.getLogger(__name__)


class MutualFundsResource(_BaseResource):
    """Resource for fetching and parsing mutual fund details from TickerTape."""

    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self._parser = MFParser()
        self.lookup = ISINLookupTable(cache_dir=client.cache_dir)
        self._resolver = ISINResolver(client=self._client, table=self.lookup)
        self._indexer = ISINIndexer(client=self._client, table=self.lookup)

    def _normalize_slug(self, slug_or_mfid: str) -> str:
        """Ensure slug path is formatted correctly."""
        slug = slug_or_mfid.strip()
        if slug.startswith(("http://", "https://")):
            return slug
        if slug.startswith("/mutualfunds/"):
            return slug
        if slug.startswith("/"):
            return f"/mutualfunds{slug}"
        return f"/mutualfunds/{slug}"

    async def get(self, slug_or_mfid: str) -> MutualFundDetail:
        """Fetch mutual fund details from TickerTape by slug or MFID.

        Args:
            slug_or_mfid: Slug (e.g. 'quant-infrastructure-fund-M_QUNG') or MFID ('M_QUNG').

        Returns:
            Parsed MutualFundDetail.
        """
        path = self._normalize_slug(slug_or_mfid)
        html_content = await self._client.request("GET", path)
        return self._parser.parse(html_content)

    async def get_by_isin(
        self,
        isin: str,
        hint_name: Optional[str] = None,
    ) -> Optional[MutualFundDetail]:
        """Fetch mutual fund details using an ISIN from Folioman.

        Looks up the ISIN in the SQLite lookup table. If not found, attempts targeted
        resolution using hint_name against the sitemap and persists the result.

        Args:
            isin: Mutual fund ISIN (e.g. 'INF966L01721').
            hint_name: Optional scheme name from Folioman to assist targeted resolution.

        Returns:
            Parsed MutualFundDetail if resolved, otherwise None.
        """
        mapping = await self._resolver.resolve(isin, hint_name=hint_name)
        if not mapping:
            return None
        return await self.get(mapping.slug)

    async def get_isin(self, slug_or_mfid: str) -> Optional[str]:
        """Convenience method to retrieve the ISIN for a mutual fund.

        Args:
            slug_or_mfid: Slug or MFID.

        Returns:
            ISIN string (e.g., 'INF966L01721') or None if not found.
        """
        fund = await self.get(slug_or_mfid)
        return fund.isin

    async def get_raw(self, slug_or_mfid: str) -> dict[str, Any]:
        """Fetch and extract the raw Next.js hydration payload dictionary."""
        path = self._normalize_slug(slug_or_mfid)
        html_content = await self._client.request("GET", path)
        return self._parser.extract_next_data(html_content)

    def get_peers(
        self,
        isin: str,
        match_plan: bool = True,
        match_option: bool = True,
        limit: int = 20,
    ) -> list[ISINMapping]:
        """Gather peer mutual funds in the same subsector/category as the given ISIN.

        Args:
            isin: Source fund ISIN.
            match_plan: If True, matches plan (e.g. Direct with Direct).
            match_option: If True, matches option (e.g. Growth with Growth).
            limit: Maximum peers to return.
        """
        return self.lookup.get_peers(
            isin,
            match_plan=match_plan,
            match_option=match_option,
            limit=limit,
        )

    def find_funds(
        self,
        *,
        sector: Optional[str] = None,
        subsector: Optional[str] = None,
        fund_type: Optional[str] = None,
        plan: Optional[str] = None,
        option: Optional[str] = None,
        risk_level: Optional[str] = None,
        benchmark: Optional[str] = None,
        amc: Optional[str] = None,
        limit: int = 100,
    ) -> list[ISINMapping]:
        """Find and gather mutual funds sharing similar classification attributes."""
        return self.lookup.find_funds(
            sector=sector,
            subsector=subsector,
            fund_type=fund_type,
            plan=plan,
            option=option,
            risk_level=risk_level,
            benchmark=benchmark,
            amc=amc,
            limit=limit,
        )

    async def build_isin_index(
        self,
        *,
        force_refresh: bool = False,
        concurrency: int = 5,
        delay: float = 0.5,
        limit: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, int, int], None]] = None,
    ) -> int:
        """Crawl sitemap URLs and populate the SQLite ISIN lookup table.

        When force_refresh=True:
            1. Refreshes live sitemap XML.
            2. Updates local sitemap disk cache (.cache/tickertape/sitemaps/mf.json).
            3. Crawls fund pages and updates SQLite database (.cache/tickertape/isin_lookup.db).

        When force_refresh=False:
            1. Uses cached sitemap.
            2. Resumes by crawling only unindexed funds.
            3. Updates SQLite database.

        Returns:
            Number of indexed mappings saved to SQLite.
        """
        return await self._indexer.build_index(
            force_refresh=force_refresh,
            concurrency=concurrency,
            delay=delay,
            limit=limit,
            progress_callback=progress_callback,
        )

    async def get_cached_by_isin(self, isin: str) -> ISINMapping | None:
        """
        Get table record by isin.

        Args:
            isin (str): Unique Identifier of scheme.

        Returns:
            ISINMapping: ISINMapping Object (Table Record)
        """
        mapping = await self._resolver.resolve(isin=isin)
        if not mapping:
            return None
        return mapping

    async def get_cached_by_isin_batch(
        self, isins: List[str]
    ) -> Dict[str, ISINMapping]:
        mappings = self.lookup.get_batch(isins)
        if not mappings:
            return {}
        return mappings
