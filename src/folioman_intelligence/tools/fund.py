"""Mutual Fund Tools for LangChain / DeepAgents.

Wraps the pure financial calculations in the analytics layer into
tool definitions with clear docstrings, typing, and JSON serialization.
"""

from __future__ import annotations

import json
from typing import Any

from langchain.tools import tool

from src.folioman_intelligence.analytics.fund import (
    analyze_fund_comprehensive,
    check_mandate_compliance,
    get_asset_allocation,
    get_cagr_history,
    get_cost_and_tax_profile,
    get_fund_health_audit,
    get_fund_managers_analysis,
    get_fund_overview,
    get_peer_comparison,
    get_portfolio_activity,
    get_portfolio_valuation,
    get_risk_and_volatility,
    get_sector_allocation,
    get_sector_rotation_trends,
    get_top_holdings,
    get_trailing_returns,
    search_stock_in_fund,
)


def _serialize(data: Any) -> Any:
    """Ensure data is cleanly JSON serializable."""
    return json.loads(json.dumps(data, default=str))


@tool
async def get_fund_overview_tool(identifier: str) -> dict[str, Any]:
    """Get the baseline profile and metadata for a mutual fund scheme.

    Args:
        identifier: Mutual fund ISIN (e.g. 'INF966L01721'), TickerTape slug, or MFID.

    Returns:
        Scheme name, AMC, category, subsector, benchmark index, risk rating,
        current NAV with 1-day change, fund vintage/age in years, AUM, and minimum SIP/lumpsum.
    """
    analysis = await get_fund_overview(identifier)
    return _serialize(analysis)


@tool
async def get_fund_trailing_returns_tool(identifier: str) -> dict[str, Any]:
    """Get trailing returns for a mutual fund across standard investment horizons.

    Args:
        identifier: Mutual fund ISIN (e.g. 'INF966L01721'), TickerTape slug, or MFID.

    Returns:
        1-Year, 3-Year CAGR, 5-Year CAGR, and Since Inception (Life) CAGR returns.
    """
    analysis = await get_trailing_returns(identifier)
    return _serialize(analysis)


@tool
async def get_fund_cagr_history_tool(identifier: str) -> dict[str, Any]:
    """Analyze the historical rolling CAGR series of a fund to evaluate return compounding consistency.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Historical CAGR statistics: min CAGR, max CAGR, median CAGR, CAGR spread across cycles,
        and past multi-year observation intervals.
    """
    analysis = await get_cagr_history(identifier)
    return _serialize(analysis)


@tool
async def get_fund_risk_metrics_tool(identifier: str) -> dict[str, Any]:
    """Get risk, volatility, and Modern Portfolio Theory (MPT) risk-adjusted metrics for a mutual fund.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Alpha, annualized standard deviation (volatility), Sharpe ratio, Sortino ratio,
        category average Sharpe ratio, and risk-adjusted outperformance classification.
    """
    analysis = await get_risk_and_volatility(identifier)
    return _serialize(analysis)


@tool
async def get_fund_valuation_tool(identifier: str) -> dict[str, Any]:
    """Get portfolio valuation multiples (P/E ratio) compared against the category average.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Underlying portfolio weighted P/E ratio, category average P/E, and valuation premium or discount percentage.
    """
    analysis = await get_portfolio_valuation(identifier)
    return _serialize(analysis)


@tool
async def get_fund_top_holdings_tool(
    identifier: str, top_n: int = 10
) -> dict[str, Any]:
    """Get the top stock holdings and portfolio concentration for a mutual fund.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.
        top_n: Number of top holdings to return (default is 10).

    Returns:
        Total stock holdings count, Top 5 concentration %, Top 10 concentration %,
        high-conviction bets (>5% weight), and sorted list of top holdings with weights and ratings.
    """
    analysis = await get_top_holdings(identifier, top_n=top_n)
    return _serialize(analysis)


@tool
async def get_fund_portfolio_activity_tool(identifier: str) -> dict[str, Any]:
    """Identify recent fund manager portfolio actions over the last 3 months.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Stocks being accumulated (weight increased) vs stocks being trimmed or exited (weight decreased).
    """
    analysis = await get_portfolio_activity(identifier)
    return _serialize(analysis)


@tool
async def search_stock_in_fund_tool(identifier: str, query: str) -> dict[str, Any]:
    """Check whether a specific stock or company is held in a mutual fund's portfolio.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.
        query: Company name, ticker, or symbol to search for (e.g. 'Adani', 'Airtel', 'INFY').

    Returns:
        Whether the stock is held, matching company details, weight percentage, and 3-month weight change.
    """
    analysis = await search_stock_in_fund(identifier, query=query)
    return _serialize(analysis)


@tool
async def get_fund_asset_allocation_tool(identifier: str) -> dict[str, Any]:
    """Get the asset class allocation breakdown (Equity, Derivatives/F&O, Debt, Cash, REITs).

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Current allocation percentages across pure equity, futures & options derivatives,
        treasury bills/debt, cash equivalents, and REITs.
    """
    analysis = await get_asset_allocation(identifier)
    return _serialize(analysis)


@tool
async def check_fund_mandate_compliance_tool(identifier: str) -> dict[str, Any]:
    """Check whether the fund's asset allocation adheres to SEBI and scheme mandate limits.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Target allocation limits, actual exposure, compliance status for each asset class,
        and any detected breaches or excessive cash holdings.
    """
    analysis = await check_mandate_compliance(identifier)
    return _serialize(analysis)


@tool
async def get_fund_sector_allocation_tool(identifier: str) -> dict[str, Any]:
    """Get the current sector breakdown and sector concentration for a mutual fund.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Total sectors count, Top 3 and Top 5 sector concentration percentages,
        and sorted sector weights.
    """
    analysis = await get_sector_allocation(identifier)
    return _serialize(analysis)


@tool
async def get_sector_rotation_trends_tool(identifier: str) -> dict[str, Any]:
    """Analyze historical sector changes to identify macro sector rotation by the fund manager.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Expanding sectors (where allocation has systematically increased) vs contracting sectors
        (where allocation has been reduced) across historical rebalance dates.
    """
    analysis = await get_sector_rotation_trends(identifier)
    return _serialize(analysis)


@tool
async def get_fund_peer_comparison_tool(identifier: str) -> dict[str, Any]:
    """Compare the fund against its direct category peers on returns, expense ratio, and category ranks.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Comparative matrix with peer names, 1Y return, 3Y CAGR, Life CAGR, expense ratios,
        and the fund's rank within the peer group.
    """
    analysis = await get_peer_comparison(identifier)
    return _serialize(analysis)


@tool
async def get_fund_managers_info_tool(identifier: str) -> dict[str, Any]:
    """Get detailed information on fund managers, including qualifications, experience, and workload.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Manager names, qualifications, years of experience, cumulative AUM overseen,
        count of other schemes managed, and sample schemes under management.
    """
    analysis = await get_fund_managers_analysis(identifier)
    return _serialize(analysis)


@tool
async def get_fund_cost_and_tax_tool(identifier: str) -> dict[str, Any]:
    """Get fee structure, expense ratio comparison, exit load rules, and taxation implications.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Expense ratio vs category average, cost advantage in basis points,
        exit load penalty schedule & holding horizon, and capital gains tax rules (STCG/LTCG).
    """
    analysis = await get_cost_and_tax_profile(identifier)
    return _serialize(analysis)


@tool
async def get_fund_health_audit_tool(identifier: str) -> dict[str, Any]:
    """Perform a health audit covering the 5 scorecard pillars and underlying portfolio red flags.

    Args:
        identifier: Mutual fund ISIN, TickerTape slug, or MFID.

    Returns:
        Performance, Risk, Cost, Composition, and Red flag scorecard tags, plus total red flag counts.
    """
    analysis = await get_fund_health_audit(identifier)
    return _serialize(analysis)


@tool
async def analyze_fund_tool(identifier: str) -> dict[str, Any]:
    """Master tool: Perform a comprehensive 360-degree audit and due-diligence report on a mutual fund.

    Use this tool when you need a complete initial overview covering returns, risk ratios,
    top holdings, top sectors, expense ratio advantage, and health scorecard in a single call.

    Args:
        identifier: Mutual fund ISIN (e.g. 'INF966L01721'), TickerTape slug, or MFID.

    Returns:
        Consolidated audit report combining scheme overview, multi-horizon returns, risk ratios,
        top holdings, top sectors, cost analysis, and health scorecard.
    """
    analysis = await analyze_fund_comprehensive(identifier)
    return _serialize(analysis)


fund_tools = [
    analyze_fund_tool,
    get_fund_overview_tool,
    get_fund_trailing_returns_tool,
    get_fund_cagr_history_tool,
    get_fund_risk_metrics_tool,
    get_fund_valuation_tool,
    get_fund_top_holdings_tool,
    get_fund_portfolio_activity_tool,
    search_stock_in_fund_tool,
    get_fund_asset_allocation_tool,
    check_fund_mandate_compliance_tool,
    get_fund_sector_allocation_tool,
    get_sector_rotation_trends_tool,
    get_fund_peer_comparison_tool,
    get_fund_managers_info_tool,
    get_fund_cost_and_tax_tool,
    get_fund_health_audit_tool,
]
