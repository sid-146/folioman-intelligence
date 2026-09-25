from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal, Optional

from folioman_client import FoliomanClient
from folioman_client.models import (
    CapitalGainsFyPoint,
    CapitalGainsReport,
    Holding,
    PortfolioSummary,
    SchemeDetail,
    Transaction,
    ValuationStatus,
    ValueSeries,
)


class PortfolioRepository:
    """Repository abstraction over FoliomanClient for portfolio and investor data."""

    def __init__(self, client: Optional[FoliomanClient] = None) -> None:
        self._client = client

    @asynccontextmanager
    async def _client_session(self) -> AsyncGenerator[FoliomanClient]:
        if self._client is not None:
            yield self._client
        else:
            async with FoliomanClient.from_env() as client:
                yield client

    async def get_portfolio(
        self, investor_id: int, *, as_of: date | str | None = None
    ) -> PortfolioSummary:
        """Get portfolio summary and holdings metrics for an investor."""
        async with self._client_session() as client:
            if as_of is not None:
                return await client.portfolio.get(investor_id, as_of=as_of)
            return await client.portfolio.get(investor_id)

    async def get_holding(
        self, investor_id: int, security_id: int, *, as_of: date | str | None = None
    ) -> SchemeDetail:
        """Get detailed holding view including transactions, NAV points, and folios."""
        async with self._client_session() as client:
            if as_of is not None:
                return await client.holdings.get(investor_id, security_id, as_of=as_of)
            return await client.holdings.get(investor_id, security_id)

    async def get_holdings(
        self, investor_id: int, *, as_of: date | str | None = None
    ) -> list[Holding]:
        """List priced holdings under an investor."""
        async with self._client_session() as client:
            return await client.holdings.list(investor_id, as_of=as_of)

    async def get_value_series(
        self,
        investor_id: int,
        *,
        from_date: date | str | None = None,
        to_date: date | str | None = None,
        granularity: Literal["daily", "weekly", "monthly"] = "monthly",
    ) -> ValueSeries:
        """Get historical net-worth and invested valuation time series."""
        async with self._client_session() as client:
            return await client.valuations.list(
                investor_id,
                from_date=from_date,
                to_date=to_date,
                granularity=granularity,
            )

    async def get_valuation_status(self, investor_id: int) -> ValuationStatus:
        """Get valuation engine calculation readiness and coverage status."""
        async with self._client_session() as client:
            return await client.valuations.status(investor_id)

    async def get_transactions(self, investor_id: int) -> list[Transaction]:
        """Get all historical transaction ledger entries for an investor."""
        async with self._client_session() as client:
            return await client.transactions.list(investor_id)

    async def get_capital_gains_summary(
        self, investor_id: int, *, include_unreconciled: bool = False
    ) -> list[CapitalGainsFyPoint]:
        """List realized capital gains summarized by financial year."""
        async with self._client_session() as client:
            return await client.capital_gains.list(
                investor_id, include_unreconciled=include_unreconciled
            )

    async def get_capital_gains_report(
        self, investor_id: int, *, fy: str, include_unreconciled: bool = False
    ) -> CapitalGainsReport:
        """Get detailed realized capital gains report for a specific financial year."""
        async with self._client_session() as client:
            return await client.capital_gains.get(
                investor_id, fy=fy, include_unreconciled=include_unreconciled
            )
