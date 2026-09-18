"""Example demonstrating usage of TickerTapeClient.

Shows:
1. Loading sitemap with persistent local caching (.cache/tickertape)
2. Explicitly refreshing sitemap
3. Fetching mutual fund details and extracting ISIN
"""

import asyncio
from folioman_intelligence import TickerTapeClient


async def main():
    async with TickerTapeClient() as client:
        print("=== 1. Getting Mutual Funds Sitemap (cached in .cache/tickertape) ===")
        # Uses local cache if available; only fetches live XML on first run or forced refresh
        sitemap_items = await client.sitemap.get("mf")
        print(f"Total Mutual Fund sitemap URLs found: {len(sitemap_items)}")
        if sitemap_items:
            first = sitemap_items[0]
            print(f"First item: ID={first.record_id}, URL={first.url}")

        print("\n=== 2. Fetching Single Mutual Fund Details ===")
        # Fetch fund details by slug or MFID
        sample_slug = "quant-infrastructure-fund-M_QUNG"
        fund = await client.mf.get(sample_slug)
        print(f"Fund Name: {fund.name}")
        print(f"ISIN: {fund.isin}")
        print(f"NAV: {fund.nav}")
        if fund.meta:
            print(f"Benchmark: {fund.meta.benchmark_index}")
            print(f"Expense Ratio: {fund.meta.expense_ratio}%")
            print(f"AUM: ₹{fund.meta.aum} Cr")

        print("\n=== 3. Convenience ISIN Extraction ===")
        isin = await client.mf.get_isin(sample_slug)
        print(f"ISIN via get_isin(): {isin}")

        # print("\n=== 4. Explicit Sitemap Refresh (Bypasses Cache) ===")
        # refreshed_items = await client.sitemap.refresh("mf")
        # print(f"Refreshed sitemap count: {len(refreshed_items)}")


if __name__ == "__main__":
    asyncio.run(main())
