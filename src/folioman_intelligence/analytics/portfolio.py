from copy import deepcopy

from src.folioman_intelligence.repository.portfolio import PortfolioRepository


async def analyze_portfolio(investor_id: int):
    repo = PortfolioRepository()
    portfolio_data = await repo.get_portfolio(investor_id)
    analysis = deepcopy(portfolio_data)

    top_3_holding = sorted(
        analysis["holdings"], key=lambda x: x["invested_inr"] or 0, reverse=True
    )[:3]
    analysis["top_3_holdings"] = [t["name"] for t in top_3_holding]

    return analysis
