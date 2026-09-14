"""Folioman API Client.

A thin, async, typed Python client for the Folioman REST API.
Handles HTTP transport, JWT token lifecycle (obtain, store, inject, refresh, retry on 401),
and response parsing into typed Pydantic models.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

import httpx

from folioman_intelligence.clients.folioman.auth import JWTAuthManager
from folioman_intelligence.clients.folioman.errors import (
    FoliomanAPIError,
    FoliomanAuthError,
    FoliomanError,
    FoliomanNotFoundError,
)
from folioman_intelligence.clients.folioman.models import (
    CapitalGainsFyPoint,
    CapitalGainsReport,
    Holding,
    Investor,
    InvestorDetail,
    PortfolioSummary,
    SchemeDetail,
    Transaction,
    ValuationStatus,
    ValueSeries,
)
from folioman_intelligence.config import FoliomanSettings, settings as default_settings


class _BaseResource:
    def __init__(self, client: FoliomanClient) -> None:
        self._client = client


class InvestorsResource(_BaseResource):
    """Endpoints for managing and querying investors."""

    async def list(
        self,
        *,
        family_id: int | None = None,
        unaffiliated: bool = False,
    ) -> list[Investor]:
        """List investors accessible to the authenticated advisor.

        Args:
            family_id: Filter by family ID.
            unaffiliated: Filter for investors with no family assigned.
        """
        params: dict[str, Any] = {}
        if family_id is not None:
            params["family_id"] = family_id
        if unaffiliated:
            params["unaffiliated"] = "true"

        data = await self._client.request("GET", "/investors/", params=params)
        return [Investor.model_validate(item) for item in data]

    async def get(self, investor_id: int) -> InvestorDetail:
        """Get investor details including masked PAN.

        Args:
            investor_id: The ID of the investor.
        """
        data = await self._client.request("GET", f"/investors/{investor_id}")
        return InvestorDetail.model_validate(data)


class PortfolioResource(_BaseResource):
    """Endpoints for investor portfolio summary and allocation."""

    async def get(
        self,
        investor_id: int,
        *,
        as_of: date | str | None = None,
    ) -> PortfolioSummary:
        """Get the full portfolio summary, metrics, and asset mix for an investor.

        Args:
            investor_id: The ID of the investor.
            as_of: Optional point-in-time date (YYYY-MM-DD or date object).
        """
        params: dict[str, Any] = {}
        if as_of is not None:
            params["as_of"] = as_of.isoformat() if isinstance(as_of, date) else str(as_of)

        data = await self._client.request("GET", f"/investors/{investor_id}/summary", params=params)
        return PortfolioSummary.model_validate(data)


class HoldingsResource(_BaseResource):
    """Endpoints for querying investor holdings and scheme details."""

    async def list(
        self,
        investor_id: int,
        *,
        as_of: date | str | None = None,
    ) -> list[Holding]:
        """List priced holdings for an investor (extracted from portfolio summary).

        Args:
            investor_id: The ID of the investor.
            as_of: Optional point-in-time date.
        """
        summary = await self._client.portfolio.get(investor_id, as_of=as_of)
        return summary.holdings

    async def get(
        self,
        investor_id: int,
        security_id: int,
        *,
        as_of: date | str | None = None,
    ) -> SchemeDetail:
        """Get detailed holding/scheme information (NAV history, transactions, folios).

        Args:
            investor_id: The ID of the investor.
            security_id: The ID of the security/scheme.
            as_of: Optional point-in-time date.
        """
        params: dict[str, Any] = {}
        if as_of is not None:
            params["as_of"] = as_of.isoformat() if isinstance(as_of, date) else str(as_of)

        data = await self._client.request(
            "GET",
            f"/investors/{investor_id}/holdings/{security_id}",
            params=params,
        )
        return SchemeDetail.model_validate(data)


class TransactionsResource(_BaseResource):
    """Endpoints for querying transaction ledger entries."""

    async def list(self, investor_id: int) -> list[Transaction]:
        """List all transactions for an investor.

        Args:
            investor_id: The ID of the investor.
        """
        data = await self._client.request("GET", f"/investors/{investor_id}/transactions")
        return [Transaction.model_validate(item) for item in data]


class ValuationsResource(_BaseResource):
    """Endpoints for portfolio net-worth history and valuation status."""

    async def list(
        self,
        investor_id: int,
        *,
        from_date: date | str | None = None,
        to_date: date | str | None = None,
        granularity: Literal["daily", "weekly", "monthly"] = "monthly",
    ) -> ValueSeries:
        """Get net-worth time series reconstructed from ledger + NAV history.

        Args:
            investor_id: The ID of the investor.
            from_date: Start date of series (alias for from).
            to_date: End date of series.
            granularity: "daily", "weekly", or "monthly".
        """
        params: dict[str, Any] = {"granularity": granularity}
        if from_date is not None:
            params["from"] = from_date.isoformat() if isinstance(from_date, date) else str(from_date)
        if to_date is not None:
            params["to"] = to_date.isoformat() if isinstance(to_date, date) else str(to_date)

        data = await self._client.request(
            "GET",
            f"/investors/{investor_id}/value-series",
            params=params,
        )
        return ValueSeries.model_validate(data)

    async def status(self, investor_id: int) -> ValuationStatus:
        """Get the current valuation calculation readiness status for an investor.

        Args:
            investor_id: The ID of the investor.
        """
        data = await self._client.request("GET", f"/investors/{investor_id}/valuation-status")
        return ValuationStatus.model_validate(data)


class CapitalGainsResource(_BaseResource):
    """Endpoints for realised capital gains reporting."""

    async def list(
        self,
        investor_id: int,
        *,
        include_unreconciled: bool = False,
    ) -> list[CapitalGainsFyPoint]:
        """List realised STCG/LTCG across every financial year with disposals.

        Args:
            investor_id: The ID of the investor.
            include_unreconciled: Include unreconciled transactions.
        """
        params = {"include_unreconciled": str(include_unreconciled).lower()}
        data = await self._client.request(
            "GET",
            f"/investors/{investor_id}/reports/capital-gains-by-fy",
            params=params,
        )
        return [CapitalGainsFyPoint.model_validate(item) for item in data]

    async def get(
        self,
        investor_id: int,
        *,
        fy: str,
        include_unreconciled: bool = False,
    ) -> CapitalGainsReport:
        """Get realised capital gains report for a specific financial year.

        Args:
            investor_id: The ID of the investor.
            fy: Financial year string, e.g. "2024-25".
            include_unreconciled: Include unreconciled transactions.
        """
        params = {
            "fy": fy,
            "include_unreconciled": str(include_unreconciled).lower(),
        }
        data = await self._client.request(
            "GET",
            f"/investors/{investor_id}/exports/capital-gains",
            params=params,
        )
        return CapitalGainsReport.model_validate(data)


class FoliomanClient:
    """Asynchronous client for interacting with the Folioman API.

    Handles authentication, token refresh, and request execution.

    Example:
        async with FoliomanClient(base_url="http://localhost:8000", username="...", password="...") as client:
            investor = await client.investors.get(1)
            summary = await client.portfolio.get(1)
    """

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = (base_url or default_settings.base_url).rstrip("/")
        self.username = username if username is not None else default_settings.username
        self.password = password if password is not None else default_settings.password
        self.timeout = timeout

        self._auth = JWTAuthManager(
            base_url=self.base_url,
            username=self.username,
            password=self.password,
        )

        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )

        # Resource sub-clients
        self.investors = InvestorsResource(self)
        self.portfolio = PortfolioResource(self)
        self.holdings = HoldingsResource(self)
        self.transactions = TransactionsResource(self)
        self.valuations = ValuationsResource(self)
        self.capital_gains = CapitalGainsResource(self)

    @classmethod
    def from_settings(cls, settings: FoliomanSettings) -> FoliomanClient:
        """Create a client instance from a FoliomanSettings object."""
        return cls(
            base_url=settings.base_url,
            username=settings.username,
            password=settings.password,
            timeout=settings.timeout,
        )

    @classmethod
    def from_env(cls) -> FoliomanClient:
        """Create a client instance using environment variables."""
        return cls.from_settings(FoliomanSettings())

    async def __aenter__(self) -> FoliomanClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP transport."""
        if self._owns_http_client:
            await self._http_client.aclose()

    def _normalize_path(self, path: str) -> str:
        """Ensure path starts with /api prefix as required by Folioman API."""
        path = path.strip()
        if not path.startswith("/"):
            path = f"/{path}"
        if not path.startswith("/api/"):
            path = f"/api{path}"
        return path

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Execute an authenticated HTTP request with automatic token refresh and 401 retry.

        Args:
            method: HTTP method ("GET", "POST", etc.)
            path: Relative API path (e.g. "/investors/1")
            params: Optional query parameters.
            json: Optional JSON request payload.
            headers: Optional extra headers.
        """
        normalized_path = self._normalize_path(path)
        req_headers = dict(headers or {})

        # Obtain valid Bearer token
        token = await self._auth.get_valid_token(self._http_client)
        req_headers["Authorization"] = f"Bearer {token}"

        response = await self._http_client.request(
            method=method,
            url=normalized_path,
            params=params,
            json=json,
            headers=req_headers,
            **kwargs,
        )

        # Reactive refresh if 401 Unauthorized occurs
        if response.status_code == 401:
            new_token = await self._auth.force_refresh(self._http_client)
            req_headers["Authorization"] = f"Bearer {new_token}"
            response = await self._http_client.request(
                method=method,
                url=normalized_path,
                params=params,
                json=json,
                headers=req_headers,
                **kwargs,
            )

        return self._handle_response(response, normalized_path)

    def _handle_response(self, response: httpx.Response, path: str) -> Any:
        """Process HTTP response, translating errors to Folioman client exceptions."""
        if response.status_code == 404:
            raise FoliomanNotFoundError(f"Resource not found at {path}")

        if response.status_code == 401:
            raise FoliomanAuthError(f"Authentication failed for {path} (HTTP 401)")

        if not response.is_success:
            detail: Any = None
            try:
                data = response.json()
                detail = data.get("detail", data)
            except Exception:
                detail = response.text
            raise FoliomanAPIError(
                message=f"Folioman API error on {response.request.method} {path}: {detail}",
                status_code=response.status_code,
                response_data=detail,
            )

        if response.status_code == 204 or not response.content:
            return None

        try:
            return response.json()
        except Exception as exc:
            raise FoliomanAPIError(
                message=f"Failed to parse JSON response from {path}: {exc}",
                status_code=response.status_code,
                response_data=response.text,
            ) from exc
