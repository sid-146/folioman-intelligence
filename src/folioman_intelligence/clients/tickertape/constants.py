"""Constants required for proper execution of TickerTapeClient."""

from pathlib import Path

BASE_URL = "https://www.tickertape.in"

SITEMAP_URLS = {
    "stocks": "https://www.tickertape.in/sitemaps/stocks/sitemap.xml",
    "etf": "https://www.tickertape.in/sitemaps/etfs/sitemap.xml",
    "mf": "https://www.tickertape.in/sitemaps/mutualfunds/sitemap.xml",
    "us-stocks": "https://www.tickertape.in/sitemaps/us-stocks/sitemap.xml",
    "us-etf": "https://www.tickertape.in/sitemaps/us-etfs/sitemap.xml",
}

# Kept for backward compatibility
URLS = SITEMAP_URLS

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
}

DEFAULT_CACHE_DIR = Path(".cache/tickertape")
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
