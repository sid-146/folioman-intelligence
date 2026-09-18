"""Pydantic models representing Folioman API schemas.

These models mirror the OpenAPI contracts in Folioman (v1).
All models use extra="ignore" to remain resilient against future schema extensions.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class FoliomanBaseModel(BaseModel):
    """Base model with common configuration for all Folioman models."""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )

    @field_serializer("*", mode="wrap", check_fields=False)
    def _serialize_all(self, v: Any, handler: Any) -> Any:
        if isinstance(v, Decimal):
            return float(v)
        return handler(v)


# --- Auth Models ---
class TokenPair(FoliomanBaseModel):
    """Access and refresh token pair returned on authentication."""

    access: str
    refresh: str


class AccessToken(FoliomanBaseModel):
    """Refreshed access token."""

    access: str


# --- Investor Models ---
class Investor(FoliomanBaseModel):
    """Investor summary representation."""

    id: int
    name: str
    email: str = ""
    is_huf: bool = False
    relation: str = ""
    family_id: int | None = None
    has_pan: bool = False
    pan_locked: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InvestorDetail(Investor):
    """Investor detailed representation with masked PAN."""

    pan_masked: str = ""


# --- Holding & Security Models ---
class Holding(FoliomanBaseModel):
    """Priced holding row under an investor."""

    security_id: int
    name: str
    security_type: str
    symbol: str = ""
    amc: str = ""
    category: str = ""
    units: Decimal
    value_inr: Decimal | None = None
    invested_inr: Decimal | None = None
    latest_nav: Decimal | None = None
    return_pct: float | None = None
    xirr: float | None = None
    day_change_inr: Decimal | None = None
    day_change_pct: float | None = None


class SchemeRef(FoliomanBaseModel):
    """Security identity metadata."""

    id: int
    name: str
    isin: str = ""
    symbol: str = ""
    security_type: str = ""
    amfi_code: str = ""
    amc: str | None = None
    category: str | None = None


class NavPoint(FoliomanBaseModel):
    """Single date and NAV point."""

    date: date
    nav: Decimal


class FolioBalance(FoliomanBaseModel):
    """Balance for one folio holding a security."""

    number: str
    broker: str = ""
    folio_type: str = ""
    units: Decimal
    value_inr: Decimal | None = None


# --- Transaction Models ---
class Transaction(FoliomanBaseModel):
    """Transaction ledger record."""

    id: int
    investor_id: int
    security_id: int
    folio_id: int | None = None
    date: date
    transaction_type: str
    units: Decimal
    nav_or_price: Decimal
    amount: Decimal | None = None
    fees: Decimal = Decimal("0")
    stamp_duty: Decimal = Decimal("0")
    brokerage: Decimal = Decimal("0")
    currency: str = "INR"
    source: str = ""
    narration: str = ""
    cost_basis_complete: bool = True
    via_security: str | None = None
    balance: Decimal | None = None


class SchemeDetail(FoliomanBaseModel):
    """Detailed scheme view for an investor."""

    security: SchemeRef
    as_of: date
    units: Decimal
    value_inr: Decimal | None = None
    invested_inr: Decimal | None = None
    return_pct: float | None = None
    xirr: float | None = None
    xirr_status: str = ""
    day_change_inr: Decimal | None = None
    day_change_pct: float | None = None
    latest_nav: Decimal | None = None
    latest_nav_date: date | None = None
    has_transactions: bool = False
    partial_history: bool = False
    partial_history_from: date | None = None
    folios: list[FolioBalance] = Field(default_factory=list)
    nav_history: list[NavPoint] = Field(default_factory=list)
    transactions: list[Transaction] = Field(default_factory=list)


# --- Portfolio & Valuation Models ---
class AssetMixRow(FoliomanBaseModel):
    """Allocation breakdown row by security type."""

    security_type: str
    value_inr: Decimal


class AllocationBucket(FoliomanBaseModel):
    """Allocation breakdown row by AMC or category."""

    label: str
    value_inr: Decimal


class PeriodReturn(FoliomanBaseModel):
    """Trailing window money-weighted return (1M, 1Y, All, etc.)."""

    period: str
    annualized: float
    absolute: float | None = None
    days: int


class PortfolioSummary(FoliomanBaseModel):
    """Overall portfolio summary for an investor (InvestorSummaryOut)."""

    investor_id: int
    as_of: date
    total_inr: Decimal
    is_provisional: bool = False
    navs_as_of: date | None = None
    navs_stale: bool = False
    holdings_count: int = 0
    integrity_unit_count: int = 0
    tax_ready_count: int = 0
    needs_attention_count: int = 0
    snapshot_count: int = 0
    stale_count: int = 0
    unpriced_fund_count: int = 0
    last_import_at: datetime | None = None
    day_change_inr: Decimal | None = None
    xirr: float | None = None
    period_returns: list[PeriodReturn] = Field(default_factory=list)
    asset_mix: list[AssetMixRow] = Field(default_factory=list)
    amc_mix: list[AllocationBucket] = Field(default_factory=list)
    category_mix: list[AllocationBucket] = Field(default_factory=list)
    top_holdings: list[Holding] = Field(default_factory=list)
    holdings: list[Holding] = Field(default_factory=list)


class ValueSeriesPoint(FoliomanBaseModel):
    """Single date point in net worth valuation series."""

    date: date
    value_inr: Decimal
    invested_inr: Decimal
    stale: bool = False


class ValueSeries(FoliomanBaseModel):
    """Reconstructed net-worth-over-time time series."""

    investor_id: int | None = None
    family_id: int | None = None
    start: date
    end: date
    granularity: str
    points: list[ValueSeriesPoint] = Field(default_factory=list)


class ValuationStatus(FoliomanBaseModel):
    """Valuation calculation readiness status."""

    investor_id: int | None = None
    family_id: int | None = None
    status: str
    computed_through: date | None = None
    recompute_from: date | None = None
    is_provisional: bool = False


# --- Capital Gains Models ---
class CapitalGainRow(FoliomanBaseModel):
    """One realised disposal lot in capital gains report."""

    security_id: int | None = None
    name: str
    isin: str = ""
    units: Decimal
    sale_value: Decimal
    cost: Decimal
    gain: Decimal
    term: str
    acquired_on: date
    sold_on: date
    grandfathering_unavailable: bool = False


class CapitalGainsReport(FoliomanBaseModel):
    """Realised capital gains report for a financial year (CapitalGainsOut)."""

    fy: str
    stcg_total: Decimal
    ltcg_total: Decimal
    rows: list[CapitalGainRow] = Field(default_factory=list)
    disclaimer: str = ""


class CapitalGainsFyPoint(FoliomanBaseModel):
    """Year-over-year capital gains summary point."""

    fy: str
    stcg: Decimal
    ltcg: Decimal
