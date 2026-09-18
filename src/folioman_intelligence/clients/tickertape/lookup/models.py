"""Data models for ISIN to TickerTape lookup table."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ISINMapping(BaseModel):
    """Mapping entry linking a mutual fund ISIN to TickerTape record and metadata."""

    model_config = ConfigDict(extra="ignore")

    isin: str
    record_id: str
    slug: str
    name: str
    amc: Optional[str] = None
    plan: Optional[str] = None
    option: Optional[str] = None
    url: str
    nav: Optional[float] = None
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
