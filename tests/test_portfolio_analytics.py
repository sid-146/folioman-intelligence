"""Unit tests for portfolio analytics."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from folioman_client.errors import FoliomanNotFoundError
from src.folioman_intelligence.analytics.portfolio import analyze_portfolio


@pytest.fixture
def sample_portfolio_data():
    return {
        "currency": "INR",
        "total_value": Decimal("300000.00"),
        "total_invested": Decimal("250000.00"),
        "absolute_returns": Decimal("50000.00"),
        "navs_as_of": "2026-03-01",
        "category_mix": [],
        "xirr": 15.0,
        "period_returns": [],
        "holdings": [
            {
                "name": "Fund Alpha",
                "invested_inr": Decimal("50000.00"),
                "value_inr": Decimal("60000.00"),
            },
            {
                "name": "Fund Beta",
                "invested_inr": Decimal("10000.00"),
                "value_inr": Decimal("12000.00"),
            },
            {
                "name": "Fund Gamma",
                "invested_inr": Decimal("80000.00"),
                "value_inr": Decimal("95000.00"),
            },
            {
                "name": "Fund Delta",
                "invested_inr": Decimal("25000.00"),
                "value_inr": Decimal("30000.00"),
            },
            {
                "name": "Fund Epsilon",
                "invested_inr": Decimal("100000.00"),
                "value_inr": Decimal("120000.00"),
            },
        ],
    }


@pytest.mark.asyncio
async def test_analyze_portfolio_top_3_selection(sample_portfolio_data):
    """Test that top 3 holdings are correctly sorted by invested_inr descending."""
    with patch(
        "src.folioman_intelligence.analytics.portfolio.PortfolioRepository.get_portfolio",
        new_callable=AsyncMock,
    ) as mock_get_portfolio:
        mock_get_portfolio.return_value = sample_portfolio_data

        result = await analyze_portfolio(investor_id=42)

        mock_get_portfolio.assert_awaited_once_with(42)
        assert "top_3_holdings" in result
        # Top 3 invested amounts: Fund Epsilon (100k), Fund Gamma (80k), Fund Alpha (50k)
        assert result["top_3_holdings"] == [
            "Fund Epsilon",
            "Fund Gamma",
            "Fund Alpha",
        ]
        assert result["total_invested"] == Decimal("250000.00")


@pytest.mark.asyncio
async def test_analyze_portfolio_fewer_than_3_holdings():
    """Test analytics when portfolio contains fewer than 3 holdings."""
    two_holdings_data = {
        "currency": "INR",
        "total_value": Decimal("70000.00"),
        "total_invested": Decimal("50000.00"),
        "holdings": [
            {"name": "Small Cap", "invested_inr": Decimal("20000.00")},
            {"name": "Large Cap", "invested_inr": Decimal("30000.00")},
        ],
    }

    with patch(
        "src.folioman_intelligence.analytics.portfolio.PortfolioRepository.get_portfolio",
        new_callable=AsyncMock,
    ) as mock_get_portfolio:
        mock_get_portfolio.return_value = two_holdings_data

        result = await analyze_portfolio(investor_id=1)
        assert result["top_3_holdings"] == ["Large Cap", "Small Cap"]


@pytest.mark.asyncio
async def test_analyze_portfolio_empty_holdings():
    """Test analytics when portfolio has no holdings."""
    empty_data = {
        "currency": "INR",
        "total_value": Decimal("0.00"),
        "total_invested": Decimal("0.00"),
        "holdings": [],
    }

    with patch(
        "src.folioman_intelligence.analytics.portfolio.PortfolioRepository.get_portfolio",
        new_callable=AsyncMock,
    ) as mock_get_portfolio:
        mock_get_portfolio.return_value = empty_data

        result = await analyze_portfolio(investor_id=1)
        assert result["top_3_holdings"] == []


@pytest.mark.asyncio
async def test_analyze_portfolio_handles_none_invested_inr():
    """Test analytics sorting when some holdings have None or 0 invested_inr."""
    data_with_none = {
        "currency": "INR",
        "total_value": Decimal("50000.00"),
        "total_invested": Decimal("40000.00"),
        "holdings": [
            {"name": "None Investment", "invested_inr": None},
            {"name": "Highest Investment", "invested_inr": Decimal("30000.00")},
            {"name": "Zero Investment", "invested_inr": Decimal("0.00")},
            {"name": "Second Investment", "invested_inr": Decimal("10000.00")},
        ],
    }

    with patch(
        "src.folioman_intelligence.analytics.portfolio.PortfolioRepository.get_portfolio",
        new_callable=AsyncMock,
    ) as mock_get_portfolio:
        mock_get_portfolio.return_value = data_with_none

        result = await analyze_portfolio(investor_id=1)
        # Highest (30000) and Second (10000) must be the first two
        assert result["top_3_holdings"][:2] == [
            "Highest Investment",
            "Second Investment",
        ]
        assert len(result["top_3_holdings"]) == 3


@pytest.mark.asyncio
async def test_analyze_portfolio_deepcopy_immutability(sample_portfolio_data):
    """Test that analyze_portfolio returns a deep copy without mutating the original dictionary."""
    with patch(
        "src.folioman_intelligence.analytics.portfolio.PortfolioRepository.get_portfolio",
        new_callable=AsyncMock,
    ) as mock_get_portfolio:
        mock_get_portfolio.return_value = sample_portfolio_data

        result = await analyze_portfolio(investor_id=1)

        # Mutate result
        result["holdings"][0]["name"] = "MODIFIED_NAME"
        result["top_3_holdings"].append("NEW_FUND")

        # Original data must remain untouched
        assert sample_portfolio_data["holdings"][0]["name"] == "Fund Alpha"
        assert "top_3_holdings" not in sample_portfolio_data


@pytest.mark.asyncio
async def test_analyze_portfolio_propagates_repository_exceptions():
    """Test that repository errors propagate up through analyze_portfolio."""
    with patch(
        "src.folioman_intelligence.analytics.portfolio.PortfolioRepository.get_portfolio",
        new_callable=AsyncMock,
    ) as mock_get_portfolio:
        mock_get_portfolio.side_effect = FoliomanNotFoundError("Portfolio not found")

        with pytest.raises(FoliomanNotFoundError, match="Portfolio not found"):
            await analyze_portfolio(investor_id=999)
