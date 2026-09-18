"""Bulk indexer for crawling sitemap URLs and populating the SQLite ISIN lookup table."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable, Optional

from folioman_intelligence.clients.tickertape.lookup.models import ISINMapping
from folioman_intelligence.clients.tickertape.lookup.table import ISINLookupTable

if TYPE_CHECKING:
    from folioman_intelligence.clients.tickertape.client import TickerTapeClient

logger = logging.getLogger(__name__)

ProgressCallback = Callable[
    [int, int, int, int], None
]  # (completed, total, successful, failed)


class ISINIndexer:
    """Crawls mutual fund pages from sitemap and populates SQLite ISIN lookup table."""

    def __init__(
        self, client: TickerTapeClient, table: Optional[ISINLookupTable] = None
    ) -> None:
        self.client = client
        self.table = table or ISINLookupTable(cache_dir=client.cache_dir)

    async def build_index(
        self,
        *,
        force_refresh: bool = False,
        concurrency: int = 5,
        delay: float = 0.5,
        limit: Optional[int] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> int:
        """Build or update the SQLite ISIN lookup table from the mutual funds sitemap.

        Force Refresh Logic:
            When force_refresh=True:
            1. Fetches live sitemap XML from TickerTape.
            2. Parses sitemap and updates the local sitemap cache (.cache/tickertape/sitemaps/mf.json).
            3. Crawls fund pages and updates the SQLite database (.cache/tickertape/isin_lookup.db).

        When force_refresh=False:
            1. Loads sitemap from local disk cache.
            2. Skips record_ids already present in SQLite database (resumable).
            3. Crawls only missing funds and inserts into SQLite database.

        Args:
            force_refresh: If True, forces live sitemap fetch, updates sitemap cache, and re-indexes.
            concurrency: Number of concurrent HTTP workers.
            delay: Delay in seconds between requests per worker to respect rate limits.
            limit: Optional maximum number of funds to process (useful for testing or batch runs).
            progress_callback: Optional callback(completed, total, successful, failed).

        Returns:
            Number of mappings successfully indexed/updated in SQLite database.
        """
        # Step 1: Get sitemap items (force_refresh updates live XML and disk cache)
        if force_refresh:
            logger.info(
                "Force refresh triggered: fetching live sitemap and updating sitemap cache..."
            )
            sitemap_items = await self.client.sitemap.refresh("mf")
        else:
            sitemap_items = await self.client.sitemap.get("mf", force_refresh=False)

        if not sitemap_items:
            logger.warning("No sitemap items found to index")
            return 0

        # Step 2: Determine items to process
        if force_refresh:
            items_to_process = sitemap_items
        else:
            existing_ids = self.table.get_all_record_ids()
            items_to_process = [
                item for item in sitemap_items if item.record_id not in existing_ids
            ]

        if limit is not None:
            items_to_process = items_to_process[:limit]

        total = len(items_to_process)
        if total == 0:
            logger.info("All sitemap items are already indexed in SQLite lookup table.")
            return 0

        logger.info(
            "Starting ISIN indexing for %d funds (concurrency=%d)...",
            total,
            concurrency,
        )

        semaphore = asyncio.Semaphore(concurrency)
        completed = 0
        successful = 0
        failed = 0
        batch: list[ISINMapping] = []
        lock = asyncio.Lock()

        async def worker(item):
            nonlocal completed, successful, failed
            async with semaphore:
                try:
                    fund = await self.client.mf.get(item.url)
                    if fund.isin:
                        raw_slug = fund.slug or item.url
                        clean_slug = raw_slug.split("/mutualfunds/")[-1].lstrip("/")

                        sec_info = fund.security_info
                        meta = fund.meta

                        mapping = ISINMapping(
                            isin=fund.isin.strip().upper(),
                            record_id=fund.mf_id or item.record_id,
                            slug=clean_slug,
                            name=fund.name,
                            amc=(meta.amc if meta else None)
                            or (sec_info.amc if sec_info else None),
                            amc_code=sec_info.amc_code if sec_info else None,
                            sector=(sec_info.sector if sec_info else None)
                            or (meta.sector if meta else None),
                            subsector=(sec_info.subsector if sec_info else None)
                            or (meta.subsector if meta else None),
                            fund_type=meta.fund_type if meta else None,
                            fund_class=meta.type if meta else None,
                            plan=meta.plan if meta else None,
                            option=(sec_info.option if sec_info else None)
                            or (meta.option if meta else None),
                            risk_level=meta.risk_classification if meta else None,
                            benchmark=meta.benchmark_index if meta else None,
                            url=item.url,
                            nav=fund.nav,
                        )

                        async with lock:
                            batch.append(mapping)
                            successful += 1
                            if len(batch) >= 20:
                                self.table.upsert_batch(batch)
                                batch.clear()
                    else:
                        async with lock:
                            failed += 1
                except Exception as exc:
                    logger.debug("Failed to index %s: %s", item.url, exc)
                    async with lock:
                        failed += 1
                finally:
                    async with lock:
                        completed += 1
                        if progress_callback:
                            try:
                                progress_callback(completed, total, successful, failed)
                            except Exception:
                                pass

                if delay > 0:
                    await asyncio.sleep(delay)

        # Run workers concurrently
        tasks = [asyncio.create_task(worker(item)) for item in items_to_process]
        await asyncio.gather(*tasks)

        # Flush remaining batch
        if batch:
            self.table.upsert_batch(batch)
            batch.clear()

        logger.info(
            "Indexing completed: %d/%d successfully saved to SQLite (%d failed)",
            successful,
            total,
            failed,
        )
        return successful
