"""Mutual Fund Repository.

Interacts directly with TickerTapeClient to fetch mutual fund details.
Strips frontend/Next.js page plumbing and returns a standardized,
pure mutual fund dictionary without calculating analytics.
"""

from __future__ import annotations
import re


import logging
from typing import Any, Optional

from tickertape import MutualFundDetail, TickerTapeClient

logger = logging.getLogger(__name__)


def standardize_mutual_fund_payload(raw_props: dict[str, Any]) -> dict[str, Any]:
    """Strip Next.js page metadata and standardize raw props into a pure mutual fund dictionary.

    Args:
        raw_props: Raw pageProps dictionary from TickerTape __NEXT_DATA__.

    Returns:
        Standardized dictionary containing strictly mutual fund information.
    """
    security_info = raw_props.get("securityInfo", {})
    security_summary = raw_props.get("securitySummary", {})
    meta = security_summary.get("meta", {})
    faq = raw_props.get("mfPageFaq", {})
    holdings_graph = raw_props.get("holdingsGraph", {})

    # Trailing returns from FAQ or fallback
    trailing_returns = faq.get("returns", [])
    if not trailing_returns and "returns" in raw_props:
        trailing_returns = raw_props.get("returns", [])

    return {
        # Core Scheme Identification & Security Info
        "mf_id": raw_props.get("mfId")
        or security_info.get("mfId")
        or meta.get("mfId")
        or "",
        "name": security_info.get("name")
        or meta.get("name")
        or meta.get("fullName")
        or "",
        "full_name": meta.get("fullName") or security_info.get("name") or "",
        "isin": meta.get("isin"),
        "slug": security_info.get("slug") or raw_props.get("slugId"),
        "nav": security_info.get("navClose"),
        "nav_1d_change": security_info.get("navCh1d"),
        "amc": security_info.get("amc") or meta.get("amc"),
        "amc_code": security_info.get("amcCode") or meta.get("amcCode"),
        "plan": meta.get("plan"),
        "option": security_info.get("option") or meta.get("option"),
        "category": security_info.get("sector")
        or meta.get("sector")
        or meta.get("fundType"),
        "subsector": security_info.get("subsector") or meta.get("subsector"),
        "subsector_desc": meta.get("subsectorDesc"),
        "benchmark": meta.get("benchmarkIndex"),
        "risk_classification": meta.get("riskClassification"),
        "inception_date": meta.get("inceptionDate"),
        "objective": meta.get("objective"),
        "scheme_type": meta.get("type"),
        "cams_code": meta.get("camsCode"),
        "rta_scheme_code": meta.get("rtaSchemeCode"),
        "series": meta.get("series"),
        "is_primary": meta.get("isPrimary", True),
        "sip_allowed": meta.get("sipinvest") == "Allowed",
        "lumpsum_allowed": meta.get("lumpsum", True),
        "investment_amount_info": meta.get("invAmountInfo"),
        "exit_load_remarks": meta.get("exitLoadRemarks"),
        # Financial Ratios & MPT Statistics
        "key_ratios": security_summary.get("keyRatios", []),
        "faq_ratios": faq.get("ratios", {}),
        # Trailing Returns & Historical CAGR Trajectory
        "trailing_returns": trailing_returns,
        "cagr_series": security_summary.get("cagrSeries", []),
        # Scorecard Ratings & Health Check
        "scorecard": raw_props.get("scorecard", []),
        # Portfolio Holdings & Allocations
        "current_allocation": holdings_graph.get("currentAllocation", []),
        "asset_allocation_history": holdings_graph.get("assetAllocationHistory", []),
        "target_asset_allocation": holdings_graph.get("targetAssetAllocation", []),
        # Sector Weights & Rotation
        "sector_distribution": holdings_graph.get("sectorDistribution", []),
        "sector_weightage": holdings_graph.get("sectorWeightage", []),
        "sector_taxonomy": raw_props.get("sectorConfig", []),
        # Red Flags & Governance
        "total_red_flags": holdings_graph.get("totalRedFlagsCount", {}),
        # Peers & Category Comparison
        "peers": security_summary.get("peers", []),
        "peers_tab_data": raw_props.get("peersTabData", []),
        # Fund Management Team
        "fund_managers": raw_props.get("fundManagers", []),
        # Scheme Rules, Fees & Taxation
        "scheme_info": security_summary.get("schemeInfo", []),
        "tax_meta": security_summary.get("taxMeta", {}),
        # AMC House Profile
        "amc_details": security_summary.get("amcDetails", {}),
    }


class MutualFundRepository:
    """Repository for accessing clean mutual fund data without Next.js artifacts."""

    def __init__(self, client: Optional[TickerTapeClient] = None) -> None:
        self._client = client

    async def get_fund_data(
        self,
        identifier: str,
        hint_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Retrieve standardized mutual fund information.

        Args:
            identifier: Fund ISIN (e.g. 'INF966L01721'), TickerTape slug, MFID ('M_QUNG'),
                        or scheme name (e.g. 'Quant Infrastructure Fund').
            hint_name: Optional fund name to assist ISIN resolution.

        Returns:
            Standardized dictionary containing only mutual fund information.
        """

        async def _fetch(client: TickerTapeClient) -> MutualFundDetail:
            ident = identifier.strip()

            # 1. If standard 12-char Indian ISIN, try ISIN lookup first
            if len(ident) == 12 and ident.startswith("IN") and ident[2:5].isalnum():
                detail = await client.mf.get_by_isin(ident, hint_name=hint_name)
                if detail:
                    return detail

            # 2. Try direct fetch if no spaces (valid slug, MFID or URL)
            try:
                if not any(c.isspace() for c in ident):
                    return await client.mf.get(ident)
            except Exception:
                pass

            # 3. Fallback: Search sitemap by record_id (MFID) or scheme name tokens
            try:
                sitemap_items = await client.sitemap.get("mf")
                if sitemap_items:
                    # 3a. Exact match on record_id / MFID
                    for item in sitemap_items:
                        if item.record_id and item.record_id.upper() == ident.upper():
                            return await client.mf.get(item.url)

                    # 3b. Match by scheme name tokens
                    tokens = [
                        t.lower()
                        for t in re.findall(r"[a-zA-Z0-9]+", ident)
                        if len(t) > 2
                        and t.lower()
                        not in {
                            "fund",
                            "mutual",
                            "plan",
                            "growth",
                            "direct",
                            "regular",
                            "the",
                            "and",
                            "for",
                        }
                    ]
                    if tokens:
                        best_match = None
                        best_score = 0
                        for item in sitemap_items:
                            slug_lower = item.url.lower()
                            score = sum(1 for tok in tokens if tok in slug_lower)
                            if score > best_score:
                                best_score = score
                                best_match = item
                        if best_match and best_score >= len(tokens) * 0.6:
                            return await client.mf.get(best_match.url)
            except Exception as exc:
                logger.debug("Sitemap fallback search failed: %s", exc)

            return await client.mf.get(ident)

        if self._client is not None:
            fund_detail = await _fetch(self._client)
        else:
            async with TickerTapeClient() as client:
                fund_detail = await _fetch(client)

        raw_props = fund_detail.raw_props or {}
        return standardize_mutual_fund_payload(raw_props)
