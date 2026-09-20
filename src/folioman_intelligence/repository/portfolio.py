from folioman_intelligence.clients.folioman import FoliomanClient


class PortfolioRepository:
    def __init__(self):
        pass

    async def get_portfolio(self, investor_id: int):
        """
        Get only portfolio from the folioman.
        No calculation or anything here.

        Args:
            investor_id (int): Investor Id to search
        """
        async with FoliomanClient.from_env() as client:
            portfolio = await client.portfolio.get(investor_id)
        return portfolio

    async def get_holding(self, investor_id: int, security_id: int):
        async with FoliomanClient.from_env() as client:
            holding = await client.holdings.get(investor_id, security_id)

        return holding
