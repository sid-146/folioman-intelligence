import asyncio
from folioman_intelligence import FoliomanClient, settings


async def main():
    # Can use FoliomanClient.from_env() or pass credentials directly:
    async with FoliomanClient(
        base_url=settings.folioman_url,
        username=settings.folioman_username,
        password=settings.folioman_password,
    ) as client:
        # 1. Investors
        investors = await client.investors.list()
        investor = await client.investors.get(investors[0].id)
        print(
            f"Investor: {investor.name}, Masked PAN: {investor.pan_masked}", end="\n\n"
        )

        # 2. Portfolio Summary & Holdings
        summary = await client.portfolio.get(investor.id)
        print(f"Net Worth: INR {summary.total_inr}", end="\n\n")

        holdings = await client.holdings.list(investor.id)
        for h in holdings:
            print(f"- {h.name}: {h.units} units (₹{h.value_inr})", end="\n\n")

        # 3. Scheme Details
        if holdings:
            scheme = await client.holdings.get(investor.id, holdings[0].security_id)
            print(
                f"ISIN: {scheme.security.isin}, NAV Points: {len(scheme.nav_history)}",
            )

        # 4. Transactions
        txns = await client.transactions.list(investor.id)
        print(f"Transactions recorded: {len(txns)}", end="\n\n")

        # 5. Valuation Time-Series & Status
        status = await client.valuations.status(investor.id)
        print(f"Valuation Status: {status.status}", end="\n\n")

        series = await client.valuations.list(investor.id, granularity="monthly")
        print(f"Valuation data points: {len(series.points)}", end="\n\n")

        # 6. Capital Gains
        gains = await client.capital_gains.list(investor.id)
        if gains:
            report = await client.capital_gains.get(investor.id, fy=gains[-1].fy)
            print(
                f"FY {report.fy} LTCG: INR {report.ltcg_total}, STCG: INR {report.stcg_total}",
                end="\n\n",
            )


if __name__ == "__main__":
    asyncio.run(main())
