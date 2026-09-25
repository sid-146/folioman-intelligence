"""Unit tests for historical portfolio analytics."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from folioman_client.models import (
    CapitalGainsFyPoint,
    NavPoint,
    SchemeDetail,
    SchemeRef,
    Transaction,
    ValuationStatus,
    ValueSeries,
    ValueSeriesPoint,
)
from src.folioman_intelligence.analytics.historical import (
    analyze_portfolio_historical,
    get_historical_capital_gains,
    get_historical_cashflows,
    get_historical_drawdown_analysis,
    get_historical_risk_and_returns,
    get_historical_scheme_tenure,
    get_historical_valuation_trajectory,
)


@pytest.fixture
def sample_value_series() -> ValueSeries:
    """Fixture providing a standard 6-month monthly valuation series."""
    return ValueSeries(
        investor_id=1,
        start=date(2025, 1, 1),
        end=date(2025, 6, 1),
        granularity="monthly",
        points=[
            ValueSeriesPoint(
                date=date(2025, 1, 1),
                value_inr=Decimal("100000.00"),
                invested_inr=Decimal("90000.00"),
            ),
            ValueSeriesPoint(
                date=date(2025, 2, 1),
                value_inr=Decimal("110000.00"),
                invested_inr=Decimal("95000.00"),
            ),
            ValueSeriesPoint(
                date=date(2025, 3, 1),
                value_inr=Decimal("105000.00"),
                invested_inr=Decimal("95000.00"),
            ),
            ValueSeriesPoint(
                date=date(2025, 4, 1),
                value_inr=Decimal("95000.00"),
                invested_inr=Decimal("95000.00"),
            ),
            ValueSeriesPoint(
                date=date(2025, 5, 1),
                value_inr=Decimal("115000.00"),
                invested_inr=Decimal("100000.00"),
            ),
            ValueSeriesPoint(
                date=date(2025, 6, 1),
                value_inr=Decimal("125000.00"),
                invested_inr=Decimal("100000.00"),
            ),
        ],
    )


@pytest.fixture
def sample_transactions() -> list[Transaction]:
    """Fixture providing sample buy, SIP, and redemption transactions."""
    return [
        Transaction(
            id=1,
            investor_id=1,
            security_id=10,
            date=date(2024, 1, 15),
            transaction_type="PURCHASE",
            units=Decimal("100.0"),
            nav_or_price=Decimal("500.00"),
            amount=Decimal("50000.00"),
            fees=Decimal("20.00"),
            stamp_duty=Decimal("2.50"),
        ),
        Transaction(
            id=2,
            investor_id=1,
            security_id=10,
            date=date(2024, 2, 15),
            transaction_type="SIP",
            units=Decimal("20.0"),
            nav_or_price=Decimal("500.00"),
            amount=Decimal("10000.00"),
            narration="Monthly SIP",
        ),
        Transaction(
            id=3,
            investor_id=1,
            security_id=10,
            date=date(2024, 3, 15),
            transaction_type="SIP",
            units=Decimal("19.23"),
            nav_or_price=Decimal("520.00"),
            amount=Decimal("10000.00"),
            narration="Monthly SIP",
        ),
        Transaction(
            id=4,
            investor_id=1,
            security_id=10,
            date=date(2024, 6, 10),
            transaction_type="REDEMPTION",
            units=Decimal("25.0"),
            nav_or_price=Decimal("600.00"),
            amount=Decimal("15000.00"),
        ),
    ]


@pytest.fixture
def sample_capital_gains() -> list[CapitalGainsFyPoint]:
    """Fixture providing sample capital gains points."""
    return [
        CapitalGainsFyPoint(
            fy="2023-24",
            stcg=Decimal("12500.00"),
            ltcg=Decimal("45000.00"),
        ),
        CapitalGainsFyPoint(
            fy="2024-25",
            stcg=Decimal("-5000.00"),
            ltcg=Decimal("80000.00"),
        ),
    ]


# ============================================================================
# Trajectory Analytics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_valuation_trajectory_success(sample_value_series):
    """Test calculation of growth, invested capital changes, and trajectory series."""
    result = await get_historical_valuation_trajectory(
        investor_id=1, value_series=sample_value_series
    )

    assert result["investor_id"] == 1
    assert result["data_points_count"] == 6
    assert result["initial_value_inr"] == 100000.00
    assert result["latest_value_inr"] == 125000.00
    assert result["initial_invested_inr"] == 90000.00
    assert result["latest_invested_inr"] == 100000.00
    assert result["net_invested_change_inr"] == 10000.00
    assert result["net_wealth_generated_inr"] == 25000.00
    assert result["absolute_growth_pct"] == 25.00
    assert result["peak_valuation_inr"] == 125000.00
    assert result["peak_valuation_date"] == "2025-06-01"
    assert result["trough_valuation_inr"] == 95000.00
    assert result["trough_valuation_date"] == "2025-04-01"

    # Trajectory points validation
    traj = result["trajectory"]
    assert len(traj) == 6
    assert traj[0]["unrealized_gain_inr"] == 10000.00
    assert traj[-1]["unrealized_gain_inr"] == 25000.00
    assert traj[1]["period_change_inr"] == 10000.00
    assert traj[1]["period_return_pct"] == 10.00
    assert traj[1]["net_inflow_inr"] == 5000.00


@pytest.mark.asyncio
async def test_valuation_trajectory_empty():
    """Test valuation trajectory with empty points."""
    result = await get_historical_valuation_trajectory(
        investor_id=1, value_series={"points": []}
    )

    assert result["data_points_count"] == 0
    assert result["initial_value_inr"] == 0.0
    assert result["latest_value_inr"] == 0.0
    assert result["absolute_growth_pct"] is None
    assert result["trajectory"] == []


# ============================================================================
# Drawdown Analytics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_drawdown_analysis_with_recovery(sample_value_series):
    """Test drawdown calculation with peak, trough, and subsequent full recovery."""
    result = await get_historical_drawdown_analysis(
        investor_id=1, value_series=sample_value_series
    )

    # In sample_value_series:
    # 2025-01-01: 100k (Peak: 100k)
    # 2025-02-01: 110k (Peak: 110k)
    # 2025-03-01: 105k (Drawdown: (105-110)/110 = -4.55%)
    # 2025-04-01: 95k  (Drawdown: (95-110)/110 = -13.64%) -> MDD trough
    # 2025-05-01: 115k (Exceeds peak 110k -> Recovered!)
    # 2025-06-01: 125k (New Peak)

    assert result["max_drawdown_pct"] == pytest.approx(-13.64, abs=0.01)
    assert result["max_drawdown_inr"] == -15000.00
    assert result["peak_date"] == "2025-02-01"
    assert result["peak_value_inr"] == 110000.00
    assert result["trough_date"] == "2025-04-01"
    assert result["trough_value_inr"] == 95000.00
    assert result["recovery_date"] == "2025-05-01"
    assert result["is_recovered"] is True
    assert result["current_drawdown_pct"] == 0.0
    assert result["is_at_all_time_high"] is True
    assert len(result["drawdown_episodes"]) >= 1


@pytest.mark.asyncio
async def test_drawdown_analysis_unrecovered():
    """Test drawdown calculation when portfolio is currently in an unrecovered dip."""
    unrecovered_series = {
        "points": [
            {"date": "2025-01-01", "value_inr": 100000.0, "invested_inr": 80000.0},
            {"date": "2025-02-01", "value_inr": 120000.0, "invested_inr": 80000.0},
            {"date": "2025-03-01", "value_inr": 100000.0, "invested_inr": 80000.0},
        ]
    }
    result = await get_historical_drawdown_analysis(
        investor_id=2, value_series=unrecovered_series
    )

    # Peak: 120k, current/trough: 100k -> (100 - 120) / 120 = -16.67%
    assert result["max_drawdown_pct"] == pytest.approx(-16.67, abs=0.01)
    assert result["is_recovered"] is False
    assert result["recovery_date"] is None
    assert result["current_drawdown_pct"] == pytest.approx(-16.67, abs=0.01)
    assert result["is_at_all_time_high"] is False


@pytest.mark.asyncio
async def test_drawdown_empty_points():
    """Test drawdown analysis when no points exist."""
    result = await get_historical_drawdown_analysis(
        investor_id=1, value_series={"points": []}
    )
    assert result["max_drawdown_pct"] == 0.0
    assert result["is_recovered"] is True
    assert result["drawdown_series"] == []


# ============================================================================
# Risk-Adjusted Returns & Volatility Tests
# ============================================================================


@pytest.mark.asyncio
async def test_risk_and_returns_success(sample_value_series):
    """Test volatility, CAGR, Sharpe, and Sortino calculations."""
    result = await get_historical_risk_and_returns(
        investor_id=1,
        granularity="monthly",
        risk_free_rate=0.065,
        value_series=sample_value_series,
    )

    assert result["investor_id"] == 1
    assert result["periods_evaluated"] == 5
    assert result["annualized_volatility_pct"] > 0.0
    assert result["annualized_return_cagr"] is not None
    assert result["sharpe_ratio"] is not None
    assert result["sortino_ratio"] is not None
    assert result["best_period"] is not None
    assert result["worst_period"] is not None
    assert result["win_rate_pct"] >= 0.0


@pytest.mark.asyncio
async def test_risk_and_returns_single_point():
    """Test risk and returns with fewer than 2 points."""
    result = await get_historical_risk_and_returns(
        investor_id=1,
        value_series={
            "points": [
                {"date": "2025-01-01", "value_inr": 100000.0, "invested_inr": 90000.0}
            ]
        },
    )
    assert result["periods_evaluated"] == 0
    assert result["annualized_volatility_pct"] == 0.0
    assert result["sharpe_ratio"] is None


# ============================================================================
# Cash Flow Analytics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_cashflow_analytics(sample_transactions):
    """Test cash flow totals, SIP metrics, and yearly group breakdown."""
    result = await get_historical_cashflows(
        investor_id=1, transactions=sample_transactions
    )

    assert result["investor_id"] == 1
    assert result["total_transactions_count"] == 4
    assert result["first_transaction_date"] == "2024-01-15"
    assert result["latest_transaction_date"] == "2024-06-10"

    # Inflows: Purchase (50k) + SIP (10k) + SIP (10k) = 70k
    assert result["total_gross_inflows_inr"] == 70000.00
    # Outflows: Redemption (15k)
    assert result["total_gross_outflows_inr"] == 15000.00
    assert result["net_cash_invested_inr"] == 55000.00

    # SIP metrics
    sip_m = result["sip_metrics"]
    assert sip_m["total_sip_amount_inr"] == 20000.00
    assert sip_m["total_sip_count"] == 2
    assert sip_m["average_sip_amount_inr"] == 10000.00
    assert sip_m["sip_share_of_inflows_pct"] == pytest.approx(28.57, abs=0.01)
    assert sip_m["lumpsum_amount_inr"] == 50000.00
    assert sip_m["lumpsum_count"] == 1

    # Yearly breakdown
    assert len(result["yearly_summary"]) == 1
    y2024 = result["yearly_summary"][0]
    assert y2024["year"] == 2024
    assert y2024["inflows_inr"] == 70000.00
    assert y2024["outflows_inr"] == 15000.00
    assert y2024["net_inflow_inr"] == 55000.00


@pytest.mark.asyncio
async def test_cashflows_empty():
    """Test cash flow analytics with empty transactions."""
    result = await get_historical_cashflows(investor_id=1, transactions=[])
    assert result["total_transactions_count"] == 0
    assert result["net_cash_invested_inr"] == 0.0
    assert result["sip_metrics"]["total_sip_count"] == 0


# ============================================================================
# Capital Gains Analytics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_capital_gains_analytics(sample_capital_gains):
    """Test cumulative STCG/LTCG aggregation and FY breakdown."""
    result = await get_historical_capital_gains(
        investor_id=1, fy_points=sample_capital_gains
    )

    assert result["investor_id"] == 1
    assert result["financial_years_count"] == 2
    # STCG: 12500 - 5000 = 7500
    assert result["cumulative_stcg_inr"] == 7500.00
    # LTCG: 45000 + 80000 = 125000
    assert result["cumulative_ltcg_inr"] == 125000.00
    # Total: 7500 + 125000 = 132500
    assert result["cumulative_realized_gain_inr"] == 132500.00
    assert result["profitable_financial_years"] == 2
    assert result["loss_making_financial_years"] == 0


@pytest.mark.asyncio
async def test_capital_gains_empty():
    """Test capital gains with empty list."""
    result = await get_historical_capital_gains(investor_id=1, fy_points=[])
    assert result["financial_years_count"] == 0
    assert result["cumulative_realized_gain_inr"] == 0.0
    assert result["fy_breakdown"] == []


# ============================================================================
# Scheme Tenure Analytics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_scheme_tenure_analytics():
    """Test scheme holding vintage, average buy price, and transactions."""
    detail = SchemeDetail(
        security=SchemeRef(
            id=10, name="Alpha Bluechip", isin="INF10000001", category="Large Cap"
        ),
        as_of=date(2025, 6, 1),
        units=Decimal("100.0"),
        value_inr=Decimal("60000.00"),
        invested_inr=Decimal("50000.00"),
        latest_nav=Decimal("600.00"),
        return_pct=0.20,
        xirr=0.15,
        nav_history=[
            NavPoint(date=date(2024, 1, 1), nav=Decimal("500.00")),
            NavPoint(date=date(2025, 6, 1), nav=Decimal("600.00")),
        ],
        transactions=[
            Transaction(
                id=1,
                investor_id=1,
                security_id=10,
                date=date(2024, 1, 1),
                transaction_type="BUY",
                units=Decimal("50.0"),
                nav_or_price=Decimal("500.00"),
                amount=Decimal("25000.00"),
            ),
            Transaction(
                id=2,
                investor_id=1,
                security_id=10,
                date=date(2024, 6, 1),
                transaction_type="BUY",
                units=Decimal("50.0"),
                nav_or_price=Decimal("500.00"),
                amount=Decimal("25000.00"),
            ),
        ],
    )

    result = await get_historical_scheme_tenure(
        investor_id=1, security_id=10, scheme_detail=detail
    )

    assert result["security_id"] == 10
    assert result["name"] == "Alpha Bluechip"
    assert result["isin"] == "INF10000001"
    assert result["total_transactions_count"] == 2
    assert result["buy_transactions_count"] == 2
    assert result["avg_buy_nav"] == 500.00
    assert result["latest_nav"] == 600.00
    assert result["nav_multiple"] == 1.20
    assert result["tenure_days"] == 152
    assert result["nav_history_points_count"] == 2


# ============================================================================
# Master Consolidated Historical Report Test
# ============================================================================


@pytest.mark.asyncio
async def test_analyze_portfolio_historical_master(
    sample_value_series, sample_transactions, sample_capital_gains
):
    """Test master 360-degree historical report consolidating all components."""
    mock_status = ValuationStatus(
        investor_id=1,
        status="READY",
        computed_through=date(2025, 6, 1),
        is_provisional=False,
    )

    mock_repo = AsyncMock()
    mock_repo.get_valuation_status = AsyncMock(return_value=mock_status)
    mock_repo.get_value_series = AsyncMock(return_value=sample_value_series)
    mock_repo.get_transactions = AsyncMock(return_value=sample_transactions)
    mock_repo.get_capital_gains_summary = AsyncMock(return_value=sample_capital_gains)

    report = await analyze_portfolio_historical(investor_id=1, repo=mock_repo)

    assert report["investor_id"] == 1
    assert report["valuation_status"]["status"] == "READY"
    assert "trajectory_summary" in report
    assert report["trajectory_summary"]["initial_value_inr"] == 100000.00
    assert report["trajectory_summary"]["latest_value_inr"] == 125000.00
    assert "drawdown_summary" in report
    assert report["drawdown_summary"]["max_drawdown_pct"] < 0
    assert "risk_adjusted_performance" in report
    assert "cashflow_discipline" in report
    assert report["cashflow_discipline"]["total_gross_inflows_inr"] == 70000.00
    assert "realized_tax_summary" in report
    assert report["realized_tax_summary"]["cumulative_realized_gain_inr"] == 132500.00
    assert len(report["key_insights"]) >= 3
