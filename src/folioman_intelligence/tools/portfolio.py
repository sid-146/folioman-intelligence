import json

from langchain.tools import tool

from folioman_intelligence.analytics.portfolio import (
    analyze_portfolio,
    analyze_portfolio_historical,
    get_historical_capital_gains,
    get_historical_cashflows,
    get_historical_drawdown_analysis,
    holding_details,
    portfolio_risk_analyse,
)


# Todo: This returns a very large object; break down into more tools to be called by llm.
@tool
async def get_portfolio_analysis(investor_id: int = 1):
    """
    Use for portfolio performance and general portfolio summary.

    Provides:
        - portfolio value
        - invested value
        - returns
        - holding summary
        - allocation
    """
    analysis = await analyze_portfolio(investor_id)
    # Ensure Decimals and dates are JSON-serializable
    return json.loads(json.dumps(analysis, default=str))


@tool
async def get_holding_details(investor_id: int, security_id: int):
    """Get the latest calculated Holding analysis.
    Returns deterministic Holding metrics such as:
        Holding value,
        Invested value,
        returns,
        Transaction Details,
        Average Buying Price,
        Buy Transaction,
        Current Units
        ISIN.
    """
    analysis = await holding_details(investor_id, security_id)
    return json.loads(json.dumps(analysis, default=str))


@tool
async def get_portfolio_risk_analyse(investor_id: int = 1):
    """
    Use only for questions specifically about portfolio risk.

    Provides:
        - concentration
        - volatility
        - drawdown
        - diversification
        - risk exposures
    """
    analysis = await portfolio_risk_analyse(investor_id)
    return json.loads(json.dumps(analysis, default=str))


@tool
async def get_historical_portfolio_analytics(investor_id: int = 1):
    """
    Use for historical net worth trajectory, annualized CAGR, peak valuations,
    wealth generated over time, and 360-degree historical portfolio audit.
    """
    analysis = await analyze_portfolio_historical(investor_id)
    return json.loads(json.dumps(analysis, default=str))


@tool
async def get_portfolio_drawdown_analysis(investor_id: int = 1):
    """
    Use for historical drawdown analysis, maximum peak-to-trough decline (MDD),
    drawdown episodes, and recovery status over time.
    """
    analysis = await get_historical_drawdown_analysis(investor_id)
    return json.loads(json.dumps(analysis, default=str))


@tool
async def get_portfolio_cashflow_history(investor_id: int = 1):
    """
    Use for historical cash flows, SIP discipline, cumulative gross inflows/outflows,
    net cash invested, and portfolio vintage years.
    """
    analysis = await get_historical_cashflows(investor_id)
    return json.loads(json.dumps(analysis, default=str))


@tool
async def get_portfolio_tax_history(investor_id: int = 1):
    """
    Use for historical realized capital gains (STCG/LTCG) across financial years.
    """
    analysis = await get_historical_capital_gains(investor_id)
    return json.loads(json.dumps(analysis, default=str))


portfolio_tools = [
    get_portfolio_analysis,
    get_holding_details,
    get_portfolio_risk_analyse,
    get_historical_portfolio_analytics,
    get_portfolio_drawdown_analysis,
    get_portfolio_cashflow_history,
    get_portfolio_tax_history,
]
