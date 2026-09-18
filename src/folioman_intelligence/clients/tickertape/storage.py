"""Storage and caching for TickerTape client data."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Optional

from folioman_intelligence.clients.tickertape.constants import DEFAULT_CACHE_DIR
from folioman_intelligence.clients.tickertape.models import SitemapCacheData, SitemapURL

logger = logging.getLogger(__name__)


class SitemapCacheManager:
    """Manages persistent caching of parsed sitemap records on disk.

    Ensures that parsed sitemap entries are stored locally and only
    re-fetched when an explicit refresh is requested.
    """

    def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR) -> None:
        self.cache_dir = Path(cache_dir)
        self.sitemaps_dir = self.cache_dir / "sitemaps"
        self.sitemaps_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, category: str) -> Path:
        """Return the JSON file path for a sitemap category."""
        clean_category = category.lower().strip().replace("/", "_").replace("\\", "_")
        return self.sitemaps_dir / f"{clean_category}.json"

    def exists(self, category: str) -> bool:
        """Check if a valid, non-empty cache exists for category."""
        path = self.get_cache_path(category)
        return path.is_file() and path.stat().st_size > 0

    def load(self, category: str) -> Optional[list[SitemapURL]]:
        """Load cached sitemap URLs for category if present.

        Returns None if cache does not exist or is corrupted.
        """
        path = self.get_cache_path(category)
        if not path.is_file():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            cache_data = SitemapCacheData.model_validate(raw)
            return cache_data.items
        except Exception as exc:
            logger.warning(
                "Failed to load sitemap cache for %s from %s: %s", category, path, exc
            )
            return None

    def save(self, category: str, items: list[SitemapURL]) -> Path:
        """Atomically persist parsed sitemap URLs to disk.

        Returns the path to the saved cache file.
        """
        path = self.get_cache_path(category)
        cache_data = SitemapCacheData(
            category=category,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            count=len(items),
            items=items,
        )

        # Atomic write via temporary file
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(cache_data.model_dump(), f, indent=2)

        temp_path.replace(path)
        logger.info(
            "Persisted %d sitemap items for '%s' to %s", len(items), category, path
        )
        return path

    def clear(self, category: Optional[str] = None) -> None:
        """Clear cache for a specific category or all sitemap categories."""
        if category:
            path = self.get_cache_path(category)
            if path.exists():
                path.unlink()
                logger.info("Removed sitemap cache for '%s' at %s", category, path)
        else:
            for file in self.sitemaps_dir.glob("*.json"):
                file.unlink()
            logger.info("Cleared all sitemap caches in %s", self.sitemaps_dir)
