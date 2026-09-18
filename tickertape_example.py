"""Example demonstrating usage of TickerTapeClient and ISIN Lookup.

Shows:
1. Loading sitemap with persistent local caching (.cache/tickertape)
2. Fetching mutual fund details
3. Looking up and resolving mutual funds directly by ISIN (from Folioman DB)
4. Querying the persistent SQLite lookup table
5. Building / syncing the ISIN index with force refresh logic
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

        print("\n=== 2. Resolving Mutual Fund by Folioman ISIN ===")
        # Scenario: You only have an ISIN from Folioman (e.g. 'INF966L01721')
        sample_isin = "INF966L01721"
        hint = "Quant Infrastructure Fund - Direct Plan - Growth"

        # Resolves via SQLite lookup table (or sitemap keyword match if not yet indexed)
        fund = await client.mf.get_by_isin(sample_isin, hint_name=hint)
        if fund:
            print(f"Resolved ISIN {sample_isin} -> {fund.name}")
            print(f"TickerTape MFID: {fund.mf_id}, Slug: {fund.slug}")
            print(f"NAV: ₹{fund.nav}")
            if fund.meta:
                print(f"Benchmark: {fund.meta.benchmark_index}")
                print(f"Expense Ratio: {fund.meta.expense_ratio}%")
                print(f"AUM: ₹{fund.meta.aum} Cr")

        print("\n=== 3. Querying the SQLite Lookup Table directly ===")
        # Instant O(1) query by ISIN from .cache/tickertape/isin_lookup.db
        mapping = client.mf.lookup.get(sample_isin)
        if mapping:
            print(
                f"Lookup Table Match: {mapping.isin} -> {mapping.record_id} ({mapping.name})"
            )

        print(f"Total indexed schemes in SQLite: {client.mf.lookup.count()}")

        # print("\n=== 4. Indexing / Syncing (Force Refresh Example) ===")
        # # Force logic parses live sitemap, updates sitemap cache, and updates SQLite DB:
        # count = await client.mf.build_isin_index(force_refresh=True, limit=10000)
        # print(f"Indexed {count} funds into SQLite table")


if __name__ == "__main__":
    asyncio.run(main())
