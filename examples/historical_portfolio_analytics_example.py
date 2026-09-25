"""Example: Historical Portfolio Analytics.

Demonstrates using historical portfolio analytics functions from
folioman_intelligence.analytics to analyze valuation trajectories,
maximum drawdowns, risk-adjusted returns, cash flow patterns,
and financial year capital gains.
"""

import asyncio
from datetime import date
from decimal import Decimal
from pprint import pprint

from folioman_client.models import (
    CapitalGainsFyPoint,
    Transaction,
    ValueSeries,
    ValueSeriesPoint,
)
from folioman_intelligence.analytics.historical import (
    analyze_portfolio_historical,
    get_historical_capital_gains,
    get_historical_cashflows,
    get_historical_drawdown_analysis,
    get_historical_risk_and_returns,
    get_historical_valuation_trajectory,
)


def create_demo_value_series() -> ValueSeries:
    """Create sample 12-month net-worth valuation series."""
    monthly_data = [
        (date(2024, 1, 1), 500000.0, 450000.0),
        (date(2024, 2, 1), 520000.0, 470000.0),
        (date(2024, 3, 1), 540000.0, 490000.0),
        (date(2024, 4, 1), 510000.0, 510000.0),  # Dip (drawdown)
        (date(2024, 5, 1), 490000.0, 530000.0),  # Trough
        (date(2024, 6, 1), 535000.0, 550000.0),
        (date(2024, 7, 1), 560000.0, 570000.0),  # Recovery
        (date(2024, 8, 1), 590000.0, 590000.0),
        (date(2024, 9, 1), 610000.0, 610000.0),
        (date(2024, 10, 1), 600000.0, 630000.0),
        (date(2024, 11, 1), 640000.0, 650000.0),
        (date(2024, 12, 1), 680000.0, 670000.0),
    ]
    return ValueSeries(
        investor_id=1,
        start=monthly_data[0][0],
        end=monthly_data[-1][0],
        granularity="monthly",
        points=[
            ValueSeriesPoint(
                date=d,
                value_inr=Decimal(str(v)),
                invested_inr=Decimal(str(i)),
            )
            for d, v, i in monthly_data
        ],
    )


def create_demo_transactions() -> list[Transaction]:
    """Create sample historical transactions."""
    return [
        Transaction(
            id=1,
            investor_id=1,
            security_id=101,
            date=date(2024, 1, 10),
            transaction_type="PURCHASE",
            units=Decimal("500"),
            nav_or_price=Decimal("500"),
            amount=Decimal("250000"),
        ),
        Transaction(
            id=2,
            investor_id=1,
            security_id=101,
            date=date(2024, 2, 10),
            transaction_type="SIP",
            units=Decimal("40"),
            nav_or_price=Decimal("500"),
            amount=Decimal("20000"),
            narration="Monthly SIP",
        ),
        Transaction(
            id=3,
            investor_id=1,
            security_id=101,
            date=date(2024, 3, 10),
            transaction_type="SIP",
            units=Decimal("38"),
            nav_or_price=Decimal("526.31"),
            amount=Decimal("20000"),
            narration="Monthly SIP",
        ),
        Transaction(
            id=4,
            investor_id=1,
            security_id=101,
            date=date(2024, 5, 20),
            transaction_type="REDEMPTION",
            units=Decimal("50"),
            nav_or_price=Decimal("550"),
            amount=Decimal("27500"),
        ),
    ]


def create_demo_capital_gains() -> list[CapitalGainsFyPoint]:
    """Create sample capital gains history across FYs."""
    return [
        CapitalGainsFyPoint(fy="2022-23", stcg=Decimal("15000"), ltcg=Decimal("45000")),
        CapitalGainsFyPoint(fy="2023-24", stcg=Decimal("-5000"), ltcg=Decimal("95000")),
        CapitalGainsFyPoint(
            fy="2024-25", stcg=Decimal("22000"), ltcg=Decimal("110000")
        ),
    ]


async def run():
    investor_id = 1
    value_series = create_demo_value_series()
    txns = create_demo_transactions()
    cg_points = create_demo_capital_gains()

    print("=" * 80)
    print("1. Historical Valuation Trajectory")
    print("=" * 80)
    traj = await get_historical_valuation_trajectory(
        investor_id, value_series=value_series
    )
    pprint(
        {
            "start_date": traj["start_date"],
            "end_date": traj["end_date"],
            "initial_value_inr": traj["initial_value_inr"],
            "latest_value_inr": traj["latest_value_inr"],
            "net_invested_change_inr": traj["net_invested_change_inr"],
            "net_wealth_generated_inr": traj["net_wealth_generated_inr"],
            "absolute_growth_pct": traj["absolute_growth_pct"],
            "peak_valuation_inr": traj["peak_valuation_inr"],
            "peak_valuation_date": traj["peak_valuation_date"],
        }
    )
    print()

    print("=" * 80)
    print("2. Historical Peak-to-Trough Drawdown Analysis")
    print("=" * 80)
    drawdown = await get_historical_drawdown_analysis(
        investor_id, value_series=value_series
    )
    pprint(
        {
            "max_drawdown_pct": drawdown["max_drawdown_pct"],
            "max_drawdown_inr": drawdown["max_drawdown_inr"],
            "peak_date": drawdown["peak_date"],
            "trough_date": drawdown["trough_date"],
            "recovery_date": drawdown["recovery_date"],
            "is_recovered": drawdown["is_recovered"],
            "current_drawdown_pct": drawdown["current_drawdown_pct"],
            "is_at_all_time_high": drawdown["is_at_all_time_high"],
        }
    )
    print()

    print("=" * 80)
    print("3. Risk-Adjusted Returns & MPT Metrics")
    print("=" * 80)
    risk_returns = await get_historical_risk_and_returns(
        investor_id, value_series=value_series, risk_free_rate=0.065
    )
    pprint(
        {
            "annualized_return_cagr": risk_returns["annualized_return_cagr"],
            "annualized_volatility_pct": risk_returns["annualized_volatility_pct"],
            "downside_deviation_pct": risk_returns["downside_deviation_pct"],
            "sharpe_ratio": risk_returns["sharpe_ratio"],
            "sortino_ratio": risk_returns["sortino_ratio"],
            "calmar_ratio": risk_returns["calmar_ratio"],
            "win_rate_pct": risk_returns["win_rate_pct"],
            "best_period": risk_returns["best_period"],
            "worst_period": risk_returns["worst_period"],
        }
    )
    print()

    print("=" * 80)
    print("4. Historical Cash Flow Discipline & SIP Analytics")
    print("=" * 80)
    cashflows = await get_historical_cashflows(investor_id, transactions=txns)
    pprint(
        {
            "total_transactions_count": cashflows["total_transactions_count"],
            "total_gross_inflows_inr": cashflows["total_gross_inflows_inr"],
            "total_gross_outflows_inr": cashflows["total_gross_outflows_inr"],
            "net_cash_invested_inr": cashflows["net_cash_invested_inr"],
            "sip_metrics": cashflows["sip_metrics"],
            "yearly_summary": cashflows["yearly_summary"],
        }
    )
    print()

    print("=" * 80)
    print("5. Realized Capital Gains & Tax Efficiency")
    print("=" * 80)
    gains = await get_historical_capital_gains(investor_id, fy_points=cg_points)
    pprint(
        {
            "financial_years_count": gains["financial_years_count"],
            "cumulative_stcg_inr": gains["cumulative_stcg_inr"],
            "cumulative_ltcg_inr": gains["cumulative_ltcg_inr"],
            "cumulative_realized_gain_inr": gains["cumulative_realized_gain_inr"],
            "fy_breakdown": gains["fy_breakdown"],
        }
    )
    print()


if __name__ == "__main__":
    asyncio.run(run())
