"""Data models for ISIN to TickerTape lookup table."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ISINMapping(BaseModel):
    """Mapping entry linking a mutual fund ISIN to TickerTape record and categorization metadata.

    Contains stable classification and grouping attributes used by AI agents
    to cluster and identify similar/peer mutual funds.
    """

    model_config = ConfigDict(extra="ignore")

    isin: str
    record_id: str
    slug: str
    name: str
    amc: Optional[str] = None
    amc_code: Optional[str] = None
    sector: Optional[str] = (
        None  # Primary asset class (e.g. 'Equity', 'Debt', 'Hybrid')
    )
    subsector: Optional[str] = (
        None  # Granular category (e.g. 'Sectoral Fund - Infrastructure', 'Large Cap Fund')
    )
    fund_type: Optional[str] = None  # Fund type (e.g. 'Equity')
    fund_class: Optional[str] = None  # Structure type (e.g. 'Open', 'Close')
    plan: Optional[str] = None  # 'Direct' vs 'Regular'
    option: Optional[str] = None  # 'Growth' vs 'IDCW'
    risk_level: Optional[str] = (
        None  # Risk classification (e.g. 'Very High', 'Moderate', 'Low')
    )
    benchmark: Optional[str] = (
        None  # Benchmark Index (e.g. 'Nifty Infrastructure - TRI')
    )
    url: str
    nav: Optional[float] = None
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
