"""Pydantic data models for TickerTape client."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Sitemap Models
# ---------------------------------------------------------------------------


class SitemapURL(BaseModel):
    """Represents a single <url> entry parsed from a sitemap XML."""

    model_config = ConfigDict(extra="ignore")

    record_id: str
    url: str
    last_modified: Optional[str] = None
    change_frequency: Optional[str] = None
    priority: Optional[float] = None


class SitemapReference(BaseModel):
    """Represents a <sitemap> reference inside a sitemap index XML."""

    model_config = ConfigDict(extra="ignore")

    url: str
    last_modified: Optional[str] = None


class SitemapCacheData(BaseModel):
    """Represents persisted cache data for a sitemap category."""

    model_config = ConfigDict(extra="ignore")

    category: str
    fetched_at: str
    count: int
    items: list[SitemapURL]


# ---------------------------------------------------------------------------
# Mutual Fund Models
# ---------------------------------------------------------------------------


class MFScorecardItem(BaseModel):
    """Scorecard evaluation for a mutual fund metric (e.g., Performance, Risk, Cost)."""

    model_config = ConfigDict(extra="ignore")

    name: str
    tag: Optional[str] = None
    colour: Optional[str] = None
    description: Optional[str] = None


class MFSecurityInfo(BaseModel):
    """Security level information for a mutual fund."""

    model_config = ConfigDict(extra="ignore")

    mf_id: str = Field(alias="mfId")
    name: Optional[str] = None
    type: Optional[str] = None
    slug: Optional[str] = None
    amc: Optional[str] = None
    amc_code: Optional[str] = Field(default=None, alias="amcCode")
    nav_close: Optional[float] = Field(default=None, alias="navClose")
    nav_ch_1d: Optional[float] = Field(default=None, alias="navCh1d")
    option: Optional[str] = None
    sector: Optional[str] = None
    subsector: Optional[str] = None


class MFMeta(BaseModel):
    """Detailed metadata for a mutual fund from securitySummary.meta."""

    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    isin: Optional[str] = None
    amc: Optional[str] = None
    plan: Optional[str] = None
    option: Optional[str] = None
    type: Optional[str] = None
    sector: Optional[str] = None
    subsector: Optional[str] = None
    benchmark_index: Optional[str] = Field(default=None, alias="benchmarkIndex")
    fund_type: Optional[str] = Field(default=None, alias="fundType")
    full_name: Optional[str] = Field(default=None, alias="fullName")
    risk_classification: Optional[str] = Field(default=None, alias="riskClassification")
    cams_code: Optional[str] = Field(default=None, alias="camsCode")
    rta_scheme_code: Optional[str] = Field(default=None, alias="rtaSchemeCode")
    expense_ratio: Optional[float] = Field(default=None, alias="expenseRatio")
    aum: Optional[float] = None


class MutualFundDetail(BaseModel):
    """Unified mutual fund details extracted from TickerTape page."""

    model_config = ConfigDict(extra="ignore")

    mf_id: str
    name: str
    isin: Optional[str] = None
    slug: Optional[str] = None
    nav: Optional[float] = None
    security_info: Optional[MFSecurityInfo] = None
    meta: Optional[MFMeta] = None
    scorecard: list[MFScorecardItem] = []
    raw_props: Optional[dict[str, Any]] = None
