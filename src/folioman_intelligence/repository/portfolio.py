from src.folioman_intelligence.clients.folioman import FoliomanClient


class PortfolioRepository:
    def __init__(self):
        pass

    async def get_portfolio(self, investor_id: int):
        async with FoliomanClient.from_env() as client:
            portfolio = await client.portfolio.get(investor_id)

        total_invested = sum(
            [
                holding.invested_inr
                for holding in portfolio.holdings
                if holding.invested_inr
            ]
        )
        period_returns = [
            {
                "period": pr.period,
                "absolute_return": pr.absolute,
            }
            for pr in portfolio.period_returns
        ]
        holdings = [
            {
                "name": holding.name,
                "category": holding.category,
                "units": holding.units,
                "value_inr": holding.value_inr,
                "invested_inr": holding.invested_inr,
                "return_pct": holding.return_pct * 100 if holding.return_pct else None,
                "contribution_to_portfolio (invested_inr / total_invested)": (
                    holding.invested_inr / total_invested
                    if holding.invested_inr and total_invested
                    else 0
                )
                * 100,
                "xirr": holding.xirr * 100 if holding.xirr else 0,
            }
            for holding in portfolio.holdings
        ]

        portfolio_data = {
            "currency": "INR",
            "total_value": portfolio.total_inr,
            "total_invested": total_invested,
            "absolute_returns": portfolio.total_inr - total_invested,
            "navs_as_of": portfolio.navs_as_of,
            "category_mix": [
                category.model_dump(mode="json") for category in portfolio.category_mix
            ],
            "xirr": portfolio.xirr,
            "period_returns": period_returns,
            "holdings": holdings,
        }
        return portfolio_data
