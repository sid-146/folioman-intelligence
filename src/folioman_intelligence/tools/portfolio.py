import json

from langchain.tools import tool

from src.folioman_intelligence.analytics.portfolio import (
    analyze_portfolio,
    holding_details,
)


# Todo: This returns a very large object; break down into more tools to be called by llm.
@tool
async def get_portfolio_analysis(investor_id: int = 1):
    """Get the latest calculated portfolio analysis.
    Returns deterministic portfolio metrics such as:
        portfolio value,
        invested value,
        returns,
        holdings,
        allocation,
        concentration,
        gainers and losers.
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


portfolio_tools = [get_portfolio_analysis, get_holding_details]
