import asyncio

from pprint import pprint
from folioman_intelligence.analytics.portfolio import (
    get_isin,
    get_top_holdings_by_invested,
    get_top_holdings_by_returns,
    get_asset_allocation,
    get_sector_exposure,
    get_portfolio_volatility,
    analyze_portfolio,
    holding_details,
    portfolio_risk_analyse,
)


async def run():
    investor_id = 1
    security_id = 1

    print("==" * 40)
    print("Example: `get_isin`")
    isin = await get_isin(investor_id, security_id)
    print(f"ISIN: {isin}")
    print("==" * 40)
    print()

    print("Example: `get_top_holdings_by_invested`")
    top_holdings = await get_top_holdings_by_invested(investor_id)
    pprint(top_holdings)
    print("==" * 40)
    print()

    print("Example: `get_top_holdings_by_returns`")
    top_holdings = await get_top_holdings_by_returns(investor_id)
    pprint(top_holdings)
    print("==" * 40)
    print()

    print("Example: `get_asset_allocation`")
    allocations = await get_asset_allocation(investor_id)
    pprint(allocations)
    print("==" * 40)
    print()

    print("Example: `get_sector_exposure`")
    exposure = await get_sector_exposure(investor_id)
    pprint(exposure)
    print("==" * 40)
    print()

    print("Example: `get_portfolio_volatility`")
    volatility = await get_portfolio_volatility(investor_id)
    pprint(volatility)
    print("==" * 40)
    print()

    print("Example: `analyze_portfolio`")
    analysis = await analyze_portfolio(investor_id)
    pprint(analysis)
    print("==" * 40)
    print()

    print("Example: `holding_details`")
    holding_detail = await holding_details(investor_id, security_id)
    pprint(holding_detail)
    print("==" * 40)
    print()

    print("Example: `portfolio_risk_analyse`")
    risk = await portfolio_risk_analyse(investor_id)
    pprint(risk)
    print("==" * 40)
    print()


if __name__ == "__main__":
    asyncio.run(run())
