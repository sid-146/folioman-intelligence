"""Mutual funds resource for TickerTape client."""

from __future__ import annotations

import logging
from typing import Any, Optional

from folioman_intelligence.clients.tickertape.models import MutualFundDetail
from folioman_intelligence.clients.tickertape.parsers.mf import MFParser
from folioman_intelligence.clients.tickertape.resources.base import _BaseResource

logger = logging.getLogger(__name__)


class MutualFundsResource(_BaseResource):
    """Resource for fetching and parsing mutual fund details from TickerTape."""

    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self._parser = MFParser()

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
