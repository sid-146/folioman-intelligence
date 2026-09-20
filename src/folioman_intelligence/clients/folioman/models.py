"""Pydantic models representing Folioman API schemas.

These models mirror the OpenAPI contracts in Folioman (v1).
All models use extra="ignore" to remain resilient against future schema extensions.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from folioman_intelligence.types import (
    ConfiguredDate,
    ConfiguredDatetime,
    ConfiguredDecimal,
)


class FoliomanBaseModel(BaseModel):
    """Base model with common configuration for all Folioman models."""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )


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
    created_at: ConfiguredDatetime | None = None
    updated_at: ConfiguredDatetime | None = None


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
    units: ConfiguredDecimal
    value_inr: ConfiguredDecimal | None = None
    invested_inr: ConfiguredDecimal | None = None
    latest_nav: ConfiguredDecimal | None = None
    return_pct: float | None = None
    xirr: float | None = None
    day_change_inr: ConfiguredDecimal | None = None
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

    date: ConfiguredDate
    nav: ConfiguredDecimal


class FolioBalance(FoliomanBaseModel):
    """Balance for one folio holding a security."""

    number: str
    broker: str = ""
    folio_type: str = ""
    units: ConfiguredDecimal
    value_inr: ConfiguredDecimal | None = None


# --- Transaction Models ---
class Transaction(FoliomanBaseModel):
    """Transaction ledger record."""

    id: int
    investor_id: int
    security_id: int
    folio_id: int | None = None
    date: ConfiguredDate
    transaction_type: str
    units: ConfiguredDecimal
    nav_or_price: ConfiguredDecimal
    amount: ConfiguredDecimal | None = None
    fees: ConfiguredDecimal = Decimal("0")
    stamp_duty: ConfiguredDecimal = Decimal("0")
    brokerage: ConfiguredDecimal = Decimal("0")
    currency: str = "INR"
    source: str = ""
    narration: str = ""
    cost_basis_complete: bool = True
    via_security: str | None = None
    balance: ConfiguredDecimal | None = None


class SchemeDetail(FoliomanBaseModel):
    """Detailed scheme view for an investor."""

    security: SchemeRef
    as_of: ConfiguredDate
    units: ConfiguredDecimal
    value_inr: ConfiguredDecimal | None = None
    invested_inr: ConfiguredDecimal | None = None
    return_pct: float | None = None
    xirr: float | None = None
    xirr_status: str = ""
    day_change_inr: ConfiguredDecimal | None = None
    day_change_pct: float | None = None
    latest_nav: ConfiguredDecimal | None = None
    latest_nav_date: ConfiguredDate | None = None
    has_transactions: bool = False
    partial_history: bool = False
    partial_history_from: ConfiguredDate | None = None
    folios: list[FolioBalance] = Field(default_factory=list)
    nav_history: list[NavPoint] = Field(default_factory=list)
    transactions: list[Transaction] = Field(default_factory=list)


# --- Portfolio & Valuation Models ---
class AssetMixRow(FoliomanBaseModel):
    """Allocation breakdown row by security type."""

    security_type: str
    value_inr: ConfiguredDecimal


class AllocationBucket(FoliomanBaseModel):
    """Allocation breakdown row by AMC or category."""

    label: str
    value_inr: ConfiguredDecimal


class PeriodReturn(FoliomanBaseModel):
    """Trailing window money-weighted return (1M, 1Y, All, etc.)."""

    period: str
    annualized: float
    absolute: float | None = None
    days: int


class PortfolioSummary(FoliomanBaseModel):
    """Overall portfolio summary for an investor (InvestorSummaryOut)."""

    investor_id: int
    as_of: ConfiguredDate
    total_inr: ConfiguredDecimal
    is_provisional: bool = False
    navs_as_of: ConfiguredDate | None = None
    navs_stale: bool = False
    holdings_count: int = 0
    integrity_unit_count: int = 0
    tax_ready_count: int = 0
    needs_attention_count: int = 0
    snapshot_count: int = 0
    stale_count: int = 0
    unpriced_fund_count: int = 0
    last_import_at: ConfiguredDatetime | None = None
    day_change_inr: ConfiguredDecimal | None = None
    xirr: float | None = None
    period_returns: list[PeriodReturn] = Field(default_factory=list)
    asset_mix: list[AssetMixRow] = Field(default_factory=list)
    amc_mix: list[AllocationBucket] = Field(default_factory=list)
    category_mix: list[AllocationBucket] = Field(default_factory=list)
    top_holdings: list[Holding] = Field(default_factory=list)
    holdings: list[Holding] = Field(default_factory=list)


class ValueSeriesPoint(FoliomanBaseModel):
    """Single date point in net worth valuation series."""

    date: ConfiguredDate
    value_inr: ConfiguredDecimal
    invested_inr: ConfiguredDecimal
    stale: bool = False


class ValueSeries(FoliomanBaseModel):
    """Reconstructed net-worth-over-time time series."""

    investor_id: int | None = None
    family_id: int | None = None
    start: ConfiguredDate
    end: ConfiguredDate
    granularity: str
    points: list[ValueSeriesPoint] = Field(default_factory=list)


class ValuationStatus(FoliomanBaseModel):
    """Valuation calculation readiness status."""

    investor_id: int | None = None
    family_id: int | None = None
    status: str
    computed_through: ConfiguredDate | None = None
    recompute_from: ConfiguredDate | None = None
    is_provisional: bool = False


# --- Capital Gains Models ---
class CapitalGainRow(FoliomanBaseModel):
    """One realised disposal lot in capital gains report."""

    security_id: int | None = None
    name: str
    isin: str = ""
    units: ConfiguredDecimal
    sale_value: ConfiguredDecimal
    cost: ConfiguredDecimal
    gain: ConfiguredDecimal
    term: str
    acquired_on: ConfiguredDate
    sold_on: ConfiguredDate
    grandfathering_unavailable: bool = False


class CapitalGainsReport(FoliomanBaseModel):
    """Realised capital gains report for a financial year (CapitalGainsOut)."""

    fy: str
    stcg_total: ConfiguredDecimal
    ltcg_total: ConfiguredDecimal
    rows: list[CapitalGainRow] = Field(default_factory=list)
    disclaimer: str = ""


class CapitalGainsFyPoint(FoliomanBaseModel):
    """Year-over-year capital gains summary point."""

    fy: str
    stcg: ConfiguredDecimal
    ltcg: ConfiguredDecimal


__all__ = [
    "FoliomanBaseModel",
    "TokenPair",
    "AccessToken",
    "Investor",
    "InvestorDetail",
    "Holding",
    "SchemeRef",
    "NavPoint",
    "FolioBalance",
    "Transaction",
    "SchemeDetail",
    "AssetMixRow",
    "AllocationBucket",
    "PeriodReturn",
    "PortfolioSummary",
    "ValueSeriesPoint",
    "ValueSeries",
    "ValuationStatus",
    "CapitalGainRow",
    "CapitalGainsReport",
    "CapitalGainsFyPoint",
    "ConfiguredDecimal",
    "ConfiguredDate",
    "ConfiguredDatetime",
]
