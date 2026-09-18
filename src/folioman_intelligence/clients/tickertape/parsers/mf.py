"""Parser for TickerTape Mutual Fund pages.

Extracts structured mutual fund data from HTML pages or the embedded
Next.js SSR payload (__NEXT_DATA__).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from bs4 import BeautifulSoup

from folioman_intelligence.clients.tickertape.errors import TickerTapeParseError
from folioman_intelligence.clients.tickertape.models import (
    MFMeta,
    MFScorecardItem,
    MFSecurityInfo,
    MutualFundDetail,
)
from folioman_intelligence.clients.tickertape.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class MFParser(BaseParser[MutualFundDetail]):
    """Parser for mutual fund page HTML and Next.js hydration payload."""

    def parse(self, content: str | dict[str, Any]) -> MutualFundDetail:
        """Parse mutual fund page HTML string or pre-extracted JSON dict into MutualFundDetail.

        Args:
            content: Raw HTML text containing <script id="__NEXT_DATA__"> or the parsed JSON dict.

        Returns:
            MutualFundDetail containing metadata, security info, scorecard, and NAV.

        Raises:
            TickerTapeParseError: If required data cannot be found or parsed.
        """
        if isinstance(content, dict):
            raw_data = content
        elif isinstance(content, str):
            raw_data = self.extract_next_data(content)
        else:
            raise TickerTapeParseError(
                f"Expected str or dict, got {type(content).__name__}"
            )

        page_props = raw_data.get("props", {}).get("pageProps", {})
        if not page_props:
            raise TickerTapeParseError("Next.js payload is missing 'props.pageProps'")

        security_info_dict = page_props.get("securityInfo", {})
        security_summary_dict = page_props.get("securitySummary", {})
        meta_dict = security_summary_dict.get("meta", {})
        scorecard_list = page_props.get("scorecard", [])

        # Extract primary identifiers
        mf_id = (
            page_props.get("mfId")
            or security_info_dict.get("mfId")
            or meta_dict.get("mfId")
            or ""
        )
        name = (
            security_info_dict.get("name")
            or meta_dict.get("name")
            or meta_dict.get("fullName")
            or ""
        )
        isin = meta_dict.get("isin")
        slug = security_info_dict.get("slug")
        nav = security_info_dict.get("navClose")

        # Parse security info model if data exists
        security_info: Optional[MFSecurityInfo] = None
        if security_info_dict:
            try:
                security_info = MFSecurityInfo.model_validate(security_info_dict)
            except Exception as exc:
                logger.debug("Could not validate MFSecurityInfo: %s", exc)

        # Parse key ratios like expense ratio & AUM
        expense_ratio: Optional[float] = None
        key_ratios = security_summary_dict.get("keyRatios", [])
        if isinstance(key_ratios, list):
            for ratio in key_ratios:
                if isinstance(ratio, dict) and ratio.get("backL") == "expRatio":
                    expense_ratio = ratio.get("value")
                    break

        aum: Optional[float] = None
        faq_ratios = page_props.get("mfPageFaq", {}).get("ratios", {})
        if isinstance(faq_ratios, dict):
            aum = faq_ratios.get("aum")

        # Parse metadata model
        meta: Optional[MFMeta] = None
        if meta_dict:
            try:
                meta_payload = dict(meta_dict)
                if expense_ratio is not None and "expenseRatio" not in meta_payload:
                    meta_payload["expenseRatio"] = expense_ratio
                if aum is not None and "aum" not in meta_payload:
                    meta_payload["aum"] = aum
                meta = MFMeta.model_validate(meta_payload)
            except Exception as exc:
                logger.debug("Could not validate MFMeta: %s", exc)

        # Parse scorecards
        scorecard: list[MFScorecardItem] = []
        if isinstance(scorecard_list, list):
            for item in scorecard_list:
                if isinstance(item, dict):
                    try:
                        scorecard.append(MFScorecardItem.model_validate(item))
                    except Exception as exc:
                        logger.debug("Could not validate MFScorecardItem: %s", exc)

        return MutualFundDetail(
            mf_id=mf_id,
            name=name,
            isin=isin,
            slug=slug,
            nav=nav,
            security_info=security_info,
            meta=meta,
            scorecard=scorecard,
            raw_props=page_props,
        )

    def extract_next_data(self, html: str) -> dict[str, Any]:
        """Extract and parse __NEXT_DATA__ JSON script from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag or not script_tag.string:
            raise TickerTapeParseError(
                "Could not find <script id='__NEXT_DATA__'> tag in HTML"
            )

        try:
            return json.loads(script_tag.string)
        except json.JSONDecodeError as exc:
            raise TickerTapeParseError(
                f"Failed to decode __NEXT_DATA__ JSON: {exc}"
            ) from exc

    def extract_isin(self, content: str | dict[str, Any]) -> Optional[str]:
        """Convenience method to extract only ISIN."""
        fund = self.parse(content)
        return fund.isin
