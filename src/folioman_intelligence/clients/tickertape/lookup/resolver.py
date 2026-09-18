"""Targeted on-demand resolver for matching Folioman ISINs to TickerTape records."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Optional

from folioman_intelligence.clients.tickertape.lookup.models import ISINMapping
from folioman_intelligence.clients.tickertape.lookup.table import ISINLookupTable

if TYPE_CHECKING:
    from folioman_intelligence.clients.tickertape.client import TickerTapeClient

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "fund",
    "mutual",
    "plan",
    "growth",
    "direct",
    "regular",
    "idcw",
    "dividend",
    "reinvestment",
    "payout",
    "scheme",
    "equity",
    "debt",
    "the",
    "and",
    "of",
    "in",
    "to",
    "for",
    "a",
    "an",
    "is",
}


class ISINResolver:
    """Resolves specific ISINs on demand using local sitemap slug matching and verification."""

    def __init__(
        self, client: TickerTapeClient, table: Optional[ISINLookupTable] = None
    ) -> None:
        self.client = client
        self.table = table or ISINLookupTable(cache_dir=client.cache_dir)

    async def resolve(
        self,
        isin: str,
        hint_name: Optional[str] = None,
        max_candidates: int = 3,
    ) -> Optional[ISINMapping]:
        """Resolve an ISIN to a TickerTape mapping.

        Checks the persistent SQLite table first. If not found, uses hint_name
        to search candidate slugs in the cached sitemap, verifies the page ISIN,
        and saves it to the SQLite lookup table upon match.

        Args:
            isin: Mutual fund ISIN string (e.g. 'INF966L01721').
            hint_name: Optional scheme name from Folioman to narrow candidates.
            max_candidates: Maximum candidate pages to inspect.

        Returns:
            ISINMapping if successfully resolved, otherwise None.
        """
        clean_isin = isin.strip().upper()

        # 1. Check persistent SQLite table
        existing = self.table.get(clean_isin)
        if existing:
            return existing

        # 2. If no hint_name, we cannot narrow down 5,900+ sitemap URLs safely
        if not hint_name:
            logger.debug(
                "Cannot resolve ISIN %s without a hint name or pre-built index",
                clean_isin,
            )
            return None

        # 3. Load cached sitemap
        sitemap_items = await self.client.sitemap.get("mf")
        if not sitemap_items:
            return None

        # 4. Extract search tokens from hint_name
        tokens = [
            t.lower()
            for t in re.findall(r"[a-zA-Z0-9]+", hint_name)
            if t.lower() not in STOP_WORDS and len(t) > 2
        ]

        if not tokens:
            return None

        # 5. Score sitemap slugs based on token overlap
        scored_candidates = []
        for item in sitemap_items:
            slug_lower = item.url.lower()
            matched_count = sum(1 for token in tokens if token in slug_lower)
            if matched_count > 0:
                scored_candidates.append((matched_count, item))

        # Sort highest match count first
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [item for _, item in scored_candidates[:max_candidates]]

        # 6. Fetch candidate pages and verify ISIN
        for candidate in top_candidates:
            try:
                fund = await self.client.mf.get(candidate.url)
                if fund.isin and fund.isin.strip().upper() == clean_isin:
                    raw_slug = fund.slug or candidate.url
                    clean_slug = raw_slug.split("/mutualfunds/")[-1].lstrip("/")

                    sec_info = fund.security_info
                    meta = fund.meta

                    mapping = ISINMapping(
                        isin=clean_isin,
                        record_id=fund.mf_id or candidate.record_id,
                        slug=clean_slug,
                        name=fund.name,
                        amc=(meta.amc if meta else None)
                        or (sec_info.amc if sec_info else None),
                        amc_code=sec_info.amc_code if sec_info else None,
                        sector=(sec_info.sector if sec_info else None)
                        or (meta.sector if meta else None),
                        subsector=(sec_info.subsector if sec_info else None)
                        or (meta.subsector if meta else None),
                        fund_type=meta.fund_type if meta else None,
                        fund_class=meta.type if meta else None,
                        plan=meta.plan if meta else None,
                        option=(sec_info.option if sec_info else None)
                        or (meta.option if meta else None),
                        risk_level=meta.risk_classification if meta else None,
                        benchmark=meta.benchmark_index if meta else None,
                        url=candidate.url,
                        nav=fund.nav,
                    )

                    self.table.upsert(mapping)
                    logger.info(
                        "Successfully resolved %s -> %s (%s)",
                        clean_isin,
                        mapping.record_id,
                        mapping.name,
                    )
                    return mapping
            except Exception as exc:
                logger.debug("Candidate check failed for %s: %s", candidate.url, exc)

        return None
