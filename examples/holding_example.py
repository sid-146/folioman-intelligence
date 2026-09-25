import asyncio
from folioman_intelligence.analytics.portfolio import holding_details


async def main(isin: str):
    response = await holding_details(1, 8)
    print(response)


if __name__ == "__main__":
    asyncio.run(main("INF966L01689"))
