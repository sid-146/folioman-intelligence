"""Unit tests for PortfolioRepository."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from folioman_client.errors import (
    FoliomanAPIError,
    FoliomanNotFoundError,
)
from folioman_client.models import (
    AllocationBucket,
    Holding,
    PeriodReturn,
    PortfolioSummary,
)
from src.folioman_intelligence.repository.portfolio import PortfolioRepository


@pytest.fixture
def mock_portfolio_summary() -> PortfolioSummary:
    return PortfolioSummary(
        investor_id=101,
        as_of=date(2026, 3, 1),
        total_inr=Decimal("150000.00"),
        xirr=14.50,
        navs_as_of=date(2026, 3, 1),
        category_mix=[
            AllocationBucket(
                label="Equity",
                value_inr=Decimal("120000.00"),
            ),
            AllocationBucket(
                label="Debt",
                value_inr=Decimal("30000.00"),
            ),
        ],
        period_returns=[
            PeriodReturn(period="1y", annualized=12.0, absolute=15.2, days=365),
            PeriodReturn(period="3y", annualized=14.0, absolute=42.8, days=1095),
        ],
        holdings=[
            Holding(
                security_id=1,
                security_type="MF",
                name="Fund Alpha Large Cap",
                category="Equity",
                units=Decimal("100.5"),
                value_inr=Decimal("90000.00"),
                invested_inr=Decimal("60000.00"),
                return_pct=0.50,
                xirr=0.18,
            ),
            Holding(
                security_id=2,
                security_type="MF",
                name="Fund Beta Mid Cap",
                category="Equity",
                units=Decimal("50.0"),
                value_inr=Decimal("60000.00"),
                invested_inr=Decimal("40000.00"),
                return_pct=0.50,
                xirr=0.16,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_get_portfolio_success(mock_portfolio_summary: PortfolioSummary):
    """Test standard portfolio transformation with complete data."""
    repo = PortfolioRepository()

    mock_client = MagicMock()
    mock_client.portfolio.get = AsyncMock(return_value=mock_portfolio_summary)

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_client
    mock_cm.__aexit__.return_value = None

    with patch(
        "src.folioman_intelligence.repository.portfolio.FoliomanClient.from_env",
        return_value=mock_cm,
    ):
        data = await repo.get_portfolio(investor_id=101)

    mock_client.portfolio.get.assert_awaited_once_with(101)

    assert data == mock_portfolio_summary
    assert data.investor_id == 101
    assert data.total_inr == Decimal("150000.00")
    assert data.xirr == 14.50
    assert data.navs_as_of == date(2026, 3, 1)

    # Category mix
    assert len(data.category_mix) == 2
    assert data.category_mix[0].label == "Equity"
    assert data.category_mix[0].value_inr == Decimal("120000.00")

    # Period returns
    assert len(data.period_returns) == 2
    assert data.period_returns[0].period == "1y"
    assert data.period_returns[0].absolute == 15.2

    # Holdings
    assert len(data.holdings) == 2
    holding_alpha = data.holdings[0]
    assert holding_alpha.name == "Fund Alpha Large Cap"
    assert holding_alpha.category == "Equity"
    assert holding_alpha.units == Decimal("100.5")
    assert holding_alpha.value_inr == Decimal("90000.00")
    assert holding_alpha.invested_inr == Decimal("60000.00")
    assert holding_alpha.return_pct == pytest.approx(0.50)
    assert holding_alpha.xirr == pytest.approx(0.18)


@pytest.mark.asyncio
async def test_get_portfolio_with_none_holding_fields():
    """Test handling of None fields in holdings (missing return_pct, xirr, invested_inr)."""
    repo = PortfolioRepository()

    summary = PortfolioSummary(
        investor_id=1,
        as_of=date(2026, 3, 1),
        total_inr=Decimal("50000.00"),
        xirr=None,
        navs_as_of=None,
        category_mix=[],
        period_returns=[],
        holdings=[
            Holding(
                security_id=10,
                security_type="MF",
                name="Zero/None Holding",
                category="Others",
                units=Decimal("10"),
                value_inr=Decimal("50000.00"),
                invested_inr=None,
                return_pct=None,
                xirr=None,
            )
        ],
    )

    mock_client = MagicMock()
    mock_client.portfolio.get = AsyncMock(return_value=summary)

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_client
    mock_cm.__aexit__.return_value = None

    with patch(
        "src.folioman_intelligence.repository.portfolio.FoliomanClient.from_env",
        return_value=mock_cm,
    ):
        data = await repo.get_portfolio(investor_id=1)

    assert data == summary
    assert data.holdings[0].invested_inr is None
    assert data.holdings[0].return_pct is None
    assert data.holdings[0].xirr is None


@pytest.mark.asyncio
async def test_get_portfolio_empty_holdings():
    """Test portfolio with empty holdings to verify zero-division protection."""
    repo = PortfolioRepository()

    summary = PortfolioSummary(
        investor_id=2,
        as_of=date(2026, 3, 1),
        total_inr=Decimal("0.00"),
        xirr=None,
        navs_as_of=None,
        category_mix=[],
        period_returns=[],
        holdings=[],
    )

    mock_client = MagicMock()
    mock_client.portfolio.get = AsyncMock(return_value=summary)

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_client
    mock_cm.__aexit__.return_value = None

    with patch(
        "src.folioman_intelligence.repository.portfolio.FoliomanClient.from_env",
        return_value=mock_cm,
    ):
        data = await repo.get_portfolio(investor_id=2)

    assert data == summary
    assert data.total_inr == Decimal("0.00")
    assert data.holdings == []
    assert data.period_returns == []
    assert data.category_mix == []


@pytest.mark.asyncio
async def test_get_portfolio_api_error_propagation():
    """Test that FoliomanNotFoundError and FoliomanAPIError propagate from client."""
    repo = PortfolioRepository()

    mock_client = MagicMock()
    mock_client.portfolio.get = AsyncMock(
        side_effect=FoliomanNotFoundError("Investor not found")
    )

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_client
    mock_cm.__aexit__.return_value = None

    with patch(
        "src.folioman_intelligence.repository.portfolio.FoliomanClient.from_env",
        return_value=mock_cm,
    ):
        with pytest.raises(FoliomanNotFoundError, match="Investor not found"):
            await repo.get_portfolio(investor_id=999)
